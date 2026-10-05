from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from gym_app.models import LegalUpdate
from gym_app.serializers import LegalUpdateSerializer
from gym_app.utils.auth_utils import is_gym_staff

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def legal_update_list(request):
    """
    List all active legal updates or create a new legal update.
    """
    if request.method == 'GET':
        updates = LegalUpdate.objects.filter(is_active=True).order_by('-created_at')
        serializer = LegalUpdateSerializer(updates, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        if not is_gym_staff(request.user):
            return Response(
                {'detail': 'No tienes permiso para modificar novedades jurídicas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LegalUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def legal_update_detail(request, pk):
    """
    Retrieve, update or delete a legal update.
    """
    if request.method in ('PUT', 'DELETE') and not is_gym_staff(request.user):
        return Response(
            {'detail': 'No tienes permiso para modificar novedades jurídicas.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        update = LegalUpdate.objects.get(pk=pk, is_active=True)
    except LegalUpdate.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = LegalUpdateSerializer(update, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = LegalUpdateSerializer(update, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        update.is_active = False
        update.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_legal_updates(request):
    """
    Get a list of all active legal updates.
    """
    updates = LegalUpdate.objects.filter(is_active=True).order_by('-created_at')
    serializer = LegalUpdateSerializer(updates, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)
