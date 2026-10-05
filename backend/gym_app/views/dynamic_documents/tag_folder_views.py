from django.db.models import Prefetch, prefetch_related_objects
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from gym_app.models.dynamic_document import Tag, DocumentFolder, DynamicDocument
from gym_app.serializers.dynamic_document import TagSerializer, DocumentFolderSerializer
from .document_views import get_optimized_document_queryset
from .permissions import require_lawyer_only

# -----------------------------------------------------------------------------
# Helper permission checks
# -----------------------------------------------------------------------------

def _is_lawyer(user):  # pragma: no cover – unused helper, kept for potential future use
    """Return True if the user has role 'lawyer'."""
    return getattr(user, 'role', None) == 'lawyer'


def _is_folder_owner(user, folder: DocumentFolder):
    """Return True if the user owns the folder."""
    return folder.owner_id == user.id


def _folder_queryset():
    """Load nested documents with the existing complete serializer query plan."""
    return DocumentFolder.objects.prefetch_related(
        Prefetch('documents', queryset=get_optimized_document_queryset()),
    )

# -----------------------------------------------------------------------------
# Tag endpoints (lawyers only for mutations)
# -----------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tags(request):
    """Return a list of all tags (any role)."""
    tags = Tag.objects.all().order_by('name')
    serializer = TagSerializer(tags, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_lawyer_only
def create_tag(request):
    """Create a new tag (lawyer only)."""
    serializer = TagSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@require_lawyer_only
def update_tag(request, pk):
    """Update an existing tag (lawyer only)."""
    try:
        tag = Tag.objects.get(pk=pk)
    except Tag.DoesNotExist:
        return Response({'detail': 'Etiqueta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = TagSerializer(tag, data=request.data, partial=(request.method == 'PATCH'), context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_lawyer_only
def delete_tag(request, pk):
    """Delete a tag (lawyer only)."""
    try:
        tag = Tag.objects.get(pk=pk)
    except Tag.DoesNotExist:
        return Response({'detail': 'Etiqueta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    tag.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# -----------------------------------------------------------------------------
# Folder endpoints (clients – owner only)
# -----------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_folders(request):
    """List folders belonging to the authenticated client."""
    folders = _folder_queryset().filter(owner=request.user).order_by('-created_at')
    serializer = DocumentFolderSerializer(folders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_folder(request):
    """Create a new folder for the authenticated client."""
    serializer = DocumentFolderSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_folder(request, pk):
    """Retrieve a folder if the user is the owner."""
    try:
        folder = DocumentFolder.objects.get(pk=pk)
    except DocumentFolder.DoesNotExist:
        return Response({'detail': 'Carpeta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if not _is_folder_owner(request.user, folder):
        return Response({'detail': 'No tiene permiso para acceder a esta carpeta.'}, status=status.HTTP_403_FORBIDDEN)

    prefetch_related_objects(
        [folder],
        Prefetch('documents', queryset=get_optimized_document_queryset()),
    )
    serializer = DocumentFolderSerializer(folder)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_folder(request, pk):
    """Update folder name, color or document list (owner only)."""
    try:
        folder = DocumentFolder.objects.get(pk=pk)
    except DocumentFolder.DoesNotExist:
        return Response({'detail': 'Carpeta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if not _is_folder_owner(request.user, folder):
        return Response({'detail': 'No tiene permiso para modificar esta carpeta.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = DocumentFolderSerializer(folder, data=request.data, partial=(request.method == 'PATCH'), context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_folder(request, pk):
    """Delete a folder (owner only)."""
    try:
        folder = DocumentFolder.objects.get(pk=pk)
    except DocumentFolder.DoesNotExist:
        return Response({'detail': 'Carpeta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if not _is_folder_owner(request.user, folder):
        return Response({'detail': 'No tiene permiso para eliminar esta carpeta.'}, status=status.HTTP_403_FORBIDDEN)

    folder.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
