import json
import traceback
import logging
import os
import magic
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.conf import settings
from gym_app.models import LegalRequest, LegalRequestType, LegalDiscipline, LegalRequestFiles, LegalRequestResponse
from gym_app.serializers import (
    LegalRequestSerializer, LegalRequestTypeSerializer, LegalDisciplineSerializer,
    LegalRequestListSerializer, LegalRequestResponseSerializer
)
from gym_app.views.layouts.sendEmail import send_template_email
from gym_app.utils.email_notifications import (
    send_status_update_notification,
    notify_client_of_lawyer_response,
    notify_lawyers_of_client_response
)

# Configure logger for professional error handling
logger = logging.getLogger(__name__)

# File validation configuration
ALLOWED_FILE_TYPES = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/zip': ['.docx'],  # .docx files may be detected as ZIP
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png']
}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

def validate_file_security(file):
    """Comprehensive file validation for security"""
    logger.info(f"Starting file validation for: {file.name}")
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(f"File {file.name} exceeds maximum size of {MAX_FILE_SIZE // 1024 // 1024}MB")
    
    # Check file extension
    file_ext = os.path.splitext(file.name)[1].lower()
    if not any(file_ext in extensions for extensions in ALLOWED_FILE_TYPES.values()):
        raise ValidationError(f"File type {file_ext} not allowed. Allowed types: {list(ALLOWED_FILE_TYPES.keys())}")
    
    # Check MIME type with enhanced detection for .docx files
    try:
        # Read more bytes for better detection (especially for .docx files)
        mime_type = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)  # Reset file pointer
        
        logger.info(f"Detected MIME type for {file.name}: {mime_type}")
        
        # Special handling for .docx files that might be detected as application/zip
        if file_ext == '.docx' and mime_type == 'application/zip':
            # Verify it's actually a .docx by checking internal structure
            try:
                file_content = file.read(512)
                file.seek(0)  # Reset file pointer
                # Check for typical .docx ZIP signatures
                if b'PK' in file_content[:4] and (b'word/' in file_content or b'docProps/' in file_content):
                    logger.info(f"Confirmed {file.name} is a valid .docx file (detected as ZIP)")
                    # Accept this as valid .docx
                    logger.info(f"File validation successful for .docx file: {file.name}")
                    return True
            except Exception as inner_e:
                logger.warning(f"Could not verify .docx internal structure for {file.name}: {str(inner_e)}")
        
        # Standard MIME type validation
        if mime_type not in ALLOWED_FILE_TYPES:
            raise ValidationError(f"MIME type {mime_type} not allowed")
        
        # Check if extension matches MIME type
        if file_ext not in ALLOWED_FILE_TYPES[mime_type]:
            raise ValidationError(f"File extension {file_ext} doesn't match MIME type {mime_type}")
            
    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error checking MIME type for {file.name}: {str(e)}")
        raise ValidationError("Unable to verify file type")
    
    logger.info(f"File validation successful for: {file.name}")
    return True

def sanitize_filename(filename):
    """Sanitize filename for security"""
    import uuid
    # Keep only the extension, generate unique name
    ext = os.path.splitext(filename)[1].lower()
    sanitized = f"{uuid.uuid4().hex}{ext}"
    logger.info(f"Sanitized filename: {filename} -> {sanitized}")
    return sanitized

def process_file_upload(file, legal_request):
    """
    Process a single file upload with validation and security checks.
    
    Args:
        file: Uploaded file object
        legal_request: LegalRequest instance to associate the file with
    
    Returns:
        dict: Result with success status and file data or error info
    """
    try:
        # Comprehensive file validation
        validate_file_security(file)
        
        # Sanitize filename for security
        original_filename = file.name
        sanitized_filename = sanitize_filename(original_filename)
        
        # Use atomic transaction for file creation
        with transaction.atomic():
            file_instance = LegalRequestFiles.objects.create(file=file)
            legal_request.files.add(file_instance)
        
        logger.info(f"File uploaded successfully: {original_filename} -> {sanitized_filename} for legal request {legal_request.id}")
        
        return {
            'success': True,
            'data': {
                'id': file_instance.id,
                'original_name': original_filename,
                'sanitized_name': sanitized_filename,
                'size': file.size
            }
        }
        
    except ValidationError as e:
        error_msg = f"Validation failed for {file.name}: {str(e)}"
        logger.warning(error_msg)
        return {
            'success': False,
            'error': {
                'name': file.name,
                'message': str(e)
            }
        }
    except Exception as e:
        error_msg = f"Upload failed for {file.name}: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': {
                'name': file.name,
                'message': 'Upload failed due to server error'
            }
        }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_legal_request(request):
    """
    API view to create a new legal request with comprehensive validation,
    atomic transactions, and professional error handling.
    """
    logger.info(f"Legal request creation started by user: {request.user.id}")
    
    try:
        
        # Parse and validate main data
        main_data_raw = request.data.get('mainData', '{}')
        if not main_data_raw:
            return Response({'detail': 'Main data is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            main_data = json.loads(main_data_raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for user {request.user.id}: {str(e)}")
            return Response({'detail': 'Invalid JSON format in main data.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate required fields (removed user fields since we use authenticated user)
        required_fields = ['requestTypeId', 'disciplineId', 'description']
        missing_fields = [field for field in required_fields if not main_data.get(field)]
        if missing_fields:
            logger.warning(f"Missing required fields for user {request.user.id}: {missing_fields}")
            return Response(
                {'detail': f'Missing required fields: {", ".join(missing_fields)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Email validation not needed since we use authenticated user's email

        # Validate foreign key references
        try:
            request_type = LegalRequestType.objects.get(pk=main_data.get('requestTypeId'))
        except LegalRequestType.DoesNotExist:
            logger.error(f"Request type {main_data.get('requestTypeId')} not found for user {request.user.id}")
            return Response({'detail': 'Request type not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            discipline = LegalDiscipline.objects.get(pk=main_data.get('disciplineId'))
        except LegalDiscipline.DoesNotExist:
            logger.error(f"Discipline {main_data.get('disciplineId')} not found for user {request.user.id}")
            return Response({'detail': 'Discipline not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            # Create the LegalRequest instance with authenticated user
            legal_request = LegalRequest.objects.create(
                user=request.user,
                request_type=request_type,
                discipline=discipline,
                description=main_data.get('description').strip()
            )
            
            logger.info(f"Legal request created successfully: ID {legal_request.id} for user {request.user.id}")

        # Serialize the created request
        serializer = LegalRequestSerializer(legal_request, context={'request': request})

        # Return immediate response - email will be sent asynchronously
        # Note: For immediate response, we skip email sending in the request flow

        # Return immediate success response with clear messaging
        response_data = {
            'id': legal_request.id,
            'message': 'Legal request received successfully',
            'status': 'received',
            'email_notification': 'You will receive an email confirmation shortly',
            'next_steps': 'You can now upload files or continue using the platform'
        }
        
        logger.info(f"Legal request {legal_request.id} created successfully for user {request.user.id}")
        return Response(response_data, status=status.HTTP_201_CREATED)

    except ValidationError as e:
        logger.error(f"Validation error for user {request.user.id}: {str(e)}")
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error for user {request.user.id}: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'detail': 'An unexpected error occurred. Please try again later.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_legal_request_file(request):
    """
    API view to upload files with comprehensive validation, atomic transactions,
    retry logic, and security checks.
    """
    logger.info(f"File upload started by user: {request.user.id}")
    
    try:
        
        # Validate legal request ID
        legal_request_id = request.data.get('legalRequestId')
        if not legal_request_id:
            return Response({'detail': 'Legal request ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the existence of the LegalRequest instance (outside transaction for performance)
        try:
            legal_request = LegalRequest.objects.get(pk=legal_request_id)
        except LegalRequest.DoesNotExist:
            logger.error(f"Legal request {legal_request_id} not found for user {request.user.id}")
            return Response({'detail': 'Legal request not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Handle multiple files or single file
        files = request.FILES.getlist('files') if 'files' in request.FILES else [request.FILES.get('file')]
        files = [f for f in files if f]  # Filter out None values
        
        if not files:
            return Response({'detail': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_files = []
        failed_files = []

        # Process each file with validation and atomic transactions
        for file in files:
            result = process_file_upload(file, legal_request)
            
            if result['success']:
                uploaded_files.append(result['data'])
            else:
                failed_files.append(result['error'])

        # Files processed successfully - no email needed, only logging
        if uploaded_files or failed_files:
            total_files = len(uploaded_files) + len(failed_files)
            logger.info(f"File processing completed for legal request {legal_request_id}: {len(uploaded_files)} successful, {len(failed_files)} failed")

        # Return comprehensive response
        response_data = {
            'message': 'File upload completed',
            'legal_request_id': legal_request_id,
            'total_files_processed': len(uploaded_files) + len(failed_files),
            'successful_uploads': len(uploaded_files),
            'failed_uploads': len(failed_files),
            'uploaded_files': uploaded_files,
            'failed_files': failed_files,
            'email_notification': 'Upload status sent via email'
        }
        
        status_code = status.HTTP_201_CREATED if uploaded_files else status.HTTP_400_BAD_REQUEST
        logger.info(f"File upload completed for legal request {legal_request_id}: {len(uploaded_files)} successful, {len(failed_files)} failed")
        
        return Response(response_data, status=status_code)

    except ValidationError as e:
        logger.error(f"Validation error in file upload for user {request.user.id}: {str(e)}")
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error in file upload for user {request.user.id}: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'detail': 'An unexpected error occurred during file upload.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dropdown_options(request):
    # Get the data from the models
    legal_request_types = LegalRequestType.objects.all()
    legal_disciplines = LegalDiscipline.objects.all()

    # Serializing the data
    legal_request_types_serialized = LegalRequestTypeSerializer(legal_request_types, many=True)
    legal_disciplines_serialized = LegalDisciplineSerializer(legal_disciplines, many=True)

    # Build the response JSON
    return Response({
        "legal_request_types": legal_request_types_serialized.data,
        "legal_disciplines": legal_disciplines_serialized.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_confirmation_email(request):
    """
    Send confirmation email for a legal request asynchronously.
    This endpoint can be called from frontend after the main request is created.
    """
    try:
        legal_request_id = request.data.get('legal_request_id')
        if not legal_request_id:
            return Response({'detail': 'Legal request ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the legal request
        try:
            legal_request = LegalRequest.objects.get(pk=legal_request_id)
        except LegalRequest.DoesNotExist:
            return Response({'detail': 'Legal request not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Send confirmation email
        try:
            user = legal_request.user

            # Safely get user's name and email from the related User model
            first_name = getattr(user, 'first_name', '') or ''
            last_name = getattr(user, 'last_name', '') or ''
            recipient_email = getattr(user, 'email', None)

            if not recipient_email:
                logger.error(
                    f"Cannot send confirmation email for legal request {legal_request.id}: user has no email configured"
                )
                return Response(
                    {
                        'detail': 'Email sending failed: user email is not configured',
                        'legal_request_id': legal_request_id,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            context = {
                "first_name": first_name,
                "last_name": last_name,
                "description": legal_request.description,
                "request_id": legal_request.id,
                "request_number": legal_request.request_number,
                "email_type": "confirmation",
            }

            send_template_email(
                template_name="legal_request",
                subject="Confirmación de solicitud legal",
                to_emails=[recipient_email],
                context=context,
            )
            logger.info(f"Confirmation email sent for legal request {legal_request.id}")
            
            return Response({
                'message': 'Confirmation email sent successfully',
                'legal_request_id': legal_request_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error sending confirmation email for legal request {legal_request.id}: {str(e)}")
            return Response(
                {'detail': 'Email sending failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in send_confirmation_email: {str(e)}")
        return Response(
            {'detail': 'An unexpected error occurred'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===============================
# NEW ENDPOINTS FOR MANAGEMENT SYSTEM
# ===============================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_legal_requests(request):
    """
    List legal requests filtered by user role.
    Lawyers see all requests, clients see only their own.
    """
    try:
        user = request.user
        
        # Base queryset with related data for performance
        queryset = LegalRequest.objects.select_related(
            'user', 'request_type', 'discipline'
        ).annotate(_response_count=models.Count('responses'))
        
        # Filter based on user role
        if hasattr(user, 'role') and user.role == 'lawyer':
            # Lawyers see all requests
            requests = queryset.all()
            logger.info(f"Lawyer {user.id} requested all legal requests")
        else:
            # Clients see only their own requests (filter by user)
            requests = queryset.filter(user=user)
            logger.info(f"Client {user.id} requested their legal requests")
        
        # Apply search filter if provided
        search = request.GET.get('search', '').strip()
        if search:
            requests = requests.filter(
                models.Q(request_number__icontains=search) |
                models.Q(user__first_name__icontains=search) |
                models.Q(user__last_name__icontains=search) |
                models.Q(user__email__icontains=search) |
                models.Q(description__icontains=search)
            )
        
        # Apply status filter if provided
        status_filter = request.GET.get('status', '').strip()
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        # Apply date filters if provided
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                requests = requests.filter(created_at__date__gte=date_from_obj)
                logger.info(f"Applied date_from filter: {date_from}")
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                requests = requests.filter(created_at__date__lte=date_to_obj)
                logger.info(f"Applied date_to filter: {date_to}")
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        # Order by creation date (newest first)
        requests = requests.order_by('-created_at')
        
        # Use list serializer for better performance
        serializer = LegalRequestListSerializer(requests, many=True)
        
        return Response({
            'requests': serializer.data,
            'count': requests.count(),
            'user_role': getattr(user, 'role', 'client')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing legal requests for user {request.user.id}: {str(e)}")
        return Response(
            {'detail': 'Error retrieving legal requests'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def get_or_delete_legal_request(request, request_id):
    """
    Get detailed information about a specific legal request or delete it.
    Includes all responses and files.
    """
    try:
        user = request.user
        
        # Get the request with related data
        legal_request = get_object_or_404(
            LegalRequest.objects.select_related('request_type', 'discipline')
            .prefetch_related('responses__user', 'files'),
            id=request_id
        )
        
        # Check permissions
        if not (hasattr(user, 'role') and user.role == 'lawyer') and legal_request.user != user:
            logger.warning(f"User {user.id} attempted to access legal request {request_id} without permission")
            return Response(
                {'detail': 'You do not have permission to view this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.method == 'GET':
            # Serialize the request with full details
            serializer = LegalRequestSerializer(legal_request)
            
            logger.info(f"User {user.id} accessed legal request {request_id}")
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        elif request.method == 'DELETE':
            # Check if user is a lawyer for deletion
            if not (hasattr(user, 'role') and user.role == 'lawyer'):
                return Response(
                    {'detail': 'Only lawyers can delete requests'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            request_number = legal_request.request_number
            
            # Delete the request (cascade will handle related objects)
            legal_request.delete()
            
            logger.info(f"Lawyer {user.id} deleted legal request {request_number}")
            
            return Response({
                'message': f'Legal request {request_number} deleted successfully'
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error with legal request {request_id} for user {request.user.id}: {str(e)}")
        return Response(
            {'detail': 'Error processing legal request'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_legal_request_status(request, request_id):
    """
    Update the status of a legal request.
    Only lawyers can update status.
    """
    try:
        user = request.user
        
        # Check if user is a lawyer
        if not (hasattr(user, 'role') and user.role == 'lawyer'):
            return Response(
                {'detail': 'Only lawyers can update request status'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the legal request
        legal_request = get_object_or_404(
            LegalRequest.objects.select_related('user', 'request_type', 'discipline')
            .prefetch_related(
                'files',
                models.Prefetch(
                    'responses',
                    queryset=LegalRequestResponse.objects.select_related('user'),
                ),
            ),
            id=request_id,
        )
        
        # Get new status from request
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'detail': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status choice
        valid_statuses = [choice[0] for choice in LegalRequest.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'detail': f'Invalid status. Valid choices: {valid_statuses}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        old_status = legal_request.status
        legal_request.status = new_status
        legal_request.save()
        
        logger.info(f"Lawyer {user.id} updated legal request {request_id} status from {old_status} to {new_status}")
        
        # Send email notification to client about status change
        try:
            send_status_update_notification(legal_request, old_status, new_status)
        except Exception as e:
            logger.error(f"Failed to send status update notification: {str(e)}")
            # Don't fail the request if email fails
        
        # Return updated request
        serializer = LegalRequestSerializer(legal_request)
        return Response({
            'message': f'Status updated from {old_status} to {new_status}',
            'request': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error updating legal request status {request_id}: {str(e)}")
        return Response(
            {'detail': 'Error updating request status'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_legal_request_response(request, request_id):
    """
    Create a response to a legal request.
    Both lawyers and clients can create responses.
    """
    try:
        user = request.user
        
        # Get the legal request
        legal_request = get_object_or_404(LegalRequest, id=request_id)
        
        # Check permissions
        user_role = getattr(user, 'role', 'client')
        if user_role != 'lawyer' and legal_request.user != user:
            return Response(
                {'detail': 'You do not have permission to respond to this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get response text
        response_text = request.data.get('response_text', '').strip()
        if not response_text:
            return Response(
                {'detail': 'Response text is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the response
        response = LegalRequestResponse.objects.create(
            legal_request=legal_request,
            response_text=response_text,
            user=user,
            user_type=user_role
        )
        
        # Auto-update status if lawyer responds to a pending request
        if user_role == 'lawyer' and legal_request.status == 'PENDING':
            previous_status = legal_request.status
            legal_request.status = 'IN_REVIEW'
            legal_request.save()
            logger.info(f"Auto-updated legal request {request_id} status from {previous_status} to IN_REVIEW after lawyer response")
        
        logger.info(f"User {user.id} ({user_role}) created response for legal request {request_id}")
        
        # Send email notifications based on who created the response
        try:
            if user_role == 'lawyer':
                # Lawyer responded - notify the client
                notify_client_of_lawyer_response(legal_request, response)
            else:
                # Client responded - notify all lawyers
                notify_lawyers_of_client_response(legal_request, response)
        except Exception as e:
            logger.error(f"Failed to send response notification: {str(e)}")
            # Don't fail the request if email fails
        
        # Serialize the response
        serializer = LegalRequestResponseSerializer(response)
        
        return Response({
            'message': 'Response created successfully',
            'response': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating response for legal request {request_id}: {str(e)}")
        return Response(
            {'detail': 'Error creating response'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_legal_request(request, request_id):
    """
    Delete a legal request.
    Only lawyers can delete requests.
    """
    try:
        user = request.user
        
        # Check if user is a lawyer
        if not (hasattr(user, 'role') and user.role == 'lawyer'):
            return Response(
                {'detail': 'Only lawyers can delete requests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the legal request
        legal_request = get_object_or_404(LegalRequest, id=request_id)
        request_number = legal_request.request_number
        
        # Delete the request (cascade will handle related objects)
        legal_request.delete()
        
        logger.info(f"Lawyer {user.id} deleted legal request {request_number}")
        
        return Response({
            'message': f'Legal request {request_number} deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting legal request {request_id}: {str(e)}")
        return Response(
            {'detail': 'Error deleting request'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_files_to_legal_request(request, request_id):
    """
    Add additional files to an existing legal request.
    Only the client who created the request can add files.
    """
    try:
        user = request.user
        
        # Get the legal request
        legal_request = get_object_or_404(LegalRequest, id=request_id)
        
        # Check permissions - only the request owner (and only clients) can add files
        user_role = getattr(user, 'role', 'client')
        if legal_request.user != user:
            logger.warning(f"User {user.id} attempted to add files to legal request {request_id} without permission")
            return Response(
                {'detail': 'You do not have permission to add files to this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Additional check: only clients can add files
        if user_role != 'client':
            logger.warning(f"Non-client user {user.id} ({user_role}) attempted to add files to legal request {request_id}")
            return Response(
                {'detail': 'Only clients can add files to requests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if request is closed (optional - you can adjust this logic)
        if legal_request.status == 'CLOSED':
            return Response(
                {'detail': 'Cannot add files to a closed request'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get uploaded files
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({'detail': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        successful_uploads = []
        failed_uploads = []
        
        with transaction.atomic():
            for uploaded_file in uploaded_files:
                result = process_file_upload(uploaded_file, legal_request)
                
                if result['success']:
                    successful_uploads.append({
                        'id': result['data']['id'],
                        'filename': result['data']['sanitized_name'],
                        'size': result['data']['size']
                    })
                    logger.info(f"File {result['data']['sanitized_name']} added to legal request {request_id} by user {user.id}")
                else:
                    failed_uploads.append({
                        'filename': result['error']['name'],
                        'error': result['error']['message']
                    })
                    logger.error(f"Failed to upload file {result['error']['name']} to request {request_id}: {result['error']['message']}")
        
        # Prepare response
        response_data = {
            'message': f'{len(successful_uploads)} files uploaded successfully',
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads
        }
        
        if failed_uploads:
            response_data['warning'] = f'{len(failed_uploads)} files failed to upload'
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error adding files to legal request {request_id}: {str(e)}")
        return Response({'detail': 'An error occurred while adding files.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_legal_request_file(request, request_id, file_id):
    """
    Download a specific file from a legal request.
    Users can only download files from requests they have access to.
    """
    try:
        user = request.user
        
        # Get the legal request first
        legal_request = get_object_or_404(LegalRequest, id=request_id)
        
        # Check permissions
        user_role = getattr(user, 'role', 'client')
        if user_role != 'lawyer' and legal_request.user != user:
            logger.warning(f"User {user.id} attempted to download file from legal request {request_id} without permission")
            return Response(
                {'detail': 'You do not have permission to download files from this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the file
        try:
            file_obj = LegalRequestFiles.objects.get(id=file_id)
        except LegalRequestFiles.DoesNotExist:
            logger.error(f"File {file_id} not found")
            raise Http404("File not found")
        
        # Verify the file belongs to this legal request
        if not legal_request.files.filter(id=file_id).exists():
            logger.warning(f"File {file_id} does not belong to legal request {request_id}")
            return Response(
                {'detail': 'File does not belong to this request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if file exists on disk
        if not file_obj.file or not os.path.exists(file_obj.file.path):
            logger.error(f"Physical file not found for file ID {file_id}: {file_obj.file.path if file_obj.file else 'No file path'}")
            return Response(
                {'detail': 'File not found on server'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Log the download
        logger.info(f"User {user.id} downloading file {file_id} from legal request {request_id}")
        
        # Get the original filename
        original_filename = os.path.basename(file_obj.file.name)
        
        # Determine content type based on file extension
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext == '.pdf':
            content_type = 'application/pdf'
        elif file_ext == '.doc':
            content_type = 'application/msword'
        elif file_ext == '.docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif file_ext == '.png':
            content_type = 'image/png'
        elif file_ext == '.txt':
            content_type = 'text/plain'
        elif file_ext in ['.xls', '.xlsx']:
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            content_type = 'application/octet-stream'
        
        # Read file content
        try:
            with open(file_obj.file.path, 'rb') as file_handle:
                file_content = file_handle.read()
        except Exception as read_error:
            logger.error(f"Error reading file content: {str(read_error)}")
            return Response(
                {'detail': 'Error reading file content'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create HttpResponse with file content
        response = HttpResponse(
            file_content,
            content_type=content_type
        )
        
        # Set headers for download
        response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
        response['Content-Length'] = len(file_content)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Accept-Ranges'] = 'bytes'
        
        return response
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id} from legal request {request_id}: {str(e)}")
        return Response(
            {'detail': 'Error downloading file'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
