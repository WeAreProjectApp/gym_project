import logging

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gym_app.models import (
    SECOPProcess, ProcessClassification, SECOPAlert,
    SyncLog, SavedView
)
from gym_app.serializers.secop import (
    SECOPProcessListSerializer, SECOPProcessDetailSerializer,
    ProcessClassificationSerializer, SECOPAlertSerializer,
    SyncLogSerializer, SavedViewSerializer
)
from gym_app.utils.auth_utils import is_gym_staff

logger = logging.getLogger(__name__)

# Allowed ordering fields for process list
ALLOWED_ORDER_FIELDS = {
    'publication_date', '-publication_date',
    'closing_date', '-closing_date',
    'base_price', '-base_price',
    'entity_name', '-entity_name',
}

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_page_size(query_params):
    """Parse page_size from query params with safe fallback."""
    try:
        return min(int(query_params.get('page_size', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    except (ValueError, TypeError):
        return DEFAULT_PAGE_SIZE


def _apply_secop_filters(queryset, query_params):
    """Apply filtering and search to a SECOPProcess queryset.

    Shared by secop_process_list and secop_export_excel.
    """
    entity_name = query_params.get('entity_name')
    if entity_name:
        values = [v.strip() for v in entity_name.split(',') if v.strip()]
        if len(values) == 1:
            queryset = queryset.filter(entity_name__iexact=values[0])
        elif values:
            queryset = queryset.filter(entity_name__in=values)

    department = query_params.get('department')
    if department:
        values = [v.strip() for v in department.split(',') if v.strip()]
        if len(values) == 1:
            queryset = queryset.filter(department__iexact=values[0])
        elif values:
            queryset = queryset.filter(department__in=values)

    procurement_method = query_params.get('procurement_method')
    if procurement_method:
        values = [v.strip() for v in procurement_method.split(',') if v.strip()]
        if len(values) == 1:
            queryset = queryset.filter(procurement_method__iexact=values[0])
        elif values:
            queryset = queryset.filter(procurement_method__in=values)

    proc_status = query_params.get('status')
    if proc_status:
        values = [v.strip() for v in proc_status.split(',') if v.strip()]
        if len(values) == 1:
            queryset = queryset.filter(status__iexact=values[0])
        elif values:
            queryset = queryset.filter(status__in=values)

    contract_type = query_params.get('contract_type')
    if contract_type:
        values = [v.strip() for v in contract_type.split(',') if v.strip()]
        if len(values) == 1:
            queryset = queryset.filter(contract_type__iexact=values[0])
        elif values:
            queryset = queryset.filter(contract_type__in=values)

    min_budget = query_params.get('min_budget')
    if min_budget:
        try:
            queryset = queryset.filter(base_price__gte=float(min_budget))
        except (ValueError, TypeError):
            pass

    max_budget = query_params.get('max_budget')
    if max_budget:
        try:
            queryset = queryset.filter(base_price__lte=float(max_budget))
        except (ValueError, TypeError):
            pass

    pub_from = query_params.get('publication_date_from')
    if pub_from:
        queryset = queryset.filter(publication_date__gte=pub_from)

    pub_to = query_params.get('publication_date_to')
    if pub_to:
        queryset = queryset.filter(publication_date__lte=pub_to)

    close_from = query_params.get('closing_date_from')
    if close_from:
        queryset = queryset.filter(closing_date__date__gte=close_from)

    close_to = query_params.get('closing_date_to')
    if close_to:
        queryset = queryset.filter(closing_date__date__lte=close_to)

    is_open = query_params.get('is_open')
    if is_open == 'true':
        queryset = queryset.filter(
            Q(status__in=SECOPProcess.APIStatus.ACTIVE_STATUSES),
            Q(closing_date__gte=timezone.now()) | Q(closing_date__isnull=True),
        )

    search = query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search) |
            Q(procedure_name__icontains=search) |
            Q(entity_name__icontains=search) |
            Q(reference__icontains=search)
        )

    # --- UNION: keywords OR UNSPSC codes (search broadening) ---
    search_union = Q()

    unspsc_code = query_params.get('unspsc_code')
    if unspsc_code:
        values = [v.strip() for v in unspsc_code.split(',') if v.strip()]
        if len(values) == 1:
            search_union |= Q(unspsc_code__icontains=values[0])
        elif values:
            search_union |= Q(unspsc_code__in=values)

    keywords = query_params.get('keywords')
    if keywords:
        phrases = [p.strip() for p in keywords.split('|') if p.strip()]
        for phrase in phrases:
            word_query = Q()
            for word in phrase.split():
                word_query &= (
                    Q(procedure_name__icontains=word) |
                    Q(description__icontains=word)
                )
            search_union |= word_query

    if search_union:
        queryset = queryset.filter(search_union)

    return queryset


# ---------------------------------------------------------------------------
# Process endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_process_list(request):
    """
    List SECOP processes with filtering, search, and pagination.

    Query params:
        search, entity_name, department, procurement_method, status,
        contract_type, min_budget, max_budget,
        publication_date_from, publication_date_to,
        closing_date_from, closing_date_to,
        is_open, ordering, page, page_size
    """
    queryset = SECOPProcess.objects.prefetch_related(
        Prefetch(
            'classifications',
            queryset=ProcessClassification.objects.filter(user=request.user),
            to_attr='_current_user_classifications',
        )
    ).all()
    queryset = _apply_secop_filters(queryset, request.query_params)

    # --- Ordering ---
    ordering = request.query_params.get('ordering', '-publication_date')
    if ordering in ALLOWED_ORDER_FIELDS:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-publication_date')

    # --- Pagination ---
    page_size = _safe_page_size(request.query_params)
    page_number = request.query_params.get('page', 1)

    paginator = Paginator(queryset, page_size)

    try:
        page = paginator.page(page_number)
    except Exception:
        page = paginator.page(1)

    serializer = SECOPProcessListSerializer(
        page.object_list,
        many=True,
        context={'request': request}
    )

    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page.number,
        'page_size': page_size,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_process_detail(request, pk):
    """
    Retrieve a single SECOP process with full detail.
    """
    try:
        process = SECOPProcess.objects.prefetch_related(
            Prefetch(
                'classifications',
                queryset=ProcessClassification.objects.select_related('user'),
                to_attr='_detail_classifications',
            )
        ).get(pk=pk)
    except SECOPProcess.DoesNotExist:
        return Response(
            {'detail': 'Process not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = SECOPProcessDetailSerializer(
        process,
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_my_classified(request):
    """
    List processes classified by the current user.

    Query params:
        classification_status: Filter by classification status
        page, page_size
    """
    classification_status = request.query_params.get('classification_status')

    classifications = ProcessClassification.objects.filter(
        user=request.user
    ).select_related('process')

    if classification_status:
        classifications = classifications.filter(status=classification_status)

    process_ids = classifications.values_list('process_id', flat=True)
    queryset = SECOPProcess.objects.filter(
        id__in=process_ids
    ).prefetch_related(
        Prefetch(
            'classifications',
            queryset=ProcessClassification.objects.filter(user=request.user),
            to_attr='_current_user_classifications',
        )
    ).order_by('-closing_date')

    page_size = _safe_page_size(request.query_params)
    page_number = request.query_params.get('page', 1)
    paginator = Paginator(queryset, page_size)

    try:
        page = paginator.page(page_number)
    except Exception:
        page = paginator.page(1)

    serializer = SECOPProcessListSerializer(
        page.object_list,
        many=True,
        context={'request': request}
    )

    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page.number,
        'page_size': page_size,
    })


# ---------------------------------------------------------------------------
# Classification endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def secop_create_classification(request):
    """
    Create or update a classification for a SECOP process.
    """
    serializer = ProcessClassificationSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        classification = serializer.save()
        return Response(
            ProcessClassificationSerializer(
                classification,
                context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def secop_delete_classification(request, pk):
    """
    Delete a classification. Users can only delete their own.
    """
    try:
        classification = ProcessClassification.objects.get(
            pk=pk, user=request.user
        )
    except ProcessClassification.DoesNotExist:
        return Response(
            {'detail': 'Classification not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    classification.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def secop_alerts_list_create(request):
    """
    GET: List alerts for the current user.
    POST: Create a new alert.
    """
    if request.method == 'GET':
        alerts = SECOPAlert.objects.filter(
            user=request.user
        ).annotate(
            _notification_count=Count('notifications')
        ).order_by('-created_at')
        serializer = SECOPAlertSerializer(alerts, many=True)
        return Response(serializer.data)

    # POST
    serializer = SECOPAlertSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        alert = serializer.save()
        return Response(
            SECOPAlertSerializer(alert).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def secop_alert_update_delete(request, pk):
    """
    PUT: Update an alert.
    DELETE: Delete an alert. Users can only manage their own.
    """
    try:
        alert = SECOPAlert.objects.get(pk=pk, user=request.user)
    except SECOPAlert.DoesNotExist:
        return Response(
            {'detail': 'Alert not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'DELETE':
        alert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT
    serializer = SECOPAlertSerializer(
        alert,
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def secop_alert_toggle(request, pk):
    """
    Toggle an alert's active status.
    """
    try:
        alert = SECOPAlert.objects.get(pk=pk, user=request.user)
    except SECOPAlert.DoesNotExist:
        return Response(
            {'detail': 'Alert not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    alert.is_active = not alert.is_active
    alert.save()
    return Response(SECOPAlertSerializer(alert).data)


# ---------------------------------------------------------------------------
# Saved view endpoints
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def secop_saved_views(request):
    """
    GET: List saved views for the current user.
    POST: Create a new saved view.
    """
    if request.method == 'GET':
        views = SavedView.objects.filter(
            user=request.user
        ).order_by('-created_at')
        serializer = SavedViewSerializer(views, many=True)
        return Response(serializer.data)

    # POST
    serializer = SavedViewSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        saved_view = serializer.save()
        return Response(
            SavedViewSerializer(saved_view).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def secop_delete_saved_view(request, pk):
    """
    PUT/PATCH: Update a saved view (name and/or filters). Both methods use partial updates.
    DELETE: Delete a saved view. Users can only delete their own.
    """
    try:
        saved_view = SavedView.objects.get(pk=pk, user=request.user)
    except SavedView.DoesNotExist:
        return Response(
            {'detail': 'Saved view not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'DELETE':
        saved_view.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT / PATCH — both use partial=True for consistent partial-update semantics
    serializer = SavedViewSerializer(
        saved_view,
        data=request.data,
        context={'request': request},
        partial=True,
    )
    if serializer.is_valid():
        serializer.save()
        return Response(SavedViewSerializer(saved_view).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def secop_saved_view_set_favorite(request, pk):
    """
    Toggle favorite status on a saved view.
    Only one view per user can be favorite at a time.
    """
    try:
        saved_view = SavedView.objects.get(pk=pk, user=request.user)
    except SavedView.DoesNotExist:
        return Response(
            {'detail': 'Saved view not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if saved_view.is_favorite:
        saved_view.is_favorite = False
        saved_view.save(update_fields=['is_favorite'])
    else:
        SavedView.objects.filter(
            user=request.user, is_favorite=True
        ).update(is_favorite=False)
        saved_view.is_favorite = True
        saved_view.save(update_fields=['is_favorite'])

    return Response(SavedViewSerializer(saved_view).data)


# ---------------------------------------------------------------------------
# Filter values & sync endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_available_filters(request):
    """
    Return distinct values for filter dropdowns.
    """
    departments = SECOPProcess.objects.exclude(
        department=''
    ).values_list(
        'department', flat=True
    ).distinct().order_by('department')

    procurement_methods = SECOPProcess.objects.exclude(
        procurement_method=''
    ).values_list(
        'procurement_method', flat=True
    ).distinct().order_by('procurement_method')

    statuses = SECOPProcess.objects.exclude(
        status=''
    ).values_list(
        'status', flat=True
    ).distinct().order_by('status')

    contract_types = SECOPProcess.objects.exclude(
        contract_type=''
    ).values_list(
        'contract_type', flat=True
    ).distinct().order_by('contract_type')

    entity_names = SECOPProcess.objects.exclude(
        entity_name=''
    ).values_list(
        'entity_name', flat=True
    ).distinct().order_by('entity_name')[:200]

    unspsc_codes = SECOPProcess.objects.exclude(
        unspsc_code=''
    ).values_list(
        'unspsc_code', flat=True
    ).distinct().order_by('unspsc_code')[:200]

    return Response({
        'departments': list(departments),
        'procurement_methods': list(procurement_methods),
        'statuses': list(statuses),
        'contract_types': list(contract_types),
        'entity_names': list(entity_names),
        'unspsc_codes': list(unspsc_codes),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_sync_status(request):
    """
    Return last sync status and recent sync history.
    """
    recent_logs = SyncLog.objects.all()[:5]
    serializer = SyncLogSerializer(recent_logs, many=True)

    last_success = SyncLog.objects.filter(
        status=SyncLog.Status.SUCCESS
    ).first()

    return Response({
        'last_success': SyncLogSerializer(last_success).data if last_success else None,
        'recent': serializer.data,
        'total_processes': SECOPProcess.objects.filter(
            Q(status__in=SECOPProcess.APIStatus.ACTIVE_STATUSES),
            Q(closing_date__gte=timezone.now()) | Q(closing_date__isnull=True),
        ).count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def secop_trigger_sync(request):
    """
    Trigger a manual SECOP sync. Restricted to lawyer-like users.
    """
    if not is_gym_staff(request.user):
        return Response(
            {'detail': 'Only lawyers and administrators can trigger sync.'},
            status=status.HTTP_403_FORBIDDEN
        )

    from gym_app.secop_tasks import sync_secop_data
    sync_secop_data.schedule(delay=0)

    return Response({'detail': 'Sync triggered.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secop_export_excel(request):
    """
    Export filtered SECOP processes to Excel.
    Applies the same filters as the list endpoint.
    """
    from openpyxl import Workbook
    from django.http import HttpResponse

    queryset = _apply_secop_filters(
        SECOPProcess.objects.all(), request.query_params
    ).only(
        'reference', 'entity_name', 'department', 'procedure_name',
        'procurement_method', 'contract_type', 'status', 'base_price',
        'publication_date', 'closing_date', 'process_url',
    ).order_by('-publication_date')[:500]

    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "SECOP Procesos"

    headers = [
        'Referencia', 'Entidad', 'Departamento', 'Objeto',
        'Modalidad', 'Tipo Contrato', 'Estado',
        'Presupuesto', 'Fecha Publicación', 'Fecha Cierre', 'URL'
    ]
    ws.append(headers)

    for process in queryset:
        ws.append([
            process.reference,
            process.entity_name,
            process.department,
            process.procedure_name[:200],
            process.procurement_method,
            process.contract_type,
            process.status,
            float(process.base_price) if process.base_price else '',
            str(process.publication_date) if process.publication_date else '',
            str(process.closing_date) if process.closing_date else '',
            process.process_url,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"secop_export_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
