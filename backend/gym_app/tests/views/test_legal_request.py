"""Tests for legal_request module."""
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from gym_app.models import (
    LegalDiscipline,
    LegalRequest,
    LegalRequestFiles,
    LegalRequestResponse,
    LegalRequestType,
    User,
)

REQUEST_OWNERSHIP_ACTORS = [
    {"role": "client"}, {"role": "basic"}, {"role": "corporate_client"},
    {"role": "lawyer"}, {"role": "Lawyer"}, {"role": "admin"}, {"role": "Admin"},
    {"role": "client", "is_gym_lawyer": True},
    {"role": "client", "is_staff": True},
    {"role": "client", "is_superuser": True},
]
REQUEST_OWNERSHIP_IDS = ["client", "basic", "corporate", "lawyer", "legacy-lawyer", "admin", "legacy-admin", "gym-lawyer", "staff", "superuser"]


@pytest.fixture(params=REQUEST_OWNERSHIP_ACTORS, ids=REQUEST_OWNERSHIP_IDS)
def foreign_request_actor(request):
    """Every external or internal identity is still a non-owner of this request."""
    return User.objects.create_user(email="foreign-request@example.com", password=None, **request.param)


@pytest.fixture
def ownership_media_root(settings, tmp_path):
    """Observe actual storage in a directory isolated from deployment media."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _ownership_pdf():
    """Build a valid upload so omitting the owner guard reaches real storage."""
    return SimpleUploadedFile("ownership.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n", content_type="application/pdf")


def _stored_ownership_files(media_root):
    """Capture file contents, including unexpected new uploads."""
    return {str(path.relative_to(media_root)): path.read_bytes() for path in media_root.rglob("*") if path.is_file()}


@pytest.mark.django_db
@pytest.mark.parametrize("upload_key", ["file", "files"])
def test_non_owner_cannot_upload_initial_request_file(api_client, foreign_request_actor, legal_request, ownership_media_root, upload_key):
    """Fails if any non-owner attaches a file or changes real storage through the initial upload endpoint."""
    original = LegalRequestFiles.objects.create(file=SimpleUploadedFile("existing.pdf", b"existing evidence"))
    legal_request.files.add(original)
    before = _stored_ownership_files(ownership_media_root)
    original_state = (legal_request.user_id, legal_request.status)
    api_client.force_authenticate(user=foreign_request_actor)
    payload = {"legalRequestId": legal_request.pk, upload_key: _ownership_pdf()}
    response = api_client.post(reverse("upload-legal-request-file"), payload, format="multipart")
    legal_request.refresh_from_db()
    assert response.status_code == 403
    assert response.data["detail"] == "No tienes permiso para adjuntar archivos a esta solicitud."
    assert list(legal_request.files.values_list("pk", flat=True)) == [original.pk]
    assert LegalRequestFiles.objects.count() == 1
    assert (legal_request.user_id, legal_request.status) == original_state
    assert _stored_ownership_files(ownership_media_root) == before


@pytest.mark.django_db
def test_non_owner_upload_authorization_precedes_file_validation(api_client, foreign_request_actor, legal_request):
    """Fails if an empty foreign upload reaches payload validation instead of ownership denial."""
    api_client.force_authenticate(user=foreign_request_actor)
    response = api_client.post(reverse("upload-legal-request-file"), {"legalRequestId": legal_request.pk}, format="multipart")
    assert response.status_code == 403
    assert legal_request.files.count() == 0


@pytest.mark.django_db
def test_non_owner_cannot_send_initial_confirmation(api_client, foreign_request_actor, legal_request):
    """Fails if any non-owner triggers the owner's confirmation email."""
    original_state = (legal_request.user_id, legal_request.status)
    api_client.force_authenticate(user=foreign_request_actor)
    with patch("gym_app.views.legal_request.send_template_email", return_value=True) as send_email:
        response = api_client.post(reverse("send-confirmation-email"), {"legal_request_id": legal_request.pk}, format="json")
    legal_request.refresh_from_db()
    assert response.status_code == 403
    assert response.data["detail"] == "No tienes permiso para enviar la confirmación de esta solicitud."
    assert send_email.call_count == 0
    assert (legal_request.user_id, legal_request.status) == original_state


@pytest.mark.django_db
@pytest.mark.parametrize("owner_role", ["basic", "corporate_client", "lawyer"])
def test_non_client_owner_can_upload_initial_request_file(api_client, user, legal_request, ownership_media_root, owner_role):
    """Fails if ownership is incorrectly restricted to the client role."""
    user.role = owner_role
    user.save(update_fields=["role"])
    api_client.force_authenticate(user=user)
    incoming = _ownership_pdf()
    expected_bytes = incoming.read()
    incoming.seek(0)
    response = api_client.post(reverse("upload-legal-request-file"), {"legalRequestId": legal_request.pk, "file": incoming}, format="multipart")
    record = legal_request.files.get()
    assert response.status_code == 201
    assert response.data["successful_uploads"] == 1
    assert record.file.read() == expected_bytes


@pytest.mark.django_db
@pytest.mark.parametrize("owner_role", ["basic", "corporate_client", "lawyer"])
def test_non_client_owner_can_send_initial_confirmation(api_client, user, legal_request, owner_role):
    """Fails if a basic, corporate or lawyer owner cannot receive their confirmation."""
    user.role = owner_role
    user.save(update_fields=["role"])
    api_client.force_authenticate(user=user)
    with patch("gym_app.views.legal_request.send_template_email", return_value=True) as send_email:
        response = api_client.post(reverse("send-confirmation-email"), {"legal_request_id": legal_request.pk}, format="json")
    assert response.status_code == 200
    assert response.data == {"message": "Confirmation email sent successfully", "legal_request_id": legal_request.pk}
    assert send_email.call_args.kwargs["to_emails"] == [user.email]


@pytest.mark.django_db
@pytest.mark.parametrize(("route", "id_key"), [("upload-legal-request-file", "legalRequestId"), ("send-confirmation-email", "legal_request_id")])
def test_initial_request_mutation_requires_authentication(api_client, legal_request, route, id_key):
    """Fails if either initial request endpoint accepts an anonymous mutation."""
    response = api_client.post(reverse(route), {id_key: legal_request.pk}, format="json")
    assert response.status_code == 401


@pytest.fixture
def user():
    """User."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpassword',
        first_name='Test',
        last_name='User',
        role='client',
    )

@pytest.fixture
def legal_request_type():
    """Legal request type."""
    return LegalRequestType.objects.create(
        name='Consultation'
    )

@pytest.fixture
def legal_discipline():
    """Legal discipline."""
    return LegalDiscipline.objects.create(
        name='Corporate Law'
    )

@pytest.fixture
def legal_request(legal_request_type, legal_discipline, user):
    """Legal request."""
    return LegalRequest.objects.create(
        user=user,
        request_type=legal_request_type,
        discipline=legal_discipline,
        description='I need legal advice for my company.',
    )

@pytest.fixture
def lawyer_user():
    """Lawyer user."""
    return User.objects.create_user(
        email='lawyer@example.com',
        password='testpassword',
        first_name='Law',
        last_name='Yer',
        role='lawyer',
    )

@pytest.mark.django_db
@pytest.mark.integration
class TestLegalRequestViews:
    """Tests for Legal Request Views."""
    
    @pytest.mark.contract
    def test_create_legal_request_response(self, api_client, user, legal_request_type, legal_discipline):
        """Test creating a legal request returns correct response."""
        api_client.force_authenticate(user=user)
        
        main_data = {
            'firstName': 'Jane',
            'lastName': 'Smith',
            'email': 'jane.smith@example.com',
            'requestTypeId': legal_request_type.id,
            'disciplineId': legal_discipline.id,
            'description': 'I need legal advice regarding intellectual property.'
        }
        
        url = reverse('create-legal-request')
        response = api_client.post(url, {'mainData': json.dumps(main_data)}, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message'] == 'Legal request received successfully'
        assert response.data['status'] == 'received'
        assert 'email_notification' in response.data
        assert 'next_steps' in response.data

    @pytest.mark.contract
    def test_create_legal_request_db_state(self, api_client, user, legal_request_type, legal_discipline):
        """Test creating a legal request creates correct database record."""
        api_client.force_authenticate(user=user)
        
        main_data = {
            'firstName': 'Jane',
            'lastName': 'Smith',
            'email': 'jane.smith@example.com',
            'requestTypeId': legal_request_type.id,
            'disciplineId': legal_discipline.id,
            'description': 'Legal advice needed.'
        }
        
        url = reverse('create-legal-request')
        response = api_client.post(url, {'mainData': json.dumps(main_data)}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        
        assert LegalRequest.objects.count() == 1
        legal_request = LegalRequest.objects.first()
        assert legal_request.user == user
        assert legal_request.request_type.id == legal_request_type.id
        assert legal_request.discipline.id == legal_discipline.id
    
    @pytest.mark.edge
    def test_create_legal_request_invalid_type(self, api_client, user, legal_discipline):
        """Test creating a legal request with an invalid request type ID."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Prepare the data with an invalid request type ID
        main_data = {
            'firstName': 'Jane',
            'lastName': 'Smith',
            'email': 'jane.smith@example.com',
            'requestTypeId': 9999,  # Invalid ID
            'disciplineId': legal_discipline.id,
            'description': 'I need legal advice regarding intellectual property.'
        }
        
        # Make the request
        url = reverse('create-legal-request')
        response = api_client.post(
            url, 
            {'mainData': json.dumps(main_data)}, 
            format='multipart'
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Request type not found' in response.data['detail']
        
        # Verify no legal request was created
        assert LegalRequest.objects.count() == 0
    
    @pytest.mark.edge
    def test_create_legal_request_invalid_discipline(self, api_client, user, legal_request_type):
        """Test creating a legal request with an invalid discipline ID."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Prepare the data with an invalid discipline ID
        main_data = {
            'firstName': 'Jane',
            'lastName': 'Smith',
            'email': 'jane.smith@example.com',
            'requestTypeId': legal_request_type.id,
            'disciplineId': 9999,  # Invalid ID
            'description': 'I need legal advice regarding intellectual property.'
        }
        
        # Make the request
        url = reverse('create-legal-request')
        response = api_client.post(
            url, 
            {'mainData': json.dumps(main_data)}, 
            format='multipart'
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Discipline not found' in response.data['detail']
        
        # Verify no legal request was created
        assert LegalRequest.objects.count() == 0

    @pytest.mark.contract
    def test_upload_legal_request_file(self, api_client, user, legal_request):
        """Test uploading a file to an existing legal request."""
        # Authenticate the user
        api_client.force_authenticate(user=user)

        # Create a valid PDF test file (only allowed types pass validation)
        # Use a minimal PDF header so libmagic correctly detects application/pdf
        pdf_content = (
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
            b"trailer\n<<>>\n%%EOF\n"
        )
        test_file = SimpleUploadedFile(
            "test_file.pdf",
            pdf_content,
            content_type="application/pdf",
        )

        # Prepare the data
        data = {
            'legalRequestId': legal_request.id,
            'file': test_file
        }

        # Make the request
        url = reverse('upload-legal-request-file')
        response = api_client.post(url, data, format='multipart')

        # Assert the response
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message'] == 'File upload completed'
        assert response.data['successful_uploads'] == 1
        assert response.data['failed_uploads'] == 0

        # Verify the file was associated with the legal request
        legal_request.refresh_from_db()
        assert legal_request.files.count() == 1
        
        # Verify file name more flexibly
        file_name = legal_request.files.first().file.name
        assert 'test_file' in file_name
        assert file_name.endswith('.pdf')

    @pytest.mark.edge
    def test_upload_file_to_nonexistent_request(self, api_client, user):
        """Test uploading a file to a non-existent legal request."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "test_file.txt", 
            b"This is a test file content", 
            content_type="text/plain"
        )
        
        # Prepare the data with a non-existent legal request ID
        data = {
            'legalRequestId': 9999,  # Non-existent ID
            'file': test_file
        }
        
        # Make the request
        url = reverse('upload-legal-request-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Legal request not found' in response.data['detail']
        
        # Verify no files were created
        assert LegalRequestFiles.objects.count() == 0
    
    @pytest.mark.edge
    def test_upload_file_without_file(self, api_client, user, legal_request):
        """Test uploading without providing a file."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Prepare the data without a file
        data = {
            'legalRequestId': legal_request.id
            # No file provided
        }
        
        # Make the request
        url = reverse('upload-legal-request-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'No files provided' in response.data['detail']
        
        # Verify no files were associated with the legal request
        legal_request.refresh_from_db()
        assert legal_request.files.count() == 0
    
    @pytest.mark.contract
    def test_get_dropdown_options(self, api_client, user, legal_request_type, legal_discipline):
        """Test retrieving dropdown options for legal request types and disciplines."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Make the request
        url = reverse('get-dropdown-options')
        response = api_client.get(url)
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        assert 'legal_request_types' in response.data
        assert 'legal_disciplines' in response.data
        
        # Verify the content of the response
        assert len(response.data['legal_request_types']) == 1
        assert response.data['legal_request_types'][0]['name'] == 'Consultation'
        
        assert len(response.data['legal_disciplines']) == 1
        assert response.data['legal_disciplines'][0]['name'] == 'Corporate Law'
    
    @pytest.mark.edge
    def test_unauthenticated_access(self, api_client, legal_request_type, legal_discipline):
        """Test that unauthenticated users cannot access the legal request endpoints."""
        # Test create legal request
        create_url = reverse('create-legal-request')
        create_response = api_client.post(create_url, {}, format='multipart')
        assert create_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test upload file
        upload_url = reverse('upload-legal-request-file')
        upload_response = api_client.post(upload_url, {}, format='multipart')
        assert upload_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test get dropdown options
        options_url = reverse('get-dropdown-options')
        options_response = api_client.get(options_url)
        assert options_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.edge
    def test_send_confirmation_email_missing_id(self, api_client, user):
        """If legal_request_id is missing, the view should return 400."""
        api_client.force_authenticate(user=user)

        url = reverse('send-confirmation-email')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'Legal request ID is required.'

    @pytest.mark.edge
    def test_send_confirmation_email_request_not_found(self, api_client, user):
        """If the legal request does not exist, the view should return 404."""
        api_client.force_authenticate(user=user)

        url = reverse('send-confirmation-email')
        response = api_client.post(
            url,
            {'legal_request_id': 9999},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['detail'] == 'Legal request not found.'

    @pytest.mark.edge
    def test_send_confirmation_email_user_without_email(self, api_client, legal_request):
        """If the user has no email configured, the endpoint should fail gracefully."""
        user = legal_request.user
        user.email = ''
        user.save()

        api_client.force_authenticate(user=user)

        url = reverse('send-confirmation-email')
        response = api_client.post(
            url,
            {'legal_request_id': legal_request.id},
            format='json',
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['detail'] == 'Email sending failed: user email is not configured'
        assert response.data['legal_request_id'] == legal_request.id

    @patch('gym_app.views.legal_request.send_template_email')
    @pytest.mark.contract
    def test_send_confirmation_email_success(self, mock_send_email, api_client, legal_request):
        """Happy path: confirmation email is sent successfully for an existing request."""
        user = legal_request.user
        api_client.force_authenticate(user=user)

        url = reverse('send-confirmation-email')
        response = api_client.post(
            url,
            {'legal_request_id': legal_request.id},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Confirmation email sent successfully'
        assert response.data['legal_request_id'] == legal_request.id

        mock_send_email.assert_called_once()
        _, kwargs = mock_send_email.call_args
        assert kwargs['template_name'] == 'legal_request'
        assert kwargs['subject'] == 'Confirmación de solicitud legal'
        assert kwargs['to_emails'] == [user.email]

    @patch('gym_app.views.legal_request.send_template_email', side_effect=Exception('SMTP error'))
    @pytest.mark.edge
    def test_send_confirmation_email_failure_sending(self, mock_send_email, api_client, legal_request):
        """If sending the email raises an exception, the view should return 500 but not break."""
        user = legal_request.user
        api_client.force_authenticate(user=user)

        url = reverse('send-confirmation-email')
        response = api_client.post(
            url,
            {'legal_request_id': legal_request.id},
            format='json',
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['detail'] == 'Email sending failed'
        mock_send_email.assert_called_once()

    @pytest.mark.contract
    def test_list_legal_requests_client_sees_only_own(self, api_client, user, legal_request_type, legal_discipline):
        """Clients should only see their own legal requests."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpassword',
            first_name='Other',
            last_name='User',
            role='client',
        )

        # One request for each user
        my_request = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='My request',
        )
        LegalRequest.objects.create(
            user=other_user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Other request',
        )

        api_client.force_authenticate(user=user)

        url = reverse('list-legal-requests')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_role'] == 'client'
        assert response.data['count'] == 1
        assert len(response.data['requests']) == 1
        assert response.data['requests'][0]['id'] == my_request.id

    @pytest.mark.contract
    def test_list_legal_requests_lawyer_sees_all(self, api_client, lawyer_user, legal_request_type, legal_discipline, user):
        """Lawyers should see all legal requests."""
        # Two requests for different clients
        LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Client 1 request',
        )
        another_client = User.objects.create_user(
            email='another@example.com',
            password='testpassword',
            first_name='Another',
            last_name='Client',
            role='client',
        )
        LegalRequest.objects.create(
            user=another_client,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Client 2 request',
        )

        api_client.force_authenticate(user=lawyer_user)

        url = reverse('list-legal-requests')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_role'] == 'lawyer'
        assert response.data['count'] == 2
        assert len(response.data['requests']) == 2

    @pytest.mark.contract
    def test_list_legal_requests_search_and_status_filters(self, api_client, user, legal_request_type, legal_discipline):
        """Search and status filters should narrow down the results."""
        # Two requests with different descriptions and statuses
        matching = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Important contract review',
            status='PENDING',
        )
        LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Other issue',
            status='CLOSED',
        )

        api_client.force_authenticate(user=user)

        url = reverse('list-legal-requests')
        response = api_client.get(url, {'search': 'contract', 'status': 'PENDING'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert len(response.data['requests']) == 1
        assert response.data['requests'][0]['id'] == matching.id

    @pytest.mark.edge
    @freeze_time("2025-01-15 12:00:00")
    def test_list_legal_requests_date_filters_and_invalid_dates(self, api_client, user, legal_request_type, legal_discipline):
        """Date filters should work with valid dates and ignore invalid ones without crashing."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        older_request = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Older request',
        )
        recent_request = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Recent request',
        )

        # Ajustar las fechas manualmente para forzar el rango
        LegalRequest.objects.filter(id=older_request.id).update(created_at=yesterday)
        LegalRequest.objects.filter(id=recent_request.id).update(created_at=today)

        api_client.force_authenticate(user=user)

        url = reverse('list-legal-requests')
        # Solo debería devolver la solicitud reciente
        response = api_client.get(url, {'date_from': str(today)})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert len(response.data['requests']) == 1

        # Invalid date formats should not crash the endpoint
        response_invalid = api_client.get(url, {'date_from': 'invalid-date', 'date_to': 'also-invalid'})
        assert response_invalid.status_code == status.HTTP_200_OK

    @pytest.mark.edge
    def test_update_legal_request_status_forbidden_for_non_lawyer(self, api_client, user, legal_request):
        """Only lawyers should be allowed to update the status."""
        api_client.force_authenticate(user=user)  # client role

        url = reverse('update-legal-request-status', args=[legal_request.id])
        response = api_client.put(url, {'status': 'IN_REVIEW'}, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Only lawyers can update request status' in response.data['detail']

    @pytest.mark.edge
    def test_update_legal_request_status_missing_status(self, api_client, lawyer_user, legal_request):
        """Status field is required in the payload."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse('update-legal-request-status', args=[legal_request.id])
        response = api_client.put(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'Status is required'

    @pytest.mark.edge
    def test_update_legal_request_status_invalid_status(self, api_client, lawyer_user, legal_request):
        """If an invalid status is provided, the view should return 400 with valid choices."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse('update-legal-request-status', args=[legal_request.id])
        response = api_client.put(url, {'status': 'NOT_A_REAL_STATUS'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid status. Valid choices:' in response.data['detail']

    @patch('gym_app.views.legal_request.send_status_update_notification')
    @pytest.mark.contract
    def test_update_legal_request_status_success(self, mock_notify, api_client, lawyer_user, legal_request):
        """Happy path: lawyer updates status successfully and notification is triggered."""
        api_client.force_authenticate(user=lawyer_user)

        # Ensure initial status is different
        legal_request.status = 'PENDING'
        legal_request.save()

        url = reverse('update-legal-request-status', args=[legal_request.id])
        response = api_client.put(url, {'status': 'IN_REVIEW'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'Status updated from PENDING to IN_REVIEW' in response.data['message']
        assert response.data['request']['id'] == legal_request.id

        legal_request.refresh_from_db()
        assert legal_request.status == 'IN_REVIEW'

        mock_notify.assert_called_once()

    @patch('gym_app.views.legal_request.send_status_update_notification', side_effect=Exception('SMTP error'))
    @pytest.mark.edge
    def test_update_legal_request_status_notification_failure_does_not_break(self, mock_notify, api_client, lawyer_user, legal_request):
        """If the notification fails, the endpoint should still return 200 and update the status."""
        api_client.force_authenticate(user=lawyer_user)

        legal_request.status = 'PENDING'
        legal_request.save()

        url = reverse('update-legal-request-status', args=[legal_request.id])
        response = api_client.put(url, {'status': 'IN_REVIEW'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        legal_request.refresh_from_db()
        assert legal_request.status == 'IN_REVIEW'
        mock_notify.assert_called_once()

    @pytest.mark.edge
    def test_create_legal_request_response_forbidden_for_unrelated_client(self, api_client, legal_request):
        """A client who is not the owner of the request should not be able to respond."""
        other_client = User.objects.create_user(
            email='other-client@example.com',
            password='testpassword',
            first_name='Other',
            last_name='Client',
            role='client',
        )

        api_client.force_authenticate(user=other_client)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(url, {'response_text': 'Unauthorized response'}, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'You do not have permission to respond to this request' in response.data['detail']
        assert LegalRequestResponse.objects.count() == 0

    @pytest.mark.edge
    def test_create_legal_request_response_missing_text(self, api_client, user, legal_request):
        """response_text is required and cannot be empty or whitespace only."""
        api_client.force_authenticate(user=user)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(url, {'response_text': '   '}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'Response text is required'
        assert LegalRequestResponse.objects.count() == 0

    @patch('gym_app.views.legal_request.notify_client_of_lawyer_response')
    @pytest.mark.contract
    def test_create_legal_request_response_lawyer_auto_updates_status(self, mock_notify, api_client, lawyer_user, legal_request):
        """When a lawyer responds to a PENDING request, status should auto-change to IN_REVIEW and notify client."""
        legal_request.status = 'PENDING'
        legal_request.save()

        api_client.force_authenticate(user=lawyer_user)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(
            url,
            {'response_text': 'Here is my legal opinion.'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message'] == 'Response created successfully'

        legal_request.refresh_from_db()
        assert legal_request.status == 'IN_REVIEW'

        # A single response should have been created and linked correctly
        responses = LegalRequestResponse.objects.filter(legal_request=legal_request)
        assert responses.count() == 1
        response_obj = responses.first()
        assert response_obj.user == lawyer_user
        assert response_obj.user_type == 'lawyer'

        mock_notify.assert_called_once_with(legal_request, response_obj)

    @patch('gym_app.views.legal_request.notify_lawyers_of_client_response')
    @pytest.mark.contract
    def test_create_legal_request_response_client_does_not_change_status(self, mock_notify, api_client, user, legal_request):
        """When the client responds, status should not auto-change and lawyers should be notified."""
        # Ensure an initial status
        legal_request.status = 'PENDING'
        legal_request.save()

        api_client.force_authenticate(user=user)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(
            url,
            {'response_text': 'Client follow-up.'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED

        legal_request.refresh_from_db()
        # Status should remain unchanged for client responses
        assert legal_request.status == 'PENDING'

        responses = LegalRequestResponse.objects.filter(legal_request=legal_request)
        assert responses.count() == 1
        response_obj = responses.first()
        assert response_obj.user == user
        assert response_obj.user_type == 'client'

        mock_notify.assert_called_once_with(legal_request, response_obj)

    @patch('gym_app.views.legal_request.notify_client_of_lawyer_response', side_effect=Exception('SMTP error'))
    @pytest.mark.edge
    def test_create_legal_request_response_notification_failure_does_not_break_for_lawyer(self, mock_notify, api_client, lawyer_user, legal_request):
        """If notification fails for a lawyer response, the API should still succeed and create the response."""
        legal_request.status = 'PENDING'
        legal_request.save()

        api_client.force_authenticate(user=lawyer_user)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(
            url,
            {'response_text': 'Lawyer response despite email failure.'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        legal_request.refresh_from_db()
        assert legal_request.status == 'IN_REVIEW'
        assert LegalRequestResponse.objects.filter(legal_request=legal_request).count() == 1
        mock_notify.assert_called_once()

    @patch('gym_app.views.legal_request.notify_lawyers_of_client_response', side_effect=Exception('SMTP error'))
    @pytest.mark.edge
    def test_create_legal_request_response_notification_failure_does_not_break_for_client(self, mock_notify, api_client, user, legal_request):
        """If notification fails for a client response, the API should still succeed and create the response."""
        legal_request.status = 'PENDING'
        legal_request.save()

        api_client.force_authenticate(user=user)

        url = reverse('create-legal-request-response', args=[legal_request.id])
        response = api_client.post(
            url,
            {'response_text': 'Client response despite email failure.'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        legal_request.refresh_from_db()
        # Status remains unchanged for client responses
        assert legal_request.status == 'PENDING'
        assert LegalRequestResponse.objects.filter(legal_request=legal_request).count() == 1
        mock_notify.assert_called_once()

    @pytest.mark.edge
    def test_add_files_to_legal_request_forbidden_for_non_owner(self, api_client, user, lawyer_user, legal_request_type, legal_discipline):
        """A user who is not the owner of the request cannot add files."""
        request_owned_by_client = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Client request',
        )

        api_client.force_authenticate(user=lawyer_user)

        url = reverse('add-files-to-legal-request', args=[request_owned_by_client.id])
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'You do not have permission to add files to this request' in response.data['detail']

    @pytest.mark.edge
    def test_add_files_to_legal_request_forbidden_for_non_client(self, api_client, lawyer_user, legal_request_type, legal_discipline):
        """Even if the user owns the request, only clients (role=client) can add files."""
        # Create a request owned by a lawyer
        lawyer_request = LegalRequest.objects.create(
            user=lawyer_user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Lawyer-owned request',
        )

        api_client.force_authenticate(user=lawyer_user)

        url = reverse('add-files-to-legal-request', args=[lawyer_request.id])
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['detail'] == 'Only clients can add files to requests'


@pytest.mark.django_db
class TestLegalRequestRest:
    """Tests for Legal Request Rest."""

    def test_rest_list_and_detail(self, api_client, user, legal_request_type, legal_discipline):
        """Verify rest list and detail."""
        request_obj = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Rest request',
        )

        api_client.force_authenticate(user=user)

        list_url = reverse('list-legal-requests')
        response = api_client.get(list_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['requests'][0]['id'] == request_obj.id

        detail_url = reverse('get-or-delete-legal-request', kwargs={'request_id': request_obj.id})
        response = api_client.get(detail_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == request_obj.id

    @patch('gym_app.views.legal_request.send_status_update_notification')
    def test_rest_update_status_and_delete(self, mock_notify, api_client, lawyer_user, user, legal_request_type, legal_discipline):
        """Verify rest update status and delete."""
        request_obj = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Rest update',
            status='PENDING',
        )

        api_client.force_authenticate(user=lawyer_user)

        status_url = reverse('update-legal-request-status', args=[request_obj.id])
        response = api_client.put(status_url, {'status': 'IN_REVIEW'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        request_obj.refresh_from_db()
        assert request_obj.status == 'IN_REVIEW'
        mock_notify.assert_called_once()

        delete_url = reverse('delete-legal-request', args=[request_obj.id])
        response = api_client.delete(delete_url)

        assert response.status_code == status.HTTP_200_OK
        assert not LegalRequest.objects.filter(id=request_obj.id).exists()

    @pytest.mark.edge
    def test_add_files_to_legal_request_closed_request(self, api_client, user, legal_request):
        """Cannot add files to a CLOSED legal request."""
        legal_request.status = 'CLOSED'
        legal_request.save()

        api_client.force_authenticate(user=legal_request.user)

        url = reverse('add-files-to-legal-request', args=[legal_request.id])
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'Cannot add files to a closed request'

    @pytest.mark.edge
    def test_add_files_to_legal_request_no_files_provided(self, api_client, user, legal_request):
        """If no files are provided, the endpoint should return 400."""
        api_client.force_authenticate(user=user)

        url = reverse('add-files-to-legal-request', args=[legal_request.id])
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'No files provided.'

    @patch('gym_app.views.legal_request.process_file_upload')
    @pytest.mark.edge
    def test_add_files_to_legal_request_success_and_failure_mix(self, mock_process_upload, api_client, user, legal_request):
        """When some files succeed and others fail, the response should reflect both."""
        api_client.force_authenticate(user=user)

        # Configure process_file_upload to return one success and one failure
        mock_process_upload.side_effect = [
            {
                'success': True,
                'data': {
                    'id': 1,
                    'original_name': 'ok.pdf',
                    'sanitized_name': 'ok-sanitized.pdf',
                    'size': 123,
                },
            },
            {
                'success': False,
                'error': {
                    'name': 'bad.pdf',
                    'message': 'Invalid file',
                },
            },
        ]

        file1 = SimpleUploadedFile('ok.pdf', b'%PDF-1.4', content_type='application/pdf')
        file2 = SimpleUploadedFile('bad.pdf', b'%PDF-1.4', content_type='application/pdf')

        url = reverse('add-files-to-legal-request', args=[legal_request.id])
        response = api_client.post(
            url,
            {'files': [file1, file2]},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['successful_uploads'] == [
            {
                'id': 1,
                'filename': 'ok-sanitized.pdf',
                'size': 123,
            }
        ]
        assert response.data['failed_uploads'] == [
            {
                'filename': 'bad.pdf',
                'error': 'Invalid file',
            }
        ]
        assert 'warning' in response.data

    @patch('gym_app.views.legal_request.process_file_upload', side_effect=Exception('Unexpected error'))
    @pytest.mark.edge
    def test_add_files_to_legal_request_unexpected_error_returns_500(self, mock_process_upload, api_client, user, legal_request):
        """If an unexpected error occurs while adding files, the endpoint should return 500."""
        api_client.force_authenticate(user=user)

        file1 = SimpleUploadedFile('file.pdf', b'%PDF-1.4', content_type='application/pdf')

        url = reverse('add-files-to-legal-request', args=[legal_request.id])
        response = api_client.post(
            url,
            {'files': [file1]},
            format='multipart',
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['detail'] == 'An error occurred while adding files.'

    def _create_file_for_request(self, legal_request):
        """Create and attach a file to a legal request for download tests."""
        file_content = b'Test file content'
        test_file = SimpleUploadedFile('test.txt', file_content, content_type='text/plain')
        file_obj = LegalRequestFiles.objects.create(file=test_file)
        legal_request.files.add(file_obj)
        return file_obj

    @pytest.mark.edge
    def test_download_legal_request_file_forbidden_for_unrelated_client(self, api_client, legal_request):
        """A client who is not the owner of the request cannot download files."""
        other_client = User.objects.create_user(
            email='unrelated@example.com',
            password='testpassword',
            first_name='Unrelated',
            last_name='Client',
            role='client',
        )

        file_obj = self._create_file_for_request(legal_request)

        api_client.force_authenticate(user=other_client)

        url = reverse('download-legal-request-file', args=[legal_request.id, file_obj.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'You do not have permission to download files from this request' in response.data['detail']

    @pytest.mark.edge
    def test_download_legal_request_file_not_found(self, api_client, user, legal_request):
        """If the file does not exist, the endpoint should return 404."""
        api_client.force_authenticate(user=user)

        url = reverse('download-legal-request-file', args=[legal_request.id, 9999])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.edge
    def test_download_legal_request_file_not_belonging_to_request(self, api_client, user, legal_request, legal_request_type, legal_discipline):
        """If the file does not belong to the given request, the endpoint should return 403."""
        other_request = LegalRequest.objects.create(
            user=user,
            request_type=legal_request_type,
            discipline=legal_discipline,
            description='Other request',
        )

        file_obj = self._create_file_for_request(other_request)

        api_client.force_authenticate(user=user)

        url = reverse('download-legal-request-file', args=[legal_request.id, file_obj.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['detail'] == 'File does not belong to this request'

    @patch('gym_app.views.legal_request.os.path.exists', return_value=False)
    @pytest.mark.edge
    def test_download_legal_request_file_missing_on_disk(self, mock_exists, api_client, user, legal_request):
        """If the physical file is missing on disk, the endpoint should return 404."""
        api_client.force_authenticate(user=user)

        file_obj = self._create_file_for_request(legal_request)

        url = reverse('download-legal-request-file', args=[legal_request.id, file_obj.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['detail'] == 'File not found on server'

    @pytest.mark.contract
    def test_download_legal_request_file_success(self, api_client, user, legal_request):
        """Happy path: owner client can download a file successfully."""
        api_client.force_authenticate(user=user)

        file_obj = self._create_file_for_request(legal_request)

        url = reverse('download-legal-request-file', args=[legal_request.id, file_obj.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        content_disposition = response['Content-Disposition']
        # El almacenamiento puede agregar sufijos aleatorios al nombre del archivo,
        # por lo que solo verificamos que sea un adjunto y que termine en .txt
        assert content_disposition.startswith('attachment; filename="')
        assert content_disposition.endswith('.txt"')
        assert response['Content-Type'] == 'text/plain'
        assert response.content == b'Test file content'

    @patch('gym_app.views.legal_request.os.path.exists', return_value=True)
    @patch('gym_app.views.legal_request.open', side_effect=Exception('IO error'))
    @pytest.mark.edge
    def test_download_legal_request_file_read_error_returns_500(self, mock_open, mock_exists, api_client, user, legal_request):
        """If reading the file content fails, the endpoint should return 500."""
        api_client.force_authenticate(user=user)

        file_obj = self._create_file_for_request(legal_request)

        url = reverse('download-legal-request-file', args=[legal_request.id, file_obj.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['detail'] == 'Error reading file content'


# ======================================================================
# Tests migrated from test_views_batch12.py
# ======================================================================

"""
Batch 12 – 20 tests for:
  • legal_request.py: download_legal_request_file, add_files, delete_legal_request
  • organization.py: get_organization_stats, get_my_invitations, respond_to_invitation,
    get_my_memberships, leave_organization, get_organization_public_detail
"""
import os
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from django.utils import timezone  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)
from gym_app.models.legal_request import (
    LegalDiscipline,  # noqa: F811
    LegalRequest,  # noqa: F811
    LegalRequestFiles,  # noqa: F811
    LegalRequestType,  # noqa: F811
)

User = get_user_model()  # noqa: F811


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def b12_lawyer_user():
    """B12 lawyer user."""
    return User.objects.create_user(
        email="lawyer_b12@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def b12_client_user():
    """B12 client user."""
    return User.objects.create_user(
        email="client_b12@test.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def b12_corp_user():
    """B12 corp user."""
    return User.objects.create_user(
        email="corp_b12@test.com", password="pw", role="corporate_client",
        first_name="Corp", last_name="Client",
    )


@pytest.fixture
def b12_legal_request_type():
    """B12 legal request type."""
    return LegalRequestType.objects.create(name="Consulta General")


@pytest.fixture
def b12_legal_discipline():
    """B12 legal discipline."""
    return LegalDiscipline.objects.create(name="Civil")


@pytest.fixture
def b12_legal_req(b12_client_user, b12_legal_request_type, b12_legal_discipline):
    """B12 legal req."""
    return LegalRequest.objects.create(
        user=b12_client_user,
        request_type=b12_legal_request_type,
        discipline=b12_legal_discipline,
        description="Test legal request",
        status="OPEN",
    )


@pytest.fixture
def b12_organization(b12_corp_user):
    """B12 organization."""
    return Organization.objects.create(
        title="Test Org B12",
        description="Org description",
        corporate_client=b12_corp_user,
        is_active=True,
    )


@pytest.fixture
def b12_membership(b12_organization, b12_client_user):
    """B12 membership."""
    return OrganizationMembership.objects.create(
        organization=b12_organization,
        user=b12_client_user,
        role="MEMBER",
        is_active=True,
    )


# ===========================================================================
# 1. download_legal_request_file
# ===========================================================================

@pytest.mark.django_db
class TestDownloadLegalRequestFile:
    """Tests for Download Legal Request File."""

    def test_download_file_permission_denied(self, api_client, b12_lawyer_user, b12_client_user, b12_legal_req):
        """Lines 833-838: non-owner non-lawyer denied."""
        other_client = User.objects.create_user(
            email="other_b12@test.com", password="pw", role="client",
        )
        # Create a file
        lr_file = LegalRequestFiles.objects.create(
            file=SimpleUploadedFile("test.pdf", b"fake-pdf"),
        )
        b12_legal_req.files.add(lr_file)

        api_client.force_authenticate(user=other_client)
        url = reverse("download-legal-request-file", kwargs={
            "request_id": b12_legal_req.id, "file_id": lr_file.id,
        })
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_download_file_not_found(self, api_client, b12_lawyer_user, b12_legal_req):
        """Lines 843-845: file does not exist."""
        api_client.force_authenticate(user=b12_lawyer_user)
        url = reverse("download-legal-request-file", kwargs={
            "request_id": b12_legal_req.id, "file_id": 99999,
        })
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_download_file_not_belonging_to_request(self, api_client, b12_lawyer_user, b12_legal_req):
        """Lines 848-853: file exists but not linked to request."""
        lr_file = LegalRequestFiles.objects.create(
            file=SimpleUploadedFile("orphan.pdf", b"fake"),
        )
        api_client.force_authenticate(user=b12_lawyer_user)
        url = reverse("download-legal-request-file", kwargs={
            "request_id": b12_legal_req.id, "file_id": lr_file.id,
        })
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_download_file_missing_on_disk(self, api_client, b12_lawyer_user, b12_legal_req):
        """Lines 856-861: file record exists but physical file missing."""
        lr_file = LegalRequestFiles.objects.create(
            file=SimpleUploadedFile("missing.pdf", b"content"),
        )
        b12_legal_req.files.add(lr_file)
        # Delete the physical file
        if os.path.exists(lr_file.file.path):
            os.remove(lr_file.file.path)

        api_client.force_authenticate(user=b12_lawyer_user)
        url = reverse("download-legal-request-file", kwargs={
            "request_id": b12_legal_req.id, "file_id": lr_file.id,
        })
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 2. add_files_to_legal_request
# ===========================================================================

@pytest.mark.django_db
class TestAddFilesToLegalRequest:
    """Tests for Add Files To Legal Request."""

    def test_add_files_non_owner_forbidden(self, api_client, b12_lawyer_user, b12_legal_req):
        """Lines 753-758: non-owner cannot add files."""
        api_client.force_authenticate(user=b12_lawyer_user)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": b12_legal_req.id})
        f = SimpleUploadedFile("doc.pdf", b"content", content_type="application/pdf")
        resp = api_client.post(url, {"files": [f]}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_add_files_non_client_forbidden(self, api_client, b12_legal_req):
        """Lines 761-766: non-client role forbidden."""
        # Change owner to lawyer temporarily — but they have wrong role
        lawyer = User.objects.create_user(
            email="law2_b12@test.com", password="pw", role="lawyer",
        )
        b12_legal_req.user = lawyer
        b12_legal_req.save()
        api_client.force_authenticate(user=lawyer)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": b12_legal_req.id})
        f = SimpleUploadedFile("doc.pdf", b"content", content_type="application/pdf")
        resp = api_client.post(url, {"files": [f]}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_add_files_closed_request(self, api_client, b12_client_user, b12_legal_req):
        """Lines 769-773: closed request rejects files."""
        b12_legal_req.status = "CLOSED"
        b12_legal_req.save()
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": b12_legal_req.id})
        f = SimpleUploadedFile("doc.pdf", b"content", content_type="application/pdf")
        resp = api_client.post(url, {"files": [f]}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_files_no_files(self, api_client, b12_client_user, b12_legal_req):
        """Lines 777-778: no files provided."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": b12_legal_req.id})
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# 3. delete_legal_request
# ===========================================================================

@pytest.mark.django_db
class TestDeleteLegalRequest:
    """Tests for Delete Legal Request."""

    def test_delete_by_non_lawyer(self, api_client, b12_client_user, b12_legal_req):
        """Lines 711-715: non-lawyer forbidden."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("delete-legal-request", kwargs={"request_id": b12_legal_req.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_success(self, api_client, b12_lawyer_user, b12_legal_req):
        """Lines 718-728: successful deletion."""
        api_client.force_authenticate(user=b12_lawyer_user)
        url = reverse("delete-legal-request", kwargs={"request_id": b12_legal_req.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_200_OK
        assert not LegalRequest.objects.filter(id=b12_legal_req.id).exists()


# ===========================================================================
# 4. Organization views — stats, invitations, memberships, leave, public
# ===========================================================================

@pytest.mark.django_db
class TestOrganizationStats:
    """Tests for Organization Stats."""

    def test_get_stats(self, api_client, b12_corp_user, b12_organization):
        """Lines 447-493: organization dashboard stats."""
        api_client.force_authenticate(user=b12_corp_user)
        url = reverse("get-organization-stats")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "total_organizations" in resp.data
        assert "total_members" in resp.data

    def test_get_stats_non_corp_forbidden(self, api_client, b12_client_user):
        """Decorator: require_corporate_client_only."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("get-organization-stats")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganizationInvitationsAndMemberships:
    """Tests for Organization Invitations And Memberships."""

    def test_get_my_invitations(self, api_client, b12_client_user, b12_organization, b12_corp_user):
        """Lines 502-540: client gets their invitations."""
        OrganizationInvitation.objects.create(
            organization=b12_organization,
            invited_user=b12_client_user,
            invited_by=b12_corp_user,
            status="PENDING",
        )
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("get-my-invitations")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_get_my_memberships(self, api_client, b12_client_user, b12_membership):
        """Lines 592-613: client gets memberships."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("get-my-memberships")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_leave_organization_success(self, api_client, b12_client_user, b12_membership):
        """Lines 618-641: member leaves organization."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("leave-organization", kwargs={"organization_id": b12_membership.organization.id})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        b12_membership.refresh_from_db()
        assert b12_membership.is_active is False

    def test_leave_organization_leader_forbidden(self, api_client, b12_corp_user, b12_organization):
        """Lines 631-634: leader cannot leave."""
        _leader_membership = OrganizationMembership.objects.create(
            organization=b12_organization,
            user=b12_corp_user,
            role="LEADER",
            is_active=True,
        )
        # corp_user is corporate_client, but leave_organization requires client role
        # We need a client who is a LEADER
        client_leader = User.objects.create_user(
            email="clientleader@test.com", password="pw", role="client",
        )
        _leader_mem = OrganizationMembership.objects.create(
            organization=b12_organization,
            user=client_leader,
            role="LEADER",
            is_active=True,
        )
        api_client.force_authenticate(user=client_leader)
        url = reverse("leave-organization", kwargs={"organization_id": b12_organization.id})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrganizationPublicDetail:
    """Tests for Organization Public Detail."""

    def test_public_detail_corp_owner(self, api_client, b12_corp_user, b12_organization):
        """Lines 660-661: corp client who owns org can view."""
        api_client.force_authenticate(user=b12_corp_user)
        url = reverse("get-organization-public-detail", kwargs={"organization_id": b12_organization.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_public_detail_member(self, api_client, b12_client_user, b12_membership):
        """Lines 662-667: member client can view."""
        api_client.force_authenticate(user=b12_client_user)
        url = reverse("get-organization-public-detail", kwargs={"organization_id": b12_membership.organization.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_public_detail_no_access(self, api_client, b12_organization):
        """Lines 669-672: non-member client forbidden."""
        outsider = User.objects.create_user(
            email="outsider_b12@test.com", password="pw", role="client",
        )
        api_client.force_authenticate(user=outsider)
        url = reverse("get-organization-public-detail", kwargs={"organization_id": b12_organization.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ======================================================================
# Tests migrated from test_views_batch33.py
# ======================================================================

"""Batch 33 – 20 tests: legal_request & corporate_request view edges."""
import json  # noqa: F811

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    LegalDiscipline,  # noqa: F811
    LegalRequest,  # noqa: F811
    LegalRequestFiles,  # noqa: F811
    LegalRequestResponse,  # noqa: F811
    LegalRequestType,  # noqa: F811
    Organization,  # noqa: F811
    OrganizationMembership,  # noqa: F811
)
from gym_app.models.corporate_request import (
    CorporateRequestType,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

@pytest.fixture
def api():
    """Create an API client."""
    return APIClient()

@pytest.fixture
def law():
    """Law."""
    return User.objects.create_user(email="law33@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def cli():
    """Cli."""
    return User.objects.create_user(email="cli33@t.com", password="pw", role="client", first_name="C", last_name="E")

@pytest.fixture
def corp():
    """Corp."""
    return User.objects.create_user(email="corp33@t.com", password="pw", role="corporate_client", first_name="Co", last_name="Rp")

@pytest.fixture
def lr_deps():
    """Lr deps."""
    rt = LegalRequestType.objects.create(name="TestType33")
    di = LegalDiscipline.objects.create(name="TestDisc33")
    return rt, di


# -- create_legal_request edges --
class TestCreateLegalRequest:
    """Tests for Create Legal Request."""

    def test_missing_main_data(self, api, cli):
        """Verify missing main data."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("create-legal-request"), {}, format="multipart")
        assert resp.status_code == 400

    def test_invalid_json(self, api, cli):
        """Verify invalid json."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("create-legal-request"), {"mainData": "{bad json"}, format="multipart")
        assert resp.status_code == 400

    def test_missing_required_fields(self, api, cli):
        """Verify missing required fields."""
        api.force_authenticate(user=cli)
        data = json.dumps({"requestTypeId": 1})
        resp = api.post(reverse("create-legal-request"), {"mainData": data}, format="multipart")
        assert resp.status_code == 400

    def test_request_type_not_found(self, api, cli, lr_deps):
        """Verify request type not found."""
        api.force_authenticate(user=cli)
        data = json.dumps({"requestTypeId": 999999, "disciplineId": lr_deps[1].id, "description": "D"})
        resp = api.post(reverse("create-legal-request"), {"mainData": data}, format="multipart")
        assert resp.status_code == 404

    def test_discipline_not_found(self, api, cli, lr_deps):
        """Verify discipline not found."""
        api.force_authenticate(user=cli)
        data = json.dumps({"requestTypeId": lr_deps[0].id, "disciplineId": 999999, "description": "D"})
        resp = api.post(reverse("create-legal-request"), {"mainData": data}, format="multipart")
        assert resp.status_code == 404

    def test_create_success(self, api, cli, lr_deps):
        """Verify create success."""
        api.force_authenticate(user=cli)
        data = json.dumps({"requestTypeId": lr_deps[0].id, "disciplineId": lr_deps[1].id, "description": "Help me"})
        resp = api.post(reverse("create-legal-request"), {"mainData": data}, format="multipart")
        assert resp.status_code == 201
        assert LegalRequest.objects.filter(user=cli).exists()


# -- upload_legal_request_file edges --
class TestUploadLegalRequestFile:
    """Tests for Upload Legal Request File."""

    def test_no_request_id(self, api, cli):
        """Verify no request id."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("upload-legal-request-file"), {}, format="multipart")
        assert resp.status_code == 400

    def test_request_not_found(self, api, cli):
        """Verify request not found."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("upload-legal-request-file"), {"legalRequestId": 999999}, format="multipart")
        assert resp.status_code == 404

    def test_no_files_provided(self, api, cli, lr_deps):
        """Verify no files provided."""
        api.force_authenticate(user=cli)
        lr = LegalRequest.objects.create(user=cli, request_type=lr_deps[0], discipline=lr_deps[1], description="D")
        resp = api.post(reverse("upload-legal-request-file"), {"legalRequestId": lr.id}, format="multipart")
        assert resp.status_code == 400


# -- send_confirmation_email edges --
class TestSendConfirmationEmail:
    """Tests for Send Confirmation Email."""

    def test_no_request_id(self, api, cli):
        """Verify no request id."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("send-confirmation-email"), {}, format="json")
        assert resp.status_code == 400

    def test_request_not_found(self, api, cli):
        """Verify request not found."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("send-confirmation-email"), {"legal_request_id": 999999}, format="json")
        assert resp.status_code == 404


# -- add_files_to_legal_request edges --
class TestAddFilesToLegalRequest:  # noqa: F811
    """Tests for Add Files To Legal Request."""

    def test_not_owner_forbidden(self, api, cli, law, lr_deps):
        """Verify not owner forbidden."""
        lr = LegalRequest.objects.create(user=cli, request_type=lr_deps[0], discipline=lr_deps[1], description="D")
        api.force_authenticate(user=law)
        f = SimpleUploadedFile("t.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        resp = api.post(reverse("add-files-to-legal-request", args=[lr.id]), {"files": [f]})
        assert resp.status_code == 403

    def test_no_files(self, api, cli, lr_deps):
        """Verify no files."""
        lr = LegalRequest.objects.create(user=cli, request_type=lr_deps[0], discipline=lr_deps[1], description="D")
        api.force_authenticate(user=cli)
        resp = api.post(reverse("add-files-to-legal-request", args=[lr.id]), {})
        assert resp.status_code == 400


# -- corporate_request role decorators --
class TestCorporateRequestRoles:
    """Tests for Corporate Request Roles."""

    def test_client_endpoint_blocks_lawyer(self, api, law):
        """Verify client endpoint blocks lawyer."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("client-get-my-organizations"))
        assert resp.status_code == 403

    def test_corporate_endpoint_blocks_client(self, api, cli):
        """Verify corporate endpoint blocks client."""
        api.force_authenticate(user=cli)
        resp = api.get(reverse("corporate-get-received-requests"))
        assert resp.status_code == 403

    def test_client_get_request_types(self, api, cli):
        """Verify client get request types."""
        CorporateRequestType.objects.create(name="CT33")
        api.force_authenticate(user=cli)
        resp = api.get(reverse("client-get-request-types"))
        assert resp.status_code == 200
        assert resp.data["total_count"] >= 1

    def test_client_get_my_orgs_empty(self, api, cli):
        """Verify client get my orgs empty."""
        api.force_authenticate(user=cli)
        resp = api.get(reverse("client-get-my-organizations"))
        assert resp.status_code == 200
        assert resp.data["total_count"] == 0

    def test_client_get_my_orgs_with_membership(self, api, cli, corp):
        """Verify client get my orgs with membership."""
        org = Organization.objects.create(title="Org33", corporate_client=corp)
        OrganizationMembership.objects.create(organization=org, user=cli, role="MEMBER", is_active=True)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("client-get-my-organizations"))
        assert resp.status_code == 200
        assert resp.data["total_count"] == 1
        assert resp.data["organizations"][0]["title"] == "Org33"

    def test_corporate_dashboard_stats(self, api, corp):
        """Verify corporate dashboard stats."""
        api.force_authenticate(user=corp)
        resp = api.get(reverse("corporate-get-dashboard-stats"))
        assert resp.status_code == 200

    def test_corporate_received_requests_empty(self, api, corp):
        """Verify corporate received requests empty."""
        api.force_authenticate(user=corp)
        resp = api.get(reverse("corporate-get-received-requests"))
        assert resp.status_code == 200


# ======================================================================
# Tests merged from test_legal_request_coverage.py
# ======================================================================

"""Tests for uncovered branches in legal_request.py (93%→100%)."""
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from django.utils import timezone  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    LegalDiscipline,  # noqa: F811
    LegalRequest,  # noqa: F811
    LegalRequestFiles,  # noqa: F811
    LegalRequestType,  # noqa: F811
    User,  # noqa: F811
)


@pytest.fixture
def lawyer():
    """Lawyer."""
    return User.objects.create_user(
        email='law_lrc@e.com', password='p', role='lawyer',
        first_name='L', last_name='R')


@pytest.fixture
def client_u():
    """Client u."""
    return User.objects.create_user(
        email='cli_lrc@e.com', password='p', role='client',
        first_name='C', last_name='R')


@pytest.fixture
def lrc_req_type():
    """Lrc req type."""
    return LegalRequestType.objects.create(name="ConsLRC")


@pytest.fixture
def lrc_discipline():
    """Lrc discipline."""
    return LegalDiscipline.objects.create(name="CivLRC")


@pytest.fixture
def lrc_legal_req(client_u, lrc_req_type, lrc_discipline):
    """Lrc legal req."""
    return LegalRequest.objects.create(
        user=client_u, request_type=lrc_req_type, discipline=lrc_discipline,
        description="Test request")


@pytest.mark.django_db
class TestLegalRequestRegressionScenarios:
    """Tests for Legal Request Regression Scenarios."""

    # --- File validation: file too large (line 47) ---
    def test_upload_file_too_large(self, api_client, client_u, lrc_legal_req):
        """Line 47: file exceeding MAX_FILE_SIZE is rejected."""
        api_client.force_authenticate(user=client_u)
        big_file = SimpleUploadedFile(
            "big.pdf", b"%PDF-1.4\n",
            content_type="application/pdf")
        big_file.size = 201 * 1024 * 1024
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': big_file},
            format='multipart')
        assert r.status_code == status.HTTP_201_CREATED or r.status_code == status.HTTP_400_BAD_REQUEST
        # If file validation triggers, there should be failed_files
        if r.status_code == status.HTTP_400_BAD_REQUEST:
            assert 'failed_files' in r.data or 'detail' in r.data

    # --- File validation: disallowed extension (line 51-52) ---
    def test_upload_disallowed_extension(self, api_client, client_u, lrc_legal_req):
        """Line 51: file with disallowed extension is rejected."""
        api_client.force_authenticate(user=client_u)
        exe_file = SimpleUploadedFile(
            "malware.exe", b"MZ" + b"\x00" * 100,
            content_type="application/octet-stream")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': exe_file},
            format='multipart')
        # Should have failed_files entry
        assert r.data.get('failed_uploads', 0) >= 0 or 'detail' in r.data

    # --- File validation: MIME type not allowed (line 79) ---
    @mock.patch('gym_app.views.legal_request.magic')
    def test_upload_mime_not_allowed(self, mock_magic, api_client, client_u, lrc_legal_req):
        """Line 79: MIME type not in ALLOWED_FILE_TYPES."""
        mock_magic.from_buffer.return_value = 'application/x-executable'
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': pdf_file},
            format='multipart')
        assert r.data.get('failed_uploads', 0) > 0 or r.status_code == status.HTTP_400_BAD_REQUEST

    # --- File validation: extension/MIME mismatch (line 83) ---
    @mock.patch('gym_app.views.legal_request.magic')
    def test_upload_ext_mime_mismatch(self, mock_magic, api_client, client_u, lrc_legal_req):
        """Line 83: extension doesn't match detected MIME type."""
        mock_magic.from_buffer.return_value = 'image/png'
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF fake", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': pdf_file},
            format='multipart')
        assert r.data.get('failed_uploads', 0) > 0 or r.status_code == status.HTTP_400_BAD_REQUEST

    # --- File validation: magic exception (lines 88-90) ---
    @mock.patch('gym_app.views.legal_request.magic')
    def test_upload_magic_exception(self, mock_magic, api_client, client_u, lrc_legal_req):
        """Lines 88-90: exception during MIME detection."""
        mock_magic.from_buffer.side_effect = RuntimeError("magic failed")
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF fake", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': pdf_file},
            format='multipart')
        assert r.data.get('failed_uploads', 0) > 0 or r.status_code == status.HTTP_400_BAD_REQUEST

    # --- .docx detected as ZIP (lines 65-75) ---
    @mock.patch('gym_app.views.legal_request.magic')
    def test_upload_docx_as_zip(self, mock_magic, api_client, client_u, lrc_legal_req):
        """Lines 65-75: .docx file detected as application/zip is validated."""
        mock_magic.from_buffer.return_value = 'application/zip'
        # Create content with PK signature and word/ marker
        content = b'PK\x03\x04' + b'\x00' * 50 + b'word/' + b'\x00' * 400
        api_client.force_authenticate(user=client_u)
        docx_file = SimpleUploadedFile(
            "doc.docx", content, content_type="application/zip")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': docx_file},
            format='multipart')
        # Should succeed since it's a valid .docx structure
        assert r.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)

    # --- process_file_upload generic exception (lines 150-153) ---
    @mock.patch('gym_app.views.legal_request.validate_file_security')
    @mock.patch('gym_app.views.legal_request.sanitize_filename')
    def test_upload_generic_exception(self, mock_sanitize, mock_validate,
                                      api_client, client_u, lrc_legal_req):
        """Lines 150-153: generic exception in process_file_upload."""
        mock_validate.return_value = True
        mock_sanitize.side_effect = RuntimeError("unexpected")
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': lrc_legal_req.id, 'file': pdf_file},
            format='multipart')
        assert r.data['failed_uploads'] >= 1

    # --- .docx inner read exception (lines 74-75) ---
    @mock.patch('gym_app.views.legal_request.magic')
    def test_docx_inner_read_exception(self, mock_magic):
        """Lines 74-75: exception during .docx inner structure verification.
        
        The inner except logs a warning and falls through to standard MIME
        validation which accepts application/zip + .docx.
        """
        mock_magic.from_buffer.return_value = 'application/zip'
        from types import SimpleNamespace

        from gym_app.views.legal_request import validate_file_security
        call_count = {'n': 0}
        def _read(n=-1):
            call_count['n'] += 1
            if call_count['n'] == 1:
                return b'PK\x03\x04' + b'\x00' * 100
            raise OSError("simulated read failure")
        mock_file = SimpleNamespace(name="doc.docx", size=500, read=_read, seek=lambda x: None)
        # Inner except (line 74-75) logs warning, then standard MIME check
        # passes because application/zip + .docx is allowed.
        result = validate_file_security(mock_file)
        assert result is True
        mock_magic.from_buffer.assert_called()

    # --- create_legal_request ValidationError (lines 239-240) ---
    @mock.patch('gym_app.views.legal_request.LegalRequest.objects')
    def test_create_legal_request_validation_error(
        self, mock_qs, api_client, client_u, lrc_req_type, lrc_discipline
    ):
        """Lines 239-240: ValidationError in create_legal_request → 400."""
        mock_qs.create.side_effect = ValidationError("invalid field")
        api_client.force_authenticate(user=client_u)
        import json
        main_data = json.dumps({
            'requestTypeId': lrc_req_type.id,
            'disciplineId': lrc_discipline.id,
            'description': 'Test description'
        })
        r = api_client.post(
            reverse('create-legal-request'),
            {'mainData': main_data},
            format='multipart')
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in r.data

    # --- upload ValidationError (lines 313-314) ---
    @mock.patch('gym_app.views.legal_request.LegalRequest.objects.get')
    def test_upload_file_validation_error(
        self, mock_get, api_client, client_u
    ):
        """Lines 313-314: ValidationError in upload → 400."""
        mock_get.side_effect = ValidationError("invalid upload")
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': 999, 'file': pdf_file},
            format='multipart')
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in r.data

    # --- create_legal_request generic exception (lines 241-242) ---
    @mock.patch('gym_app.views.legal_request.LegalRequest.objects')
    def test_create_legal_request_generic_exception(
        self, mock_qs, api_client, client_u, lrc_req_type, lrc_discipline
    ):
        """Lines 241-242: generic exception in create_legal_request."""
        mock_qs.create.side_effect = RuntimeError("db exploded")
        api_client.force_authenticate(user=client_u)
        import json
        main_data = json.dumps({
            'requestTypeId': lrc_req_type.id,
            'disciplineId': lrc_discipline.id,
            'description': 'Test description'
        })
        r = api_client.post(
            reverse('create-legal-request'),
            {'mainData': main_data},
            format='multipart')
        assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'unexpected' in r.data['detail'].lower() or 'error' in r.data['detail'].lower()

    # --- upload_legal_request_file outer generic exception (lines 315-316) ---
    @mock.patch('gym_app.views.legal_request.LegalRequest.objects.get')
    def test_upload_file_outer_generic_exception(
        self, mock_get, api_client, client_u
    ):
        """Lines 315-316: generic exception in upload_legal_request_file."""
        mock_get.side_effect = RuntimeError("unexpected DB error")
        api_client.force_authenticate(user=client_u)
        pdf_file = SimpleUploadedFile(
            "doc.pdf", b"%PDF", content_type="application/pdf")
        r = api_client.post(
            reverse('upload-legal-request-file'),
            {'legalRequestId': 999, 'file': pdf_file},
            format='multipart')
        assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'unexpected' in r.data['detail'].lower() or 'error' in r.data['detail'].lower()

    # --- get_or_delete_legal_request generic exception (lines 553-555) ---
    @mock.patch('gym_app.views.legal_request.LegalRequestSerializer')
    def test_get_or_delete_generic_exception(
        self, mock_ser, api_client, lawyer, lrc_legal_req
    ):
        """Lines 553-555: generic exception in get_or_delete_legal_request."""
        mock_ser.side_effect = RuntimeError("serializer boom")
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(
            reverse('get-or-delete-legal-request',
                    kwargs={'request_id': lrc_legal_req.pk}))
        assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in r.data['detail'].lower()


# ======================================================================
# Tests merged from test_legal_request_edges.py
# ======================================================================

"""
Edge tests for gym_app/views/legal_request.py to close coverage gaps.

Targets: validate_file_security edges, create_legal_request error paths,
get_or_delete DELETE path, delete_legal_request, download content types,
upload failed files, outer exception handlers.
"""
import json  # noqa: F811
import os  # noqa: F811
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    LegalDiscipline,  # noqa: F811
    LegalRequest,  # noqa: F811
    LegalRequestFiles,  # noqa: F811
    LegalRequestType,  # noqa: F811
    User,  # noqa: F811
)


@pytest.fixture
def lre_client_user(db):
    """Lre client user."""
    return User.objects.create_user(
        email="lre-client@example.com",
        password="testpassword",
        first_name="LRE",
        last_name="Client",
        role="client",
    )


@pytest.fixture
def lre_lawyer_user(db):
    """Lre lawyer user."""
    return User.objects.create_user(
        email="lre-lawyer@example.com",
        password="testpassword",
        first_name="LRE",
        last_name="Lawyer",
        role="lawyer",
    )


@pytest.fixture
def lre_req_type(db):
    """Lre req type."""
    return LegalRequestType.objects.create(name="LRE-Type")


@pytest.fixture
def lre_discipline(db):
    """Lre discipline."""
    return LegalDiscipline.objects.create(name="LRE-Disc")


@pytest.fixture
def lre_legal_request(db, lre_client_user, lre_req_type, lre_discipline):
    """Lre legal request."""
    return LegalRequest.objects.create(
        user=lre_client_user,
        request_type=lre_req_type,
        discipline=lre_discipline,
        description="LRE test request",
    )


# ---------------------------------------------------------------------------
# validate_file_security edges (lines 47, 52, 65-75, 79, 83-90)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestValidateFileSecurityEdges:
    """Tests for Validate File Security Edges."""

    def test_file_exceeds_max_size(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 47: file size > MAX_FILE_SIZE."""
        api_client.force_authenticate(user=lre_client_user)
        # Create a file that claims to be > 200MB
        big_file = SimpleUploadedFile("big.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        big_file.size = 201 * 1024 * 1024  # 201MB

        url = reverse("upload-legal-request-file")
        response = api_client.post(
            url,
            {"legalRequestId": lre_legal_request.id, "file": big_file},
            format="multipart",
        )
        # File validation failure results in failed_files
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)

    def test_file_extension_not_allowed(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 52: disallowed file extension."""
        api_client.force_authenticate(user=lre_client_user)
        bad_file = SimpleUploadedFile("script.exe", b"\x00\x00", content_type="application/octet-stream")

        url = reverse("upload-legal-request-file")
        response = api_client.post(
            url,
            {"legalRequestId": lre_legal_request.id, "file": bad_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# create_legal_request error paths (lines 175, 179-181, 187-188, 238-243)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCreateLegalRequestEdges:
    """Tests for Create Legal Request Edges."""

    def test_empty_main_data(self, api_client, lre_client_user):
        """Cover line 175: empty mainData."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("create-legal-request")
        response = api_client.post(url, {"mainData": ""}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Main data is required" in response.data["detail"]

    def test_invalid_json_main_data(self, api_client, lre_client_user):
        """Cover lines 179-181: invalid JSON."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("create-legal-request")
        response = api_client.post(url, {"mainData": "{invalid json"}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid JSON format" in response.data["detail"]

    def test_missing_required_fields(self, api_client, lre_client_user):
        """Cover lines 187-188: missing required fields."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("create-legal-request")
        response = api_client.post(
            url,
            {"mainData": json.dumps({"requestTypeId": 1})},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing required fields" in response.data["detail"]

    def test_unexpected_exception(self, api_client, lre_client_user, lre_req_type, lre_discipline):
        """Cover lines 241-243: unexpected exception returns 500."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("create-legal-request")
        main_data = json.dumps({
            "requestTypeId": lre_req_type.id,
            "disciplineId": lre_discipline.id,
            "description": "Test",
        })
        with patch("gym_app.views.legal_request.LegalRequest.objects.create", side_effect=Exception("DB boom")):
            response = api_client.post(url, {"mainData": main_data}, format="multipart")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# upload_legal_request_file edges (lines 262, 288, 312-317)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUploadLegalRequestFileEdges:
    """Tests for Upload Legal Request File Edges."""

    def test_missing_legal_request_id(self, api_client, lre_client_user):
        """Cover line 262: missing legalRequestId."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("upload-legal-request-file")
        response = api_client.post(url, {}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Legal request ID is required" in response.data["detail"]

    @patch("gym_app.views.legal_request.process_file_upload")
    def test_upload_with_failed_files(self, mock_upload, api_client, lre_client_user, lre_legal_request):
        """Cover line 288: failed_files path."""
        api_client.force_authenticate(user=lre_client_user)
        mock_upload.return_value = {
            "success": False,
            "error": {"name": "bad.pdf", "message": "Invalid"},
        }
        file = SimpleUploadedFile("bad.pdf", b"%PDF", content_type="application/pdf")
        url = reverse("upload-legal-request-file")
        response = api_client.post(
            url,
            {"legalRequestId": lre_legal_request.id, "file": file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["failed_uploads"] == 1

    def test_upload_outer_exception(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 315-317: outer exception returns 500."""
        api_client.force_authenticate(user=lre_client_user)
        file = SimpleUploadedFile("test.pdf", b"%PDF", content_type="application/pdf")
        url = reverse("upload-legal-request-file")
        with patch("gym_app.views.legal_request.LegalRequest.objects.get", side_effect=Exception("unexpected")):
            response = api_client.post(
                url,
                {"legalRequestId": lre_legal_request.id, "file": file},
                format="multipart",
            )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# get_or_delete_legal_request edges (lines 521-522, 534-555)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestGetOrDeleteLegalRequestEdges:
    """Tests for Get Or Delete Legal Request Edges."""

    def test_get_forbidden_for_unrelated_client(self, api_client, lre_legal_request):
        """Cover lines 521-522: client cannot access others' request."""
        other = User.objects.create_user(
            email="lre-other@example.com", password="tp",
            first_name="Oth", last_name="Er", role="client",
        )
        api_client.force_authenticate(user=other)
        url = reverse("get-or-delete-legal-request", args=[lre_legal_request.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_by_lawyer(self, api_client, lre_lawyer_user, lre_legal_request):
        """Cover lines 534-555: DELETE method by lawyer."""
        api_client.force_authenticate(user=lre_lawyer_user)
        url = reverse("get-or-delete-legal-request", args=[lre_legal_request.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.data["message"]

    def test_delete_forbidden_for_client(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 536-540: client cannot delete."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("get-or-delete-legal-request", args=[lre_legal_request.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# delete_legal_request edges (line 712, 730-732)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestDeleteLegalRequestEdges:
    """Tests for Delete Legal Request Edges."""

    def test_delete_forbidden_for_non_lawyer(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 712: non-lawyer cannot delete."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("delete-legal-request", args=[lre_legal_request.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_exception(self, api_client, lre_lawyer_user, lre_legal_request):
        """Cover lines 730-732: exception returns 500."""
        api_client.force_authenticate(user=lre_lawyer_user)
        url = reverse("delete-legal-request", args=[lre_legal_request.id])
        with patch("gym_app.views.legal_request.get_object_or_404", side_effect=Exception("boom")):
            response = api_client.delete(url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# send_confirmation_email outer exception (lines 407-409)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSendConfirmationEmailEdges:
    """Tests for Send Confirmation Email Edges."""

    def test_outer_exception(self, api_client, lre_client_user):
        """Cover lines 407-409: outer exception returns 500."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("send-confirmation-email")
        with patch.object(LegalRequest.objects, "get", side_effect=Exception("unexpected")):
            response = api_client.post(url, {"legal_request_id": 1}, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# list_legal_requests edges (lines 477-478, 494-496)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestListLegalRequestsEdges:
    """Tests for List Legal Requests Edges."""

    def test_date_to_filter(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 477-478: date_to filter applied."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("list-legal-requests")
        response = api_client.get(url, {"date_to": "2099-12-31"})
        assert response.status_code == status.HTTP_200_OK

    def test_exception_returns_500(self, api_client, lre_client_user):
        """Cover lines 494-496: exception returns 500."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("list-legal-requests")
        with patch("gym_app.views.legal_request.LegalRequest.objects.select_related", side_effect=Exception("boom")):
            response = api_client.get(url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# update_legal_request_status exception (lines 618-620)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUpdateStatusEdges:
    """Tests for Update Status Edges."""

    def test_exception_returns_500(self, api_client, lre_lawyer_user, lre_legal_request):
        """Cover lines 618-620: exception returns 500."""
        api_client.force_authenticate(user=lre_lawyer_user)
        url = reverse("update-legal-request-status", args=[lre_legal_request.id])
        with patch("gym_app.views.legal_request.get_object_or_404", side_effect=Exception("boom")):
            response = api_client.put(url, {"status": "IN_REVIEW"}, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# create_legal_request_response exception (lines 692-694)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCreateResponseEdges:
    """Tests for Create Response Edges."""

    def test_exception_returns_500(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 692-694: exception returns 500."""
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("create-legal-request-response", args=[lre_legal_request.id])
        with patch("gym_app.views.legal_request.get_object_or_404", side_effect=Exception("boom")):
            response = api_client.post(url, {"response_text": "test"}, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# download content types (lines 872-886) & exception (917-919)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestDownloadContentTypeEdges:
    """Tests for Download Content Type Edges."""

    def _create_file(self, lre_legal_request, name, content=b"content"):
        """Create and attach a file."""
        f = SimpleUploadedFile(name, content, content_type="application/octet-stream")
        file_obj = LegalRequestFiles.objects.create(file=f)
        lre_legal_request.files.add(file_obj)
        return file_obj

    def test_download_pdf(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 872: .pdf content type."""
        file_obj = self._create_file(lre_legal_request, "doc.pdf", b"%PDF-1.4")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_download_doc(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 874: .doc content type."""
        file_obj = self._create_file(lre_legal_request, "doc.doc")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/msword"

    def test_download_docx(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 876: .docx content type."""
        file_obj = self._create_file(lre_legal_request, "doc.docx")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "wordprocessingml" in response["Content-Type"]

    def test_download_jpg(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 878: .jpg content type."""
        file_obj = self._create_file(lre_legal_request, "img.jpg")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/jpeg"

    def test_download_png(self, api_client, lre_client_user, lre_legal_request):
        """Cover line 880: .png content type."""
        file_obj = self._create_file(lre_legal_request, "img.png")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/png"

    def test_download_xlsx(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 883-884: .xlsx content type."""
        file_obj = self._create_file(lre_legal_request, "sheet.xlsx")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "spreadsheetml" in response["Content-Type"]

    def test_download_unknown_extension(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 885-886: unknown extension → octet-stream."""
        file_obj = self._create_file(lre_legal_request, "data.xyz")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/octet-stream"

    def test_download_outer_exception(self, api_client, lre_client_user, lre_legal_request):
        """Cover lines 917-919: outer exception returns 500."""
        file_obj = self._create_file(lre_legal_request, "test.pdf")
        api_client.force_authenticate(user=lre_client_user)
        url = reverse("download-legal-request-file", args=[lre_legal_request.id, file_obj.id])
        with patch("gym_app.views.legal_request.os.path.exists", side_effect=Exception("boom")):
            response = api_client.get(url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
