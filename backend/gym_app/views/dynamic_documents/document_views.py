import io
import re
import os
import logging
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import FileResponse, Http404
from django.template.loader import get_template
from PIL import Image
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from bs4 import BeautifulSoup, NavigableString
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from django.db.models import Prefetch
from gym_app.models.dynamic_document import (
    DynamicDocument, RecentDocument, DocumentSignature,
    DocumentVisibilityPermission, DocumentUsabilityPermission, Tag,
)
from gym_app.serializers.dynamic_document import DynamicDocumentSerializer, DynamicDocumentListSerializer, RecentDocumentSerializer
from gym_app.utils.documents import (
    normalize_fragmented_variables,
    sanitize_soup_for_export,
    render_document_pdf,
    get_letterhead_for_document,
    get_letterhead_word_template,
    ensure_letterhead_snapshot,
)
from django.utils import timezone
from .permissions import (
    apply_visibility_filter,
    can_modify_minuta,
    require_document_visibility,
    require_document_visibility_by_id,
    require_document_usability,
)

logger = logging.getLogger(__name__)

# States in which a document is locked for any write operations (content, letterhead, etc.)
LOCKED_STATES = frozenset(['PendingSignatures', 'FullySigned'])
MAX_DOCUMENT_PAGE_SIZE = 100


def get_optimized_document_queryset(base_qs=None):
    """Return a DynamicDocument queryset with all relations needed by DynamicDocumentSerializer.

    Every view that serialises documents with DynamicDocumentSerializer (or its
    list variant) MUST use this helper so that N+1 queries are avoided.
    """
    qs = base_qs if base_qs is not None else DynamicDocument.objects.all()
    return qs.select_related(
        'created_by', 'assigned_to', 'managed_by', 'formalized_by'
    ).prefetch_related(
        'variables',
        Prefetch('tags', queryset=Tag.objects.select_related('created_by')),
        Prefetch('signatures', queryset=DocumentSignature.objects.select_related('signer')),
        'visibility_permissions',
        'usability_permissions',
        'relationships_as_source',
        'relationships_as_target',
        'payment_records',
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_dynamic_document(request):
    """
    Create a new dynamic document with optional permissions.
    
    You can now create documents and set permissions in a single API call:
    
    Basic fields:
    - title, content, state, is_public, requires_signature
    - variables: array of document variables
    - tags: array of tag IDs
    - signers: array of user IDs for signatures
    
    Permission fields (optional):
    - visibility_user_ids: array of user IDs who can view the document
    - usability_user_ids: array of user IDs who can use/edit the document
    
    Example payload:
    {
        "title": "Contract Template",
        "content": "Document content...",
        "is_public": false,
        "visibility_user_ids": [5, 6, 7, 8],
        "usability_user_ids": [5, 6],
        "variables": [...],
        "tags": [1, 2]
    }
    """
    # If it's a creation from the client, assign `assigned_to`.
    if request.data.get('state') in ['Progress', 'Completed'] and not request.data.get('assigned_to'):
        request.data['assigned_to'] = request.user.id

    # Validate and save the document
    serializer = DynamicDocumentSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        instance = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_dynamic_documents(request):
    """
    Get a list of all dynamic documents.
    """
    # Base queryset with all related data needed by the serializer.
    # Uses shared helper so that N+1 queries are avoided.
    queryset = get_optimized_document_queryset().order_by('-updated_at')

    # Queryset-level visibility filtering — lawyers see everything,
    # non-lawyers see only documents they are permitted to view.
    # This replaces the old post-serialization filter_documents_by_visibility
    # decorator, eliminating a redundant DB round-trip.
    queryset = apply_visibility_filter(queryset, request.user)

    # Optional filters used by the frontend store
    state = request.query_params.get('state')
    # Optional multi-state filter: comma-separated list of states, e.g. "Draft,Published"
    states_param = request.query_params.get('states')
    client_id = request.query_params.get('client_id')
    lawyer_id = request.query_params.get('lawyer_id')

    # If a multi-state filter is provided, it takes precedence over the single state filter
    if states_param:
        raw_states = [s.strip() for s in states_param.split(',') if s.strip()]
        if raw_states:
            queryset = queryset.filter(state__in=raw_states)
    elif state:
        queryset = queryset.filter(state=state)

    if client_id:
        queryset = queryset.filter(assigned_to_id=client_id)

    if lawyer_id:
        # Scoped by the CURRENT manager (created OR reassigned to). Backfill
        # makes this equivalent to created_by for pre-feature data; after a
        # transfer, minutas move between lawyers' "Mías" scope correctly.
        queryset = queryset.filter(managed_by_id=lawyer_id)

    # Filter minutas flagged as collaboratively editable ("Compartidas" scope)
    shared = request.query_params.get('shared', '')
    if shared.lower() in ('1', 'true'):
        queryset = queryset.filter(allow_shared_edit=True)

    # When true, restrict results to documents where the requesting user is
    # the creator (created_by) OR a signer (has a DocumentSignature row).
    user_related = request.query_params.get('user_related', '').lower() in ('true', '1')
    # When true (only meaningful with user_related), require the signer to
    # have signed=True.  Used by the FullySigned tab to exclude unsigned signers.
    signer_signed = request.query_params.get('signer_signed', '').lower() in ('true', '1')
    # When true, return only documents without an assigned client.
    unassigned = request.query_params.get('unassigned', '').lower() in ('true', '1')

    if user_related:
        signer_q = Q(signatures__signer=request.user)
        if signer_signed:
            signer_q = Q(signatures__signer=request.user, signatures__signed=True)
        queryset = queryset.filter(Q(created_by=request.user) | signer_q).distinct()

    if unassigned:
        queryset = queryset.filter(assigned_to__isnull=True)

    # Full-text search across title, variable values, assigned user name,
    # and the creator's name (so lawyers can search shared minutas by author).
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(variables__value__icontains=search)
            | Q(assigned_to__first_name__icontains=search)
            | Q(assigned_to__last_name__icontains=search)
            | Q(created_by__first_name__icontains=search)
            | Q(created_by__last_name__icontains=search)
        ).distinct()

    # Filter by tag
    tag_id = request.query_params.get('tag_id')
    if tag_id:
        try:
            queryset = queryset.filter(tags__id=int(tag_id))
        except (TypeError, ValueError):
            pass  # Ignore invalid tag_id values

    # Date range filter (subscription date variable, falling back to created_at)
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from or date_to:
        # IDs of documents that have a subscription_date variable within range
        date_q = Q(variables__summary_field='subscription_date')
        if date_from:
            date_q &= Q(variables__value__gte=date_from)
        if date_to:
            date_q &= Q(variables__value__lte=date_to)

        docs_with_date_var = queryset.filter(date_q).values_list('pk', flat=True)

        # Fallback: documents without a subscription_date variable use created_at
        no_date_var_q = ~Q(variables__summary_field='subscription_date')
        fallback_q = no_date_var_q
        if date_from:
            fallback_q &= Q(created_at__date__gte=date_from)
        if date_to:
            fallback_q &= Q(created_at__date__lte=date_to)

        docs_fallback = queryset.filter(fallback_q).values_list('pk', flat=True)

        queryset = queryset.filter(pk__in=set(docs_with_date_var) | set(docs_fallback))

    # Sort parameter
    sort_by = request.query_params.get('sort_by', 'recent')
    # Lower() keeps name ordering case-insensitive on every backend (MySQL's
    # _ci collation already behaves this way; SQLite's binary collation does not).
    sort_map = {
        'recent': '-updated_at',
        'oldest': 'updated_at',
        'name-asc': Lower('title').asc(),
        'name-desc': Lower('title').desc(),
    }
    order_field = sort_map.get(sort_by, '-updated_at')
    queryset = queryset.order_by(order_field)

    # Pagination parameters (fallback to sensible defaults)
    try:
        page = int(request.query_params.get('page', 1))
    except (TypeError, ValueError):
        page = 1

    try:
        limit = int(request.query_params.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10

    if limit <= 0:
        limit = 10
    limit = min(limit, MAX_DOCUMENT_PAGE_SIZE)

    paginator = Paginator(queryset, limit)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:  # pragma: no cover – lines 106-109 already convert page to int
        page_obj = paginator.page(1)
        page = 1
    except EmptyPage:
        # If page is out of range, return last page
        page_obj = paginator.page(paginator.num_pages)
        page = paginator.num_pages

    serializer = DynamicDocumentListSerializer(page_obj.object_list, many=True, context={'request': request})

    logger.debug(
        "list_dynamic_documents: user=%s role=%s page=%s limit=%s state=%s client_id=%s lawyer_id=%s search=%s total_items=%s items_on_page=%s total_pages=%s",
        getattr(request.user, "id", None),
        getattr(request.user, "role", None),
        page,
        limit,
        state,
        client_id,
        lawyer_id,
        search,
        paginator.count,
        len(page_obj.object_list),
        paginator.num_pages,
    )

    paginated_response = {
        'items': serializer.data,
        'totalItems': paginator.count,
        'totalPages': paginator.num_pages,
        'currentPage': page,
    }

    return Response(paginated_response, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def get_dynamic_document(request, pk):
    """
    Get a specific dynamic document by ID.
    """
    try:
        document = get_optimized_document_queryset().get(pk=pk)
        
        # Ensure variables have select_options initialized
        for variable in document.variables.all():
            if variable.field_type == 'select' and not variable.select_options:
                variable.select_options = []
                variable.save()
        
        serializer = DynamicDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response({'detail': 'Dynamic document not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@require_document_usability('usability')
def update_dynamic_document(request, pk):
    """
    Update an existing dynamic document with optional permissions.
    
    You can now update documents and modify permissions in a single API call:
    
    Basic fields that can be updated:
    - title, content, state, is_public, requires_signature
    - variables: array of document variables (replaces existing)
    - tags: array of tag IDs (replaces existing)
    - signers: array of user IDs for signatures (adds new ones)
    
    Permission fields (optional - replaces existing permissions):
    - visibility_user_ids: array of user IDs who can view the document
    - usability_user_ids: array of user IDs who can use/edit the document
    
    Example payload:
    {
        "title": "Updated Contract Template",
        "is_public": false,
        "visibility_user_ids": [5, 6, 8, 9],
        "usability_user_ids": [5, 6],
        "variables": [...]
    }
    
    Note: Providing permission fields will REPLACE existing permissions.
    """
    try:
        # Get the document and load its related variables
        document = DynamicDocument.objects.prefetch_related('variables', 'tags').get(pk=pk)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response({'detail': 'Dynamic document not found.'}, status=status.HTTP_404_NOT_FOUND)

    if document.state in LOCKED_STATES:
        return Response(
            {'detail': 'No se puede modificar un documento en estado de firma.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if not can_modify_minuta(document, request.user, request.data):
        return Response(
            {'detail': 'Solo el creador de la minuta puede realizar esta acción.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Prevent modifying the `created_by` field (audit) and `managed_by`
    # (only the admin reassignment endpoint may change management).
    if 'created_by' in request.data:
        request.data.pop('created_by')
    if 'managed_by' in request.data:
        request.data.pop('managed_by')

    # Validate and update the document
    serializer = DynamicDocumentSerializer(document, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        instance = serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_document_usability('owner')
def delete_dynamic_document(request, pk):
    """
    Delete a dynamic document.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response({'detail': 'Dynamic document not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_modify_minuta(document, request.user):
        return Response(
            {'detail': 'Solo el creador de la minuta puede eliminarla.'},
            status=status.HTTP_403_FORBIDDEN
        )

    document.delete()
    return Response({'detail': 'Dynamic document deleted successfully.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def download_dynamic_document_pdf(request, pk, for_version=False):
    """
    Generates and returns a PDF file for a given document using WeasyPrint.

    This function retrieves a document from the database, replaces dynamic variables within 
    its content, applies a predefined font style, and converts the content into a properly 
    formatted PDF file. The generated PDF is then returned as a downloadable response.

    Parameters:
        request (HttpRequest): The request object.
        pk (int): The primary key of the document to be retrieved.
        for_version (bool): If True, returns the PDF buffer instead of a FileResponse (for version creation).

    Returns:
        FileResponse: A downloadable PDF file response.
        BytesIO: PDF buffer if for_version is True.
        Response: A JSON response with an error message if an exception occurs.

    Raises:
        FileNotFoundError: If any of the required font files are missing.
        Exception: If there is an error during the HTML-to-PDF conversion or any other 
                   unexpected issue.
    """
    try:
        # Retrieve the document from the database
        document = DynamicDocument.objects.select_related(
            'created_by', 'formalized_by'
        ).prefetch_related('variables', 'signatures__signer', 'tags').get(pk=pk)

        # Normalize any {{ }} patterns that TinyMCE may have split across HTML tags
        processed_content = normalize_fragmented_variables(document.content)

        # Replace variables within the content (use formatted values when available).
        # Use a regex so we tolerate whitespace inside ``{{ name }}`` markers that
        # the editor or paste-postprocessing may have introduced.
        for variable in document.variables.all():
            try:
                replacement_value = variable.get_formatted_value()
            except AttributeError:  # pragma: no cover – defensive fallback for missing method
                replacement_value = variable.value or ""
            pattern = re.compile(
                r'\{\{\s*' + re.escape(variable.name_en) + r'\s*\}\}'
            )
            processed_content = pattern.sub(replacement_value or "", processed_content)

        # Parse once; sanitize Word-pasted markup in place so the renderer
        # preserves table formatting and alignment.
        soup = sanitize_soup_for_export(BeautifulSoup(processed_content, 'html.parser'))

        ensure_letterhead_snapshot(document)
        letterhead_image = get_letterhead_for_document(
            document, fallback_user=request.user
        )

        # Render with WeasyPrint (browser-grade CSS/table layout → matches editor)
        pdf_buffer = io.BytesIO(render_document_pdf(
            title=document.title,
            body_html=str(soup),
            letterhead_image=letterhead_image,
            top_padding="1cm",
        ))

        # If this is for a version, return the buffer
        if for_version:  # pragma: no cover – not currently invoked with True
            return pdf_buffer

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=f"{document.title}.pdf",
            content_type='application/pdf'
        )

    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
    except FileNotFoundError as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        # Log the full traceback: the broad except otherwise returns a bare 500
        # to the client and Django logs only "Internal Server Error" with no
        # stack, making PDF failures undiagnosable without a manual repro.
        logger.exception("Error generating PDF for doc_id=%s: %s", pk, e)
        return Response({'detail': f'Error generating PDF: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def download_dynamic_document_word(request, pk):
    """
    Generates and returns a Word (.docx) file for the given document using python-docx.
    The document content is retrieved from the database, and its variables are dynamically replaced.
    The content is then parsed from HTML using BeautifulSoup and converted into a Word document,
    applying appropriate formatting, including headings, paragraphs, and styles.
    
    Parameters:
        request (HttpRequest): The HTTP request object.
        pk (int): The primary key of the document to be retrieved.
    
    Returns:
        FileResponse: A response containing the generated Word document.
    """
    try:
        # Retrieve the document from the database
        document = DynamicDocument.objects.select_related(
            'created_by', 'formalized_by'
        ).prefetch_related('variables', 'signatures__signer', 'tags').get(pk=pk)

        # Normalize any {{ }} patterns that TinyMCE may have split across HTML tags
        normalized_content = normalize_fragmented_variables(document.content)

        # Replace variables dynamically
        def replace_variables(text):
            processed_text = text
            for variable in document.variables.all():
                pattern = re.compile(rf"{{{{{variable.name_en}}}}}")
                try:
                    replacement_value = variable.get_formatted_value()
                except AttributeError:  # pragma: no cover – defensive fallback for missing method
                    replacement_value = variable.value or ""
                processed_text = pattern.sub(replacement_value or "", processed_text)
            return processed_text

        processed_content = replace_variables(normalized_content)
        
        # Render HTML with template
        template = get_template("pdf_template.html")
        html_content = template.render({"content": processed_content})

        # Parse HTML with BeautifulSoup and clean paste-from-Word artifacts
        # (empty block runs, <o:p> tags, excessive inline margins) so the
        # docx output keeps the same vertical rhythm as the editor and PDF.
        soup = sanitize_soup_for_export(BeautifulSoup(html_content, "html.parser"))

        from docx.shared import Inches, Pt
        from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

        ensure_letterhead_snapshot(document)
        use_word_template = False

        word_template = get_letterhead_word_template(
            document, fallback_user=request.user,
        )

        if word_template and hasattr(word_template, 'path') and os.path.exists(word_template.path):
            try:
                doc = Document(word_template.path)
                use_word_template = True
            except Exception as e:
                logger.warning(
                    "Failed to open Word letterhead template for doc_id=%s: %s",
                    document.pk, e,
                )
                doc = Document()
        else:
            doc = Document()

        # If we are using a blank document, configure Letter page size and margins
        section = doc.sections[0]
        if not use_word_template:
            section.page_width = Inches(8.5)   # 8.5 inches width
            section.page_height = Inches(11)   # 11 inches height (Letter/Carta)
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        
        # Configure default font for the document to Calibri
        font_name = 'Calibri'
        
        # Set default font for the document
        style = doc.styles['Normal']
        style.font.name = font_name
        
        # Configure other default styles to use Calibri
        for style_name in ['Heading1', 'Heading2', 'Heading3', 'Heading4', 'Heading5', 'Heading6']:
            if style_name in doc.styles:
                doc.styles[style_name].font.name = font_name

        # Track whether we've already placed the first body paragraph
        first_body_paragraph_used = False

        # Mirrors the PDF stylesheet (p { margin: 0 0 6pt 0; line-height: 1.35 })
        # and the editor content_style so all three renderers agree on spacing.
        def apply_body_paragraph_spacing(paragraph):
            pf = paragraph.paragraph_format
            pf.space_before = Pt(0)
            pf.space_after = Pt(6)
            if pf.line_spacing is None:
                pf.line_spacing = 1.35

        # Track table adjacency: two docx tables with nothing between them
        # auto-merge when opened in Word, so a spacer paragraph is required.
        last_block_was_table = False

        # Process HTML content
        # Include both <p> and <div> tags as paragraph blocks so that
        # templates that wrap content in <div> elements are still rendered.
        block_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "hr", "table"]
        for tag in soup.find_all(block_tags):
            # find_all is recursive: skip blocks whose content is emitted by
            # another branch, otherwise text gets duplicated in the output.
            if tag.find_parent("table"):
                # Cell content is handled by the <table> branch below.
                continue
            if tag.name in ("p", "div") and tag.find(block_tags):
                # Container block (e.g. the template wrapper <div>): its block
                # children are matched by find_all on their own iteration.
                continue

            if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(tag.name[1])
                heading = doc.add_heading(tag.get_text().strip(), level=level)
                last_block_was_table = False

                # Ensure heading uses Calibri
                for run in heading.runs:
                    run.font.name = font_name

            elif tag.name in ["p", "div"]:
                last_block_was_table = False

                # For the very first body paragraph when using a template that has
                # only the default empty paragraph, reuse that paragraph instead
                # of creating a new one. This avoids starting on the "second" line
                # while preserving any content the user may have added to the body.
                if (
                    use_word_template
                    and not first_body_paragraph_used
                    and len(doc.paragraphs) == 1
                    and not doc.paragraphs[0].text.strip()
                ):  # pragma: no cover – word template first paragraph reuse
                    paragraph = doc.paragraphs[0]
                else:
                    paragraph = doc.add_paragraph()

                first_body_paragraph_used = True
                apply_body_paragraph_spacing(paragraph)

                if tag.get_text().strip() == "":
                    # Keep the (single, post-sanitize) intentional blank line as
                    # an empty paragraph — it also prevents adjacent docx tables
                    # from auto-merging in Word.
                    continue

                # Apply paragraph style attributes
                style = tag.get("style", "")

                if "text-align: center" in style:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                elif "text-align: right" in style:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
                elif "text-align: left" in style:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
                elif "text-align: justify" in style:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

                if "padding-left" in style:
                    try:
                        padding_value = int(style.split("padding-left:")[1].split("px")[0].strip())
                        paragraph.paragraph_format.left_indent = Pt(padding_value)
                    except (ValueError, IndexError) as e:
                        pass

                if "line-height" in style:
                    try:
                        line_height = float(style.split("line-height:")[1].split(";")[0].strip())
                        paragraph.paragraph_format.line_spacing = line_height
                    except (ValueError, IndexError) as e:
                        pass

                # Define a helper function to apply styles to runs
                def apply_styles_to_run(run, element):
                    """Apply appropriate styles to a run based on the element and its style attributes"""
                    try:
                        from docx.shared import RGBColor
                        
                        element_name = element.name if hasattr(element, 'name') else None
                        element_style = element.get("style", "") if hasattr(element, 'get') else ""
                        
                        # Always apply Calibri font
                        run.font.name = font_name
                        
                        # Apply styles based on element type
                        if element_name == "strong" or element_name == "b":
                            run.bold = True
                        
                        if element_name == "em" or element_name == "i":
                            run.italic = True
                        
                        if element_name == "s" or "text-decoration: line-through" in element_style:
                            run.font.strike = True
                        
                        if element_name == "u" or "text-decoration: underline" in element_style:
                            run.underline = True
                        
                        # Apply span-specific styles
                        if element_name == "span":
                            if "text-decoration: underline" in element_style:
                                run.underline = True
                                
                            if "text-decoration: line-through" in element_style:
                                run.font.strike = True
                                
                            if "font-size" in element_style:
                                try:
                                    font_size_part = element_style.split("font-size:")[1].split(";")[0].strip()
                                    if "pt" in font_size_part:
                                        font_size = int(font_size_part.split("pt")[0].strip())
                                        run.font.size = Pt(font_size)
                                except (ValueError, IndexError) as e:  # pragma: no cover
                                    pass
                                    
                            if "color:" in element_style or "color :" in element_style:
                                COLOR_MAP = {
                                    "red": (255, 0, 0),
                                    "green": (0, 128, 0),
                                    "blue": (0, 0, 255),
                                    "black": (0, 0, 0),
                                    "white": (255, 255, 255),
                                    "yellow": (255, 255, 0),
                                    "purple": (128, 0, 128),
                                    "orange": (255, 165, 0),
                                    "gray": (128, 128, 128),
                                    "pink": (255, 192, 203),
                                    "brown": (165, 42, 42),
                                    "cyan": (0, 255, 255),
                                    "magenta": (255, 0, 255),
                                    "lime": (0, 255, 0),
                                    "navy": (0, 0, 128),
                                    "teal": (0, 128, 128),
                                    "olive": (128, 128, 0),
                                    "maroon": (128, 0, 0),
                                    "silver": (192, 192, 192),
                                    "gold": (255, 215, 0)
                                }

                                try:
                                    normalized_style = element_style.replace(" :", ":")
                                    
                                    # Search color
                                    if "color:" in normalized_style:
                                        color_part = normalized_style.split("color:")[1].split(";")[0].strip()
                                    else:  # pragma: no cover
                                        return run  # Color not found
                                    
                                    # Handle RGB colors
                                    if color_part.startswith("rgb("):
                                        color_values = color_part.replace("rgb(", "").replace(")", "").split(",")
                                        r = int(color_values[0].strip())
                                        g = int(color_values[1].strip())
                                        b = int(color_values[2].strip())
                                        run.font.color.rgb = RGBColor(r, g, b)
                                    
                                    # Handle color with name (red, blue, etc.)
                                    elif color_part in COLOR_MAP:
                                        r, g, b = COLOR_MAP[color_part]
                                        run.font.color.rgb = RGBColor(r, g, b)
                                    
                                    # Handle hexadecimal colors (#FF0000, etc.)
                                    elif color_part.startswith("#"):
                                        hex_color = color_part.lstrip("#")
                                        r = int(hex_color[0:2], 16)
                                        g = int(hex_color[2:4], 16)
                                        b = int(hex_color[4:6], 16)
                                        run.font.color.rgb = RGBColor(r, g, b)
                                        
                                except (ValueError, IndexError) as e:
                                    pass
                        
                        return run
                    except Exception as e:  # pragma: no cover – defensive fallback
                        return run

                # Improved recursive function to flatten the HTML structure
                def process_element_flat(element, current_styles=None):
                    """
                    Process elements by flattening the structure and tracking styles
                    This approach creates separate runs for each text node but applies all parent styles
                    """
                    from bs4 import NavigableString
                    
                    if current_styles is None:
                        current_styles = []
                    
                    # Skip None elements
                    if element is None:  # pragma: no cover – defensive guard
                        return
                        
                    # For text nodes, create a run with all accumulated styles
                    if isinstance(element, NavigableString) and str(element).strip():
                        # Skip empty strings
                        if not str(element).strip():  # pragma: no cover – unreachable, outer if already checks
                            return
                            
                        text = str(element)
                        
                        # Create a new run for this text
                        run = paragraph.add_run(text)
                        
                        # Apply all parent styles to this run
                        for style_element in current_styles:
                            run = apply_styles_to_run(run, style_element)
                            
                        # Ensure Calibri is applied even if no styles were applied
                        if not current_styles:
                            run.font.name = font_name
                            
                        return
                    
                    # If it's a tag element, add it to current styles and process children
                    if hasattr(element, 'name') and element.name:
                        # Add this element to the current style context
                        new_styles = current_styles + [element]
                        
                        # Process all children with updated styles
                        for child in element.children:
                            process_element_flat(child, new_styles)
                
                # Process paragraph using the flat approach
                for child in tag.children:
                    process_element_flat(child)

            elif tag.name == "hr":
                hr_paragraph = doc.add_paragraph("_" * 71)
                apply_body_paragraph_spacing(hr_paragraph)
                last_block_was_table = False
                # Ensure Calibri is applied to the horizontal rule
                for run in hr_paragraph.runs:
                    run.font.name = font_name

            elif tag.name == "table":
                # Process HTML <table> into a python-docx Table
                rows = tag.find_all("tr")
                if not rows:
                    continue

                # Two directly adjacent docx tables auto-merge when the file is
                # opened in Word — separate them with a zero-spacing paragraph.
                if last_block_was_table:
                    spacer = doc.add_paragraph()
                    spacer.paragraph_format.space_before = Pt(0)
                    spacer.paragraph_format.space_after = Pt(0)

                # Determine number of columns from the first row
                first_row_cells = rows[0].find_all(["td", "th"])
                num_cols = len(first_row_cells) if first_row_cells else 1

                docx_table = doc.add_table(rows=0, cols=num_cols)
                docx_table.style = 'Table Grid'

                for row_tag in rows:
                    cells = row_tag.find_all(["td", "th"])
                    if not cells:
                        continue
                    docx_row = docx_table.add_row()
                    for idx, cell_tag in enumerate(cells):
                        if idx >= num_cols:
                            break
                        cell = docx_row.cells[idx]
                        cell_text = cell_tag.get_text(strip=True)
                        cell.text = cell_text
                        # Cell paragraphs must not inherit body spacing — the
                        # editor and PDF render cells with padding only.
                        for para in cell.paragraphs:
                            para.paragraph_format.space_before = Pt(0)
                            para.paragraph_format.space_after = Pt(0)
                            for run in para.runs:
                                run.font.name = font_name
                        # Bold for <th> header cells
                        if cell_tag.name == "th":
                            for para in cell.paragraphs:
                                for run in para.runs:
                                    run.bold = True

                last_block_was_table = True

        # Save the document to a buffer
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)

        return FileResponse(
            docx_buffer, 
            as_attachment=True, 
            filename=f"{document.title}.docx", 
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': f'Error generating Word document: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_documents(request):
    """
    Get the 10 most recently visited documents for the authenticated user.
    Only returns documents the user has permission to view.
    """
    recent_documents = RecentDocument.objects.filter(user=request.user).select_related(
        'document__created_by', 'document__assigned_to'
    ).prefetch_related(
        Prefetch(
            'document__signatures',
            queryset=DocumentSignature.objects.select_related('signer'),
        ),
        'document__variables',
        Prefetch('document__tags', queryset=Tag.objects.select_related('created_by')),
        'document__visibility_permissions',
        'document__usability_permissions',
        'document__relationships_as_source',
        'document__relationships_as_target',
    ).order_by('-last_visited')

    # Filter by visibility permissions using prefetched data (no extra DB hits)
    filtered_recent = []
    for recent_doc in recent_documents:
        if recent_doc.document.can_view_prefetched(request.user):
            filtered_recent.append(recent_doc)
        if len(filtered_recent) >= 10:  # Limit to 10 documents
            break
    
    serializer = RecentDocumentSerializer(filtered_recent, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_document_visibility_by_id
def update_recent_document(request, document_id):
    """
    Track a document visit by creating or updating a RecentDocument entry.
    Only allows tracking if user has permission to view the document.
    """
    try:
        document = DynamicDocument.objects.get(pk=document_id)
        recent_doc, created = RecentDocument.objects.get_or_create(
            user=request.user,
            document=document,
            defaults={'last_visited': timezone.now()}
        )
        
        if not created:
            recent_doc.last_visited = timezone.now()
            recent_doc.save()
            
        serializer = RecentDocumentSerializer(recent_doc)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_document_usability('usability')
def upload_letterhead_image(request, pk):
    """Upload a PNG letterhead image for a specific document.

    This image will be used as background when generating PDFs for this document.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)

        if document.state in LOCKED_STATES:
            return Response(
                {'detail': 'No se puede modificar el membrete de un documento en estado de firma.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if image file is provided
        if 'image' not in request.FILES:
            return Response(
                {'detail': 'No se proporcionó ninguna imagen. Use el campo "image" para subir el archivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file extension
        if not image_file.name.lower().endswith('.png'):
            return Response(
                {'detail': 'Solo se permiten archivos PNG para el membrete.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if image_file.size > max_size:
            return Response(
                {'detail': 'El archivo es demasiado grande. Tamaño máximo: 10MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate image dimensions and format using PIL
        try:
            img = Image.open(image_file)
            width, height = img.size
            
            # Check if it's a valid image
            img.verify()
            
            # Reset file pointer after verification
            image_file.seek(0)
            
            # Recommended dimensions check (warning, not error)
            # Tamaño carta a 300 DPI: 2550x3300 px
            recommended_width, recommended_height = 2550, 3300
            aspect_ratio = width / height
            recommended_ratio = recommended_width / recommended_height
            
            warnings = []
            if abs(aspect_ratio - recommended_ratio) > 0.1:  # Allow 10% tolerance
                warnings.append(f"La proporción de aspecto recomendada es 8.5:14 ({recommended_width}x{recommended_height}). Su imagen es {width}x{height}.")
            
        except Exception as e:
            return Response(
                {'detail': f'Archivo de imagen inválido: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete previous letterhead image if exists
        if document.letterhead_image:
            try:
                if os.path.exists(document.letterhead_image.path):
                    os.remove(document.letterhead_image.path)
            except:
                pass  # Continue even if deletion fails
        
        # Save the new image
        document.letterhead_image = image_file
        document.save(update_fields=['letterhead_image'])
        
        # Prepare response data
        response_data = {
            'message': 'Imagen de membrete subida exitosamente.',
            'document_id': document.id,
            'image_info': {
                'filename': image_file.name,
                'size_bytes': image_file.size,
                'dimensions': f"{width}x{height}",
                'format': img.format if hasattr(img, 'format') else 'PNG'
            }
        }
        
        if warnings:
            response_data['warnings'] = warnings
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al subir la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def get_letterhead_image(request, pk):
    """Get the PNG letterhead image for a specific document."""
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        # Check if document has letterhead image
        if not document.letterhead_image:
            return Response(
                {'detail': 'Este documento no tiene imagen de membrete.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if file exists
        if not os.path.exists(document.letterhead_image.path):
            return Response(
                {'detail': 'El archivo de imagen no se encuentra en el servidor.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return the image file
        return FileResponse(
            open(document.letterhead_image.path, 'rb'),
            as_attachment=False,
            filename=os.path.basename(document.letterhead_image.name),
            content_type='image/png'
        )
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al obtener la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_document_usability('usability')
def delete_letterhead_image(request, pk):
    """Delete the PNG letterhead image for a specific document."""
    try:
        document = DynamicDocument.objects.get(pk=pk)

        if document.state in LOCKED_STATES:
            return Response(
                {'detail': 'No se puede modificar el membrete de un documento en estado de firma.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if document has letterhead image
        if not document.letterhead_image:
            return Response(
                {'detail': 'Este documento no tiene imagen de membrete para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete the file from filesystem
        try:
            if os.path.exists(document.letterhead_image.path):
                os.remove(document.letterhead_image.path)
        except Exception as e:
            pass
        
        # Clear the field
        document.letterhead_image = None
        document.save(update_fields=['letterhead_image'])
        
        return Response(
            {'message': 'Imagen de membrete eliminada exitosamente.'},
            status=status.HTTP_200_OK
        )
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al eliminar la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_document_usability('usability')
def upload_document_letterhead_word_template(request, pk):
    """Upload a Word letterhead template (.docx) for a specific document.

    This template has priority over the user's global Word letterhead template
    when generating Word documents for this DynamicDocument.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)

        if document.state in LOCKED_STATES:
            return Response(
                {'detail': 'No se puede modificar el membrete de un documento en estado de firma.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if 'template' not in request.FILES:
            return Response(
                {'detail': 'Se requiere un archivo de plantilla (.docx).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        template_file = request.FILES['template']

        # Validate extension
        if not template_file.name.lower().endswith('.docx'):
            return Response(
                {'detail': 'Solo se permiten archivos .docx para la plantilla de Word.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if template_file.size > max_size:
            return Response(
                {'detail': f'El archivo es demasiado grande. Tamaño máximo permitido: {max_size // (1024*1024)}MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete previous template if exists
        if document.letterhead_word_template:
            try:
                if os.path.exists(document.letterhead_word_template.path):
                    os.remove(document.letterhead_word_template.path)
            except Exception:
                pass

        # Save new template
        document.letterhead_word_template = template_file
        document.save(update_fields=['letterhead_word_template'])

        response_data = {
            'message': 'Plantilla Word de membrete del documento subida exitosamente.',
            'document_id': document.id,
            'template_info': {
                'filename': template_file.name,
                'size_bytes': template_file.size,
            }
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al subir la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def get_document_letterhead_word_template(request, pk):
    """Get the Word letterhead template (.docx) for a specific document."""
    try:
        document = DynamicDocument.objects.get(pk=pk)

        if not document.letterhead_word_template:
            return Response(
                {'detail': 'Este documento no tiene una plantilla Word de membrete configurada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not os.path.exists(document.letterhead_word_template.path):
            return Response(
                {'detail': 'El archivo de plantilla no se encuentra en el servidor.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(document.letterhead_word_template.path, 'rb'),
            as_attachment=False,
            filename=os.path.basename(document.letterhead_word_template.name),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al obtener la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_document_usability('usability')
def delete_document_letterhead_word_template(request, pk):
    """Delete the Word letterhead template (.docx) for a specific document."""
    try:
        document = DynamicDocument.objects.get(pk=pk)

        if document.state in LOCKED_STATES:
            return Response(
                {'detail': 'No se puede modificar el membrete de un documento en estado de firma.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not document.letterhead_word_template:
            return Response(
                {'detail': 'Este documento no tiene una plantilla Word de membrete para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            if os.path.exists(document.letterhead_word_template.path):
                os.remove(document.letterhead_word_template.path)
        except Exception:
            pass

        document.letterhead_word_template = None
        document.save(update_fields=['letterhead_word_template'])

        return Response(
            {'message': 'Plantilla Word de membrete del documento eliminada exitosamente.'},
            status=status.HTTP_200_OK
        )

    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al eliminar la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_user_letterhead_word_template(request):
    """Upload a global Word letterhead template (.docx) for the authenticated user."""
    if request.user.role == 'basic':
        return Response({
            'error': 'Los usuarios básicos no pueden gestionar membretes'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        user = request.user

        if 'template' not in request.FILES:
            return Response(
                {'detail': 'Se requiere un archivo de plantilla (.docx).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        template_file = request.FILES['template']

        # Validate extension
        if not template_file.name.lower().endswith('.docx'):
            return Response(
                {'detail': 'Solo se permiten archivos .docx para la plantilla de Word.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if template_file.size > max_size:
            return Response(
                {'detail': f'El archivo es demasiado grande. Tamaño máximo permitido: {max_size // (1024*1024)}MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete previous template if exists
        if user.letterhead_word_template:
            try:
                if os.path.exists(user.letterhead_word_template.path):
                    os.remove(user.letterhead_word_template.path)
            except Exception:
                pass

        # Save new template
        user.letterhead_word_template = template_file
        user.save(update_fields=['letterhead_word_template'])

        response_data = {
            'message': 'Plantilla Word de membrete global subida exitosamente.',
            'user_id': user.id,
            'template_info': {
                'filename': template_file.name,
                'size_bytes': template_file.size,
            }
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'detail': f'Error al subir la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_letterhead_word_template(request):
    """Get the global Word letterhead template (.docx) for the authenticated user."""
    try:
        user = request.user

        if not user.letterhead_word_template:
            return Response(
                {'detail': 'No tienes una plantilla Word de membrete global configurada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not os.path.exists(user.letterhead_word_template.path):
            return Response(
                {'detail': 'El archivo de plantilla no se encuentra en el servidor.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(user.letterhead_word_template.path, 'rb'),
            as_attachment=False,
            filename=os.path.basename(user.letterhead_word_template.name),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return Response(
            {'detail': f'Error al obtener la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_letterhead_word_template(request):
    """Delete the global Word letterhead template (.docx) for the authenticated user."""
    if request.user.role == 'basic':
        return Response({
            'error': 'Los usuarios básicos no pueden gestionar membretes'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        user = request.user

        if not user.letterhead_word_template:
            return Response(
                {'detail': 'No tienes una plantilla Word de membrete global para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            if os.path.exists(user.letterhead_word_template.path):
                os.remove(user.letterhead_word_template.path)
        except Exception:
            pass

        user.letterhead_word_template = None
        user.save(update_fields=['letterhead_word_template'])

        return Response(
            {'message': 'Plantilla Word de membrete global eliminada exitosamente.'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'detail': f'Error al eliminar la plantilla: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== USER GLOBAL LETTERHEAD ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_user_letterhead_image(request):
    """
    Upload a global letterhead image for the authenticated user.
    
    This letterhead will be used as a fallback for all documents created by the user
    when they don't have a specific letterhead configured.
    
    Accepts a PNG image file and saves it to the user's letterhead_image field.
    The image should be in 8.5:11 ratio (2550x3300 pixels recommended for letter size at 300 DPI) for best results.
    
    Parameters:
        request (HttpRequest): The request object containing the image file
    
    Returns:
        Response: Success message with image info or error message
    """
    # Restrict basic users from uploading letterhead images
    if request.user.role == 'basic':
        return Response({
            'error': 'Los usuarios básicos no pueden gestionar membretes'
        }, status=status.HTTP_403_FORBIDDEN)
    try:
        user = request.user
        
        # Check if image file is provided
        if 'image' not in request.FILES:
            return Response(
                {'detail': 'Se requiere un archivo de imagen.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file extension
        if not image_file.name.lower().endswith('.png'):
            return Response(
                {'detail': 'Solo se permiten archivos PNG para el membrete.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if image_file.size > max_size:
            return Response(
                {'detail': f'El archivo es demasiado grande. Tamaño máximo permitido: {max_size // (1024*1024)}MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate image dimensions and format using PIL
        try:
            img = Image.open(image_file)
            width, height = img.size
            
            # Check if it's a valid image
            img.verify()
            
            # Reset file pointer after verification
            image_file.seek(0)
            
            # Recommended dimensions check (warning, not error)
            recommended_width, recommended_height = 612, 792
            aspect_ratio = width / height
            recommended_ratio = recommended_width / recommended_height
            
            warnings = []
            if abs(aspect_ratio - recommended_ratio) > 0.1:  # Allow 10% tolerance
                warnings.append(
                    f"La proporción de aspecto recomendada es 8.5:11 (tamaño carta, {recommended_width}x{recommended_height} píxeles a 300 DPI). "
                    f"Su imagen es {width}x{height}."
                )
            
        except Exception as e:
            return Response(
                {'detail': f'Archivo de imagen inválido: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete previous letterhead image if exists
        if user.letterhead_image:
            try:
                if os.path.exists(user.letterhead_image.path):
                    os.remove(user.letterhead_image.path)
            except:
                pass  # Continue even if deletion fails
        
        # Save the new image
        user.letterhead_image = image_file
        user.save(update_fields=['letterhead_image'])
        
        # Prepare response data
        response_data = {
            'message': 'Membrete global subido exitosamente.',
            'user_id': user.id,
            'image_info': {
                'filename': image_file.name,
                'size_bytes': image_file.size,
                'dimensions': f"{width}x{height}",
                'format': img.format if hasattr(img, 'format') else 'PNG'
            }
        }
        
        if warnings:
            response_data['warnings'] = warnings
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'detail': f'Error al subir la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_letterhead_image(request):
    """
    Get the global letterhead image for the authenticated user.
    
    Returns:
        FileResponse: The letterhead image file
        Response: Error message if image not found
    """
    try:
        user = request.user
        
        # Check if user has letterhead image
        if not user.letterhead_image:
            return Response(
                {'detail': 'No tienes una imagen de membrete global configurada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if file exists
        if not os.path.exists(user.letterhead_image.path):
            return Response(
                {'detail': 'El archivo de imagen no se encuentra en el servidor.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return the image file
        return FileResponse(
            open(user.letterhead_image.path, 'rb'),
            as_attachment=False,
            filename=os.path.basename(user.letterhead_image.name),
            content_type='image/png'
        )
        
    except Exception as e:
        return Response(
            {'detail': f'Error al obtener la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_letterhead_image(request):
    """
    Delete the global letterhead image for the authenticated user.
    
    Returns:
        Response: Success or error message
    """
    # Restrict basic users from deleting letterhead images
    if request.user.role == 'basic':
        return Response({
            'error': 'Los usuarios básicos no pueden gestionar membretes'
        }, status=status.HTTP_403_FORBIDDEN)
    try:
        user = request.user
        
        # Check if user has letterhead image
        if not user.letterhead_image:
            return Response(
                {'detail': 'No tienes una imagen de membrete global para eliminar.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete the file from filesystem
        try:
            if os.path.exists(user.letterhead_image.path):
                os.remove(user.letterhead_image.path)
        except Exception as e:
            pass
        
        # Clear the field
        user.letterhead_image = None
        user.save(update_fields=['letterhead_image'])
        
        return Response(
            {'message': 'Membrete global eliminado exitosamente.'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'detail': f'Error al eliminar la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
