"""
Views for managing document permissions.

This module contains views that allow lawyers to manage document visibility 
and usability permissions for clients.

Public Documents:
- Documents with is_public=True are accessible to all authenticated users
- No explicit permissions need to be managed for public documents
- Lawyers can toggle is_public to make documents universally accessible
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from gym_app.models.dynamic_document import (
    DynamicDocument, 
    DocumentVisibilityPermission, 
    DocumentUsabilityPermission
)
from .permissions import require_lawyer_or_owner, require_lawyer_only

User = get_user_model()

MAX_ROLE_VISIBILITY_QUERIES = 8
ROLE_PERMISSION_INSERT_SIZE = 1000


def _grant_role_visibility(document, users, granted_by):
    """Insert missing permissions together, retaining get_or_create race semantics."""
    try:
        with transaction.atomic():
            # Serialize role grants for this document, including their response.
            DynamicDocument.objects.select_for_update().get(pk=document.pk)
            users = list(users)
            existing = set(DocumentVisibilityPermission.objects.filter(
                document=document, user_id__in=[user.pk for user in users],
            ).values_list('user_id', flat=True))
            missing = [DocumentVisibilityPermission(
                document=document, user=user, granted_by=granted_by,
            ) for user in users if user.pk not in existing]
            DocumentVisibilityPermission.objects.bulk_create(
                missing, batch_size=ROLE_PERMISSION_INSERT_SIZE,
            )
            return [(user, user.pk not in existing) for user in users]
    except IntegrityError:
        # A single-user grant can race the bulk insert without taking our lock.
        # The failed transaction has rolled back: only get_or_create can tell
        # which permissions this request actually created in that case.
        with transaction.atomic():
            return [(user, DocumentVisibilityPermission.objects.get_or_create(
                document=document, user=user, defaults={'granted_by': granted_by},
            )[1]) for user in users]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def get_document_permissions(request, pk):
    """
    Get all visibility and usability permissions for a specific document.
    
    Returns:
        dict: Contains lists of users with visibility and usability permissions,
              plus document public status
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        # Get all visibility permissions
        visibility_permissions = DocumentVisibilityPermission.objects.filter(
            document=document
        ).select_related('user', 'granted_by')
        
        # Get all usability permissions  
        usability_permissions = DocumentUsabilityPermission.objects.filter(
            document=document
        ).select_related('user', 'granted_by')
        
        # Format response data
        visibility_users = []
        for perm in visibility_permissions:
            user_data = {
                'user_id': perm.user.id,
                'email': perm.user.email,
                'full_name': f"{perm.user.first_name} {perm.user.last_name}".strip(),
                'granted_by': perm.granted_by.email if perm.granted_by else None,
                'granted_at': perm.granted_at
            }
            visibility_users.append(user_data)
        
        usability_users = []
        for perm in usability_permissions:
            user_data = {
                'user_id': perm.user.id,
                'email': perm.user.email,
                'full_name': f"{perm.user.first_name} {perm.user.last_name}".strip(),
                'granted_by': perm.granted_by.email if perm.granted_by else None,
                'granted_at': perm.granted_at
            }
            usability_users.append(user_data)
        
        # Group users by role for role-based permissions display
        visibility_roles = set()
        usability_roles = set()
        
        for perm in visibility_permissions:
            if perm.user.role and perm.user.role != 'lawyer':
                visibility_roles.add(perm.user.role)
        
        for perm in usability_permissions:
            if perm.user.role and perm.user.role != 'lawyer':
                usability_roles.add(perm.user.role)
        
        # Check if all users of a role have the permission (to determine if it's a role-based permission)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        active_visibility_roles = []
        active_usability_roles = []
        
        for role in visibility_roles:
            # Count users with this role
            total_users_with_role = User.objects.filter(role=role).exclude(role='lawyer').count()
            # Count users with this role that have permission
            users_with_permission = visibility_permissions.filter(user__role=role).count()
            
            # If all users of this role have permission, consider it a role-based permission
            if total_users_with_role > 0 and users_with_permission == total_users_with_role:
                active_visibility_roles.append(role)
        
        for role in usability_roles:
            total_users_with_role = User.objects.filter(role=role).exclude(role='lawyer').count()
            users_with_permission = usability_permissions.filter(user__role=role).count()
            
            if total_users_with_role > 0 and users_with_permission == total_users_with_role:
                active_usability_roles.append(role)
        
        response_data = {
            'document_id': document.id,
            'document_title': document.title,
            'is_public': document.is_public,
            'visibility_permissions': visibility_users,
            'usability_permissions': usability_users,
            'active_roles': {
                'visibility_roles': active_visibility_roles,
                'usability_roles': active_usability_roles
            },
            'summary': {
                'total_visibility_users': len(visibility_users),
                'total_usability_users': len(usability_users)
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {'detail': f'Internal server error: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def manage_document_permissions_unified(request, pk):
    """
    ENDPOINT UNIFICADO para gestionar TODOS los permisos de un documento.
    
    Maneja en una sola llamada:
    - Estado público/privado del documento
    - Permisos por roles (visibility y usability)
    - Permisos por usuarios específicos (visibility y usability)
    - Exclusiones de usuarios específicos
    
    Expected payload:
    {
        "is_public": true/false,                    // Opcional: estado público del documento
        "visibility": {
            "roles": ["client", "basic"],           // Opcional: roles con permisos de visibilidad
            "user_ids": [45, 67, 89],              // Opcional: usuarios específicos con visibilidad
            "exclude_user_ids": [12, 34]           // Opcional: excluir usuarios específicos
        },
        "usability": {
            "roles": ["client"],                    // Opcional: roles con permisos de uso
            "user_ids": [45, 67],                  // Opcional: usuarios específicos con uso
            "exclude_user_ids": [89]               // Opcional: excluir usuarios específicos
        }
    }
    
    Ejemplos de uso:
    
    1. Solo hacer público:
    {"is_public": true}
    
    2. Hacer privado y dar permisos a clientes:
    {"is_public": false, "visibility": {"roles": ["client"]}, "usability": {"roles": ["client"]}}
    
    3. Combinado completo:
    {
        "is_public": false,
        "visibility": {
            "roles": ["client", "basic"],
            "user_ids": [45],
            "exclude_user_ids": [67]
        },
        "usability": {
            "roles": ["client"],
            "user_ids": [45]
        }
    }
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        # Variables para tracking
        changes_made = []
        warnings = []
        errors = []
        
        # 1. MANEJAR ESTADO PÚBLICO
        is_public = request.data.get('is_public')
        if is_public is not None:
            old_public = document.is_public
            document.is_public = is_public
            document.save(update_fields=['is_public'])
            changes_made.append(f"Document changed from {'public' if old_public else 'private'} to {'public' if is_public else 'private'}")
            
            if is_public:
                warnings.append("Document is now public - all users have automatic access regardless of explicit permissions")
        
        # 2. PROCESAR PERMISOS DE VISIBILIDAD (REEMPLAZAR COMPLETAMENTE)
        visibility_granted = []
        visibility_removed = []
        
        visibility_config = request.data.get('visibility')
        if visibility_config is not None:  # Si se proporciona visibility config (incluso si está vacío)
            
            # PASO 1: Eliminar TODOS los permisos de visibilidad existentes
            existing_permissions = DocumentVisibilityPermission.objects.filter(document=document)
            for perm in existing_permissions:
                visibility_removed.append({
                    'user_id': perm.user.id,
                    'email': perm.user.email,
                    'full_name': f"{perm.user.first_name} {perm.user.last_name}".strip(),
                    'role': perm.user.role
                })
            
            deleted_count = existing_permissions.delete()[0]
            
            # PASO 2: Recopilar usuarios objetivo para los NUEVOS permisos
            target_users = set()
            
            # Usuarios por roles
            roles = visibility_config.get('roles', [])
            if roles:
                valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
                invalid_roles = [role for role in roles if role not in valid_roles]
                if invalid_roles:
                    errors.append(f"Invalid visibility roles: {invalid_roles}")
                else:
                    target_roles = [role for role in roles if role != 'lawyer']
                    users_from_roles = User.objects.filter(role__in=target_roles)
                    target_users.update(users_from_roles)
            
            # Usuarios específicos
            user_ids = visibility_config.get('user_ids', [])
            if user_ids:
                users_from_ids = User.objects.filter(id__in=user_ids)
                if len(users_from_ids) != len(user_ids):
                    found_ids = [user.id for user in users_from_ids]
                    missing_ids = [uid for uid in user_ids if uid not in found_ids]
                    errors.append(f"Visibility users not found: {missing_ids}")
                else:
                    target_users.update(users_from_ids)
            
            # Excluir usuarios
            exclude_user_ids = visibility_config.get('exclude_user_ids', [])
            if exclude_user_ids:
                excluded_users = User.objects.filter(id__in=exclude_user_ids)
                target_users = target_users - set(excluded_users)
            
            # PASO 3: Crear los NUEVOS permisos de visibilidad
            with transaction.atomic():
                for user in target_users:
                    if user.role == 'lawyer' or user.is_gym_lawyer:
                        continue
                    
                    permission = DocumentVisibilityPermission.objects.create(
                        document=document,
                        user=user,
                        granted_by=request.user
                    )
                    
                    visibility_granted.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role
                    })
            
            changes_made.append(f"Visibility permissions REPLACED: removed {len(visibility_removed)}, granted {len(visibility_granted)} users")
        
        # 3. PROCESAR PERMISOS DE USO (REEMPLAZAR COMPLETAMENTE)
        usability_granted = []
        usability_removed = []
        usability_errors = []
        
        usability_config = request.data.get('usability')
        if usability_config is not None:  # Si se proporciona usability config (incluso si está vacío)
            
            # PASO 1: Eliminar TODOS los permisos de uso existentes
            existing_permissions = DocumentUsabilityPermission.objects.filter(document=document)
            for perm in existing_permissions:
                usability_removed.append({
                    'user_id': perm.user.id,
                    'email': perm.user.email,
                    'full_name': f"{perm.user.first_name} {perm.user.last_name}".strip(),
                    'role': perm.user.role
                })
            
            deleted_count = existing_permissions.delete()[0]
            
            # PASO 2: Recopilar usuarios objetivo para los NUEVOS permisos
            target_users = set()
            
            # Usuarios por roles
            roles = usability_config.get('roles', [])
            if roles:
                valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
                invalid_roles = [role for role in roles if role not in valid_roles]
                if invalid_roles:
                    errors.append(f"Invalid usability roles: {invalid_roles}")
                else:
                    target_roles = [role for role in roles if role != 'lawyer']
                    users_from_roles = User.objects.filter(role__in=target_roles)
                    target_users.update(users_from_roles)
            
            # Usuarios específicos
            user_ids = usability_config.get('user_ids', [])
            if user_ids:
                users_from_ids = User.objects.filter(id__in=user_ids)
                if len(users_from_ids) != len(user_ids):
                    found_ids = [user.id for user in users_from_ids]
                    missing_ids = [uid for uid in user_ids if uid not in found_ids]
                    errors.append(f"Usability users not found: {missing_ids}")
                else:
                    target_users.update(users_from_ids)
            
            # Excluir usuarios
            exclude_user_ids = usability_config.get('exclude_user_ids', [])
            if exclude_user_ids:
                excluded_users = User.objects.filter(id__in=exclude_user_ids)
                target_users = target_users - set(excluded_users)
            
            # PASO 3: Crear los NUEVOS permisos de uso
            with transaction.atomic():
                for user in target_users:
                    if user.role == 'lawyer' or user.is_gym_lawyer:
                        continue
                    
                    # Verificar que tenga permisos de visibilidad (a menos que sea público)
                    if not document.is_public:
                        has_visibility = DocumentVisibilityPermission.objects.filter(
                            document=document, user=user
                        ).exists()
                        
                        if not has_visibility:
                            usability_errors.append({
                                'user_id': user.id,
                                'email': user.email,
                                'role': user.role,
                                'error': 'User must have visibility permission first (or document must be public)'
                            })
                            continue
                    
                    permission = DocumentUsabilityPermission.objects.create(
                        document=document,
                        user=user,
                        granted_by=request.user
                    )
                    
                    usability_granted.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role
                    })
            
            changes_made.append(f"Usability permissions REPLACED: removed {len(usability_removed)}, granted {len(usability_granted)} users")
        
        # 4. PREPARAR RESPUESTA
        response_data = {
            'document_id': document.id,
            'document_title': document.title,
            'is_public': document.is_public,
            'changes_made': changes_made,
            'results': {
                'visibility': {
                    'granted': visibility_granted,
                    'removed': visibility_removed
                },
                'usability': {
                    'granted': usability_granted,
                    'removed': usability_removed,
                    'errors': usability_errors
                }
            },
            'warnings': warnings,
            'errors': errors,
            'summary': {
                'total_visibility_granted': len(visibility_granted),
                'total_visibility_removed': len(visibility_removed),
                'total_usability_granted': len(usability_granted),
                'total_usability_removed': len(usability_removed),
                'total_errors': len(errors) + len(usability_errors)
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {'detail': f'Internal server error: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def toggle_public_access(request, pk):
    """
    Toggle the public access status of a document.
    
    When is_public=True, all authenticated users can view and edit the document.
    When is_public=False, only users with explicit permissions can access it.
    
    Two ways to use this endpoint:
    
    1. Automatic toggle (no payload needed):
       POST /api/dynamic-documents/{id}/permissions/public/toggle/
       (toggles the current state)
    
    2. Set specific value (with payload):
       POST /api/dynamic-documents/{id}/permissions/public/toggle/
       {
           "is_public": true/false
       }
    """
    
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        is_public = request.data.get('is_public')
        
        # If no is_public provided, toggle the current state
        if is_public is None:
            is_public = not document.is_public
        
        old_value = document.is_public
        document.is_public = is_public
        document.save(update_fields=['is_public'])
        
        status_text = "public" if is_public else "private"
        action_text = "toggled to" if request.data.get('is_public') is None else "changed to"
        
        
        return Response({
            'document_id': document.id,
            'document_title': document.title,
            'is_public': document.is_public,
            'message': f'Document access {action_text} {status_text}.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_visibility_permissions(request, pk):
    """
    Grant visibility permissions to multiple users for a document.
    
    Note: If document is public, explicit permissions are not necessary
    but can still be granted for tracking purposes.
    
    Expected payload:
    {
        "user_ids": [1, 2, 3, ...]
    }
    """
    
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'detail': 'user_ids list is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all users exist
        users = User.objects.filter(id__in=user_ids)
        if len(users) != len(user_ids):
            found_ids = [user.id for user in users]
            missing_ids = [uid for uid in user_ids if uid not in found_ids]
            return Response(
                {'detail': f'Users not found: {missing_ids}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Grant permissions (use get_or_create to avoid duplicates)
        created_permissions = []
        skipped_lawyers = []
        
        with transaction.atomic():
            for user in users:
                
                # Skip if user is lawyer (they have automatic access)
                if user.role == 'lawyer' or user.is_gym_lawyer:
                    skipped_lawyers.append(user.email)
                    continue
                    
                permission, created = DocumentVisibilityPermission.objects.get_or_create(
                    document=document,
                    user=user,
                    defaults={'granted_by': request.user}
                )
                
                if created:
                    created_permissions.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip()
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have access regardless of explicit permissions."
        
        
        return Response({
            'document_id': document.id,
            'granted_permissions': created_permissions,
            'warning': warning,
            'message': f'Visibility permissions granted to {len(created_permissions)} users.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_usability_permissions(request, pk):
    """
    Grant usability permissions to multiple users for a document.
    Users must already have visibility permissions (unless document is public).
    
    Note: If document is public, all users already have usability access.
    
    Expected payload:
    {
        "user_ids": [1, 2, 3, ...]
    }
    """
    
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'detail': 'user_ids list is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all users exist
        users = User.objects.filter(id__in=user_ids)
        if len(users) != len(user_ids):
            found_ids = [user.id for user in users]
            missing_ids = [uid for uid in user_ids if uid not in found_ids]
            return Response(
                {'detail': f'Users not found: {missing_ids}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_permissions = []
        errors = []
        
        with transaction.atomic():
            for user in users:
                # Skip if user is lawyer (they have automatic access)
                if user.role == 'lawyer' or user.is_gym_lawyer:
                    continue
                
                # Check if user has visibility permission (unless document is public)
                if not document.is_public:
                    has_visibility = DocumentVisibilityPermission.objects.filter(
                        document=document, user=user
                    ).exists()
                    
                    if not has_visibility:
                        errors.append({
                            'user_id': user.id,
                            'email': user.email,
                            'error': 'User must have visibility permission first (or document must be public)'
                        })
                        continue
                
                # Grant usability permission
                permission, created = DocumentUsabilityPermission.objects.get_or_create(
                    document=document,
                    user=user,
                    defaults={'granted_by': request.user}
                )
                
                if created:
                    created_permissions.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip()
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have usability access regardless of explicit permissions."
        
        return Response({
            'document_id': document.id,
            'granted_permissions': created_permissions,
            'errors': errors,
            'warning': warning,
            'message': f'Usability permissions granted to {len(created_permissions)} users.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def revoke_visibility_permission(request, pk, user_id):
    """
    Revoke visibility permission for a specific user on a document.
    This will also revoke their usability permission if they have one.
    
    Note: If document is public, user will still have access through public access.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        user = User.objects.get(pk=user_id)
        
        # Remove visibility permission
        visibility_deleted = DocumentVisibilityPermission.objects.filter(
            document=document, user=user
        ).delete()[0]
        
        # Remove usability permission if exists
        usability_deleted = DocumentUsabilityPermission.objects.filter(
            document=document, user=user
        ).delete()[0]
        
        if visibility_deleted == 0:
            return Response(
                {'detail': 'User does not have visibility permission for this document.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        warning = None
        if document.is_public:
            warning = "Note: User still has access because document is public."
        
        return Response({
            'message': f'Revoked permissions for {user.email}',
            'visibility_revoked': True,
            'usability_revoked': usability_deleted > 0,
            'warning': warning
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def revoke_usability_permission(request, pk, user_id):
    """
    Revoke usability permission for a specific user on a document.
    The user will retain visibility permission.
    
    Note: If document is public, user will still have edit access through public access.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        user = User.objects.get(pk=user_id)
        
        # Remove usability permission
        deleted_count = DocumentUsabilityPermission.objects.filter(
            document=document, user=user
        ).delete()[0]
        
        if deleted_count == 0:
            return Response(
                {'detail': 'User does not have usability permission for this document.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        warning = None
        if document.is_public:
            warning = "Note: User still has edit access because document is public."
        
        return Response({
            'message': f'Revoked usability permission for {user.email}',
            'usability_revoked': True,
            'warning': warning
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_lawyer_only
def get_available_clients(request):
    """
    Get a list of all clients (non-lawyer users) that can be granted permissions.
    """
    clients = User.objects.filter(
        role__in=['client', 'corporate_client', 'basic']
    ).values('id', 'email', 'first_name', 'last_name', 'role').order_by('email')
    
    # Format the response
    client_list = []
    for client in clients:
        client_list.append({
            'user_id': client['id'],
            'email': client['email'],
            'full_name': f"{client['first_name']} {client['last_name']}".strip(),
            'role': client['role'],
        })
    
    return Response({
        'clients': client_list,
        'total_count': len(client_list)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_lawyer_only
def get_available_roles(request):
    """
    Get a list of all available user roles for permission management.
    
    Returns information about each role including:
    - Role code (used in API calls)
    - Display name (for UI)
    - Description
    - Whether the role has automatic access (lawyers)
    - User count for each role
    """
    # Get role choices from User model
    role_choices = User.ROLE_CHOICES
    
    # Get user counts for each role
    role_counts = {}
    for role_code, _ in role_choices:
        count = User.objects.filter(role=role_code).count()
        role_counts[role_code] = count
    
    # Format response with detailed role information
    roles_info = []
    role_descriptions = {
        'client': 'Cliente regular del sistema',
        'lawyer': 'Abogado con acceso completo automático',
        'corporate_client': 'Cliente corporativo con necesidades empresariales',
        'basic': 'Usuario con acceso básico limitado'
    }
    
    for role_code, display_name in role_choices:
        roles_info.append({
            'code': role_code,
            'display_name': display_name,
            'description': role_descriptions.get(role_code, f'Rol {display_name}'),
            'user_count': role_counts.get(role_code, 0),
            'has_automatic_access': role_code == 'lawyer',
            'can_be_granted_permissions': role_code != 'lawyer'  # Lawyers don't need explicit permissions
        })
    
    return Response({
        'roles': roles_info,
        'total_roles': len(roles_info),
        'notes': {
            'automatic_access': 'Los abogados tienen acceso automático a todos los documentos',
            'permission_management': 'Solo los roles marcados como "can_be_granted_permissions" necesitan permisos explícitos'
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_visibility_permissions_by_role(request, pk):
    """
    Grant visibility permissions to all users of specific roles for a document.
    
    Expected payload:
    {
        "roles": ["client", "corporate_client", "basic"]
    }
    
    Available roles: client, lawyer, corporate_client, basic
    Note: Lawyers automatically have access, so including 'lawyer' has no effect.
    """
    
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        roles = request.data.get('roles', [])
        
        if not roles:
            return Response(
                {'detail': 'roles list is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles
        valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
        invalid_roles = [role for role in roles if role not in valid_roles]
        if invalid_roles:
            return Response(
                {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all users with the specified roles (excluding lawyers as they have automatic access)
        target_roles = [role for role in roles if role != 'lawyer']
        users = User.objects.filter(role__in=target_roles)
        
        # Grant permissions (use get_or_create to avoid duplicates)
        created_permissions = []
        skipped_users = []
        
        for user, created in _grant_role_visibility(document, users, request.user):
            if created:
                created_permissions.append({
                    'user_id': user.id,
                    'email': user.email,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                    'role': user.role
                })
            else:
                skipped_users.append({
                    'user_id': user.id,
                    'email': user.email,
                    'reason': 'Already has permission'
                })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have access regardless of explicit permissions."
        
        
        return Response({
            'document_id': document.id,
            'roles_processed': target_roles,
            'granted_permissions': created_permissions,
            'skipped_users': skipped_users,
            'warning': warning,
            'message': f'Visibility permissions granted to {len(created_permissions)} users across roles: {target_roles}.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_usability_permissions_by_role(request, pk):
    """
    Grant usability permissions to all users of specific roles for a document.
    Users must already have visibility permissions (unless document is public).
    
    Expected payload:
    {
        "roles": ["client", "corporate_client", "basic"]
    }
    
    Available roles: client, lawyer, corporate_client, basic
    Note: Lawyers automatically have access, so including 'lawyer' has no effect.
    """
    
    try:
        document = DynamicDocument.objects.get(pk=pk)
        
        roles = request.data.get('roles', [])
        
        if not roles:
            return Response(
                {'detail': 'roles list is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles
        valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
        invalid_roles = [role for role in roles if role not in valid_roles]
        if invalid_roles:
            return Response(
                {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all users with the specified roles (excluding lawyers as they have automatic access)
        target_roles = [role for role in roles if role != 'lawyer']
        users = User.objects.filter(role__in=target_roles)
        
        created_permissions = []
        errors = []
        skipped_users = []
        
        with transaction.atomic():
            for user in users:
                # Check if user has visibility permission (unless document is public)
                if not document.is_public:
                    has_visibility = DocumentVisibilityPermission.objects.filter(
                        document=document, user=user
                    ).exists()
                    
                    if not has_visibility:
                        errors.append({
                            'user_id': user.id,
                            'email': user.email,
                            'role': user.role,
                            'error': 'User must have visibility permission first (or document must be public)'
                        })
                        continue
                
                # Grant usability permission
                permission, created = DocumentUsabilityPermission.objects.get_or_create(
                    document=document,
                    user=user,
                    defaults={'granted_by': request.user}
                )
                
                if created:
                    created_permissions.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role
                    })
                else:
                    skipped_users.append({
                        'user_id': user.id,
                        'email': user.email,
                        'reason': 'Already has permission'
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have usability access regardless of explicit permissions."
        
        return Response({
            'document_id': document.id,
            'roles_processed': target_roles,
            'granted_permissions': created_permissions,
            'skipped_users': skipped_users,
            'errors': errors,
            'warning': warning,
            'message': f'Usability permissions granted to {len(created_permissions)} users across roles: {target_roles}.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def revoke_permissions_by_role(request, pk):
    """
    Revoke visibility and usability permissions for all users of specific roles.
    
    Expected payload:
    {
        "roles": ["client", "corporate_client"],
        "permission_type": "visibility"  // "visibility", "usability", or "both"
    }
    
    Available roles: client, lawyer, corporate_client, basic
    Available permission_types: visibility, usability, both
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        roles = request.data.get('roles', [])
        permission_type = request.data.get('permission_type', 'both')
        
        if not roles:
            return Response(
                {'detail': 'roles list is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles
        valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
        invalid_roles = [role for role in roles if role not in valid_roles]
        if invalid_roles:
            return Response(
                {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate permission type
        valid_permission_types = ['visibility', 'usability', 'both']
        if permission_type not in valid_permission_types:
            return Response(
                {'detail': f'Invalid permission_type: {permission_type}. Valid types: {valid_permission_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all users with the specified roles (excluding lawyers)
        target_roles = [role for role in roles if role != 'lawyer']
        users = User.objects.filter(role__in=target_roles)
        
        visibility_revoked = 0
        usability_revoked = 0
        affected_users = []
        
        with transaction.atomic():
            for user in users:
                user_visibility_revoked = 0
                user_usability_revoked = 0
                
                # Revoke visibility permissions
                if permission_type in ['visibility', 'both']:
                    user_visibility_revoked = DocumentVisibilityPermission.objects.filter(
                        document=document, user=user
                    ).delete()[0]
                    visibility_revoked += user_visibility_revoked
                
                # Revoke usability permissions
                if permission_type in ['usability', 'both']:
                    user_usability_revoked = DocumentUsabilityPermission.objects.filter(
                        document=document, user=user
                    ).delete()[0]
                    usability_revoked += user_usability_revoked
                
                # Track affected users
                if user_visibility_revoked > 0 or user_usability_revoked > 0:
                    affected_users.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role,
                        'visibility_revoked': user_visibility_revoked > 0,
                        'usability_revoked': user_usability_revoked > 0
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Users still have access because document is public."
        
        return Response({
            'document_id': document.id,
            'roles_processed': target_roles,
            'permission_type': permission_type,
            'total_visibility_revoked': visibility_revoked,
            'total_usability_revoked': usability_revoked,
            'affected_users': affected_users,
            'warning': warning,
            'message': f'Revoked {permission_type} permissions for {len(affected_users)} users across roles: {target_roles}.'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_visibility_permissions_combined(request, pk):
    """
    Grant visibility permissions to users and/or roles in a single API call.
    
    Expected payload:
    {
        "user_ids": [45, 67, 89],           // Optional: specific user IDs
        "roles": ["client", "basic"],        // Optional: user roles
        "exclude_user_ids": [12, 34]        // Optional: exclude specific users even if they match roles
    }
    
    At least one of 'user_ids' or 'roles' must be provided.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        user_ids = request.data.get('user_ids', [])
        roles = request.data.get('roles', [])
        exclude_user_ids = request.data.get('exclude_user_ids', [])
        
        if not user_ids and not roles:
            return Response(
                {'detail': 'At least one of user_ids or roles must be provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles if provided
        if roles:
            valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                return Response(
                    {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Collect all target users
        target_users = set()
        
        # Add users from user_ids
        if user_ids:
            users_from_ids = User.objects.filter(id__in=user_ids)
            if len(users_from_ids) != len(user_ids):
                found_ids = [user.id for user in users_from_ids]
                missing_ids = [uid for uid in user_ids if uid not in found_ids]
                return Response(
                    {'detail': f'Users not found: {missing_ids}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            target_users.update(users_from_ids)
        
        # Add users from roles (excluding lawyers as they have automatic access)
        if roles:
            target_roles = [role for role in roles if role != 'lawyer']
            users_from_roles = User.objects.filter(role__in=target_roles)
            target_users.update(users_from_roles)
        
        # Remove excluded users
        if exclude_user_ids:
            excluded_users = User.objects.filter(id__in=exclude_user_ids)
            target_users = target_users - set(excluded_users)
        
        # Grant permissions
        created_permissions = []
        skipped_users = []
        
        with transaction.atomic():
            for user in target_users:
                # Skip lawyers (they have automatic access)
                if user.role == 'lawyer' or user.is_gym_lawyer:
                    continue
                    
                permission, created = DocumentVisibilityPermission.objects.get_or_create(
                    document=document,
                    user=user,
                    defaults={'granted_by': request.user}
                )
                
                if created:
                    created_permissions.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role,
                        'source': 'role' if user_ids and user.id not in user_ids else 'user_id'
                    })
                else:
                    skipped_users.append({
                        'user_id': user.id,
                        'email': user.email,
                        'reason': 'Already has permission'
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have access regardless of explicit permissions."
        
        return Response({
            'document_id': document.id,
            'input_summary': {
                'user_ids_provided': len(user_ids),
                'roles_provided': roles,
                'excluded_users': len(exclude_user_ids)
            },
            'granted_permissions': created_permissions,
            'skipped_users': skipped_users,
            'warning': warning,
            'message': f'Visibility permissions granted to {len(created_permissions)} users (from {len(user_ids)} specific users + roles: {roles}).'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def grant_usability_permissions_combined(request, pk):
    """
    Grant usability permissions to users and/or roles in a single API call.
    Users must already have visibility permissions (unless document is public).
    
    Expected payload:
    {
        "user_ids": [45, 67, 89],           // Optional: specific user IDs
        "roles": ["client", "basic"],        // Optional: user roles
        "exclude_user_ids": [12, 34]        // Optional: exclude specific users even if they match roles
    }
    
    At least one of 'user_ids' or 'roles' must be provided.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        user_ids = request.data.get('user_ids', [])
        roles = request.data.get('roles', [])
        exclude_user_ids = request.data.get('exclude_user_ids', [])
        
        if not user_ids and not roles:
            return Response(
                {'detail': 'At least one of user_ids or roles must be provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles if provided
        if roles:
            valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                return Response(
                    {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Collect all target users
        target_users = set()
        
        # Add users from user_ids
        if user_ids:
            users_from_ids = User.objects.filter(id__in=user_ids)
            if len(users_from_ids) != len(user_ids):
                found_ids = [user.id for user in users_from_ids]
                missing_ids = [uid for uid in user_ids if uid not in found_ids]
                return Response(
                    {'detail': f'Users not found: {missing_ids}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            target_users.update(users_from_ids)
        
        # Add users from roles (excluding lawyers as they have automatic access)
        if roles:
            target_roles = [role for role in roles if role != 'lawyer']
            users_from_roles = User.objects.filter(role__in=target_roles)
            target_users.update(users_from_roles)
        
        # Remove excluded users
        if exclude_user_ids:
            excluded_users = User.objects.filter(id__in=exclude_user_ids)
            target_users = target_users - set(excluded_users)
        
        # Grant permissions
        created_permissions = []
        errors = []
        skipped_users = []
        
        with transaction.atomic():
            for user in target_users:
                # Skip lawyers (they have automatic access)
                if user.role == 'lawyer' or user.is_gym_lawyer:
                    continue
                
                # Check if user has visibility permission (unless document is public)
                if not document.is_public:
                    has_visibility = DocumentVisibilityPermission.objects.filter(
                        document=document, user=user
                    ).exists()
                    
                    if not has_visibility:
                        errors.append({
                            'user_id': user.id,
                            'email': user.email,
                            'role': user.role,
                            'error': 'User must have visibility permission first (or document must be public)'
                        })
                        continue
                
                # Grant usability permission
                permission, created = DocumentUsabilityPermission.objects.get_or_create(
                    document=document,
                    user=user,
                    defaults={'granted_by': request.user}
                )
                
                if created:
                    created_permissions.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role,
                        'source': 'role' if user_ids and user.id not in user_ids else 'user_id'
                    })
                else:
                    skipped_users.append({
                        'user_id': user.id,
                        'email': user.email,
                        'reason': 'Already has permission'
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Document is public, so all users already have usability access regardless of explicit permissions."
        
        return Response({
            'document_id': document.id,
            'input_summary': {
                'user_ids_provided': len(user_ids),
                'roles_provided': roles,
                'excluded_users': len(exclude_user_ids)
            },
            'granted_permissions': created_permissions,
            'skipped_users': skipped_users,
            'errors': errors,
            'warning': warning,
            'message': f'Usability permissions granted to {len(created_permissions)} users (from {len(user_ids)} specific users + roles: {roles}).'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_or_owner
def revoke_permissions_combined(request, pk):
    """
    Revoke visibility and/or usability permissions from users and/or roles in a single API call.
    
    Expected payload:
    {
        "user_ids": [45, 67, 89],           // Optional: specific user IDs
        "roles": ["client", "basic"],        // Optional: user roles
        "exclude_user_ids": [12, 34],       // Optional: exclude specific users even if they match roles
        "permission_type": "visibility"      // "visibility", "usability", or "both"
    }
    
    At least one of 'user_ids' or 'roles' must be provided.
    """
    try:
        document = DynamicDocument.objects.get(pk=pk)
        user_ids = request.data.get('user_ids', [])
        roles = request.data.get('roles', [])
        exclude_user_ids = request.data.get('exclude_user_ids', [])
        permission_type = request.data.get('permission_type', 'both')
        
        if not user_ids and not roles:
            return Response(
                {'detail': 'At least one of user_ids or roles must be provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate roles if provided
        if roles:
            valid_roles = ['client', 'lawyer', 'corporate_client', 'basic']
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                return Response(
                    {'detail': f'Invalid roles: {invalid_roles}. Valid roles: {valid_roles}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate permission type
        valid_permission_types = ['visibility', 'usability', 'both']
        if permission_type not in valid_permission_types:
            return Response(
                {'detail': f'Invalid permission_type: {permission_type}. Valid types: {valid_permission_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Collect all target users
        target_users = set()
        
        # Add users from user_ids
        if user_ids:
            users_from_ids = User.objects.filter(id__in=user_ids)
            if len(users_from_ids) != len(user_ids):
                found_ids = [user.id for user in users_from_ids]
                missing_ids = [uid for uid in user_ids if uid not in found_ids]
                return Response(
                    {'detail': f'Users not found: {missing_ids}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            target_users.update(users_from_ids)
        
        # Add users from roles (excluding lawyers)
        if roles:
            target_roles = [role for role in roles if role != 'lawyer']
            users_from_roles = User.objects.filter(role__in=target_roles)
            target_users.update(users_from_roles)
        
        # Remove excluded users
        if exclude_user_ids:
            excluded_users = User.objects.filter(id__in=exclude_user_ids)
            target_users = target_users - set(excluded_users)
        
        # Revoke permissions
        visibility_revoked = 0
        usability_revoked = 0
        affected_users = []
        
        with transaction.atomic():
            for user in target_users:
                user_visibility_revoked = 0
                user_usability_revoked = 0
                
                # Revoke visibility permissions
                if permission_type in ['visibility', 'both']:
                    user_visibility_revoked = DocumentVisibilityPermission.objects.filter(
                        document=document, user=user
                    ).delete()[0]
                    visibility_revoked += user_visibility_revoked
                
                # Revoke usability permissions
                if permission_type in ['usability', 'both']:
                    user_usability_revoked = DocumentUsabilityPermission.objects.filter(
                        document=document, user=user
                    ).delete()[0]
                    usability_revoked += user_usability_revoked
                
                # Track affected users
                if user_visibility_revoked > 0 or user_usability_revoked > 0:
                    affected_users.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'role': user.role,
                        'visibility_revoked': user_visibility_revoked > 0,
                        'usability_revoked': user_usability_revoked > 0,
                        'source': 'role' if user_ids and user.id not in user_ids else 'user_id'
                    })
        
        warning = None
        if document.is_public:
            warning = "Note: Users still have access because document is public."
        
        return Response({
            'document_id': document.id,
            'input_summary': {
                'user_ids_provided': len(user_ids),
                'roles_provided': roles,
                'excluded_users': len(exclude_user_ids),
                'permission_type': permission_type
            },
            'total_visibility_revoked': visibility_revoked,
            'total_usability_revoked': usability_revoked,
            'affected_users': affected_users,
            'warning': warning,
            'message': f'Revoked {permission_type} permissions for {len(affected_users)} users (from {len(user_ids)} specific users + roles: {roles}).'
        }, status=status.HTTP_200_OK)
        
    except DynamicDocument.DoesNotExist:  # pragma: no cover – decorator intercepts first
        return Response(
            {'detail': 'Document not found.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
