"""Tests for user_auth_views module."""
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from gym_app.models import EmailVerificationCode, PasswordCode
from gym_app.views.userAuth import (
    MICROSOFT_CONSUMERS_TENANT_ID,
    _verify_microsoft_id_token,
)

User = get_user_model()
FIXED_REFERENCE_TIME = datetime(2026, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def user():
    """User."""
    return User.objects.create_user(
        email="auth@example.com",
        password="testpassword",
        first_name="Auth",
        last_name="User",
        role="client",
    )


def _mock_captcha_success(monkeypatch):
    """Mock successful captcha verification."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True}
    mock_resp.raise_for_status = MagicMock()
    monkeypatch.setattr(
        "gym_app.utils.captcha.requests.post", lambda *a, **kw: mock_resp
    )


def _mock_captcha_failure(monkeypatch):
    """Mock failed captcha verification."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": False}
    mock_resp.raise_for_status = MagicMock()
    monkeypatch.setattr(
        "gym_app.utils.captcha.requests.post", lambda *a, **kw: mock_resp
    )


def _mock_captcha_exception(monkeypatch):
    """Mock captcha request exception."""
    import requests as req_lib
    monkeypatch.setattr(
        "gym_app.utils.captcha.requests.post",
        MagicMock(side_effect=req_lib.RequestException("timeout")),
    )


def _pin_user_auth_now(monkeypatch, fixed_now=FIXED_REFERENCE_TIME):
    """Pin userAuth timezone.now to a deterministic value for TTL tests."""
    monkeypatch.setattr("gym_app.views.userAuth.timezone.now", lambda: fixed_now)


def _sign_on_payload(email, passcode, submitted_authority):
    """Return a valid public registration payload with one authority attempt."""
    payload = {
        "email": email,
        "password": "SecurePass123!",
        "first_name": "Authority",
        "last_name": "Attempt",
        "passcode": passcode,
    }
    payload.update(submitted_authority)
    return payload


# =========================================================================
# sign_on
# =========================================================================
@pytest.mark.django_db
class TestSignOn:
    """Tests for Sign On."""

    def test_sign_on_success(self, api_client):
        """Verify sign on success."""
        EmailVerificationCode.objects.create(email="newuser@example.com", code="123456")
        url = reverse("sign_on")
        data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
            "passcode": "123456",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert User.objects.filter(email="newuser@example.com").exists()
        # Verify verification code was marked as used
        assert EmailVerificationCode.objects.get(email="newuser@example.com").used is True

    def test_sign_on_duplicate_email(self, api_client, user):
        """Verify sign on duplicate email."""
        url = reverse("sign_on")
        data = {
            "email": user.email,
            "password": "SecurePass123!",
            "first_name": "Dup",
            "last_name": "User",
            "passcode": "123456",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "warning" in response.data

    def test_sign_on_invalid_data(self, api_client):
        """Verify sign on invalid data."""
        EmailVerificationCode.objects.create(email="bad", code="123456")
        url = reverse("sign_on")
        data = {"email": "bad", "passcode": "123456"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sign_on_default_role_basic(self, api_client):
        """Verify sign on default role basic."""
        EmailVerificationCode.objects.create(email="basic@example.com", code="654321")
        url = reverse("sign_on")
        data = {
            "email": "basic@example.com",
            "password": "SecurePass123!",
            "first_name": "Basic",
            "last_name": "User",
            "passcode": "654321",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        u = User.objects.get(email="basic@example.com")
        assert u.role == "basic"

    def test_sign_on_missing_passcode(self, api_client):
        """Verify sign on missing passcode."""
        url = reverse("sign_on")
        data = {
            "email": "nopcode@example.com",
            "password": "SecurePass123!",
            "first_name": "No",
            "last_name": "Code",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Verification code is required"

    def test_sign_on_wrong_passcode(self, api_client):
        """Verify sign on wrong passcode."""
        EmailVerificationCode.objects.create(email="wrong@example.com", code="111111")
        url = reverse("sign_on")
        data = {
            "email": "wrong@example.com",
            "password": "SecurePass123!",
            "first_name": "Wrong",
            "last_name": "Code",
            "passcode": "999999",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid or expired verification code"

    def test_sign_on_expired_passcode(self, api_client, monkeypatch):
        """T12: sign_on rejects expired verification code (>30 min)."""
        _pin_user_auth_now(monkeypatch)
        code = EmailVerificationCode.objects.create(email="expired@example.com", code="777888")
        EmailVerificationCode.objects.filter(pk=code.pk).update(
            created_at=FIXED_REFERENCE_TIME - timedelta(minutes=31)
        )
        url = reverse("sign_on")
        data = {
            "email": "expired@example.com",
            "password": "SecurePass123!",
            "first_name": "Expired",
            "last_name": "Code",
            "passcode": "777888",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid or expired verification code"
        assert not User.objects.filter(email="expired@example.com").exists()

    def test_sign_on_email_with_whitespace(self, api_client):
        """T6: sign_on normalizes email with leading/trailing whitespace."""
        EmailVerificationCode.objects.create(email="spaces@example.com", code="111222")
        url = reverse("sign_on")
        data = {
            "email": "  spaces@example.com  ",
            "password": "SecurePass123!",
            "first_name": "Space",
            "last_name": "User",
            "passcode": "111222",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="spaces@example.com").exists()

    def test_sign_on_sends_admin_notification(self, api_client):
        """Verify that a registration alert is sent to the admin inbox on success."""
        EmailVerificationCode.objects.create(email="notify@example.com", code="777888")
        url = reverse("sign_on")
        data = {
            "email": "notify@example.com",
            "password": "SecurePass123!",
            "first_name": "Notify",
            "last_name": "Test",
            "passcode": "777888",
        }
        with patch("gym_app.views.userAuth.notify_admin_new_user") as mock_notify:
            response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        mock_notify.assert_called_once()
        notified_user = mock_notify.call_args.args[0]
        assert notified_user.email == "notify@example.com"

    def test_sign_on_admin_notification_failure_does_not_break_registration(self, api_client):
        """Verify registration succeeds even if the admin notification email fails."""
        EmailVerificationCode.objects.create(email="resilient@example.com", code="444555")
        url = reverse("sign_on")
        data = {
            "email": "resilient@example.com",
            "password": "SecurePass123!",
            "first_name": "Resilient",
            "last_name": "User",
            "passcode": "444555",
        }
        with patch("gym_app.utils.email_notifications.send_template_email", side_effect=Exception("SMTP error")):
            response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="resilient@example.com").exists()


# =========================================================================
# send_verification_code
# =========================================================================
@pytest.mark.django_db
class TestSendVerificationCode:
    """Tests for Send Verification Code."""

    def test_missing_email(self, api_client):
        """Verify missing email."""
        url = reverse("send_verification_code")
        response = api_client.post(url, {"captcha_token": "tok"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Email is required"

    def test_missing_captcha(self, api_client):
        """Verify missing captcha."""
        url = reverse("send_verification_code")
        response = api_client.post(url, {"email": "x@x.com"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Captcha verification is required"

    def test_captcha_failure(self, api_client, monkeypatch):
        """Verify captcha failure."""
        _mock_captcha_failure(monkeypatch)
        url = reverse("send_verification_code")
        response = api_client.post(
            url, {"email": "x@x.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Captcha verification failed"

    def test_captcha_exception(self, api_client, monkeypatch):
        """Verify captcha exception."""
        _mock_captcha_exception(monkeypatch)
        url = reverse("send_verification_code")
        response = api_client.post(
            url, {"email": "x@x.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "Error verifying captcha"

    def test_email_already_registered(self, api_client, user, monkeypatch):
        """Verify email already registered."""
        _mock_captcha_success(monkeypatch)
        url = reverse("send_verification_code")
        response = api_client.post(
            url, {"email": user.email, "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("gym_app.views.userAuth.send_template_email")
    def test_success(self, mock_email, api_client, monkeypatch):
        """Verify success."""
        _mock_captcha_success(monkeypatch)
        url = reverse("send_verification_code")
        response = api_client.post(
            url,
            {"email": "new@example.com", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "passcode" not in response.data
        # Verify code was saved in DB
        assert EmailVerificationCode.objects.filter(email="new@example.com").exists()
        mock_email.assert_called_once()


# =========================================================================
# sign_in
# =========================================================================
@pytest.mark.django_db
class TestSignIn:
    """Tests for Sign In."""

    def test_missing_credentials(self, api_client):
        """Verify missing credentials."""
        url = reverse("sign_in")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Email and password are required"

    def test_missing_captcha(self, api_client):
        """Verify missing captcha."""
        url = reverse("sign_in")
        response = api_client.post(
            url, {"email": "x@x.com", "password": "pass"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Captcha verification is required"

    def test_captcha_failure(self, api_client, monkeypatch):
        """Verify captcha failure."""
        _mock_captcha_failure(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "x@x.com", "password": "pass", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Captcha verification failed"

    def test_captcha_exception(self, api_client, monkeypatch):
        """Verify captcha exception."""
        _mock_captcha_exception(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "x@x.com", "password": "pass", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_user_not_found(self, api_client, monkeypatch):
        """Verify user not found."""
        _mock_captcha_success(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "nonexistent@x.com", "password": "pass", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_password(self, api_client, user, monkeypatch):
        """Verify wrong password."""
        _mock_captcha_success(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": user.email, "password": "wrongpass", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_success(self, api_client, user, monkeypatch):
        """Verify success."""
        _mock_captcha_success(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": user.email, "password": "testpassword", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_sign_in_email_with_whitespace(self, api_client, user, monkeypatch):
        """T7: sign_in normalizes email with leading/trailing whitespace and finds user."""
        _mock_captcha_success(monkeypatch)
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "  " + user.email + "  ", "password": "testpassword", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_archived_user_blocked(self, api_client, user, monkeypatch):
        """Archived accounts cannot sign in even with the right password."""
        _mock_captcha_success(monkeypatch)
        user.archive()
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": user.email, "password": "testpassword", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "archivada" in response.data["error"]

    def test_archived_user_wrong_password_does_not_leak_state(self, api_client, user, monkeypatch):
        """A wrong password on an archived account still returns 401, not 403."""
        _mock_captcha_success(monkeypatch)
        user.archive()
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": user.email, "password": "wrongpass", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =========================================================================
# T11: sign_in — Google user without usable password (BUG-11)
# =========================================================================
@pytest.mark.django_db
class TestSignInGoogleUser:
    """Tests for Sign In Google User."""

    def test_google_user_no_password(self, api_client, monkeypatch):
        """T11: Google-registered user without password gets descriptive error."""
        _mock_captcha_success(monkeypatch)
        # Create a user without a usable password (simulates Google registration)
        google_user = User.objects.create(
            email="google@example.com",
            first_name="Google",
            last_name="User",
            role="basic",
        )
        google_user.set_unusable_password()
        google_user.save()

        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "google@example.com", "password": "anypassword", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Google" in response.data["error"]
        assert "Forgot Password" in response.data["error"]

    def test_google_user_with_set_password_can_login(self, api_client, monkeypatch):
        """T11: Google user who has set a password via Forgot Password can log in."""
        _mock_captcha_success(monkeypatch)
        _google_user = User.objects.create_user(
            email="google2@example.com",
            password="SetViaForgotPw123!",
            first_name="Google",
            last_name="User2",
            role="basic",
        )
        url = reverse("sign_in")
        response = api_client.post(
            url,
            {"email": "google2@example.com", "password": "SetViaForgotPw123!", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


# =========================================================================
# google_login (server-side ID token verification)
# =========================================================================

def _mock_google_token(monkeypatch, payload):
    """Mock google_id_token.verify_oauth2_token to return *payload*."""
    monkeypatch.setattr(
        "gym_app.views.userAuth.google_id_token.verify_oauth2_token",
        lambda *a, **kw: payload,
    )


@pytest.mark.django_db
class TestGoogleLogin:
    """Tests for Google Login."""

    def test_missing_credential(self, api_client):
        """Verify missing credential."""
        url = reverse("google_login")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "Google credential is required."

    def test_invalid_token(self, api_client, monkeypatch):
        """Invalid/expired Google token returns 401."""
        mock_verify = MagicMock(side_effect=ValueError("Invalid token"))
        monkeypatch.setattr(
            "gym_app.views.userAuth.google_id_token.verify_oauth2_token",
            mock_verify,
        )
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "bad_token"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error_message"] == "Invalid Google token."
        mock_verify.assert_called_once()

    def test_token_without_email(self, api_client, monkeypatch):
        """Google token without email returns 400."""
        _mock_google_token(monkeypatch, {"given_name": "No", "family_name": "Email"})
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "Email not found in Google token."

    def test_create_new_user(self, api_client, monkeypatch):
        """Verify create new user."""
        _mock_google_token(monkeypatch, {
            "email": "google@example.com",
            "given_name": "G",
            "family_name": "U",
        })
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is True
        assert "access" in response.data
        assert User.objects.filter(email="google@example.com").exists()

    def test_existing_user(self, api_client, user, monkeypatch):
        """Verify existing user."""
        _mock_google_token(monkeypatch, {"email": user.email})
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is False

    def test_archived_user_blocked(self, api_client, user, monkeypatch):
        """Archived accounts cannot log in via Google."""
        _mock_google_token(monkeypatch, {"email": user.email})
        user.archive()
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "archivada" in response.data["error_message"]

    def test_google_login_exception(self, api_client, monkeypatch):
        """Unexpected exception during user creation path returns 500."""
        _mock_google_token(monkeypatch, {"email": "exc@test.com", "given_name": "Exc", "family_name": "User"})
        url = reverse("google_login")
        with patch("gym_app.views.userAuth.User.objects.get_or_create", side_effect=Exception("DB error")):
            response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error_message"] == "DB error"

    def test_create_user_with_picture_error(self, api_client, monkeypatch):
        """Profile picture fetch failure should not break user creation."""
        _mock_google_token(monkeypatch, {
            "email": "picfail@example.com",
            "given_name": "Pic",
            "family_name": "Fail",
            "picture": "http://example.com/pic.jpg",
        })
        url = reverse("google_login")
        with patch("gym_app.views.userAuth.urlopen", side_effect=Exception("fail")):
            response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is True

    def test_create_user_with_picture_success(self, api_client, monkeypatch):
        """Profile picture is fetched and save() is triggered when picture URL exists."""
        _mock_google_token(monkeypatch, {
            "email": "picsuccess@example.com",
            "given_name": "Pic",
            "family_name": "Success",
            "picture": "http://example.com/pic.jpg",
        })
        url = reverse("google_login")
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = b"image-bytes"

        with patch("gym_app.views.userAuth.urlopen", return_value=mock_http_response), patch(
            "django.db.models.fields.files.FieldFile.save"
        ) as mock_file_save:
            response = api_client.post(url, {"credential": "valid_token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is True
        mock_file_save.assert_called_once()

    def test_create_user_without_picture(self, api_client, monkeypatch):
        """Verify create user without picture."""
        _mock_google_token(monkeypatch, {
            "email": "nopic@example.com",
            "given_name": "No",
            "family_name": "Pic",
        })
        url = reverse("google_login")
        response = api_client.post(url, {"credential": "valid_token"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        u = User.objects.get(email="nopic@example.com")
        assert u.photo_profile == "" or u.photo_profile is None


# =========================================================================
# outlook_login (Microsoft Entra ID token verification + nOAuth hardening)
# =========================================================================

def _mock_microsoft_claims(monkeypatch, claims):
    """Mock _verify_microsoft_id_token to return *claims* (bypasses JWKS/network)."""
    monkeypatch.setattr(
        "gym_app.views.userAuth._verify_microsoft_id_token",
        lambda *a, **kw: claims,
    )


@pytest.mark.django_db
class TestOutlookLogin:
    """Tests for Microsoft/Outlook Login."""

    def test_missing_token(self, api_client):
        """Missing id_token returns 400."""
        url = reverse("outlook_login")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "Microsoft ID token is required."

    def test_invalid_token(self, api_client, monkeypatch):
        """Invalid Microsoft token returns 401."""
        mock_verify = MagicMock(side_effect=jwt.InvalidTokenError("bad"))
        monkeypatch.setattr(
            "gym_app.views.userAuth._verify_microsoft_id_token", mock_verify
        )
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "bad_token"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error_message"] == "Invalid Microsoft token."
        mock_verify.assert_called_once_with("bad_token")

    def test_token_without_email(self, api_client, monkeypatch):
        """Verified token without an email claim returns 400."""
        _mock_microsoft_claims(monkeypatch, {"xms_edov": True, "given_name": "No"})
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "Email not found in Microsoft token."

    def test_unverified_email_rejected(self, api_client, monkeypatch):
        """Email from an untrusted tenant without xms_edov is rejected (nOAuth)."""
        _mock_microsoft_claims(monkeypatch, {
            "email": "victim@example.com",
            "tid": "attacker-tenant-id",
        })
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "forged"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not User.objects.filter(email="victim@example.com").exists()

    def test_preferred_username_not_used_as_identity(self, api_client, monkeypatch):
        """preferred_username (UPN) is never used as the account email."""
        _mock_microsoft_claims(monkeypatch, {
            "preferred_username": "victim@example.com",
            "xms_edov": True,
        })
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email="victim@example.com").exists()

    def test_create_new_user_verified_work_account(self, api_client, monkeypatch):
        """A domain-verified work account (xms_edov) creates a new basic user."""
        _mock_microsoft_claims(monkeypatch, {
            "email": "new@corp.com",
            "xms_edov": True,
            "given_name": "New",
            "family_name": "Corp",
        })
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is True
        assert "access" in response.data
        user = User.objects.get(email="new@corp.com")
        assert user.role == "basic"

    def test_existing_user(self, api_client, user, monkeypatch):
        """An existing email logs in (created False), regardless of provider."""
        _mock_microsoft_claims(monkeypatch, {"email": user.email, "xms_edov": True})
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] is False

    def test_archived_user_blocked(self, api_client, user, monkeypatch):
        """Archived accounts cannot log in via Outlook."""
        _mock_microsoft_claims(monkeypatch, {"email": user.email, "xms_edov": True})
        user.archive()
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "archivada" in response.data["error_message"]

    def test_personal_account_consumers_tenant(self, api_client, monkeypatch):
        """A personal Microsoft account (consumers tenant) is trusted; name is split."""
        _mock_microsoft_claims(monkeypatch, {
            "email": "person@outlook.com",
            "tid": MICROSOFT_CONSUMERS_TENANT_ID,
            "name": "Person Outlook",
        })
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        user = User.objects.get(email="person@outlook.com")
        assert user.first_name == "Person"
        assert user.last_name == "Outlook"

    @override_settings(MICROSOFT_TRUSTED_TENANTS={"corp-tenant-id"})
    def test_allowlisted_tenant_without_xms_edov(self, api_client, monkeypatch):
        """A tenant in MICROSOFT_TRUSTED_TENANTS is trusted without xms_edov."""
        _mock_microsoft_claims(monkeypatch, {
            "email": "user@corp.com",
            "tid": "corp-tenant-id",
        })
        url = reverse("outlook_login")
        response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert User.objects.filter(email="user@corp.com").exists()

    def test_outlook_login_exception(self, api_client, monkeypatch):
        """Unexpected error during user creation returns 500."""
        _mock_microsoft_claims(monkeypatch, {"email": "exc@corp.com", "xms_edov": True})
        url = reverse("outlook_login")
        with patch("gym_app.views.userAuth.User.objects.get_or_create", side_effect=Exception("DB error")):
            response = api_client.post(url, {"id_token": "valid"}, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error_message"] == "DB error"


class TestVerifyMicrosoftIdToken:
    """Unit tests for the Microsoft ID token issuer validation."""

    def _patch_decode(self, monkeypatch, claims):
        """Stub the JWKS client + jwt.decode so only issuer logic is exercised."""
        signing_key = MagicMock()
        signing_key.key = "key"
        client = MagicMock()
        client.get_signing_key_from_jwt.return_value = signing_key
        monkeypatch.setattr(
            "gym_app.views.userAuth._get_microsoft_jwks_client", lambda: client
        )
        monkeypatch.setattr("gym_app.views.userAuth.jwt.decode", lambda *a, **kw: claims)

    def test_accepts_valid_issuer(self, monkeypatch):
        """A well-formed multi-tenant issuer is accepted."""
        claims = {"iss": "https://login.microsoftonline.com/some-tid/v2.0", "email": "a@b.com"}
        self._patch_decode(monkeypatch, claims)
        assert _verify_microsoft_id_token("tok") == claims

    def test_rejects_bad_issuer(self, monkeypatch):
        """An issuer outside Microsoft's host is rejected."""
        self._patch_decode(monkeypatch, {"iss": "https://evil.example.com/tid/v2.0"})
        with pytest.raises(jwt.InvalidIssuerError) as exc_info:
            _verify_microsoft_id_token("tok")
        assert "issuer" in str(exc_info.value).lower()


# =========================================================================
# update_password
# =========================================================================
@pytest.mark.django_db
class TestUpdatePassword:
    """Tests for Update Password."""

    def test_unauthenticated(self, api_client):
        """Verify unauthenticated."""
        url = reverse("update_password")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_passwords(self, api_client, user):
        """Verify missing passwords."""
        api_client.force_authenticate(user=user)
        url = reverse("update_password")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wrong_current_password(self, api_client, user):
        """Verify wrong current password."""
        api_client.force_authenticate(user=user)
        url = reverse("update_password")
        response = api_client.post(
            url,
            {"current_password": "wrongpass", "new_password": "newpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in response.data["error"]

    def test_success(self, api_client, user):
        """Verify success."""
        api_client.force_authenticate(user=user)
        url = reverse("update_password")
        response = api_client.post(
            url,
            {"current_password": "testpassword", "new_password": "newpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("newpass123")

    def test_weak_new_password(self, api_client, user):
        """Verify weak new password."""
        api_client.force_authenticate(user=user)
        url = reverse("update_password")
        response = api_client.post(
            url,
            {"current_password": "testpassword", "new_password": "1"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        user.refresh_from_db()
        assert user.check_password("testpassword")


# =========================================================================
# send_passcode (password reset)
# =========================================================================
@pytest.mark.django_db
class TestSendPasscode:
    """Tests for Send Passcode."""

    def test_missing_email(self, api_client):
        """Verify missing email."""
        url = reverse("send_passcode")
        response = api_client.post(url, {"captcha_token": "tok"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_captcha(self, api_client):
        """Verify missing captcha."""
        url = reverse("send_passcode")
        response = api_client.post(url, {"email": "x@x.com"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_captcha_failure(self, api_client, monkeypatch):
        """Verify captcha failure."""
        _mock_captcha_failure(monkeypatch)
        url = reverse("send_passcode")
        response = api_client.post(
            url, {"email": "x@x.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_captcha_exception(self, api_client, monkeypatch):
        """Verify captcha exception."""
        _mock_captcha_exception(monkeypatch)
        url = reverse("send_passcode")
        response = api_client.post(
            url, {"email": "x@x.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_user_not_found(self, api_client, monkeypatch):
        """Verify user not found."""
        _mock_captcha_success(monkeypatch)
        url = reverse("send_passcode")
        response = api_client.post(
            url, {"email": "nobody@x.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("gym_app.views.userAuth.send_template_email")
    def test_success(self, mock_email, api_client, user, monkeypatch):
        """Verify success."""
        _mock_captcha_success(monkeypatch)
        url = reverse("send_passcode")
        response = api_client.post(
            url,
            {
                "email": user.email,
                "captcha_token": "tok",
                "subject_email": "Reset",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert PasswordCode.objects.filter(user=user).exists()
        mock_email.assert_called_once()


# =========================================================================
# verify_passcode_and_reset_password
# =========================================================================
@pytest.mark.django_db
class TestVerifyPasscodeAndResetPassword:
    """Tests for Verify Passcode And Reset Password."""

    def test_missing_fields(self, api_client):
        """Verify missing fields."""
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_captcha(self, api_client):
        """Verify missing captcha."""
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url, {"passcode": "123456", "new_password": "pw", "email": "x@x.com"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_captcha_failure(self, api_client, monkeypatch):
        """Verify captcha failure."""
        _mock_captcha_failure(monkeypatch)
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "123456", "new_password": "pw", "email": "x@x.com", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_captcha_exception(self, api_client, monkeypatch):
        """Verify captcha exception."""
        _mock_captcha_exception(monkeypatch)
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "123456", "new_password": "pw", "email": "x@x.com", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_invalid_passcode(self, api_client, monkeypatch):
        """Verify invalid passcode."""
        _mock_captcha_success(monkeypatch)
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "000000", "new_password": "newpw", "email": "x@x.com", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid or expired code"

    def test_success(self, api_client, user, monkeypatch):
        """Verify success."""
        _mock_captcha_success(monkeypatch)
        code = PasswordCode.objects.create(user=user, code="654321")
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "654321", "new_password": "SecureReset123!", "email": user.email, "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("SecureReset123!")
        code.refresh_from_db()
        assert code.used is True


# =========================================================================
# validate_token
# =========================================================================
@pytest.mark.django_db
class TestValidateToken:
    """Tests for Validate Token."""

    def test_unauthenticated(self, api_client):
        """Verify unauthenticated."""
        url = reverse("validate_token")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated(self, api_client, user):
        """Verify authenticated."""
        api_client.force_authenticate(user=user)
        url = reverse("validate_token")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Token is valid"


# =========================================================================
# T1: send_verification_code — email sending failure
# =========================================================================
@pytest.mark.django_db
class TestSendVerificationCodeEmailFailure:
    """Tests for Send Verification Code Email Failure."""

    def test_email_failure_returns_500(self, api_client, monkeypatch):
        """T1: send_verification_code returns 500 when send_template_email raises."""
        _mock_captcha_success(monkeypatch)
        mock_send_email = MagicMock(side_effect=Exception("SMTP error"))
        monkeypatch.setattr(
            "gym_app.views.userAuth.send_template_email",
            mock_send_email,
        )
        url = reverse("send_verification_code")
        response = api_client.post(
            url, {"email": "new@test.com", "captcha_token": "tok"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "Error sending verification email"
        mock_send_email.assert_called_once()


# =========================================================================
# T2: send_passcode — email sending failure
# =========================================================================
@pytest.mark.django_db
class TestSendPasscodeEmailFailure:
    """Tests for Send Passcode Email Failure."""

    def test_email_failure_returns_500(self, api_client, user, monkeypatch):
        """T2: send_passcode returns 500 when send_template_email raises."""
        _mock_captcha_success(monkeypatch)
        mock_send_email = MagicMock(side_effect=Exception("SMTP error"))
        monkeypatch.setattr(
            "gym_app.views.userAuth.send_template_email",
            mock_send_email,
        )
        url = reverse("send_passcode")
        response = api_client.post(
            url,
            {"email": user.email, "subject_email": "Reset", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "Error sending verification email"
        mock_send_email.assert_called_once()


# =========================================================================
# T3: sign_on — mass assignment prevention
# =========================================================================
@pytest.mark.django_db
class TestSignOnMassAssignment:
    """Tests for Sign On Mass Assignment."""

    def test_is_staff_ignored(self, api_client, monkeypatch):
        """T3: sign_on ignores is_staff=True in payload."""
        _mock_captcha_success(monkeypatch)
        EmailVerificationCode.objects.create(email="hacker@evil.com", code="123456")
        url = reverse("sign_on")
        payload = {
            "email": "hacker@evil.com",
            "password": "SecurePass123!",
            "first_name": "Hack",
            "last_name": "Er",
            "passcode": "123456",
            "captcha_token": "tok",
        }
        payload.update(is_staff=True, is_superuser=True)
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        from django.contrib.auth import get_user_model
        created_user = get_user_model().objects.get(email="hacker@evil.com")
        assert created_user.is_staff is False
        assert created_user.is_superuser is False
        assert created_user.is_active is True

    @pytest.mark.parametrize(
        ("email", "passcode", "submitted_authority"),
        [
            ("admin-role-attempt@example.com", "901001", {"role": "admin", "is_gym_lawyer": True}),
            ("lawyer-role-attempt@example.com", "901002", {"role": "lawyer", "is_gym_lawyer": True}),
            ("lawyer-flag-attempt@example.com", "901003", {"is_gym_lawyer": True}),
        ],
    )
    def test_discards_submitted_authority(self, api_client, email, passcode, submitted_authority):
        """Fails if public registration grants a submitted role or lawyer flag."""
        EmailVerificationCode.objects.create(email=email, code=passcode)

        response = api_client.post(
            reverse("sign_on"),
            _sign_on_payload(email, passcode, submitted_authority),
            format="json",
        )

        created_user = User.objects.get(email=email)
        assert response.status_code == status.HTTP_201_CREATED
        assert created_user.role == "basic"
        assert created_user.is_gym_lawyer is False
        assert response.data["user"]["role"] == "basic"
        assert response.data["user"]["is_gym_lawyer"] is False


# =========================================================================
# T4: sign_on — weak password rejected
# =========================================================================
@pytest.mark.django_db
class TestSignOnWeakPassword:
    """Tests for Sign On Weak Password."""

    def test_short_password_rejected(self, api_client, monkeypatch):
        """T4: sign_on rejects password that is too short."""
        _mock_captcha_success(monkeypatch)
        EmailVerificationCode.objects.create(email="weak@test.com", code="123456")
        url = reverse("sign_on")
        response = api_client.post(
            url,
            {
                "email": "weak@test.com",
                "password": "1",
                "first_name": "Weak",
                "last_name": "Pass",
                "passcode": "123456",
                "captcha_token": "tok",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_common_password_rejected(self, api_client, monkeypatch):
        """T4: sign_on rejects common passwords."""
        _mock_captcha_success(monkeypatch)
        EmailVerificationCode.objects.create(email="common@test.com", code="123456")
        url = reverse("sign_on")
        response = api_client.post(
            url,
            {
                "email": "common@test.com",
                "password": "password",
                "first_name": "Common",
                "last_name": "Pass",
                "passcode": "123456",
                "captcha_token": "tok",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data


# =========================================================================
# T8: verify_passcode_and_reset_password — expired code (>30 min)
# =========================================================================
@pytest.mark.django_db
class TestResetPasswordExpiredCode:
    """Tests for Reset Password Expired Code."""

    def test_expired_code_rejected(self, api_client, user, monkeypatch):
        """T8: verify_passcode_and_reset_password rejects codes older than 30 minutes."""
        _mock_captcha_success(monkeypatch)
        _pin_user_auth_now(monkeypatch)
        code = PasswordCode.objects.create(user=user, code="999888")
        # Manually set created_at to 31 minutes ago
        PasswordCode.objects.filter(pk=code.pk).update(
            created_at=FIXED_REFERENCE_TIME - timedelta(minutes=31)
        )
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "999888", "new_password": "SecurePass123!", "email": user.email, "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid or expired code"
        # Verify password was NOT changed
        user.refresh_from_db()
        assert user.check_password("testpassword")

    def test_code_within_ttl_accepted(self, api_client, user, monkeypatch):
        """T8: Code within 30 min TTL is accepted."""
        _mock_captcha_success(monkeypatch)
        _pin_user_auth_now(monkeypatch)
        code = PasswordCode.objects.create(user=user, code="999777")
        # Set created_at to 29 minutes ago (within TTL)
        PasswordCode.objects.filter(pk=code.pk).update(
            created_at=FIXED_REFERENCE_TIME - timedelta(minutes=29)
        )
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "999777", "new_password": "SecurePass123!", "email": user.email, "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("SecurePass123!")


# =========================================================================
# T9: verify_passcode_and_reset_password — email mismatch (collision prevention)
# =========================================================================
@pytest.mark.django_db
class TestResetPasswordEmailMismatch:
    """Tests for Reset Password Email Mismatch."""

    def test_wrong_email_rejected(self, api_client, user, monkeypatch):
        """T9: verify_passcode_and_reset_password rejects when email doesn't match code's user."""
        _mock_captcha_success(monkeypatch)
        PasswordCode.objects.create(user=user, code="555666")
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "555666", "new_password": "SecurePass123!", "email": "wrong@example.com", "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid or expired code"
        # Verify password was NOT changed
        user.refresh_from_db()
        assert user.check_password("testpassword")


# =========================================================================
# T5: verify_passcode_and_reset_password — weak password rejected
# =========================================================================
@pytest.mark.django_db
class TestResetPasswordWeakPassword:
    """Tests for Reset Password Weak Password."""

    def test_weak_password_rejected(self, api_client, user, monkeypatch):
        """T5: verify_passcode_and_reset_password rejects weak passwords."""
        _mock_captcha_success(monkeypatch)
        code = PasswordCode.objects.create(user=user, code="111111")
        url = reverse("verify_passcode_and_reset_password")
        response = api_client.post(
            url,
            {"passcode": "111111", "new_password": "1", "email": user.email, "captcha_token": "tok"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        # Verify password was NOT changed
        user.refresh_from_db()
        assert not user.check_password("1")
        # Verify code was NOT marked as used
        code.refresh_from_db()
        assert code.used is False

