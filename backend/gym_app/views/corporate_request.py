from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, IntegerField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from gym_app.models import (
    CorporateRequest, CorporateRequestType, CorporateRequestFiles, 
    CorporateRequestResponse, User, Organization, OrganizationMembership
)
from gym_app.serializers.corporate_request import (
    CorporateRequestSerializer, CorporateRequestListSerializer,
    CorporateRequestCreateSerializer, CorporateRequestUpdateSerializer,
    CorporateRequestTypeSerializer, CorporateRequestFilesSerializer,
    CorporateRequestResponseSerializer, UserBasicInfoSerializer
)

# Custom pagination class
class CorporateRequestPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def _with_list_relations(queryset):
    """Load list fields without per-request queries or an outer GROUP BY."""
    response_counts = (
        CorporateRequestResponse.objects.filter(corporate_request_id=OuterRef('pk'))
        .order_by().values('corporate_request_id').annotate(total=Count('pk')).values('total')
    )
    return queryset.select_related(
        'client', 'corporate_client', 'organization', 'request_type',
    ).annotate(
        _response_count=Coalesce(Subquery(response_counts, output_field=IntegerField()), 0),
    )


def _with_detail_relations(queryset):
    """Load detail fields and keep responses in the related manager's cache."""
    return queryset.select_related(
        'client', 'corporate_client', 'assigned_to', 'organization', 'request_type',
    ).prefetch_related(
        'files',
        Prefetch(
            'responses',
            queryset=CorporateRequestResponse.objects.select_related('user').prefetch_related(
                'response_files',
            ),
        ),
    )


# Decorators for role-based access
def require_client_only(view_func):
    """Decorator to ensure only normal clients and basic users can access the view"""
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['client', 'basic']:
            return Response(
                {'error': 'Solo los clientes normales y usuarios básicos pueden acceder a este endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

def require_corporate_client_only(view_func):
    """Decorator to ensure only corporate clients can access the view"""
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'corporate_client':
            return Response(
                {'error': 'Solo los clientes corporativos pueden acceder a este endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

def require_client_or_corporate_client(view_func):
    """Decorator to ensure only clients, basic users, or corporate clients can access the view"""
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['client', 'basic', 'corporate_client']:
            return Response(
                {'error': 'Solo los clientes pueden acceder a este endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

# =============================================================================
# ENDPOINTS FOR NORMAL CLIENTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_get_my_organizations(request):
    """
    Get organizations where the current client is a member.
    Only normal clients can access this endpoint.
    """
    # Get active memberships
    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('organization__corporate_client')
    
    organizations_data = []
    for membership in memberships:
        org = membership.organization
        organizations_data.append({
            'id': org.id,
            'title': org.title,
            'description': org.description,
            'profile_image': org.profile_image.url if org.profile_image else None,
            'cover_image': org.cover_image.url if org.cover_image else None,
            'corporate_client': {
                'id': org.corporate_client.id,
                'email': org.corporate_client.email,
                'full_name': f"{org.corporate_client.first_name} {org.corporate_client.last_name}".strip()
            },
            'member_role': membership.role,
            'joined_at': membership.joined_at
        })
    
    return Response({
        'organizations': organizations_data,
        'total_count': len(organizations_data)
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_get_request_types(request):
    """
    Get list of available corporate request types.
    Only normal clients can access this endpoint.
    """
    request_types = CorporateRequestType.objects.all().order_by('name')
    serializer = CorporateRequestTypeSerializer(request_types, many=True)
    
    return Response({
        'request_types': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_create_corporate_request(request):
    """
    Create a new corporate request.
    Only normal clients can create requests.
    """
    serializer = CorporateRequestCreateSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        corporate_request = serializer.save()
        
        # Return the full created request details
        response_serializer = CorporateRequestSerializer(
            corporate_request, 
            context={'request': request}
        )
        
        return Response({
            'message': 'Solicitud corporativa creada exitosamente',
            'corporate_request': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al crear la solicitud corporativa',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_get_my_corporate_requests(request):
    """
    Get list of corporate requests created by the current normal client.
    """
    # Filter parameters
    status_filter = request.GET.get('status', None)
    priority_filter = request.GET.get('priority', None)
    search = request.GET.get('search', None)
    
    # Base queryset - only requests created by current client
    queryset = _with_list_relations(CorporateRequest.objects.filter(client=request.user))
    
    # Apply filters
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(request_number__icontains=search)
        )
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')

    # Pagination
    paginator = CorporateRequestPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = CorporateRequestListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    serializer = CorporateRequestListSerializer(queryset, many=True, context={'request': request})
    return Response({
        'corporate_requests': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_get_corporate_request_detail(request, request_id):
    """
    Get detailed information about a specific corporate request.
    Only the client who created the request can view it.
    """
    corporate_request = get_object_or_404(
        _with_detail_relations(CorporateRequest.objects.all()),
        id=request_id, 
        client=request.user
    )
    
    serializer = CorporateRequestSerializer(
        corporate_request, 
        context={'request': request}
    )
    
    return Response({
        'corporate_request': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def client_add_response_to_request(request, request_id):
    """
    Add a response to a corporate request.
    Only the client who created the request can add responses.
    """
    corporate_request = get_object_or_404(
        CorporateRequest, 
        id=request_id, 
        client=request.user
    )
    
    # Validate response text
    response_text = request.data.get('response_text', '').strip()
    if not response_text:
        return Response({
            'error': 'Error al añadir la respuesta',
            'details': {'response_text': ['Este campo no puede estar vacío.']}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Prepare data for response creation
    response_data = {
        'corporate_request': corporate_request.id,
        'response_text': response_text,
        'is_internal_note': False  # Client responses are never internal notes
    }
    
    serializer = CorporateRequestResponseSerializer(
        data=response_data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        response = serializer.save()
        
        return Response({
            'message': 'Respuesta añadida exitosamente',
            'response': CorporateRequestResponseSerializer(response).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al añadir la respuesta',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# =============================================================================
# ENDPOINTS FOR CORPORATE CLIENTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def corporate_get_received_requests(request):
    """
    Get list of corporate requests received by the current corporate client.
    """
    # Filter parameters
    status_filter = request.GET.get('status', None)
    priority_filter = request.GET.get('priority', None)
    search = request.GET.get('search', None)
    assigned_to_me = request.GET.get('assigned_to_me', None)
    
    # Base queryset - only requests for current corporate client
    queryset = _with_list_relations(CorporateRequest.objects.filter(corporate_client=request.user))
    
    # Apply filters
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    if assigned_to_me == 'true':
        queryset = queryset.filter(assigned_to=request.user)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(request_number__icontains=search) |
            Q(client__email__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    # Order by priority and creation date
    priority_order = ['URGENT', 'HIGH', 'MEDIUM', 'LOW']
    queryset = queryset.extra(
        select={'priority_order': f"CASE priority {' '.join([f'WHEN \'{p}\' THEN {i}' for i, p in enumerate(priority_order)])} END"}
    ).order_by('priority_order', '-created_at')
    
    # Pagination
    paginator = CorporateRequestPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = CorporateRequestListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    serializer = CorporateRequestListSerializer(queryset, many=True, context={'request': request})
    return Response({
        'corporate_requests': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def corporate_get_request_detail(request, request_id):
    """
    Get detailed information about a specific corporate request.
    Only the corporate client who received the request can view it.
    """
    corporate_request = get_object_or_404(
        _with_detail_relations(CorporateRequest.objects.all()),
        id=request_id, 
        corporate_client=request.user
    )
    
    serializer = CorporateRequestSerializer(
        corporate_request, 
        context={'request': request}
    )
    
    return Response({
        'corporate_request': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def corporate_update_request_status(request, request_id):
    """
    Update the status and management fields of a corporate request.
    Only the corporate client who received the request can update it.
    """
    corporate_request = get_object_or_404(
        _with_detail_relations(CorporateRequest.objects.all()).select_related(
            'organization__corporate_client',
        ),
        id=request_id, 
        corporate_client=request.user
    )
    
    serializer = CorporateRequestUpdateSerializer(
        corporate_request, 
        data=request.data, 
        partial=True
    )
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated request details
        response_serializer = CorporateRequestSerializer(
            corporate_request, 
            context={'request': request}
        )
        
        return Response({
            'message': 'Solicitud actualizada exitosamente',
            'corporate_request': response_serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Error al actualizar la solicitud',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def corporate_add_response_to_request(request, request_id):
    """
    Add a response to a corporate request.
    Only the corporate client who received the request can add responses.
    """
    print(f"🔍 DEBUG - Corporate add response: request_id={request_id}, user={request.user.email}")
    print(f"🔍 DEBUG - Request data: {request.data}")
    
    corporate_request = get_object_or_404(
        CorporateRequest, 
        id=request_id, 
        corporate_client=request.user
    )
    
    print(f"🔍 DEBUG - Found corporate request: {corporate_request.request_number}")
    
    # Validate response text - handle both string and nested object formats
    response_text_raw = request.data.get('response_text', '')
    
    # If response_text is a dict (nested), extract the actual text
    if isinstance(response_text_raw, dict):
        response_text = response_text_raw.get('response_text', '').strip()
        is_internal_note = response_text_raw.get('is_internal_note', False)
    else:
        response_text = str(response_text_raw).strip()
        is_internal_note = request.data.get('is_internal_note', False)
    
    print(f"🔍 DEBUG - Extracted response_text: '{response_text}', is_internal_note: {is_internal_note}")
    
    if not response_text:
        print("❌ DEBUG - Empty response text")
        return Response({
            'error': 'Error al añadir la respuesta',
            'details': {'response_text': ['Este campo no puede estar vacío.']}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Prepare data for response creation
    response_data = {
        'corporate_request': corporate_request.id,
        'response_text': response_text,
        'is_internal_note': is_internal_note
    }
    
    print(f"🔍 DEBUG - Response data prepared: {response_data}")
    
    serializer = CorporateRequestResponseSerializer(
        data=response_data, 
        context={'request': request}
    )
    
    print(f"🔍 DEBUG - Serializer valid: {serializer.is_valid()}")
    if not serializer.is_valid():
        print(f"❌ DEBUG - Serializer errors: {serializer.errors}")
    
    if serializer.is_valid():
        response = serializer.save()
        
        return Response({
            'message': 'Respuesta añadida exitosamente',
            'response': CorporateRequestResponseSerializer(response).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al añadir la respuesta',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def corporate_get_dashboard_stats(request):
    """
    Get dashboard statistics for corporate client.
    """
    # Base queryset for current corporate client
    base_queryset = CorporateRequest.objects.filter(corporate_client=request.user)
    
    now = timezone.now()
    status_aggregates = {
        f'status_{code}': Count('pk', filter=Q(status=code))
        for code, _ in CorporateRequest.STATUS_CHOICES
    }
    priority_aggregates = {
        f'priority_{code}': Count('pk', filter=Q(priority=code))
        for code, _ in CorporateRequest.PRIORITY_CHOICES
    }
    counts = base_queryset.aggregate(
        total_requests=Count('pk'),
        recent_requests_count=Count(
            'pk', filter=Q(created_at__gte=now - timezone.timedelta(days=7))
        ),
        assigned_to_me_count=Count('pk', filter=Q(assigned_to=request.user)),
        overdue_count=Count('pk', filter=Q(
            estimated_completion_date__lt=now,
            status__in=['PENDING', 'IN_REVIEW'],
        )),
        **status_aggregates,
        **priority_aggregates,
    )
    
    return Response({
        'total_requests': counts['total_requests'],
        'status_counts': {
            code: counts[f'status_{code}']
            for code, _ in CorporateRequest.STATUS_CHOICES
        },
        'priority_counts': {
            code: counts[f'priority_{code}']
            for code, _ in CorporateRequest.PRIORITY_CHOICES
        },
        'recent_requests_count': counts['recent_requests_count'],
        'assigned_to_me_count': counts['assigned_to_me_count'],
        'overdue_count': counts['overdue_count'],
    }, status=status.HTTP_200_OK)

# =============================================================================
# SHARED ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_or_corporate_client
def get_request_conversation(request, request_id):
    """
    Get the conversation thread for a corporate request.
    Both clients and corporate clients can view conversations for their requests.
    """
    # Check access permissions
    if request.user.role == 'client':
        corporate_request = get_object_or_404(
            CorporateRequest, 
            id=request_id, 
            client=request.user
        )
    elif request.user.role == 'corporate_client':
        corporate_request = get_object_or_404(
            CorporateRequest, 
            id=request_id, 
            corporate_client=request.user
        )
    else:
        return Response(
            {'error': 'Acceso no autorizado'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filter responses based on user type
    if request.user.role == 'client':
        # Clients can't see internal notes
        responses = corporate_request.responses.filter(is_internal_note=False)
    else:
        # Corporate clients can see all responses
        responses = corporate_request.responses.all()
    
    responses = responses.select_related('user').prefetch_related(
        'response_files'
    ).order_by('created_at')
    serializer = CorporateRequestResponseSerializer(responses, many=True)
    
    return Response({
        'request_number': corporate_request.request_number,
        'title': corporate_request.title,
        'status': corporate_request.status,
        'responses': serializer.data,
        'total_responses': len(serializer.data)
    }, status=status.HTTP_200_OK)
