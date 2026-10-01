"""Tests for user module."""
from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gym_app.models import User
from gym_app.models.user import ActivityFeed, UserSignature


@pytest.fixture
def user():
    """User."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpassword',
        first_name='Test',
        last_name='User',
        contact='1234567890',
        birthday=date(1990, 1, 1),
        identification='ID12345',
        document_type='ID'
    )

@pytest.fixture
def another_user():
    """Another user."""
    return User.objects.create_user(
        email='another@example.com',
        password='anotherpassword',
        first_name='Another',
        last_name='User'
    )


def _png_file(name='sig.png'):
    buffer = BytesIO()
    Image.new('RGB', (1, 1), color='white').save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')

@pytest.mark.django_db
class TestUserViews:
    """Tests for User Views."""
    
    def test_user_list_authenticated(self, api_client, user, another_user):
        """Test that authenticated users can retrieve a list of users."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Make the request
        url = reverse('user-list')
        response = api_client.get(url)
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        
        # Verify both users are in the response
        emails = [u['email'] for u in response.data]
        assert 'test@example.com' in emails
        assert 'another@example.com' in emails
    
    def test_user_list_unauthenticated(self, api_client, user):
        """Test that unauthenticated users cannot access the user list."""
        url = reverse('user-list')
        response = api_client.get(url)
        
        # Assert the response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile_success(self, api_client, user):
        """Test successfully updating a user's own profile."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Create test photo
        _test_photo = SimpleUploadedFile(
            "profile.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        # Prepare update data with only the fields we're changing
        # Eliminando cualquier campo que pueda causar problemas de validación
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'contact': '9876543210',
            'email': user.email,  # Mantener el mismo email para evitar problemas de unicidad
        }
        
        # Hacer la solicitud sin incluir la foto inicialmente para ver si ese es el problema
        url = reverse('update_profile', kwargs={'pk': user.id})
        response = api_client.put(url, data, format='json')
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Profile updated successfully'
        
        # Verify user was updated in the database
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'
        assert user.contact == '9876543210'
        
        # Verify profile completion status
        assert user.is_profile_completed == True
    
    def test_update_profile_partial(self, api_client, user):
        """Test updating a user's profile with only some fields."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Prepare partial update data
        data = {
            'first_name': 'NewFirst',
        }
        
        # Make the request
        url = reverse('update_profile', kwargs={'pk': user.id})
        response = api_client.put(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify only the specified field was updated
        user.refresh_from_db()
        assert user.first_name == 'NewFirst'
        assert user.last_name == 'User'  # Unchanged
        
        # Verify profile completion status
        assert user.is_profile_completed == True  # Should still be complete
    
    def test_update_profile_incomplete(self, api_client):
        """Test updating a profile to an incomplete state."""
        # Create a user with incomplete profile
        incomplete_user = User.objects.create_user(
            email='incomplete@example.com',
            password='password',
            # Missing fields to make profile incomplete
        )
        
        # Authenticate the user
        api_client.force_authenticate(user=incomplete_user)
        
        # Prepare update data - still incomplete
        data = {
            'first_name': 'Some',
            # Still missing required fields
        }
        
        # Make the request
        url = reverse('update_profile', kwargs={'pk': incomplete_user.id})
        response = api_client.put(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify profile was updated but still incomplete
        incomplete_user.refresh_from_db()
        assert incomplete_user.first_name == 'Some'
        assert incomplete_user.is_profile_completed == False
    
    def test_update_other_user_profile(self, api_client, user, another_user):
        """Test that a user cannot update another user's profile."""
        # Authenticate as user
        api_client.force_authenticate(user=user)
        
        # Prepare update data for another user's profile
        data = {
            'first_name': 'Hacked',
            'last_name': 'Name',
        }
        
        # Make the request to update another user's profile
        url = reverse('update_profile', kwargs={'pk': another_user.id})
        response = api_client.put(url, data, format='multipart')
        
        # Assert the response - should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'You do not have permission' in response.data['error']
        
        # Verify the other user's profile was not changed
        another_user.refresh_from_db()
        assert another_user.first_name == 'Another'  # Unchanged
    
    def test_update_nonexistent_user(self, api_client, user):
        """Test trying to update a non-existent user profile."""
        # Authenticate the user
        api_client.force_authenticate(user=user)
        
        # Use a non-existent user ID
        non_existent_id = user.id + 100
        
        # Make the request with the non-existent ID
        url = reverse('update_profile', kwargs={'pk': non_existent_id})
        response = api_client.put(url, {}, format='multipart')
        
        # Assert the response - should be forbidden (can't update other profiles)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_profile_unauthenticated(self, api_client, user):
        """Test that unauthenticated users cannot update profiles."""
        url = reverse('update_profile', kwargs={'pk': user.id})
        response = api_client.put(url, {}, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Verify user was not updated
        original_first_name = user.first_name
        user.refresh_from_db()
        assert user.first_name == original_first_name  # Unchanged

    def test_update_profile_invalid_email_returns_400(self, api_client, user):
        """Invalid email should return serializer errors."""
        api_client.force_authenticate(user=user)

        url = reverse('update_profile', kwargs={'pk': user.id})
        response = api_client.put(url, {'email': 'not-an-email'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_update_profile_discards_submitted_authority(self, api_client, user):
        """Fails if a basic profile update can promote its account to admin."""
        api_client.force_authenticate(user=user)
        payload = {
            'first_name': 'Protected',
            'role': 'admin',
            'is_gym_lawyer': True,
        }

        response = api_client.put(
            reverse('update_profile', kwargs={'pk': user.id}),
            payload,
            format='json',
        )

        user.refresh_from_db()
        api_client.force_authenticate(user=user)
        denied_response = api_client.get(reverse('reassignment-summary'))
        assert response.status_code == status.HTTP_200_OK
        assert user.first_name == 'Protected'
        assert user.role == 'basic'
        assert user.is_gym_lawyer is False
        assert denied_response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_profile_preserves_existing_internal_authority(self, api_client):
        """Fails if a legitimate profile edit strips an internal account's authority."""
        admin_user = User.objects.create_user(
            email='profile-admin@example.com',
            password='testpassword',
            role='admin',
            is_gym_lawyer=True,
        )
        lawyer = User.objects.create_user(
            email='profile-lawyer@example.com',
            password='testpassword',
            role='lawyer',
            is_gym_lawyer=True,
        )
        api_client.force_authenticate(user=admin_user)
        payload = {
            'first_name': 'Retained',
            'role': 'client',
            'is_gym_lawyer': False,
        }

        response = api_client.put(
            reverse('update_profile', kwargs={'pk': admin_user.id}),
            payload,
            format='json',
        )

        admin_user.refresh_from_db()
        api_client.force_authenticate(user=admin_user)
        summary_response = api_client.get(
            reverse('reassignment-summary'),
            {'lawyer_id': lawyer.id},
        )
        assert response.status_code == status.HTTP_200_OK
        assert admin_user.first_name == 'Retained'
        assert admin_user.role == 'admin'
        assert admin_user.is_gym_lawyer is True
        assert summary_response.status_code == status.HTTP_200_OK
        assert summary_response.data['lawyer']['id'] == lawyer.id

    def test_get_user_activities_returns_only_authenticated_user(self, api_client, user, another_user):
        """Activities should be filtered by the authenticated user."""
        ActivityFeed.objects.create(user=user, action_type='create', description='User action')
        ActivityFeed.objects.create(user=another_user, action_type='delete', description='Other action')

        api_client.force_authenticate(user=user)

        url = reverse('user-activities')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['description'] == 'User action'

    def test_create_activity_success(self, api_client, user):
        """Authenticated users can create activities and they are linked to the user."""
        api_client.force_authenticate(user=user)

        url = reverse('create-activity')
        response = api_client.post(
            url,
            {'action_type': 'create', 'description': 'Created something'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert ActivityFeed.objects.filter(user=user).count() == 1

    def test_create_activity_invalid_payload(self, api_client, user):
        """Invalid payload should return 400 errors."""
        api_client.force_authenticate(user=user)

        url = reverse('create-activity')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_signature_forbidden_for_other_user(self, api_client, user, another_user):
        """Users cannot update another user's signature."""
        api_client.force_authenticate(user=user)

        url = reverse('update-signature', kwargs={'user_id': another_user.id})
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'permission' in response.data['error'].lower()

    def test_update_signature_user_not_found(self, api_client, user):
        """If the user does not exist, return 404."""
        ghost_user = User(id=9999, email='ghost@example.com')
        api_client.force_authenticate(user=ghost_user)

        url = reverse('update-signature', kwargs={'user_id': ghost_user.id})
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == 'User not found'

    def test_update_signature_missing_image(self, api_client, user):
        """Signature image is required."""
        api_client.force_authenticate(user=user)

        url = reverse('update-signature', kwargs={'user_id': user.id})
        response = api_client.post(url, {'method': 'upload'}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'No signature image provided'

    @patch('django.core.files.storage.FileSystemStorage.save', return_value='signatures/test.png')
    def test_update_signature_creates_new_signature(self, mock_save, api_client, user):
        """If no signature exists, it should create one and return 201."""
        api_client.force_authenticate(user=user)

        signature_image = _png_file('sig.png')
        url = reverse('update-signature', kwargs={'user_id': user.id})

        response = api_client.post(
            url,
            {'method': 'upload', 'signature_image': signature_image},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['message'] == 'Signature created successfully'
        assert UserSignature.objects.filter(user=user).count() == 1

    @patch('django.core.files.storage.FileSystemStorage.save', return_value='signatures/test.png')
    @patch('gym_app.views.user.default_storage.exists', return_value=True)
    @patch('gym_app.views.user.default_storage.delete')
    def test_update_signature_updates_existing(self, mock_delete, mock_exists, mock_save, api_client, user):
        """Updating an existing signature should return 200 and keep one record."""
        # Create an existing signature
        _existing_signature = UserSignature.objects.create(
            user=user,
            signature_image=_png_file('old.png'),
            method='upload',
        )

        api_client.force_authenticate(user=user)

        signature_image = _png_file('new.png')
        url = reverse('update-signature', kwargs={'user_id': user.id})

        response = api_client.post(
            url,
            {'method': 'draw', 'signature_image': signature_image},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Signature updated successfully'
        assert UserSignature.objects.filter(user=user).count() == 1
        mock_delete.assert_called_once()


# ======================================================================
# Tests merged from test_user_views_coverage.py
# ======================================================================

"""Tests for uncovered branches in user.py (91%→higher)."""
import pytest


@pytest.fixture
def client_u():
    """Client u."""
    return User.objects.create_user(
        email='cli_uvc@e.com', password='p', role='client',
        first_name='C', last_name='U')


@pytest.mark.django_db
class TestUserViewsRegressionScenarios:
    """Tests for User Views Regression Scenarios."""

    def test_update_profile_with_photo(self, api_client, client_u):
        """Lines 60-64: profile update with photo_profile file."""
        from io import BytesIO

        from PIL import Image as PILImage
        buf = BytesIO()
        PILImage.new('RGB', (10, 10), color='red').save(buf, format='PNG')
        buf.seek(0)
        api_client.force_authenticate(user=client_u)
        photo = SimpleUploadedFile(
            "photo.png", buf.read(), content_type="image/png")
        r = api_client.put(
            reverse('update_profile', kwargs={'pk': client_u.pk}),
            {'first_name': 'Updated', 'last_name': 'User',
             'email': client_u.email, 'photo_profile': photo},
            format='multipart')
        assert r.status_code == 200

    def test_update_profile_user_not_found(self, api_client, client_u):
        """Lines 49-50: user DoesNotExist (impossible via auth but covers branch)."""
        api_client.force_authenticate(user=client_u)
        # User tries to update own profile but we delete the user object
        # This is covered by the permission check (user.id != pk) first
        other = User.objects.create_user(
            email='other_uvc@e.com', password='p', role='client',
            first_name='O', last_name='U')
        r = api_client.put(
            reverse('update_profile', kwargs={'pk': other.pk}),
            {'first_name': 'X'}, format='json')
        assert r.status_code == 403  # Permission denied before DoesNotExist

    def test_update_signature_with_forwarded_ip(self, api_client, client_u):
        """Line 163: X-Forwarded-For IP extraction in update_signature."""
        from io import BytesIO

        from PIL import Image as PILImage
        buf = BytesIO()
        PILImage.new('RGB', (200, 80), color='white').save(buf, format='PNG')
        buf.seek(0)
        api_client.force_authenticate(user=client_u)
        sig_img = SimpleUploadedFile(
            "sig.png", buf.read(), content_type="image/png")
        r = api_client.post(
            reverse('update-signature', kwargs={'user_id': client_u.pk}),
            {'signature_image': sig_img, 'method': 'draw'},
            format='multipart',
            HTTP_X_FORWARDED_FOR='192.168.1.1, 10.0.0.1')
        assert r.status_code in (200, 201)

    def test_update_signature_invalid_method(self, api_client, client_u):
        """Lines 205-206: serializer validation error (invalid method choice)."""
        from io import BytesIO

        from PIL import Image as PILImage
        buf = BytesIO()
        PILImage.new('RGB', (200, 80), color='white').save(buf, format='PNG')
        buf.seek(0)
        api_client.force_authenticate(user=client_u)
        sig_img = SimpleUploadedFile(
            "sig.png", buf.read(), content_type="image/png")
        r = api_client.post(
            reverse('update-signature', kwargs={'user_id': client_u.pk}),
            {'signature_image': sig_img, 'method': 'INVALID'},
            format='multipart')
        assert r.status_code == 400


# ======================================================================
# Tests moved from test_user_auth.py (misplaced – user profile domain)
# ======================================================================

@pytest.fixture
def _simple_user():
    """Create a simple user without extra profile fields, for profile update tests."""
    return User.objects.create_user(
        email='profile_move@example.com',
        password='testpassword',
        first_name='Test',
        last_name='User'
    )


@pytest.mark.django_db
@pytest.mark.integration
class TestUpdateProfile:
    """Tests for Update Profile."""

    @pytest.mark.contract
    def test_update_profile_success(self, api_client, _simple_user):  # noqa: PT019
        """Test successfully updating a user's own profile."""
        api_client.force_authenticate(user=_simple_user)

        _test_photo = SimpleUploadedFile(
            "profile.jpg",
            b"file_content",
            content_type="image/jpeg"
        )

        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'contact': '9876543210',
            'email': _simple_user.email,
        }

        url = reverse('update_profile', kwargs={'pk': _simple_user.id})
        response = api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Profile updated successfully'

        _simple_user.refresh_from_db()
        assert _simple_user.first_name == 'Updated'
        assert _simple_user.last_name == 'Name'
        assert _simple_user.contact == '9876543210'

        assert not _simple_user.is_profile_completed

    @patch('gym_app.views.user.default_storage.save')
    @pytest.mark.contract
    def test_update_profile_with_photo(self, mock_save, api_client, _simple_user):  # noqa: PT019
        """Test updating profile with photo (multipart)."""
        buf = BytesIO()
        Image.new('RGB', (100, 100), color='red').save(buf, format='JPEG')
        buf.seek(0)
        test_photo = SimpleUploadedFile(
            "profile.jpg",
            buf.read(),
            content_type="image/jpeg"
        )

        api_client.force_authenticate(user=_simple_user)
        mock_save.return_value = 'profile_photos/saved_profile.jpg'

        data = {
            'first_name': 'Updated',
            'last_name': 'Photo',
            'contact': '1234567890',
            'email': _simple_user.email,
            'photo_profile': test_photo,
        }

        url = reverse('update_profile', kwargs={'pk': _simple_user.id})
        response = api_client.put(url, data, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        _simple_user.refresh_from_db()
        assert 'profile_photos' in str(_simple_user.photo_profile)
        assert mock_save.call_count >= 1


# ======================================================================
# Tests moved from test_user_auth.py – batch36 (user views domain)
# ======================================================================

@pytest.fixture
def _b36_lawyer():
    return User.objects.create_user(
        email="law36_moved@t.com", password="pw", role="lawyer",
        first_name="L", last_name="W",
    )


@pytest.mark.django_db
class TestUserViewsAdditionalScenarios:
    """Tests for User Views Additional Scenarios."""

    def test_user_list(self, api_client, _b36_lawyer):  # noqa: PT019
        """Verify user list."""
        api_client.force_authenticate(user=_b36_lawyer)
        resp = api_client.get(reverse("user-list"))
        assert resp.status_code == 200

    def test_update_profile(self, api_client, _b36_lawyer):  # noqa: PT019
        """Verify update profile."""
        api_client.force_authenticate(user=_b36_lawyer)
        resp = api_client.put(
            reverse("update_profile", args=[_b36_lawyer.id]),
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )
        assert resp.status_code == 200
        _b36_lawyer.refresh_from_db()
        assert _b36_lawyer.first_name == "Updated"

    def test_get_user_activities(self, api_client, _b36_lawyer):  # noqa: PT019
        """Verify get user activities."""
        ActivityFeed.objects.create(user=_b36_lawyer, action_type="login", description="Logged in")
        api_client.force_authenticate(user=_b36_lawyer)
        resp = api_client.get(reverse("user-activities"))
        assert resp.status_code == 200

    def test_create_activity(self, api_client, _b36_lawyer):  # noqa: PT019
        """Verify create activity."""
        api_client.force_authenticate(user=_b36_lawyer)
        resp = api_client.post(
            reverse("create-activity"),
            {"action_type": "create", "description": "Test activity"},
            format="json",
        )
        assert resp.status_code == 201
        assert ActivityFeed.objects.filter(user=_b36_lawyer, action_type="create").exists()
