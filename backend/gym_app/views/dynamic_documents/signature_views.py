import datetime
import io
import logging
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from gym_app.models.dynamic_document import DynamicDocument, DocumentSignature, DocumentVariable, DocumentVisibilityPermission
from gym_app.models import Notification
from gym_app.serializers.dynamic_document import DocumentSignatureSerializer, DynamicDocumentSerializer, DynamicDocumentListSerializer
from gym_app.serializers.user import UserSignatureSerializer
from gym_app.services.signature_notification_service import notify_signature_requested
from ..dynamic_documents.document_views import download_dynamic_document_pdf, get_optimized_document_queryset
from gym_app.utils.documents import (
    normalize_fragmented_variables,
    sanitize_soup_for_export,
    register_carlito_fonts,
    render_document_pdf,
    get_letterhead_for_document,
    snapshot_letterhead_on_formalize,
    ensure_letterhead_snapshot,
)
from .permissions import (
    apply_visibility_filter,
    require_document_visibility,
    require_document_visibility_by_id,
    require_document_usability,
    require_lawyer_or_owner,
    require_lawyer_or_owner_by_id,
)
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.http import FileResponse, HttpResponse
import traceback
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Best-effort retrieval of the client's IP address.

    Checks common proxy headers first and falls back to REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs, client is usually the first
        ip = x_forwarded_for.split(',')[0].strip()
        if ip:
            return ip

    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip

    return request.META.get('REMOTE_ADDR')


def generate_encrypted_document_id(document_id, created_at):
    """
    Generates a unique encrypted identifier for a document combining ID, date and time.
    Uses SHA256 hash for security and readability.
    
    Parameters:
        document_id (int): The document's database ID
        created_at (datetime): Document creation timestamp
    
    Returns:
        str: Formatted hash-based identifier
    """
    try:
        # Create a unique string combining ID, date, and time
        timestamp_str = created_at.strftime("%Y%m%d%H%M%S")
        unique_string = f"DOC{document_id}_{timestamp_str}"
        
        # Create a hash-based identifier
        hash_object = hashlib.sha256(unique_string.encode())
        hex_dig = hash_object.hexdigest()
        
        # Take first 16 characters and format as document identifier
        short_hash = hex_dig[:16].upper()
        formatted_id = f"{short_hash[:4]}-{short_hash[4:8]}-{short_hash[8:12]}-{short_hash[12:16]}"
        
        return formatted_id
    except Exception as e:
        # Fallback to simple format
        return f"DOC-{document_id:04d}-{created_at.strftime('%Y%m%d')}"


SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def format_datetime_spanish(dt):
    """
    Formatea un datetime en español, por ejemplo:
    25 de diciembre de 2025 a las 14:30:15
    """
    month_name = SPANISH_MONTHS.get(dt.month, "")
    return f"{dt.day:02d} de {month_name} de {dt.year} a las {dt.strftime('%H:%M:%S')}"


def expire_overdue_documents():
    """Mark documents with past signature_due_date as Expired and notify creators.

    This runs opportunistically when fetching pending documents for signatures.
    """
    today = timezone.now().date()
    overdue_documents = DynamicDocument.objects.filter(
        requires_signature=True,
        state='PendingSignatures',
        signature_due_date__isnull=False,
        signature_due_date__lt=today,
    ).select_related('created_by')

    for document in overdue_documents:
        document.state = 'Expired'
        document.updated_at = timezone.now()
        document.save(update_fields=['state', 'updated_at'])

        creator = document.created_by
        if not creator or not getattr(creator, 'email', None):
            continue

        # Notify creator that the document has expired
        from gym_app.services.signature_notification_service import notify_signature_expired
        notify_signature_expired(document)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility_by_id
def get_document_signatures(request, document_id):
    """
    Get all signatures for a specific document.
    """
    try:
        document = DynamicDocument.objects.get(pk=document_id)

        # Ensure the authenticated user can at least view the document
        if not document.can_view(request.user):  # pragma: no cover – decorator already checks visibility
            return Response(
                {'detail': 'You do not have permission to view this document.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        signatures = document.signatures.all()
        serializer = DocumentSignatureSerializer(signatures, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_signatures(request):
    """Get all documents that require a signature from the authenticated user.

    Returns the complete document information along with signature details.
    Only returns documents the user has permission to view.
    """

    # First, expire any overdue documents
    expire_overdue_documents()

    # Get document IDs with pending (non-rejected) signatures for the user
    pending_doc_ids = DocumentSignature.objects.filter(
        signer=request.user,
        signed=False,
        rejected=False,
        document__state='PendingSignatures',
    ).values_list('document_id', flat=True)

    # Build optimised queryset with all prefetches + visibility filtering
    base_qs = DynamicDocument.objects.filter(pk__in=pending_doc_ids)
    queryset = get_optimized_document_queryset(base_qs)
    queryset = apply_visibility_filter(queryset, request.user)

    serializer = DynamicDocumentListSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_signatures_count(request):
    """Return count of documents pending signature for the authenticated user.

    Lightweight endpoint for badge polling - returns only the count, not full documents.
    """
    # First, expire any overdue documents
    expire_overdue_documents()

    # Count pending signatures for the user
    pending_count = DocumentSignature.objects.filter(
        signer=request.user,
        signed=False,
        rejected=False,
        document__state='PendingSignatures',
    ).values_list('document_id', flat=True).distinct().count()

    return Response({'pending_count': pending_count}, status=status.HTTP_200_OK)


# Document state → "Archivos Jurídicos" dashboard tab. Drives the per-tab
# unread badges so a "novedad" surfaces on whichever tab its document
# currently lives in, not only "Dcs. Por Firmar".
_DOCUMENT_STATE_TO_TAB = {
    'PendingSignatures': 'pending-signatures',
    'FullySigned': 'signed-documents',
    'Rejected': 'archived-documents',
    'Expired': 'archived-documents',
    'Progress': 'my-documents',
    'Completed': 'my-documents',
    'Draft': 'legal-documents',
    'Published': 'legal-documents',
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document_notification_counts(request):
    """Return unread document-notification counts grouped by dashboard tab.

    Each unread notification linked to a document is bucketed by the
    document's current state, so the dashboard badge follows the document as
    it moves between tabs. The frontend ignores the ``pending-signatures``
    bucket — that tab uses the dedicated pending-signatures-count endpoint.
    """
    now = timezone.now()
    link_ids = Notification.objects.filter(
        user=request.user,
        link_type='document',
        is_read=False,
        is_archived=False,
        is_deleted=False,
    ).exclude(snoozed_until__gt=now).values_list('link_id', flat=True)

    link_ids = [lid for lid in link_ids if lid is not None]
    doc_states = dict(
        DynamicDocument.objects.filter(id__in=set(link_ids)).values_list('id', 'state')
    )

    counts = {}
    for link_id in link_ids:
        tab = _DOCUMENT_STATE_TO_TAB.get(doc_states.get(link_id))
        if tab:
            counts[tab] = counts.get(tab, 0) + 1

    return Response({'counts': counts}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def sign_document(request, document_id, user_id):
    """
    Sign a document using the user's signature.
    
    The user must have a valid signature stored in their profile.
    The user must be one of the requested signers for the document.
    
    Parameters:
        request: The HTTP request
        document_id: The ID of the document to sign
        user_id: The ID of the user who is signing the document
    """
    
    try:
        # Check that the document exists
        document = DynamicDocument.objects.get(pk=document_id)

        # First, check whether the document is configured to require signatures.
        # Tests expect a 400 response in this case even if the caller would not
        # normally have visibility permissions.
        if not document.requires_signature:
            return Response(
                {'detail': 'This document does not require signatures.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure the authenticated user can at least view the document so that
        # authorization errors (like signing on behalf of others) are surfaced
        # with a proper 403 instead of leaking information.
        if not document.can_view(request.user):
            return Response(
                {'detail': 'You do not have permission to view this document.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        # Check that the authenticated user has permission to sign
        # Only the user themselves or an administrator can sign on behalf of a user
        authenticated_user = request.user
        if authenticated_user.id != user_id and not authenticated_user.is_staff:
            return Response(
                {'detail': 'You are not authorized to sign documents on behalf of other users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check that the user exists
        try:
            signing_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check that the user is an authorized signer for this document
        try:
            signature_record = DocumentSignature.objects.select_for_update().get(
                document=document,
                signer=signing_user,
                signed=False,
                rejected=False,
            )
        except DocumentSignature.DoesNotExist:
            return Response(
                {'detail': 'This user is not authorized to sign this document or has already signed it.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check that the user has an electronic signature
        if not hasattr(signing_user, 'signature'):
            return Response(
                {'detail': f'User {signing_user.email} needs to create a signature before signing documents.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update the signature record
        try:
            signature_record.signed = True
            signature_record.signed_at = timezone.now()
            # Capture client IP using helper (handles proxies and fallbacks)
            signature_record.ip_address = get_client_ip(request)
            signature_record.save()
            
            # Verify the signature was saved
            saved_signature = DocumentSignature.objects.get(id=signature_record.id)
            if not saved_signature.signed:  # pragma: no cover – defensive check after save
                raise Exception("Signature was not saved correctly")
            
            # === Send signature progress notifications ===
            from gym_app.services.signature_notification_service import notify_signature_progress, notify_signature_completed
            
            # Send progress notification to all signers
            notify_signature_progress(document, signing_user)
            
        except Exception as e:
            return Response(
                {'detail': f'Error saving signature: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Check if all signatures are complete and update document state
        all_signatures = document.signatures.all()
        total_signatures = all_signatures.count()
        signed_signatures = all_signatures.filter(signed=True).count()
        
        if all(sig.signed for sig in all_signatures):
            document.state = 'FullySigned'
            document.fully_signed = True
            document.updated_at = timezone.now()
            document.save(update_fields=['state', 'fully_signed', 'updated_at'])

            # Safety net: if formalization-time snapshot was missed for any
            # reason (legacy data, transient failure), backfill it now using
            # whatever issuer the document already knows about.
            ensure_letterhead_snapshot(document)

            # Send completion notification
            notify_signature_completed(document, signing_user)

            # For issuer_only documents, notify recipients when fully signed
            if document.signature_type == 'issuer_only':
                _notify_issuer_only_recipients(document, signing_user)
        
        # Return the updated signature record
        serializer = DocumentSignatureSerializer(signature_record)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:
        return Response(
            {'detail': 'Document not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'detail': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reject_document(request, document_id, user_id):
    """Allow a signer to reject (devolver sin firmar) a document.

    Marks the corresponding DocumentSignature as rejected, stores an optional
    comment, updates the document state to Rejected, and notifies the creator.
    """

    try:
        document = DynamicDocument.objects.get(pk=document_id)

        if not document.requires_signature:
            return Response(
                {'detail': 'This document does not require signatures.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authenticated_user = request.user
        if authenticated_user.id != user_id and not authenticated_user.is_staff:
            return Response(
                {'detail': 'You are not authorized to reject documents on behalf of other users.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            rejecting_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # The user must be a pending, non-rejected signer
        try:
            signature_record = DocumentSignature.objects.select_for_update().get(
                document=document,
                signer=rejecting_user,
                signed=False,
                rejected=False,
            )
        except DocumentSignature.DoesNotExist:
            return Response(
                {'detail': 'This user is not authorized to reject this document or it was already processed.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Optional rejection comment
        comment = request.data.get('comment') or request.data.get('reason')

        # Update the signature record as rejected
        signature_record.rejected = True
        signature_record.rejected_at = timezone.now()
        if comment:
            signature_record.rejection_comment = comment
        signature_record.save()

        # Update document state to Rejected
        document.state = 'Rejected'
        document.fully_signed = False
        document.updated_at = timezone.now()
        document.save(update_fields=['state', 'fully_signed', 'updated_at'])

        # Notify the document creator
        from gym_app.services.signature_notification_service import notify_signature_rejected
        notify_signature_rejected(document, rejecting_user, comment)

        serializer = DocumentSignatureSerializer(signature_record)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except DynamicDocument.DoesNotExist:
        return Response(
            {'detail': 'Document not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:  # pragma: no cover – defensive broad catch
        return Response(
            {'detail': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner_by_id
@transaction.atomic
def reopen_document_signatures(request, document_id):
    """Reopen the signature workflow for a rejected or expired document.

    This endpoint is intended for the document creator or a lawyer. It allows
    correcting a previously rejected/expired document and sending it back to
    the *PendingSignatures* state while reusing the same document instance.

    Effects:
    - Only works for documents that require signatures.
    - Only allowed when the document state is Rejected or Expired.
    - Resets all related DocumentSignature records to pending status.
    - Updates the document state to PendingSignatures and clears fully_signed.
    """

    try:
        document = DynamicDocument.objects.select_for_update().get(pk=document_id)

        if not document.requires_signature:
            return Response(
                {'detail': 'This document does not require signatures.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document.state not in ['Rejected', 'Expired']:
            return Response(
                {'detail': 'Only rejected or expired documents can be reopened for signatures.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset all signature records for this document to pending state
        DocumentSignature.objects.filter(document=document).update(
            signed=False,
            signed_at=None,
            rejected=False,
            rejected_at=None,
            rejection_comment=None,
        )

        # Move document back to PendingSignatures state
        document.state = 'PendingSignatures'
        document.fully_signed = False
        document.updated_at = timezone.now()
        document.save(update_fields=['state', 'fully_signed', 'updated_at'])

        # Send reopening notifications to all signers
        from gym_app.services.signature_notification_service import notify_signature_reopened
        notify_signature_reopened(document)

        serializer = DynamicDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner_by_id
@transaction.atomic
def formalize_document(request, document_id):
    """Formalize a completed document by transitioning it based on signature_type.

    Supports three signature types:
    - 'normal' (default): All parties sign. Creates DocumentSignature for each signer.
    - 'issuer_only': Only the creator/emisor signs. Recipients receive notification.
    - 'informative': No signatures needed. Document goes directly to FullySigned.

    Effects (normal):
    - Sets requires_signature=True, state='PendingSignatures', signature_type='normal'.
    - Creates DocumentSignature records for each signer + auto-adds lawyer.

    Effects (issuer_only):
    - Sets requires_signature=True, state='PendingSignatures', signature_type='issuer_only'.
    - Creates DocumentSignature for the emisor (pending) + auto-signed DS for recipients.
    - Grants visibility to recipients so they can view the document.

    Effects (informative):
    - Sets requires_signature=True, state='FullySigned', signature_type='informative'.
    - Creates auto-signed DocumentSignature for emisor + each recipient.
    - Grants visibility to recipients and sends notification email.
    """

    try:
        document = DynamicDocument.objects.get(pk=document_id)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if document.state != 'Completed':
        return Response(
            {'detail': 'Solo los documentos en estado "Completado" pueden ser formalizados.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    signature_type = request.data.get('signature_type', 'normal')
    if signature_type not in ('normal', 'issuer_only', 'informative'):
        return Response(
            {'detail': 'Tipo de firma inválido. Opciones: normal, issuer_only, informative.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    signature_due_date = request.data.get('signature_due_date', None)
    recipient_ids = request.data.get('recipients', [])

    # ── INFORMATIVE: no signatures needed, goes directly to FullySigned ──
    if signature_type == 'informative':
        # Validate recipients
        if not recipient_ids:
            return Response(
                {'detail': 'Debe incluir al menos un destinatario para documentos informativos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipients = User.objects.filter(pk__in=recipient_ids)
        if recipients.count() != len(recipient_ids):
            return Response(
                {'detail': 'Uno o más IDs de destinatario no son válidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        rows_updated = DynamicDocument.objects.filter(
            pk=document_id,
            state='Completed',
        ).update(
            state='FullySigned',
            requires_signature=True,
            signature_type='informative',
            fully_signed=True,
            formalized_by=request.user,
            updated_at=now,
        )

        if rows_updated == 0:
            logger.warning(
                "409 Conflict: formalize_document(informative) doc_id=%d user_id=%d",
                document_id, request.user.pk,
            )
            return Response(
                {'detail': 'El documento fue modificado por otro usuario. Intente nuevamente.'},
                status=status.HTTP_409_CONFLICT,
            )

        # Create DocumentSignature for the emisor (auto-signed as "Emitido")
        DocumentSignature.objects.get_or_create(
            document=document,
            signer=request.user,
            defaults={'signed': True, 'signed_at': now},
        )

        # Create DocumentSignature for each recipient (auto-signed as "Informado")
        for recipient in recipients:
            DocumentSignature.objects.get_or_create(
                document=document,
                signer=recipient,
                defaults={'signed': True, 'signed_at': now},
            )

        # Grant visibility to recipients
        _grant_visibility_to_recipients(document, recipients, request.user)

        # Send notification emails to recipients
        creator_name = request.user.get_full_name() or request.user.email
        for recipient in recipients:
            try:
                email_message = EmailMessage(
                    subject=f"[Documento Informativo] '{document.title}'",
                    body=(
                        f"El usuario {creator_name} le ha enviado el documento informativo "
                        f"'{document.title}'.\n\n"
                        f"Este documento no requiere firma. Puede consultarlo en su repositorio documental."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient.email],
                )
                email_message.send()
            except Exception:
                logger.warning(
                    "Failed to send informative notification email to %s for doc_id=%d",
                    recipient.email, document_id, exc_info=True,
                )

        # Email already sent above; suppress the email branch in the helper.
        notify_signature_requested(
            document, list(recipients), signature_type='informative', send_email=False,
        )

        # Freeze letterhead at formalization so the contents stay inalterable.
        # The "emisor" whose letterhead gets frozen is request.user (the user
        # who clicked Formalize), persisted in document.formalized_by above.
        document.refresh_from_db(fields=['state', 'formalized_by'])
        snapshot_letterhead_on_formalize(document, request.user)

        document = get_optimized_document_queryset().get(pk=document_id)
        serializer = DynamicDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── ISSUER_ONLY: only the creator signs ──
    if signature_type == 'issuer_only':
        if not recipient_ids:
            return Response(
                {'detail': 'Debe incluir al menos un destinatario para documentos de solo firma del emisor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipients = User.objects.filter(pk__in=recipient_ids)
        if recipients.count() != len(recipient_ids):
            return Response(
                {'detail': 'Uno o más IDs de destinatario no son válidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rows_updated = DynamicDocument.objects.filter(
            pk=document_id,
            state='Completed',
        ).update(
            state='PendingSignatures',
            requires_signature=True,
            signature_type='issuer_only',
            fully_signed=False,
            signature_due_date=signature_due_date if signature_due_date else None,
            formalized_by=request.user,
            updated_at=timezone.now(),
        )

        if rows_updated == 0:
            logger.warning(
                "409 Conflict: formalize_document(issuer_only) doc_id=%d user_id=%d",
                document_id, request.user.pk,
            )
            return Response(
                {'detail': 'El documento fue modificado por otro usuario. Intente nuevamente.'},
                status=status.HTTP_409_CONFLICT,
            )

        # Create DocumentSignature for the creator/emisor (pending their signature)
        DocumentSignature.objects.get_or_create(
            document=document,
            signer=request.user,
        )

        # Create DocumentSignature for each recipient (auto-signed as "Notificado")
        now_issuer = timezone.now()
        for recipient in recipients:
            DocumentSignature.objects.get_or_create(
                document=document,
                signer=recipient,
                defaults={'signed': True, 'signed_at': now_issuer},
            )

        # Creator must sign — uses the standard "Firma Solicitada" copy.
        notify_signature_requested(document, [request.user], signature_type='normal')

        # Notify recipients with issuer_only specific copy ("Documento Emitido").
        # In-app only to avoid duplicating the email already sent by the
        # underlying signing/formalization flow upstream of this view.
        notify_signature_requested(
            document, list(recipients), signature_type='issuer_only', send_email=False,
        )

        # Grant visibility to recipients
        _grant_visibility_to_recipients(document, recipients, request.user)

        # Freeze letterhead at formalization so the contents stay inalterable.
        # The "emisor" whose letterhead gets frozen is request.user (the user
        # who clicked Formalize), persisted in document.formalized_by above.
        document.refresh_from_db(fields=['state', 'formalized_by'])
        snapshot_letterhead_on_formalize(document, request.user)

        document = get_optimized_document_queryset().get(pk=document_id)
        serializer = DynamicDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── NORMAL: all parties sign (existing behavior) ──
    signer_ids = request.data.get('signers', [])
    if not signer_ids:
        return Response(
            {'detail': 'Debe incluir al menos un firmante.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    signers = User.objects.filter(pk__in=signer_ids)
    if signers.count() != len(signer_ids):
        return Response(
            {'detail': 'Uno o más IDs de firmante no son válidos.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Auto-add the requesting lawyer as signer if not already included
    if request.user.role == 'lawyer' and request.user.pk not in signer_ids:
        signers = list(signers)
        signers.append(request.user)

    rows_updated = DynamicDocument.objects.filter(
        pk=document_id,
        state='Completed',
    ).update(
        state='PendingSignatures',
        requires_signature=True,
        signature_type='normal',
        fully_signed=False,
        signature_due_date=signature_due_date if signature_due_date else None,
        formalized_by=request.user,
        updated_at=timezone.now(),
    )

    if rows_updated == 0:
        logger.warning(
            "409 Conflict: formalize_document doc_id=%d user_id=%d — state changed concurrently",
            document_id, request.user.pk,
        )
        return Response(
            {'detail': 'El documento fue modificado por otro usuario. Intente nuevamente.'},
            status=status.HTTP_409_CONFLICT,
        )

    DocumentSignature.objects.bulk_create(
        [DocumentSignature(document=document, signer=signer) for signer in signers],
        ignore_conflicts=True,
    )

    notify_signature_requested(document, list(signers))

    # Freeze letterhead at formalization so the contents stay inalterable.
    # The "emisor" whose letterhead gets frozen is request.user, persisted in
    # document.formalized_by above.
    document.refresh_from_db(fields=['state', 'formalized_by'])
    snapshot_letterhead_on_formalize(document, request.user)

    document = get_optimized_document_queryset().get(pk=document_id)
    serializer = DynamicDocumentSerializer(document, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


def _grant_visibility_to_recipients(document, recipients, granted_by):
    """Grant visibility permissions to recipients so they can view the document."""
    for recipient in recipients:
        if recipient.role == 'lawyer' or getattr(recipient, 'is_gym_lawyer', False):
            continue
        DocumentVisibilityPermission.objects.get_or_create(
            document=document,
            user=recipient,
            defaults={'granted_by': granted_by},
        )


def _notify_issuer_only_recipients(document, signing_user):
    """Notify recipients (visibility permission holders) that an issuer_only document was signed."""
    recipient_perms = document.visibility_permissions.select_related('user').exclude(
        user=signing_user,
    )
    creator_name = signing_user.get_full_name() or signing_user.email
    for perm in recipient_perms:
        try:
            email_message = EmailMessage(
                subject=f"[Documento Firmado] '{document.title}'",
                body=(
                    f"El usuario {creator_name} ha firmado el documento '{document.title}'.\n\n"
                    f"Este documento ha sido firmado por el emisor y no requiere su firma. "
                    f"Puede consultarlo en su repositorio documental."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[perm.user.email],
            )
            email_message.send()
        except Exception:
            logger.warning(
                "Failed to send issuer_only notification email to %s for doc_id=%d",
                perm.user.email, document.pk, exc_info=True,
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner_by_id
@transaction.atomic
def correct_document(request, document_id):
    """Correct a rejected/expired document and reopen its signature workflow.

    Combines document content update and signature reopening into a single
    atomic operation, replacing the previous two-step flow (update + reopen).

    Accepts:
    - content: updated HTML content (optional)
    - variables: array of variable objects to replace existing ones (optional)
    - signature_due_date: new deadline for signatures (optional)

    Effects:
    - Only works for documents in 'Rejected' or 'Expired' state.
    - Updates content and/or variables if provided.
    - Resets all DocumentSignature records to pending status.
    - Transitions document state to PendingSignatures.
    """

    try:
        document = DynamicDocument.objects.get(pk=document_id)
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not document.requires_signature:
        return Response(
            {'detail': 'Este documento no requiere firmas.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if document.state not in ['Rejected', 'Expired']:
        return Response(
            {'detail': 'Solo documentos rechazados o expirados pueden ser corregidos.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Extract request data for validation before any mutations
    content = request.data.get('content')
    variables_data = request.data.get('variables')
    signature_due_date = request.data.get('signature_due_date')

    # Optimistic state transition FIRST — ensures no partial writes on conflict.
    # All document-level field updates are done in a single .update() call
    # to avoid stale in-memory object issues.
    update_kwargs = {
        'state': 'PendingSignatures',
        'fully_signed': False,
        'updated_at': timezone.now(),
    }
    if content is not None:
        update_kwargs['content'] = content
    if signature_due_date is not None:
        update_kwargs['signature_due_date'] = signature_due_date if signature_due_date else None

    rows_updated = DynamicDocument.objects.filter(
        pk=document_id,
        state__in=['Rejected', 'Expired'],
    ).update(**update_kwargs)

    if rows_updated == 0:
        logger.warning(
            "409 Conflict: correct_document doc_id=%d user_id=%d — state changed concurrently",
            document_id, request.user.pk,
        )
        return Response(
            {'detail': 'El documento fue modificado por otro usuario. Intente nuevamente.'},
            status=status.HTTP_409_CONFLICT,
        )

    # All mutations below are safe — the optimistic lock succeeded.

    # Replace variables if provided
    if variables_data is not None:
        document.variables.all().delete()
        DocumentVariable.objects.bulk_create([
            DocumentVariable(
                document=document,
                name_en=var_data.get('name_en', ''),
                name_es=var_data.get('name_es', ''),
                tooltip=var_data.get('tooltip', ''),
                field_type=var_data.get('field_type', 'input'),
                value=var_data.get('value', ''),
                select_options=var_data.get('select_options'),
                summary_field=var_data.get('summary_field', 'none'),
                currency=var_data.get('currency'),
            )
            for var_data in variables_data
        ])

    # Reset all signature records to pending
    DocumentSignature.objects.filter(document=document).update(
        signed=False,
        signed_at=None,
        rejected=False,
        rejected_at=None,
        rejection_comment=None,
    )

    # Send reopening notifications to all signers
    from gym_app.services.signature_notification_service import notify_signature_reopened
    notify_signature_reopened(document)

    # Return the fully serialized document
    document = get_optimized_document_queryset().get(pk=document_id)
    serializer = DynamicDocumentSerializer(document, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner_by_id
def remove_signature_request(request, document_id, user_id):
    """
    Remove a signature request for a specific user on a document.
    Only the document creator can remove signature requests.
    Signatures that have already been added cannot be removed.
    """
    try:
        document = DynamicDocument.objects.get(pk=document_id)
        
        # Check if the user is the creator of the document
        if document.created_by != request.user:
            return Response(
                {'detail': 'Only the document creator can remove signature requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Find the signature record
        try:
            signature_record = DocumentSignature.objects.get(
                document=document,
                signer_id=user_id
            )
            
            # Check if the document has already been signed
            if signature_record.signed:
                return Response(
                    {'detail': 'Cannot remove a signature that has already been added.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Delete the signature record
            signature_record.delete()
            
            return Response(
                {'detail': 'Signature request removed successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DocumentSignature.DoesNotExist:
            return Response(
                {'detail': 'Signature request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_pending_documents_full(request, user_id):
    """
    Obtener información detallada sobre documentos que requieren la firma de un usuario específico.
    Only returns documents the requesting user has permission to view.
    """
    try:
        user = User.objects.get(pk=user_id)

        # First, expire overdue documents
        expire_overdue_documents()

        pending_doc_ids = DocumentSignature.objects.filter(
            signer_id=user_id,
            signed=False,
            rejected=False,
            document__state='PendingSignatures',
        ).values_list('document_id', flat=True)

        base_qs = DynamicDocument.objects.filter(pk__in=pending_doc_ids)
        queryset = get_optimized_document_queryset(base_qs)
        queryset = apply_visibility_filter(queryset, request.user)

        serializer = DynamicDocumentListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_archived_documents(request, user_id):
    """Obtener documentos rechazados o expirados asociados a un usuario firmante.

    Incluye documentos donde el usuario es firmante y el documento está en
    estado Rejected o Expired.
    """

    try:
        user = User.objects.get(pk=user_id)

        archived_doc_ids = DocumentSignature.objects.filter(
            signer_id=user_id,
            document__state__in=['Rejected', 'Expired'],
        ).values_list('document_id', flat=True)

        base_qs = DynamicDocument.objects.filter(pk__in=archived_doc_ids)
        queryset = get_optimized_document_queryset(base_qs)
        queryset = apply_visibility_filter(queryset, request.user)

        serializer = DynamicDocumentListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_signed_documents(request, user_id):
    """
    Obtener información detallada sobre documentos que han sido firmados por un usuario específico.
    Only returns documents the requesting user has permission to view.
    """
    try:
        user = User.objects.get(pk=user_id)

        signed_doc_ids = DocumentSignature.objects.filter(
            signer_id=user_id, signed=True,
        ).values_list('document_id', flat=True)

        base_qs = DynamicDocument.objects.filter(pk__in=signed_doc_ids)
        queryset = get_optimized_document_queryset(base_qs)
        queryset = apply_visibility_filter(queryset, request.user)

        serializer = DynamicDocumentListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_signature(request, user_id):
    """
    Obtener la firma del usuario especificado por su ID.
    """
    if request.user.id != user_id:
        return Response(
            {'error': 'No tienes permiso para consultar esta firma.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user = User.objects.get(pk=user_id)
        
        if hasattr(user, 'signature'):
            serializer = UserSignatureSerializer(user.signature, context={'request': request})
            return Response({
                'has_signature': True,
                'signature': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'has_signature': False}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def generate_original_document_pdf(document, fallback_user=None):
    """Generate the original document PDF and return its BytesIO buffer.

    Letterhead resolution reads ``document.formalized_by`` (with
    ``created_by`` as legacy fallback) internally via
    :func:`get_letterhead_for_document`. ``fallback_user`` is only consulted
    for non-locked states.
    """
    ensure_letterhead_snapshot(document)
    # Normalize any {{ }} patterns that TinyMCE may have split across HTML tags
    processed_content = normalize_fragmented_variables(document.content)

    # Replace variables within the content (use formatted values when available)
    for variable in document.variables.all():
        try:
            replacement_value = variable.get_formatted_value()
        except AttributeError:  # pragma: no cover – defensive fallback for missing method
            replacement_value = variable.value or ""
        processed_content = processed_content.replace(
            f"{{{{{variable.name_en}}}}}",
            replacement_value or ""
        )

    # Parse once; sanitize Word-pasted markup in place so the renderer
    # preserves table formatting and alignment.
    soup = sanitize_soup_for_export(BeautifulSoup(processed_content, 'html.parser'))

    letterhead_image = get_letterhead_for_document(document, fallback_user=fallback_user)

    # Render with WeasyPrint (browser-grade CSS/table layout → matches editor)
    return BytesIO(render_document_pdf(
        title=document.title,
        body_html=str(soup),
        letterhead_image=letterhead_image,
        top_padding="1.5cm",
    ))

def create_signatures_pdf(document, request):
    """
    Creates a PDF containing the signatures information for a document.
    Optimized for single page layout with new format.
    Returns a BytesIO buffer containing the PDF.
    """
    # Create a buffer for the PDF
    buffer = BytesIO()
    
    # Create the PDF document with smaller margins for single page optimization
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=60
    )
    
    # Get and customize styles for left alignment
    styles = getSampleStyleSheet()
    
    # Register fonts
    register_carlito_fonts()
    
    # Create custom styles optimized for single page
    # Estilos para el nuevo diseño
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        alignment=1,  # Center alignment
        fontSize=14,
        spaceAfter=16,
        fontName='Carlito-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        alignment=1,  # Center alignment
        fontSize=12,
        spaceAfter=8,
        fontName='Carlito-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        alignment=0,  # Left alignment
        fontSize=10,
        spaceAfter=4,
        fontName='Carlito'
    )
    
    normal_center_style = ParagraphStyle(
        'CustomNormalCenter',
        parent=styles['Normal'],
        alignment=1,  # Center alignment
        fontSize=10,
        spaceAfter=4,
        fontName='Carlito'
    )
    
    detail_style = ParagraphStyle(
        'DetailStyle',
        parent=styles['Normal'],
        alignment=0,  # Left alignment
        fontSize=10,
        spaceAfter=2,
        fontName='Carlito'
    )
    
    # Build the PDF content
    elements = []
    
    sig_type = document.signature_type or 'normal'
    is_informative = sig_type == 'informative'
    is_issuer_only = sig_type == 'issuer_only'
    # For informative/issuer_only the emisor is the formalizer (request.user at
    # formalization time), which is stored as granted_by in visibility permissions.
    # Fall back to created_by_id when no permissions exist (e.g. all-lawyer recipients).
    if is_informative or is_issuer_only:
        vp = document.visibility_permissions.select_related('granted_by').first()
        creator_id = vp.granted_by_id if vp and vp.granted_by_id else document.created_by_id
    else:
        creator_id = document.created_by_id
    
    # Título principal centrado — adapted per signature_type
    if is_informative:
        elements.append(Paragraph("CONSTANCIA AUDITORIA DOCUMENTO INFORMADO", title_style))
    elif is_issuer_only:
        elements.append(Paragraph("CONSTANCIA AUDITORIA DOCUMENTO Y FIRMA DEL EMISOR", title_style))
    else:
        elements.append(Paragraph("CONSTANCIA AUDITORIA DOCUMENTO Y FIRMAS", title_style))
    elements.append(Spacer(1, 12))
    
    # Generate encrypted document identifier
    encrypted_id = generate_encrypted_document_id(document.pk, document.created_at)
    
    # Tabla de Identificación del Documento
    elements.append(Paragraph("<b>Identificación del Documento</b>", subtitle_style))
    elements.append(Spacer(1, 6))
    
    # Crear tabla con bordes para identificación del documento
    from reportlab.lib import colors as rl_colors
    table_data = [
        [Paragraph("<b>Título del Documento</b>", normal_center_style), 
         Paragraph("<b>Fecha de Creación</b>", normal_center_style), 
         Paragraph("<b>Identificador Único</b>", normal_center_style)],
        [Paragraph(document.title, normal_center_style), 
         Paragraph(format_datetime_spanish(document.created_at), normal_center_style), 
         Paragraph(encrypted_id, normal_center_style)]
    ]
    
    doc_table = Table(table_data, colWidths=[180, 180, 140])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.Color(0.95, 0.95, 0.95)),  # Header row light gray
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Carlito-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Carlito'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.black),
    ]))
    elements.append(doc_table)
    elements.append(Spacer(1, 20))
    
    # Resumen — adapted per signature_type
    if is_informative:
        elements.append(Paragraph("<b>Resumen</b>", subtitle_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Estado: INFORMADO", normal_center_style))
    else:
        # For issuer_only, count only the emisor's signature
        if is_issuer_only:
            emisor_sigs = document.signatures.filter(signer_id=creator_id)
            total_signatures = emisor_sigs.count()
            signed_count = emisor_sigs.filter(signed=True).count()
        else:
            total_signatures = document.signatures.count()
            signed_count = document.signatures.filter(signed=True).count()
        elements.append(Paragraph("<b>Resumen Firmas</b>", subtitle_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f"Firmas Requeridas: {total_signatures} | Firmas Completadas: {signed_count} | Estado: {'COMPLETAMENTE FIRMADO' if document.fully_signed else 'PENDIENTE'}",
            normal_center_style
        ))
    elements.append(Spacer(1, 20))
    
    # Registro
    elements.append(Paragraph("<b>Registro</b>", subtitle_style))
    elements.append(Spacer(1, 10))
    
    signature_images_added = False
    all_signatures = document.signatures.all().order_by('created_at')

    for idx, signature in enumerate(all_signatures, 1):
        try:
            user = signature.signer
            is_creator = (user.pk == creator_id)

            # issuer_only: skip recipients entirely — audit only shows the emisor
            if is_issuer_only and not is_creator:
                continue

            user_signature = getattr(user, 'signature', None)
            
            # Determine role label and status label per signature_type
            if is_informative:
                role_label = "Emisor" if is_creator else "Destinatario"
                status_label = "Emitido" if is_creator else "Informado"
            elif is_issuer_only:
                role_label = "Emisor"
                status_label = "Firmado" if signature.signed else "Pendiente de Firma"
            else:
                role_label = "Firmante"
                status_label = None  # not shown for normal docs
            
            # Generate unique identifier for this signature (only for actual signers)
            signature_id = f"{idx:02d}{signature.signed_at.strftime('%m%d%H%M') if signature.signed_at else '0000'}"
            
            # Role + nombre completo
            elements.append(Paragraph(f"<b>{role_label}:</b> {user.get_full_name() or user.email}", detail_style))
            
            # Email (and ID Firma only for actual signers, not informative)
            if is_informative:
                elements.append(Paragraph(f"<b>Email:</b> {user.email}", detail_style))
            else:
                elements.append(Paragraph(f"<b>Email:</b> {user.email} | <b>ID Firma:</b> {signature_id}", detail_style))
            
            # Identificación
            id_info = []
            if user.document_type:
                id_info.append(f"{user.get_document_type_display()}")
            if user.identification:
                id_info.append(f"{user.identification}")
            if id_info:
                elements.append(Paragraph(f"<b>Identificación:</b> {' - '.join(id_info)}", detail_style))
            
            # Fecha y Hora
            elements.append(Paragraph(f"<b>Fecha y Hora:</b> {signature.signed_at.strftime('%d/%m/%Y %H:%M:%S') if signature.signed_at else 'N/A'}", detail_style))
            
            # IP de Registro (skip for informative recipients)
            if not (is_informative and not is_creator):
                ip_text = signature.ip_address if signature.ip_address else "No Registrada"
                elements.append(Paragraph(f"<b>IP de Registro:</b> {ip_text}", detail_style))
            
            # Estado line for informative and issuer_only
            if status_label:
                elements.append(Paragraph(f"<b>Estado:</b> {status_label}", detail_style))
            
            # Signature image — only for actual signers (not informative docs, not issuer_only recipients)
            show_signature_image = not is_informative
            if show_signature_image and user_signature and user_signature.signature_image:
                try:
                    img = Image(user_signature.signature_image.path)
                    img.drawHeight = 50
                    img.drawWidth = 180
                    # Crear tabla para centrar imagen
                    img_table = Table([[img]], colWidths=[500])
                    img_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    elements.append(img_table)
                    signature_images_added = True
                except Exception as e:  # pragma: no cover – signature image rendering error
                    pass
            
            elements.append(Spacer(1, 15))
            
        except Exception as e:  # pragma: no cover – signature processing error
            pass
    
    if not is_informative and not signature_images_added:
        elements.append(Paragraph("<b>Nota:</b> No se encontraron imágenes de firmas registradas.", normal_style))
        elements.append(Spacer(1, 4))
    
    # Constancia final (texto justificado) — adapted per signature_type
    constancia_style = ParagraphStyle(
        'ConstanciaStyle',
        parent=styles['Normal'],
        alignment=4,  # Justify
        fontSize=10,
        spaceAfter=4,
        fontName='Carlito'
    )
    elements.append(Spacer(1, 10))
    if is_informative:
        elements.append(Paragraph(
            "Este documento registra la emisión y comunicación del documento referenciado, "
            "verificado bajo autenticidad del(los) usuario(s) generador(es) del documento "
            "como del(los) destinatario(s).",
            constancia_style
        ))
    elif is_issuer_only:
        elements.append(Paragraph(
            "Este documento registra la firma digitalizada aplicada por el usuario emisor "
            "del documento referenciado. La firma ha sido verificada bajo autenticidad del "
            "usuario generador; los destinatarios fueron notificados y no requieren firma.",
            constancia_style
        ))
    else:
        elements.append(Paragraph(
            "Este documento registra las firmas digitalizadas aplicadas al documento referenciado, "
            "las firmas en este registro han sido verificadas bajo autenticidad del(los) usuario(s) "
            "generador(es) del documento como del(los) destinatario(s) firmante(s).",
            constancia_style
        ))
    elements.append(Spacer(1, 6))
    
    # Build the PDF sin marca de agua ni línea 'Generado el'
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    buffer.seek(0)
    return buffer

def combine_pdfs(pdf1_buffer, pdf2_buffer):
    """
    Combines two PDF buffers into a single PDF.
    Returns a BytesIO buffer containing the combined PDF.
    """
    # Create PDF reader objects
    pdf1 = PdfReader(pdf1_buffer)
    pdf2 = PdfReader(pdf2_buffer)
    
    # Create PDF writer object
    output = PdfWriter()
    
    # Add all pages from first PDF
    for page in pdf1.pages:
        output.add_page(page)
    
    # Add all pages from second PDF
    for page in pdf2.pages:
        output.add_page(page)
    
    # Create output buffer
    output_buffer = BytesIO()
    output.write(output_buffer)
    output_buffer.seek(0)
    
    return output_buffer


def add_identifier_footer(pdf_buffer, identifier):
    """
    Añade el identificador único en la esquina inferior derecha de todas las páginas.
    Devuelve un nuevo BytesIO con el PDF modificado.
    """
    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()

    # Crear un PDF de una sola página con el texto del identificador como footer
    footer_buffer = BytesIO()
    c = canvas.Canvas(footer_buffer, pagesize=letter)
    c.setFont('Carlito', 9)
    c.setFillColor(colors.grey)

    margin_x = 40  # margen desde la derecha
    margin_y = 60  # margen desde abajo (suficiente para no solapar con footer del membrete)
    c.drawRightString(letter[0] - margin_x, margin_y, identifier)
    c.save()

    footer_buffer.seek(0)
    footer_pdf = PdfReader(footer_buffer)

    # Mezclar el footer en cada página
    for page in reader.pages:
        writer_page = writer.add_page(page)
        writer_page.merge_page(footer_pdf.pages[0])

    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_document_visibility
def generate_signatures_pdf(request, pk):
    """
    Generates a comprehensive PDF document containing the original document and its signatures information.
    
    This function combines two PDFs:
    1. The original document PDF
    2. A new PDF containing detailed signatures information
    
    Parameters:
        request (HttpRequest): The request object.
        pk (int): The primary key of the document to be retrieved.
    
    Returns:
        FileResponse: A downloadable PDF file response with combined content.
        Response: A JSON response with an error message if an exception occurs.
    """
    try:
        
        # Retrieve the document from the database
        document = DynamicDocument.objects.prefetch_related('signatures__signer', 'variables', 'tags').get(pk=pk)
        
        # Verify document state
        if document.state != 'FullySigned':
            return Response(
                {'detail': 'El documento debe estar completamente formalizado para generar el PDF.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify signatures exist
        if not document.signatures.exists():
            return Response(
                {'detail': 'El documento no tiene firmas registradas.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the original document PDF
        original_pdf_buffer = generate_original_document_pdf(
            document, fallback_user=request.user
        )
        
        # Create the signatures PDF
        signatures_pdf_buffer = create_signatures_pdf(document, request)
        
        # Combine both PDFs
        combined_pdf_buffer = combine_pdfs(original_pdf_buffer, signatures_pdf_buffer)
        
        # Generar el mismo identificador único
        encrypted_id = generate_encrypted_document_id(document.pk, document.created_at)
        
        # Añadir el identificador como pie de página en todas las hojas
        combined_pdf_buffer = add_identifier_footer(combined_pdf_buffer, encrypted_id)
        
        # Create the HTTP response with proper headers
        response = HttpResponse(content_type='application/pdf')
        # Clean filename for better compatibility
        clean_filename = "".join(c for c in document.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        response['Content-Disposition'] = f'attachment; filename="Documento_Completo_{clean_filename}.pdf"'
        response['Content-Length'] = len(combined_pdf_buffer.getvalue())
        response.write(combined_pdf_buffer.getvalue())
        
        return response
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Documento no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:  # pragma: no cover
        return Response(
            {'detail': f'Error al generar el PDF de firmas: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
