from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from gym_app.models import (
    Organization, OrganizationPost, OrganizationMembership
)
from gym_app.serializers.organization import (
    OrganizationPostSerializer, OrganizationPostListSerializer,
    OrganizationPostCreateSerializer, OrganizationPostUpdateSerializer
)

# Custom pagination class
class OrganizationPostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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


# ========================================
# Organization Posts Management
# ========================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def create_organization_post(request, organization_id):
    """
    Create a new post for an organization.
    Only the corporate client who leads the organization can create posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    # Add organization to request data
    data = request.data.copy()
    data['organization'] = organization.id
    
    serializer = OrganizationPostCreateSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Post creado exitosamente',
            'post': OrganizationPostSerializer(serializer.instance, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    # Expose the names of fields with validation errors in a flat list so
    # callers (and tests) can easily inspect which fields failed.
    error_fields = list(serializer.errors.keys())

    return Response({
        'error': 'Error al crear el post',
        'details': error_fields,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_posts(request, organization_id):
    """
    Get posts for an organization.
    Only the corporate client who leads the organization can view all posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    # Filter parameters
    is_active = request.GET.get('is_active', None)
    is_pinned = request.GET.get('is_pinned', None)
    search = request.GET.get('search', None)
    
    # Base queryset
    queryset = OrganizationPost.objects.filter(organization=organization).select_related('author')
    
    # Apply filters
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        queryset = queryset.filter(is_active=is_active_bool)
    
    if is_pinned is not None:
        is_pinned_bool = is_pinned.lower() == 'true'
        queryset = queryset.filter(is_pinned=is_pinned_bool)
    
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(link_name__icontains=search)
        )
    
    # Order by pinned first, then by creation date
    queryset = queryset.order_by('-is_pinned', '-created_at')
    
    paginator = OrganizationPostPagination()
    result_page = paginator.paginate_queryset(queryset, request)
    serializer = OrganizationPostListSerializer(result_page, many=True, context={'request': request})
    
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_organization_posts_public(request, organization_id):
    """
    Get active posts for an organization (public view for members).
    Available to organization members and corporate client.
    """
    organization = get_object_or_404(Organization, id=organization_id)
    
    # Check if user is a member or the leader
    if request.user.role == 'corporate_client' and organization.corporate_client == request.user:
        # Corporate client can see all active posts
        pass
    elif request.user.role in ['client', 'basic']:
        # Check if client or basic user is a member
        is_member = OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True
        ).exists()
        
        if not is_member:
            return Response({
                'error': 'No tienes acceso a los posts de esta organización'
            }, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({
            'error': 'No tienes acceso a los posts de esta organización'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Only show active posts to members
    queryset = OrganizationPost.objects.filter(
        organization=organization,
        is_active=True
    ).select_related('author').order_by('-is_pinned', '-created_at')
    
    # Filter parameters
    search = request.GET.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(link_name__icontains=search)
        )
    
    paginator = OrganizationPostPagination()
    result_page = paginator.paginate_queryset(queryset, request)
    serializer = OrganizationPostListSerializer(result_page, many=True, context={'request': request})
    
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def get_organization_post_detail(request, organization_id, post_id):
    """
    Get detailed information about a specific organization post.
    Only the corporate client who leads the organization can view post details.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    post = get_object_or_404(
        OrganizationPost,
        id=post_id,
        organization=organization
    )
    
    serializer = OrganizationPostSerializer(post, context={'request': request})
    
    return Response({
        'post': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def update_organization_post(request, organization_id, post_id):
    """
    Update an organization post.
    Only the corporate client who leads the organization can update posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    post = get_object_or_404(
        OrganizationPost,
        id=post_id,
        organization=organization
    )
    
    serializer = OrganizationPostUpdateSerializer(
        post,
        data=request.data,
        partial=True,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Post actualizado exitosamente',
            'post': OrganizationPostSerializer(serializer.instance, context={'request': request}).data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Error al actualizar el post',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def delete_organization_post(request, organization_id, post_id):
    """
    Delete an organization post.
    Only the corporate client who leads the organization can delete posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    post = get_object_or_404(
        OrganizationPost,
        id=post_id,
        organization=organization
    )
    
    post.delete()
    
    return Response({
        'message': 'Post eliminado exitosamente'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def toggle_organization_post_pin(request, organization_id, post_id):
    """
    Toggle the pinned status of an organization post.
    Only the corporate client who leads the organization can pin/unpin posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    post = get_object_or_404(
        OrganizationPost,
        id=post_id,
        organization=organization
    )
    
    post.toggle_pin()
    
    return Response({
        'message': f'Post {"fijado" if post.is_pinned else "desfijado"} exitosamente',
        'post': OrganizationPostSerializer(post, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_corporate_client_only
def toggle_organization_post_status(request, organization_id, post_id):
    """
    Toggle the active status of an organization post.
    Only the corporate client who leads the organization can activate/deactivate posts.
    """
    organization = get_object_or_404(
        Organization,
        id=organization_id,
        corporate_client=request.user
    )
    
    post = get_object_or_404(
        OrganizationPost,
        id=post_id,
        organization=organization
    )
    
    if post.is_active:
        post.deactivate()
        message = 'Post desactivado exitosamente'
    else:
        post.reactivate()
        message = 'Post activado exitosamente'
    
    return Response({
        'message': message,
        'post': OrganizationPostSerializer(post, context={'request': request}).data
    }, status=status.HTTP_200_OK)
