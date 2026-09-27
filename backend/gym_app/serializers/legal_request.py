from rest_framework import serializers
from gym_app.models import LegalRequestType, LegalDiscipline, LegalRequestFiles, LegalRequest, LegalRequestResponse

class LegalRequestTypeSerializer(serializers.ModelSerializer):
    """Serializer for the LegalRequestType model."""
    class Meta:
        model = LegalRequestType
        fields = ['id', 'name']

class LegalDisciplineSerializer(serializers.ModelSerializer):
    """Serializer for the LegalDiscipline model."""
    class Meta:
        model = LegalDiscipline
        fields = ['id', 'name']

class LegalRequestFilesSerializer(serializers.ModelSerializer):
    """Serializer for the LegalRequestFiles model."""
    class Meta:
        model = LegalRequestFiles
        fields = ['id', 'file', 'created_at']

class LegalRequestResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for the LegalRequestResponse model.
    
    Handles serialization and deserialization of responses to legal requests.
    """
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LegalRequestResponse
        fields = ['id', 'response_text', 'user', 'user_name', 'user_type', 'created_at']
        read_only_fields = ['id', 'created_at', 'user_name']
    
    def get_user_name(self, obj):
        """Get the full name of the user who created the response."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class LegalRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for the LegalRequest model.
    
    Handles serialization and deserialization of legal requests,
    including nested relationships for request type, discipline, associated files, and responses.
    """
    request_type = LegalRequestTypeSerializer(read_only=True)  # ForeignKey for request_type
    discipline = LegalDisciplineSerializer(read_only=True)  # ForeignKey for discipline
    files = LegalRequestFilesSerializer(many=True, read_only=True)  # ManyToManyField for files
    responses = LegalRequestResponseSerializer(many=True, read_only=True)  # Related responses
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # User fields from related user
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = LegalRequest
        fields = [
            'id', 'request_number', 'user', 'first_name', 'last_name', 'email',
            'request_type', 'discipline', 'description', 'files', 'responses',
            'status', 'status_display', 'status_updated_at', 'created_at'
        ]
        read_only_fields = ['id', 'request_number', 'user', 'status_updated_at', 'created_at']


class LegalRequestListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing legal requests.
    
    Used for list views to reduce payload size and improve performance.
    """
    request_type_name = serializers.CharField(source='request_type.name', read_only=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    response_count = serializers.SerializerMethodField()
    
    # User fields from related user
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = LegalRequest
        fields = [
            'id', 'request_number', 'user', 'first_name', 'last_name', 'email',
            'request_type_name', 'discipline_name', 'description',
            'status', 'status_display', 'response_count', 'created_at'
        ]
    
    def get_response_count(self, obj):
        """Get the number of responses for this request."""
        if hasattr(obj, '_response_count'):
            return obj._response_count
        return obj.responses.count()
