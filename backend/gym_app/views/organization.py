from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, IntegerField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from gym_app.models import (
    Organization, OrganizationInvitation, OrganizationMembership, OrganizationPost,
    User, CorporateRequest
)
from gym_app.serializers.organization import (
    OrganizationSerializer, OrganizationListSerializer,
    OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMembershipSerializer, OrganizationInvitationSerializer,
    OrganizationInvitationCreateSerializer, OrganizationInvitationResponseSerializer,
    OrganizationStatsSerializer, UserBasicInfoSerializer,
    OrganizationPostSerializer, OrganizationPostListSerializer,
    OrganizationPostCreateSerializer, OrganizationPostUpdateSerializer
)

# Custom pagination class
class OrganizationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def _with_organization_list_relations(queryset):
    """Load organization summaries without multiplying independent counts."""
    active_members = (
        OrganizationMembership.objects.filter(organization_id=OuterRef('pk'), is_active=True)
        .order_by().values('organization_id').annotate(total=Count('pk')).values('total')
    )
    pending_invitations = (
        OrganizationInvitation.objects.filter(organization_id=OuterRef('pk'), status='PENDING')
        .order_by().values('organization_id').annotate(total=Count('pk')).values('total')
    )
    return queryset.select_related('corporate_client').annotate(
        _member_count=Coalesce(Subquery(active_members, output_field=IntegerField()), 0),
        _pending_invitations_count=Coalesce(
            Subquery(pending_invitations, output_field=IntegerField()), 0,
        ),
    )


def _with_invitation_list_relations(queryset):
    """Load each invitation's users and annotated organization summary."""
    return queryset.select_related('invited_by', 'invited_user').prefetch_related(
        Prefetch(
            'organization',
            queryset=_with_organization_list_relations(Organization.objects.all()),
        ),
    )


def _with_organization_detail_relations(queryset):
    """Load organization details with independent counts and active members."""
    recent_requests = (
        CorporateRequest.objects.filter(
            organization_id=OuterRef('pk'),
            created_at__gte=timezone.now() - timezone.timedelta(days=30),
        )
        .order_by().values('organization_id').annotate(total=Count('pk')).values('total')
    )
    return _with_organization_list_relations(queryset).annotate(
        _recent_requests_count=Coalesce(
            Subquery(recent_requests, output_field=IntegerField()), 0,
        ),
    ).prefetch_related(
        Prefetch(
            'memberships',
            queryset=OrganizationMembership.objects.filter(is_active=True).select_related('user'),
            to_attr='_active_memberships',
        ),
    )

# Decorators for role-based access
def require_corporate_client_only(view_func):
    """Decorator to ensure only corporate clients can access the view"""
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or request.user.role != 'corporate_client':
            return Response(
                {'error': 'Solo los clientes corporativos pueden acceder a este endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

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

def require_client_or_corporate_client(view_func):
    """Decorator to ensure only clients, basic users or corporate clients can access the view"""
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['client', 'basic', 'corporate_client']:
            return Response(
                {'error': 'Solo los clientes pueden acceder a este endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

# =============================================================================
# ENDPOINTS FOR CORPORATE CLIENTS (Organization Management)
# =============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def create_organization(request):
    """
    Create a new organization.
    Only corporate clients can create organizations.
    """
    serializer = OrganizationCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        organization = serializer.save()
        
        # Return the full created organization details
        response_serializer = OrganizationSerializer(
            organization,
            context={'request': request}
        )
        
        return Response({
            'message': 'Organización creada exitosamente',
            'organization': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al crear la organización',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_my_organizations(request):
    """
    Get organizations led by the current corporate client.
    """
    # Filter parameters
    search = request.GET.get('search', None)
    is_active = request.GET.get('is_active', None)
    
    # Base queryset - only organizations led by current user
    queryset = _with_organization_list_relations(
        Organization.objects.filter(corporate_client=request.user)
    )
    
    # Apply filters
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = OrganizationPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = OrganizationListSerializer(
            page, 
            many=True, 
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)
    
    serializer = OrganizationListSerializer(
        queryset, 
        many=True, 
        context={'request': request}
    )
    return Response({
        'organizations': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_detail(request, organization_id):
    """
    Get detailed information about a specific organization.
    Only the corporate client who leads the organization can view it.
    """
    organization = get_object_or_404(
        _with_organization_detail_relations(Organization.objects.all()),
        id=organization_id,
        corporate_client=request.user
    )
    
    serializer = OrganizationSerializer(
        organization,
        context={'request': request}
    )
    
    return Response({
        'organization': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['PUT', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def update_organization(request, organization_id):
    """
    Update an organization.
    Only the corporate client who leads the organization can update it.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    serializer = OrganizationUpdateSerializer(
        organization,
        data=request.data,
        partial=True,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated organization details
        response_serializer = OrganizationSerializer(
            organization,
            context={'request': request}
        )
        
        return Response({
            'message': 'Organización actualizada exitosamente',
            'organization': response_serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Error al actualizar la organización',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def delete_organization(request, organization_id):
    """
    Delete an organization.
    Only the corporate client who leads the organization can delete it.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    # Check if organization has active requests
    active_requests = organization.corporate_requests.filter(
        status__in=['PENDING', 'IN_REVIEW', 'RESPONDED']
    ).count()
    
    if active_requests > 0:
        return Response({
            'error': f'No se puede eliminar la organización. Tiene {active_requests} solicitudes activas.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    organization_title = organization.title
    organization.delete()
    
    return Response({
        'message': f'Organización "{organization_title}" eliminada exitosamente'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def send_organization_invitation(request, organization_id):
    """
    Send an invitation to join an organization.
    Only the corporate client who leads the organization can send invitations.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    serializer = OrganizationInvitationCreateSerializer(
        data=request.data,
        context={'organization': organization, 'request': request}
    )
    
    if serializer.is_valid():
        invitation = serializer.save()
        
        # Return the invitation details
        response_serializer = OrganizationInvitationSerializer(
            invitation,
            context={'request': request}
        )
        
        return Response({
            'message': 'Invitación enviada exitosamente',
            'invitation': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'error': 'Error al enviar la invitación',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_invitations(request, organization_id):
    """
    Get invitations for a specific organization.
    Only the corporate client who leads the organization can view invitations.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    # Filter parameters
    status_filter = request.GET.get('status', None)
    
    # Base queryset
    queryset = _with_invitation_list_relations(
        OrganizationInvitation.objects.filter(organization=organization)
    )
    
    # Apply filters
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = OrganizationPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = OrganizationInvitationSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)
    
    serializer = OrganizationInvitationSerializer(
        queryset,
        many=True,
        context={'request': request}
    )
    
    return Response({
        'invitations': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def cancel_organization_invitation(request, organization_id, invitation_id):
    """
    Cancel a pending organization invitation.
    Only the corporate client who sent the invitation can cancel it.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    invitation = get_object_or_404(
        OrganizationInvitation,
        id=invitation_id,
        organization=organization,
        invited_by=request.user
    )
    
    if invitation.status != 'PENDING':
        return Response({
            'error': 'Solo se pueden cancelar invitaciones pendientes'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    invitation.status = 'CANCELLED'
    invitation.save()
    
    return Response({
        'message': 'Invitación cancelada exitosamente'
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_members(request, organization_id):
    """
    Get members of a specific organization.
    Only the corporate client who leads the organization can view members.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    # Filter parameters
    is_active = request.GET.get('is_active', 'true')
    role_filter = request.GET.get('role', None)
    
    # Base queryset
    queryset = organization.memberships.select_related('user')
    
    # Apply filters
    if is_active.lower() == 'true':
        queryset = queryset.filter(is_active=True)
    elif is_active.lower() == 'false':
        queryset = queryset.filter(is_active=False)
    
    if role_filter:
        queryset = queryset.filter(role=role_filter)
    
    # Order by join date
    queryset = queryset.order_by('-joined_at')
    
    serializer = OrganizationMembershipSerializer(
        queryset,
        many=True,
        context={'request': request}
    )
    
    return Response({
        'members': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def remove_organization_member(request, organization_id, user_id):
    """
    Remove a member from an organization.
    Only the corporate client who leads the organization can remove members.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    membership = get_object_or_404(
        OrganizationMembership,
        organization=organization,
        user_id=user_id,
        is_active=True
    )
    
    # Cannot remove the leader
    if membership.role == 'LEADER':
        return Response({
            'error': 'No se puede remover al líder de la organización'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    membership.deactivate()
    
    return Response({
        'message': 'Miembro removido exitosamente'
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_stats(request):
    """
    Get dashboard statistics for organization management.
    """
    # Base queryset for current corporate client's organizations
    base_queryset = Organization.objects.filter(corporate_client=request.user)
    
    # Basic counts
    organization_counts = base_queryset.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=Q(is_active=True)),
    )
    total_organizations = organization_counts['total']
    active_organizations_count = organization_counts['active']
    
    # Member counts
    total_members = OrganizationMembership.objects.filter(
        organization__corporate_client=request.user,
        is_active=True
    ).count()
    
    # Invitation counts
    invitation_counts = OrganizationInvitation.objects.filter(
        organization__corporate_client=request.user,
    ).aggregate(
        pending=Count('pk', filter=Q(status='PENDING')),
        recent=Count('pk', filter=Q(
            created_at__gte=timezone.now() - timezone.timedelta(days=7),
        )),
    )
    total_pending_invitations = invitation_counts['pending']
    recent_invitations_count = invitation_counts['recent']
    
    # Recent requests count
    recent_requests_count = CorporateRequest.objects.filter(
        organization__corporate_client=request.user,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    # Organizations by status
    organizations_by_status = {
        'active': active_organizations_count,
        'inactive': total_organizations - active_organizations_count
    }
    
    stats_data = {
        'total_organizations': total_organizations,
        'total_members': total_members,
        'total_pending_invitations': total_pending_invitations,
        'recent_requests_count': recent_requests_count,
        'active_organizations_count': active_organizations_count,
        'organizations_by_status': organizations_by_status,
        'recent_invitations_count': recent_invitations_count
    }
    
    return Response(stats_data, status=status.HTTP_200_OK)

# =============================================================================
# ENDPOINTS FOR NORMAL CLIENTS (Invitation Management)
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def get_my_invitations(request):
    """
    Get invitations received by the current normal client.
    """
    # Filter parameters
    status_filter = request.GET.get('status', 'PENDING')
    
    # Base queryset - only invitations for current user
    queryset = _with_invitation_list_relations(
        OrganizationInvitation.objects.filter(invited_user=request.user)
    )
    
    # Apply filters
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = OrganizationPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = OrganizationInvitationSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)
    
    serializer = OrganizationInvitationSerializer(
        queryset,
        many=True,
        context={'request': request}
    )
    
    return Response({
        'invitations': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def respond_to_invitation(request, invitation_id):
    """
    Accept or reject an organization invitation.
    Only the invited normal client can respond.
    """
    invitation = get_object_or_404(
        OrganizationInvitation,
        id=invitation_id,
        invited_user=request.user
    )
    
    serializer = OrganizationInvitationResponseSerializer(
        invitation,
        data=request.data
    )
    
    if serializer.is_valid():
        try:
            serializer.save()
            
            # Return updated invitation details
            response_serializer = OrganizationInvitationSerializer(
                invitation,
                context={'request': request}
            )
            
            action = request.data.get('action')
            message = f'Invitación {"aceptada" if action == "accept" else "rechazada"} exitosamente'
            
            return Response({
                'message': message,
                'invitation': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'error': 'Error al responder a la invitación',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def get_my_memberships(request):
    """
    Get organizations where the current normal client is a member.
    """
    # Get active memberships
    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True
    ).prefetch_related(
        Prefetch(
            'organization',
            queryset=_with_organization_list_relations(Organization.objects.all()),
        ),
    )
    
    organizations = [membership.organization for membership in memberships]
    
    serializer = OrganizationListSerializer(
        organizations,
        many=True,
        context={'request': request}
    )
    
    return Response({
        'organizations': serializer.data,
        'total_count': len(serializer.data)
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_client_only
def leave_organization(request, organization_id):
    """
    Leave an organization.
    Only members can leave (not leaders).
    """
    membership = get_object_or_404(
        OrganizationMembership,
        organization_id=organization_id,
        user=request.user,
        is_active=True
    )
    
    # Leaders cannot leave their own organization
    if membership.role == 'LEADER':
        return Response({
            'error': 'Los líderes no pueden abandonar su propia organización'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    organization_title = membership.organization.title
    membership.deactivate()
    
    return Response({
        'message': f'Has abandonado la organización "{organization_title}" exitosamente'
    }, status=status.HTTP_200_OK)

# =============================================================================
# SHARED ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_client_or_corporate_client
def get_organization_public_detail(request, organization_id):
    """
    Get public information about an organization.
    Both clients and corporate clients can view this.
    """
    organization = get_object_or_404(
        _with_organization_detail_relations(Organization.objects.all()),
        id=organization_id,
        is_active=True,
    )
    
    # Check if user has access (either leader or member)
    has_access = False
    
    if request.user.role == 'corporate_client' and organization.corporate_client == request.user:
        has_access = True
    elif request.user.role in ['client', 'basic']:
        has_access = OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True
        ).exists()
    
    if not has_access:
        return Response({
            'error': 'No tienes acceso a esta organización'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = OrganizationSerializer(
        organization,
        context={'request': request}
    )
    
    return Response({
        'organization': serializer.data
    }, status=status.HTTP_200_OK)
