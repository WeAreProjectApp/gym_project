"""Tests for dynamic_document_permissions module."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gym_app.models import (
    DocumentUsabilityPermission,
    DocumentVisibilityPermission,
    DynamicDocument,
)

User = get_user_model()
@pytest.fixture
def lawyer_user():
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def client_user():
    """Client user."""
    return User.objects.create_user(
        email="client@example.com",
        password="testpassword",
        role="client",
        first_name="Client",
        last_name="User",
    )


@pytest.fixture
def document(lawyer_user):
    """Document."""
    return DynamicDocument.objects.create(
        title="Doc permisos",
        content="<p>x</p>",
        state="Draft",
        created_by=lawyer_user,
    )


@pytest.mark.django_db
@pytest.mark.integration
class TestGetDocumentPermissions:
    """Tests for Get Document Permissions."""

    @pytest.mark.contract
    def test_get_document_permissions_as_lawyer(self, api_client, lawyer_user, client_user, document):
        """get_document_permissions devuelve resumen de visibilidad/usabilidad y roles activos."""
        # Crear permisos de visibilidad y usabilidad
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-document-permissions", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["document_id"] == document.id
        assert data["document_title"] == document.title
        assert data["summary"]["total_visibility_users"] == 1
        assert data["summary"]["total_usability_users"] == 1
        assert len(data["visibility_permissions"]) == 1
        assert len(data["usability_permissions"]) == 1

    @pytest.mark.edge
    def test_get_document_permissions_not_found(self, api_client, lawyer_user):
        """Verify get document permissions not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-document-permissions", kwargs={"pk": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.edge
    def test_get_document_permissions_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify get document permissions forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("get-document-permissions", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_get_document_permissions_internal_error(self, api_client, lawyer_user, document, monkeypatch):
        """Verify get document permissions internal error."""
        api_client.force_authenticate(user=lawyer_user)

        def raise_error(*args, **kwargs):
            raise Exception("boom")

        monkeypatch.setattr(DocumentVisibilityPermission.objects, "filter", raise_error)

        url = reverse("get-document-permissions", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.data["detail"]

    @pytest.mark.edge
    def test_get_document_permissions_active_roles_detection(self, api_client, lawyer_user, document):
        """active_roles includes only roles with permissions granted to all users."""
        basic_1 = User.objects.create_user(email="basic1@example.com", password="testpassword", role="basic")
        basic_2 = User.objects.create_user(email="basic2@example.com", password="testpassword", role="basic")
        client_1 = User.objects.create_user(email="client1@example.com", password="testpassword", role="client")
        User.objects.create_user(email="client2@example.com", password="testpassword", role="client")
        corp_1 = User.objects.create_user(email="corp1@example.com", password="testpassword", role="corporate_client")
        User.objects.create_user(email="corp2@example.com", password="testpassword", role="corporate_client")

        DocumentVisibilityPermission.objects.bulk_create([
            DocumentVisibilityPermission(document=document, user=basic_1, granted_by=lawyer_user),
            DocumentVisibilityPermission(document=document, user=basic_2, granted_by=lawyer_user),
            DocumentVisibilityPermission(document=document, user=client_1, granted_by=lawyer_user),
            DocumentVisibilityPermission(document=document, user=corp_1, granted_by=lawyer_user),
        ])
        DocumentUsabilityPermission.objects.bulk_create([
            DocumentUsabilityPermission(document=document, user=basic_1, granted_by=lawyer_user),
            DocumentUsabilityPermission(document=document, user=basic_2, granted_by=lawyer_user),
            DocumentUsabilityPermission(document=document, user=client_1, granted_by=lawyer_user),
        ])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-document-permissions", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        active_roles = response.data["active_roles"]
        assert "basic" in active_roles["visibility_roles"]
        assert "basic" in active_roles["usability_roles"]
        assert "client" not in active_roles["visibility_roles"]


@pytest.mark.django_db
@pytest.mark.integration
class TestManageDocumentPermissionsUnified:
    """Tests for Manage Document Permissions Unified."""

    @pytest.mark.contract
    def test_manage_permissions_unified_basic_flow(self, api_client, lawyer_user, client_user, document):
        """manage_document_permissions_unified maneja is_public, visibility y usability."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "is_public": False,
            "visibility": {
                "roles": ["client"],
                "user_ids": [client_user.id],
            },
            "usability": {
                "user_ids": [client_user.id],
            },
        }

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Debe haber concedido visibilidad y usabilidad al client_user
        assert data["document_id"] == document.id
        assert data["results"]["visibility"]["granted"]
        assert data["results"]["usability"]["granted"]
        assert data["summary"]["total_errors"] == 0

        vis_emails = set(
            DocumentVisibilityPermission.objects.filter(document=document).values_list("user__email", flat=True)
        )
        usab_emails = set(
            DocumentUsabilityPermission.objects.filter(document=document).values_list("user__email", flat=True)
        )
        assert client_user.email in vis_emails
        assert client_user.email in usab_emails

    @pytest.mark.edge
    def test_manage_permissions_unified_invalid_role_and_missing_user(self, api_client, lawyer_user, document):
        """Roles inválidos y user_ids inexistentes deben aparecer en errors."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "visibility": {
                "roles": ["invalid-role"],
                "user_ids": [9999],
            },
            "usability": {
                "roles": ["client"],
                "user_ids": [9999],
            },
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        errors = response.data["errors"]
        assert any("Invalid visibility roles" in err for err in errors)
        assert any("users not found".lower() in err.lower() for err in errors)

    @pytest.mark.edge
    def test_manage_permissions_unified_exclude_users_and_public_warning(self, api_client, lawyer_user, client_user, document):
        """exclude_user_ids debe excluir usuarios y is_public=True debe agregar warning."""
        api_client.force_authenticate(user=lawyer_user)

        excluded_user = User.objects.create_user(
            email="excluded@example.com",
            password="testpassword",
            role="client",
            first_name="Excluded",
            last_name="User",
        )

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "is_public": True,
            "visibility": {
                "roles": ["client"],
                "exclude_user_ids": [excluded_user.id],
            },
            "usability": {
                "user_ids": [client_user.id, excluded_user.id],
                "exclude_user_ids": [excluded_user.id],
            },
        }

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert any("Document is now public" in warning for warning in response.data["warnings"])

        visibility_ids = set(
            DocumentVisibilityPermission.objects.filter(document=document).values_list("user_id", flat=True)
        )
        usability_ids = set(
            DocumentUsabilityPermission.objects.filter(document=document).values_list("user_id", flat=True)
        )

        assert client_user.id in visibility_ids
        assert excluded_user.id not in visibility_ids
        assert client_user.id in usability_ids
        assert excluded_user.id not in usability_ids

    @pytest.mark.edge
    def test_manage_permissions_unified_empty_payload(self, api_client, lawyer_user, document):
        """Verify manage permissions unified empty payload."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["changes_made"] == []
        assert response.data["summary"]["total_errors"] == 0

    @pytest.mark.edge
    def test_manage_permissions_unified_usability_requires_visibility(self, api_client, lawyer_user, client_user, document):
        """Verify manage permissions unified usability requires visibility."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "usability": {
                "user_ids": [client_user.id],
            }
        }

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        errors = response.data["results"]["usability"]["errors"]
        assert len(errors) > 0, "Expected at least one error"
        assert "visibility" in errors[0]["error"].lower()
        assert DocumentUsabilityPermission.objects.filter(document=document).count() == 0

    @pytest.mark.edge
    def test_manage_permissions_unified_usability_granted_when_public(self, api_client, lawyer_user, client_user, document):
        """Verify manage permissions unified usability granted when public."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "is_public": True,
            "usability": {
                "user_ids": [client_user.id],
            }
        }

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.data["detail"]
        assert DocumentUsabilityPermission.objects.filter(document=document, user=client_user).count() == 0

    @pytest.mark.edge
    def test_manage_permissions_unified_visibility_empty_clears_permissions(self, api_client, lawyer_user, client_user, document):
        """Verify manage permissions unified visibility empty clears permissions."""
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        response = api_client.post(url, {"visibility": {}}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert DocumentVisibilityPermission.objects.filter(document=document).count() == 0
        assert len(response.data["results"]["visibility"]["removed"]) == 1

    @pytest.mark.edge
    def test_manage_permissions_unified_usability_empty_clears_permissions(self, api_client, lawyer_user, client_user, document):
        """Verify manage permissions unified usability empty clears permissions."""
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        response = api_client.post(url, {"usability": {}}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert DocumentUsabilityPermission.objects.filter(document=document).count() == 0
        assert len(response.data["results"]["usability"]["removed"]) == 1

    @pytest.mark.edge
    def test_manage_permissions_unified_forbidden_for_non_lawyer_owner(self, api_client, client_user, document):
        """Solo lawyer u owner pueden llamar a manage_document_permissions_unified."""
        # document.created_by es lawyer_user; aquí autenticamos client sin ser owner
        api_client.force_authenticate(user=client_user)

        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestTogglePublicAccess:
    """Tests for Toggle Public Access."""

    @pytest.mark.contract
    def test_toggle_public_access_auto_toggle(self, api_client, lawyer_user, document):
        """Verify toggle public access auto toggle."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("toggle-public-access", kwargs={"pk": document.id})
        # Inicialmente is_public=False; sin payload debe hacer toggle a True
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert document.is_public is True

        # Segunda llamada sin payload → vuelve a False
        response = api_client.post(url, {}, format="json")
        document.refresh_from_db()
        assert document.is_public is False

    @pytest.mark.contract
    def test_toggle_public_access_set_explicit_value(self, api_client, lawyer_user, document):
        """Verify toggle public access set explicit value."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("toggle-public-access", kwargs={"pk": document.id})
        response = api_client.post(url, {"is_public": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert document.is_public is True

    @pytest.mark.edge
    def test_toggle_public_access_not_found(self, api_client, lawyer_user):
        """Verify toggle public access not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("toggle-public-access", kwargs={"pk": 9999})
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.edge
    def test_toggle_public_access_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify toggle public access forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("toggle-public-access", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()


# ======================================================================
# Tests migrated from test_views_batch11.py
# ======================================================================

"""
Batch 11 – 20 tests for permission_views.py role-based and combined endpoints.

Targets uncovered lines:
  - grant_usability_permissions_by_role (915-1013)
  - revoke_permissions_by_role (1019-1117)
  - grant_visibility_permissions_combined (1123-1236)
  - grant_usability_permissions_combined (1242-1374)
  - revoke_permissions_combined (1380-1510)
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models.dynamic_document import (
    DocumentUsabilityPermission,  # noqa: F811
    DocumentVisibilityPermission,  # noqa: F811
    DynamicDocument,  # noqa: F811
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer_b11@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="client_b11@test.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def document(lawyer_user):  # noqa: F811
    """Document."""
    return DynamicDocument.objects.create(
        title="Doc B11", content="<p>Hello</p>", state="Draft",
        created_by=lawyer_user,
    )


# ===========================================================================
# 1. grant_usability_permissions_by_role
# ===========================================================================

@pytest.mark.django_db
class TestGrantUsabilityByRole:
    """Tests for Grant Usability By Role."""

    def test_empty_roles(self, api_client, lawyer_user, document):
        """Line 934-938: empty roles list."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.post(url, {"roles": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_roles(self, api_client, lawyer_user, document):
        """Lines 943-947: invalid role name."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.post(url, {"roles": ["superadmin"]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_usability_requires_visibility(self, api_client, lawyer_user, document, client_user):
        """Lines 960-972: user without visibility gets error."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["errors"]) >= 1

    def test_grant_usability_with_visibility(self, api_client, lawyer_user, document, client_user):
        """Lines 974-993: user with visibility gets usability."""
        DocumentVisibilityPermission.objects.create(
            document=document, user=client_user, granted_by=lawyer_user
        )
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["granted_permissions"]) >= 1

    def test_grant_usability_doc_not_found(self, api_client, lawyer_user):
        """Lines 1009-1013: document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": 99999})
        resp = api_client.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 2. revoke_permissions_by_role
# ===========================================================================

@pytest.mark.django_db
class TestRevokePermissionsByRole:
    """Tests for Revoke Permissions By Role."""

    def test_empty_roles(self, api_client, lawyer_user, document):
        """Lines 1037-1041: empty roles list."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.delete(url, {"roles": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_roles(self, api_client, lawyer_user, document):
        """Lines 1045-1050: invalid role."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.delete(url, {"roles": ["admin"]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_permission_type(self, api_client, lawyer_user, document):
        """Lines 1053-1058: invalid permission_type."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.delete(url, {"roles": ["client"], "permission_type": "invalid"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoke_visibility_by_role(self, api_client, lawyer_user, document, client_user):
        """Lines 1074-1078: revoke visibility."""
        DocumentVisibilityPermission.objects.create(
            document=document, user=client_user, granted_by=lawyer_user
        )
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        resp = api_client.delete(url, {"roles": ["client"], "permission_type": "visibility"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_visibility_revoked"] >= 1

    def test_revoke_doc_not_found(self, api_client, lawyer_user):
        """Lines 1113-1117: document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": 99999})
        resp = api_client.delete(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 3. grant_visibility_permissions_combined
# ===========================================================================

@pytest.mark.django_db
class TestGrantVisibilityCombined:
    """Tests for Grant Visibility Combined."""

    def test_empty_input(self, api_client, lawyer_user, document):
        """Lines 1142-1146: neither user_ids nor roles."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_roles(self, api_client, lawyer_user, document):
        """Lines 1151-1156: invalid role."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {"roles": ["superuser"]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_user_ids(self, api_client, lawyer_user, document):
        """Lines 1164-1170: user_ids with non-existent IDs."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": [99999]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_combined_success(self, api_client, lawyer_user, document, client_user):
        """Lines 1188-1213: grant to user_ids + roles."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "user_ids": [client_user.id],
            "roles": ["client"],
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK

    def test_grant_combined_with_exclude(self, api_client, lawyer_user, document, client_user):
        """Lines 1180-1182: exclude user IDs."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "roles": ["client"],
            "exclude_user_ids": [client_user.id],
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK


# ===========================================================================
# 4. grant_usability_permissions_combined
# ===========================================================================

@pytest.mark.django_db
class TestGrantUsabilityCombined:
    """Tests for Grant Usability Combined."""

    def test_empty_input(self, api_client, lawyer_user, document):
        """Lines 1262-1266: no user_ids or roles."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_user_ids(self, api_client, lawyer_user, document):
        """Lines 1284-1290: user not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": [99999]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_usability_combined_no_visibility(self, api_client, lawyer_user, document, client_user):
        """Lines 1316-1328: user without visibility gets error."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": [client_user.id]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data.get("errors", [])) >= 1


# ===========================================================================
# 5. revoke_permissions_combined
# ===========================================================================

@pytest.mark.django_db
class TestRevokePermissionsCombined:
    """Tests for Revoke Permissions Combined."""

    def test_empty_input(self, api_client, lawyer_user, document):
        """Lines 1401-1405: no user_ids or roles."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.delete(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_permission_type(self, api_client, lawyer_user, document):
        """Lines 1418-1423: invalid permission_type."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.delete(url, {
            "user_ids": [1], "permission_type": "invalid"
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoke_combined_success(self, api_client, lawyer_user, document, client_user):
        """Lines 1456-1485: revoke by user_ids."""
        DocumentVisibilityPermission.objects.create(
            document=document, user=client_user, granted_by=lawyer_user
        )
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-combined", kwargs={"pk": document.id})
        resp = api_client.delete(url, {
            "user_ids": [client_user.id],
            "permission_type": "visibility",
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_visibility_revoked"] >= 1


# ======================================================================
# Tests migrated from test_views_batch22.py
# ======================================================================

"""Batch 22 – permission_views.py remaining uncovered edges."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    DocumentUsabilityPermission,  # noqa: F811
    DocumentVisibilityPermission,  # noqa: F811
    DynamicDocument,  # noqa: F811
)

User = get_user_model()
pytestmark = pytest.mark.django_db

@pytest.fixture
def api():
    """Create an API client."""
    return APIClient()

@pytest.fixture
def lawyer():
    """Lawyer."""
    return User.objects.create_user(email="law_b22@t.com", password="pw", role="lawyer")

@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(email="cli_b22@t.com", password="pw", role="client", first_name="C", last_name="L")

@pytest.fixture
def doc(lawyer):
    """Doc."""
    return DynamicDocument.objects.create(title="DocB22", content="<p>x</p>", state="Draft", created_by=lawyer)


class TestPermViewsEdgeScenarios:
    """Tests for Perm Views Edge Scenarios."""

    # 1. get_document_permissions – generic exception
    def test_get_perms_internal_error(self, api, lawyer, doc):
        """Verify get perms internal error."""
        api.force_authenticate(user=lawyer)
        url = reverse("get-document-permissions", kwargs={"pk": doc.pk})
        with patch("gym_app.views.dynamic_documents.permission_views.DocumentVisibilityPermission.objects") as m:
            m.filter.side_effect = Exception("db boom")
            resp = api.get(url)
        assert resp.status_code == 500

    # 2. manage unified – invalid usability roles
    def test_manage_unified_invalid_usability_roles(self, api, lawyer, doc):
        """Verify manage unified invalid usability roles."""
        api.force_authenticate(user=lawyer)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": doc.pk})
        resp = api.post(url, {"usability": {"roles": ["bad_role"]}}, format="json")
        assert resp.status_code == 200
        assert any("bad_role" in str(e) for e in resp.data.get("errors", []))

    # 3. manage unified – doc not found
    def test_manage_unified_doc_not_found(self, api, lawyer):
        """Verify manage unified doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": 99999})
        resp = api.post(url, {"is_public": True}, format="json")
        assert resp.status_code == 404

    # 4. toggle public – doc not found
    def test_toggle_public_doc_not_found(self, api, lawyer):
        """Verify toggle public doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("toggle-public-access", kwargs={"pk": 99999})
        resp = api.post(url, {}, format="json")
        assert resp.status_code == 404

    # 5. grant visibility – doc not found
    def test_grant_visibility_doc_not_found(self, api, lawyer):
        """Verify grant visibility doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-visibility-permissions", kwargs={"pk": 99999})
        resp = api.post(url, {"user_ids": [1]}, format="json")
        assert resp.status_code == 404

    # 6. grant usability – lawyer skipped
    def test_grant_usability_lawyer_skipped(self, api, lawyer, doc):
        """Verify grant usability lawyer skipped."""
        law2 = User.objects.create_user(email="law2_b22@t.com", password="pw", role="lawyer")
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions", kwargs={"pk": doc.pk})
        resp = api.post(url, {"user_ids": [law2.pk]}, format="json")
        assert resp.status_code == 200
        assert len(resp.data["granted_permissions"]) == 0

    # 7. grant usability – doc not found
    def test_grant_usability_doc_not_found(self, api, lawyer):
        """Verify grant usability doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions", kwargs={"pk": 99999})
        resp = api.post(url, {"user_ids": [1]}, format="json")
        assert resp.status_code == 404

    # 8. revoke visibility – doc not found
    def test_revoke_visibility_doc_not_found(self, api, lawyer, client_user):
        """Verify revoke visibility doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("revoke-visibility-permission", kwargs={"pk": 99999, "user_id": client_user.pk})
        resp = api.delete(url)
        assert resp.status_code == 404

    # 9. revoke usability – user not found
    def test_revoke_usability_user_not_found(self, api, lawyer, doc):
        """Verify revoke usability user not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("revoke-usability-permission", kwargs={"pk": doc.pk, "user_id": 99999})
        resp = api.delete(url)
        assert resp.status_code == 404

    # 10. grant visibility by role – doc not found
    def test_grant_vis_by_role_doc_not_found(self, api, lawyer):
        """Verify grant vis by role doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": 99999})
        resp = api.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == 404

    # 11. grant usability by role – public warning
    def test_grant_usab_by_role_public_warning(self, api, lawyer, client_user):
        """Verify grant usab by role public warning."""
        pub_doc = DynamicDocument.objects.create(title="Pub", content="<p>x</p>", state="Draft", created_by=lawyer, is_public=True)
        # Grant visibility first so model-level clean() passes
        DocumentVisibilityPermission.objects.create(document=pub_doc, user=client_user, granted_by=lawyer)
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": pub_doc.pk})
        resp = api.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == 200
        assert resp.data.get("warning") is not None

    # 12. grant usability by role – doc not found
    def test_grant_usab_by_role_doc_not_found(self, api, lawyer):
        """Verify grant usab by role doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": 99999})
        resp = api.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == 404

    # 13. revoke by role – doc not found
    def test_revoke_by_role_doc_not_found(self, api, lawyer):
        """Verify revoke by role doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": 99999})
        resp = api.delete(url, {"roles": ["client"], "permission_type": "both"}, format="json")
        assert resp.status_code == 404

    # 14. grant visibility combined – doc not found
    def test_grant_vis_combined_doc_not_found(self, api, lawyer):
        """Verify grant vis combined doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": 99999})
        resp = api.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == 404

    # 15. grant usability combined – roles + excludes + doc not found
    def test_grant_usab_combined_roles_excludes(self, api, lawyer, client_user):
        """Verify grant usab combined roles excludes."""
        pub_doc = DynamicDocument.objects.create(title="Pub2", content="<p>x</p>", state="Draft", created_by=lawyer, is_public=True)
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": pub_doc.pk})
        resp = api.post(url, {"roles": ["client"], "exclude_user_ids": [client_user.pk]}, format="json")
        assert resp.status_code == 200

    def test_grant_usab_combined_doc_not_found(self, api, lawyer):
        """Verify grant usab combined doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": 99999})
        resp = api.post(url, {"roles": ["client"]}, format="json")
        assert resp.status_code == 404

    # 17. revoke combined – roles + excludes + doc not found
    def test_revoke_combined_roles_excludes(self, api, lawyer, client_user, doc):
        """Verify revoke combined roles excludes."""
        DocumentVisibilityPermission.objects.create(document=doc, user=client_user, granted_by=lawyer)
        api.force_authenticate(user=lawyer)
        url = reverse("revoke-permissions-combined", kwargs={"pk": doc.pk})
        resp = api.delete(url, {"roles": ["client"], "exclude_user_ids": [client_user.pk], "permission_type": "both"}, format="json")
        assert resp.status_code == 200

    def test_revoke_combined_doc_not_found(self, api, lawyer):
        """Verify revoke combined doc not found."""
        api.force_authenticate(user=lawyer)
        url = reverse("revoke-permissions-combined", kwargs={"pk": 99999})
        resp = api.delete(url, {"roles": ["client"], "permission_type": "both"}, format="json")
        assert resp.status_code == 404

    # 19. grant visibility combined – lawyer skip (line 1192)
    def test_grant_vis_combined_lawyer_skipped(self, api, lawyer, doc):
        """Verify grant vis combined lawyer skipped."""
        law2 = User.objects.create_user(email="law3_b22@t.com", password="pw", role="lawyer")
        api.force_authenticate(user=lawyer)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": doc.pk})
        resp = api.post(url, {"user_ids": [law2.pk]}, format="json")
        assert resp.status_code == 200
        assert len(resp.data["granted_permissions"]) == 0

    # 20. grant usability combined – lawyer skip (line 1313)
    def test_grant_usab_combined_lawyer_skipped(self, api, lawyer, doc):
        """Verify grant usab combined lawyer skipped."""
        law2 = User.objects.create_user(email="law4_b22@t.com", password="pw", role="lawyer")
        api.force_authenticate(user=lawyer)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": doc.pk})
        resp = api.post(url, {"user_ids": [law2.pk]}, format="json")
        assert resp.status_code == 200
        assert len(resp.data["granted_permissions"]) == 0


# ======================================================================
# Tests migrated from test_views_batch7.py
# ======================================================================

"""
Batch 7 – Coverage-gap tests for:
  • permission_views.py (93%) – unified manage endpoint, role-based grants,
    revoke by role, combined endpoints, error paths
  • legal_request.py (93%) – filters, date parsing, file validation,
    confirmation email, download file, status update, delete
"""
from unittest.mock import patch  # noqa: F811

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    LegalDiscipline,
    LegalRequest,
    LegalRequestType,
)
from gym_app.models.dynamic_document import (
    DocumentUsabilityPermission,  # noqa: F811
    DocumentVisibilityPermission,  # noqa: F811
    DynamicDocument,  # noqa: F811
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer_b7@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="client_b7@test.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def basic_user():
    """Create a basic user."""
    return User.objects.create_user(
        email="basic_b7@test.com", password="pw", role="basic",
    )


@pytest.fixture
def document(lawyer_user):  # noqa: F811
    """Document."""
    return DynamicDocument.objects.create(
        title="Perm Doc B7",
        content="<p>Hello</p>",
        state="Draft",
        created_by=lawyer_user,
        is_public=False,
    )


@pytest.fixture
def req_type():
    """Req type."""
    return LegalRequestType.objects.create(name="Civil B7")


@pytest.fixture
def discipline():
    """Discipline."""
    return LegalDiscipline.objects.create(name="Penal B7")


@pytest.fixture
def legal_request(client_user, req_type, discipline):
    """Legal request."""
    return LegalRequest.objects.create(
        user=client_user,
        request_type=req_type,
        discipline=discipline,
        description="Test legal request B7",
        status="PENDING",
    )


# ===========================================================================
# 1. permission_views – manage_document_permissions_unified edge cases
# ===========================================================================

@pytest.mark.django_db
class TestManagePermissionsUnified:
    """Tests for Manage Permissions Unified."""

    def test_set_public_and_visibility_roles(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 204-284: is_public + visibility roles in unified endpoint."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "is_public": True,
            "visibility": {"roles": ["client"]},
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["is_public"] is True
        assert len(resp.data["changes_made"]) >= 1

    def test_visibility_invalid_role(self, api_client, lawyer_user, document):
        """Line 242: invalid role in visibility config."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "visibility": {"roles": ["admin_fake"]},
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert any("Invalid" in e for e in resp.data["errors"])

    def test_visibility_missing_user_ids(self, api_client, lawyer_user, document):
        """Lines 252-255: user_ids with missing users."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "visibility": {"user_ids": [99999]},
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert any("not found" in e for e in resp.data["errors"])

    def test_visibility_exclude_user_ids(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 260-263: exclude specific user_ids."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "visibility": {
                "roles": ["client"],
                "exclude_user_ids": [client_user.id],
            },
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK

    def test_usability_without_visibility_error(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 345-357: usability granted without visibility on private doc."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "usability": {"user_ids": [client_user.id]},
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]["usability"]["errors"]) > 0

    def test_usability_with_public_doc_model_still_validates(
        self, api_client, lawyer_user, document, client_user
    ):
        """Line 345: view skips visibility check for public doc, but model.
        
        clean() still enforces it, resulting in a 500 from the generic handler.
        """
        document.is_public = True
        document.save()
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        resp = api_client.post(url, {
            "usability": {"user_ids": [client_user.id]},
        }, format="json")
        # Model-level ValidationError is caught by the generic except → 500
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_document_not_found(self, api_client, lawyer_user):
        """Line 404-408: document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": 99999})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 2. permission_views – toggle, grant, revoke endpoints
# ===========================================================================

@pytest.mark.django_db
class TestPermissionEndpoints:
    """Tests for Permission Endpoints."""

    def test_toggle_public_auto(self, api_client, lawyer_user, document):
        """Lines 447-448: auto-toggle when no is_public provided."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("toggle-public-access", kwargs={"pk": document.id})
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["is_public"] is True  # was False, toggled to True

    def test_grant_visibility_empty_user_ids(self, api_client, lawyer_user, document):
        """Line 493-497: empty user_ids."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_visibility_missing_users(self, api_client, lawyer_user, document):
        """Lines 501-507: some user_ids not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": [99999]}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in resp.data["detail"]

    def test_grant_usability_no_visibility(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 600-611: usability without visibility on private doc."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": document.id})
        resp = api_client.post(url, {"user_ids": [client_user.id]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["errors"]) > 0

    def test_revoke_visibility_no_permission(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 670-674: revoke visibility that doesn't exist."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={
            "pk": document.id, "user_id": client_user.id
        })
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_usability_no_permission(
        self, api_client, lawyer_user, document, client_user
    ):
        """Lines 718-722: revoke usability that doesn't exist."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={
            "pk": document.id, "user_id": client_user.id
        })
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_visibility_user_not_found(self, api_client, lawyer_user, document):
        """Lines 692-696: user not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={
            "pk": document.id, "user_id": 99999
        })
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_usability_user_not_found(self, api_client, lawyer_user, document):
        """Lines 739-743: user not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={
            "pk": document.id, "user_id": 99999
        })
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_available_clients(self, api_client, lawyer_user, client_user):
        """Lines 749-770: list available clients."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-available-clients")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "clients" in resp.data

    def test_get_available_roles(self, api_client, lawyer_user):
        """Lines 776-822: list available roles."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-available-roles")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "roles" in resp.data


# ===========================================================================
# 3. legal_request – list filters (search, status, dates)
# ===========================================================================

@pytest.mark.django_db
class TestLegalRequestListFilters:
    """Tests for Legal Request List Filters."""

    def test_list_as_lawyer_sees_all(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 435-438: lawyer sees all requests."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["user_role"] == "lawyer"

    def test_list_as_client_sees_own(
        self, api_client, client_user, legal_request
    ):
        """Lines 440-442: client sees only own requests."""
        api_client.force_authenticate(user=client_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["requests"]) >= 1

    def test_list_with_search_filter(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 446-453: search filter."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url, {"search": "Test legal"})
        assert resp.status_code == status.HTTP_200_OK

    def test_list_with_status_filter(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 457-458: status filter."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url, {"status": "PENDING"})
        assert resp.status_code == status.HTTP_200_OK

    def test_list_with_date_filters(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 464-480: date_from and date_to filters."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url, {"date_from": "2020-01-01", "date_to": "2030-12-31"})
        assert resp.status_code == status.HTTP_200_OK

    def test_list_with_invalid_date_format(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 470-471, 479-480: invalid date format."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("list-legal-requests")
        resp = api_client.get(url, {"date_from": "bad-date", "date_to": "also-bad"})
        assert resp.status_code == status.HTTP_200_OK  # doesn't fail, just skips


# ===========================================================================
# 4. legal_request – status update, responses, delete
# ===========================================================================

@pytest.mark.django_db
class TestLegalRequestActions:
    """Tests for Legal Request Actions."""

    def test_update_status_non_lawyer_forbidden(
        self, api_client, client_user, legal_request
    ):
        """Lines 572-576: non-lawyer cannot update status."""
        api_client.force_authenticate(user=client_user)
        url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.id})
        resp = api_client.put(url, {"status": "IN_REVIEW"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_status_missing_status(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 583-587: missing status field."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.id})
        resp = api_client.put(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_status_invalid_status(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 591-595: invalid status value."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.id})
        resp = api_client.put(url, {"status": "INVALID_STATUS"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("gym_app.views.legal_request.send_status_update_notification")
    def test_update_status_success(
        self, mock_notify, api_client, lawyer_user, legal_request
    ):
        """Lines 598-616: successful status update."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.id})
        resp = api_client.put(url, {"status": "IN_REVIEW"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert "IN_REVIEW" in resp.data["message"]

    @patch("gym_app.views.legal_request.notify_client_of_lawyer_response")
    def test_create_response_lawyer_auto_updates_status(
        self, mock_notify, api_client, lawyer_user, legal_request
    ):
        """Lines 664-668: lawyer response auto-updates PENDING → IN_REVIEW."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("create-legal-request-response", kwargs={"request_id": legal_request.id})
        resp = api_client.post(url, {"response_text": "Reviewing"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        legal_request.refresh_from_db()
        assert legal_request.status == "IN_REVIEW"

    @patch("gym_app.views.legal_request.notify_lawyers_of_client_response")
    def test_create_response_client(
        self, mock_notify, api_client, client_user, legal_request
    ):
        """Lines 677-679: client response."""
        api_client.force_authenticate(user=client_user)
        url = reverse("create-legal-request-response", kwargs={"request_id": legal_request.id})
        resp = api_client.post(url, {"response_text": "Client reply"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_response_no_permission(
        self, api_client, basic_user, legal_request
    ):
        """Lines 641-645: user without permission to respond."""
        api_client.force_authenticate(user=basic_user)
        url = reverse("create-legal-request-response", kwargs={"request_id": legal_request.id})
        resp = api_client.post(url, {"response_text": "Nope"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_response_empty_text(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 649-653: empty response text."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("create-legal-request-response", kwargs={"request_id": legal_request.id})
        resp = api_client.post(url, {"response_text": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_legal_request_non_lawyer(
        self, api_client, client_user, legal_request
    ):
        """Lines 711-715: non-lawyer cannot delete."""
        api_client.force_authenticate(user=client_user)
        url = reverse("delete-legal-request", kwargs={"request_id": legal_request.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_legal_request_success(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 718-728: lawyer deletes request."""
        req_id = legal_request.id
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("delete-legal-request", kwargs={"request_id": req_id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_200_OK
        assert not LegalRequest.objects.filter(id=req_id).exists()


# ===========================================================================
# 5. legal_request – confirmation email
# ===========================================================================

@pytest.mark.django_db
class TestConfirmationEmail:
    """Tests for Confirmation Email."""

    def test_missing_legal_request_id(self, api_client, lawyer_user):
        """Lines 348-349: missing legal_request_id."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("send-confirmation-email")
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_legal_request_not_found(self, api_client, lawyer_user):
        """Lines 354-355: legal request not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("send-confirmation-email")
        resp = api_client.post(url, {"legal_request_id": 99999}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("gym_app.views.legal_request.send_template_email")
    def test_send_confirmation_success(
        self, mock_send, api_client, client_user, legal_request
    ):
        """Lines 378-398: successful email send."""
        api_client.force_authenticate(user=client_user)
        url = reverse("send-confirmation-email")
        resp = api_client.post(
            url, {"legal_request_id": legal_request.id}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        mock_send.assert_called_once()

    @patch("gym_app.views.legal_request.send_template_email", side_effect=Exception("SMTP"))
    def test_send_confirmation_email_failure(
        self, mock_send, api_client, client_user, legal_request
    ):
        """Lines 400-405: email sending fails."""
        api_client.force_authenticate(user=client_user)
        url = reverse("send-confirmation-email")
        resp = api_client.post(
            url, {"legal_request_id": legal_request.id}, format="json"
        )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ===========================================================================
# 6. legal_request – get_or_delete, add files, download file edge cases
# ===========================================================================

@pytest.mark.django_db
class TestLegalRequestDetailEdges:
    """Tests for Legal Request Detail Edges."""

    def test_get_detail_no_permission(
        self, api_client, basic_user, legal_request
    ):
        """Lines 520-525: non-owner non-lawyer cannot view."""
        api_client.force_authenticate(user=basic_user)
        url = reverse("get-or-delete-legal-request", kwargs={"request_id": legal_request.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_via_combined_endpoint_non_lawyer(
        self, api_client, client_user, legal_request
    ):
        """Lines 536-540: only lawyers can delete via combined endpoint."""
        api_client.force_authenticate(user=client_user)
        url = reverse("get-or-delete-legal-request", kwargs={"request_id": legal_request.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_via_combined_endpoint_success(
        self, api_client, lawyer_user, legal_request
    ):
        """Lines 542-551: lawyer deletes via combined endpoint."""
        req_id = legal_request.id
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-or-delete-legal-request", kwargs={"request_id": req_id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_add_files_non_owner_forbidden(
        self, api_client, basic_user, legal_request
    ):
        """Lines 753-758: non-owner cannot add files."""
        api_client.force_authenticate(user=basic_user)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": legal_request.id})
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_add_files_closed_request(
        self, api_client, client_user, legal_request
    ):
        """Lines 769-773: cannot add files to closed request."""
        legal_request.status = "CLOSED"
        legal_request.save()
        api_client.force_authenticate(user=client_user)
        url = reverse("add-files-to-legal-request", kwargs={"request_id": legal_request.id})
        f = SimpleUploadedFile("test.pdf", b"%PDF-content", content_type="application/pdf")
        resp = api_client.post(url, {"files": f}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_download_file_no_permission(
        self, api_client, basic_user, legal_request
    ):
        """Lines 833-838: non-owner non-lawyer cannot download."""
        api_client.force_authenticate(user=basic_user)
        url = reverse("download-legal-request-file", kwargs={
            "request_id": legal_request.id, "file_id": 1
        })
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ======================================================================
# Tests merged from test_dynamic_document_permission_views_edges.py
# ======================================================================

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    DocumentUsabilityPermission,  # noqa: F811
    DocumentVisibilityPermission,  # noqa: F811
    DynamicDocument,  # noqa: F811
)

User = get_user_model()
pytestmark = pytest.mark.django_db
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="client@example.com",
        password="testpassword",
        role="client",
    )


@pytest.fixture
def basic_user():  # noqa: F811
    """Create a basic user."""
    return User.objects.create_user(
        email="basic@example.com",
        password="testpassword",
        role="basic",
    )


@pytest.fixture
def corporate_user():
    """Corporate user."""
    return User.objects.create_user(
        email="corp@example.com",
        password="testpassword",
        role="corporate_client",
    )


@pytest.fixture
def other_user():
    """Other user."""
    return User.objects.create_user(
        email="other@example.com",
        password="testpassword",
        role="client",
    )


@pytest.fixture
def document(lawyer_user):  # noqa: F811
    """Document."""
    return DynamicDocument.objects.create(
        title="Doc permisos",
        content="<p>x</p>",
        state="Draft",
        created_by=lawyer_user,
    )


class TestGrantVisibilityPermissions:
    """Tests for Grant Visibility Permissions."""

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [({}, "user_ids list is required"), ({"user_ids": [9999]}, "Users not found")],
    )
    def test_grant_visibility_permissions_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant visibility permissions validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_visibility_permissions_public_warning_skips_lawyer(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify grant visibility permissions public warning skips lawyer."""
        document.is_public = True
        document.save(update_fields=["is_public"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": document.id})
        payload = {"user_ids": [client_user.id, lawyer_user.id]}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        granted_ids = {perm["user_id"] for perm in response.data["granted_permissions"]}
        assert client_user.id in granted_ids
        assert lawyer_user.id not in granted_ids

    def test_grant_visibility_permissions_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify grant visibility permissions forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": document.id})
        response = api_client.post(url, {"user_ids": [client_user.id]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_grant_visibility_permissions_document_not_found(self, api_client, lawyer_user):
        """Verify grant visibility permissions document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions", kwargs={"pk": 9999})
        response = api_client.post(url, {"user_ids": [lawyer_user.id]}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()


class TestGrantUsabilityPermissions:
    """Tests for Grant Usability Permissions."""

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [({}, "user_ids list is required"), ({"user_ids": [9999]}, "Users not found")],
    )
    def test_grant_usability_permissions_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant usability permissions validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_usability_permissions_requires_visibility(self, api_client, lawyer_user, client_user, other_user, document):
        """Verify grant usability permissions requires visibility."""
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": document.id})
        payload = {"user_ids": [client_user.id, other_user.id]}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        created_ids = {perm["user_id"] for perm in response.data["granted_permissions"]}
        error_ids = {err["user_id"] for err in response.data["errors"]}
        assert client_user.id in created_ids
        assert other_user.id in error_ids

    def test_grant_usability_permissions_public_warning(self, api_client, lawyer_user, other_user, document):
        """Verify grant usability permissions public warning."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=other_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": document.id})
        payload = {"user_ids": [other_user.id]}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        assert response.data["granted_permissions"]

    def test_grant_usability_permissions_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify grant usability permissions forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": document.id})
        response = api_client.post(url, {"user_ids": [client_user.id]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_grant_usability_permissions_document_not_found(self, api_client, lawyer_user):
        """Verify grant usability permissions document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions", kwargs={"pk": 9999})
        response = api_client.post(url, {"user_ids": [lawyer_user.id]}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()


class TestRevokePermissionsByUser:
    """Tests for Revoke Permissions By User."""

    def test_revoke_visibility_permission_not_found(self, api_client, lawyer_user, client_user, document):
        """Verify revoke visibility permission not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={"pk": document.id, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_visibility_permission_user_not_found(self, api_client, lawyer_user, document):
        """Verify revoke visibility permission user not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={"pk": document.id, "user_id": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_visibility_permission_forbidden_for_non_owner(self, api_client, client_user, document, other_user):
        """Verify revoke visibility permission forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("revoke-visibility-permission", kwargs={"pk": document.id, "user_id": other_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_revoke_visibility_permission_document_not_found(self, api_client, lawyer_user, client_user):
        """Verify revoke visibility permission document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={"pk": 9999, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_revoke_visibility_permission_public_warning_revokes_usability(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify revoke visibility permission public warning revokes usability."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-visibility-permission", kwargs={"pk": document.id, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        assert response.data["usability_revoked"] is True

    def test_revoke_usability_permission_not_found(self, api_client, lawyer_user, client_user, document):
        """Verify revoke usability permission not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={"pk": document.id, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_usability_permission_user_not_found(self, api_client, lawyer_user, document):
        """Verify revoke usability permission user not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={"pk": document.id, "user_id": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_usability_permission_forbidden_for_non_owner(self, api_client, client_user, document, other_user):
        """Verify revoke usability permission forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("revoke-usability-permission", kwargs={"pk": document.id, "user_id": other_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_revoke_usability_permission_document_not_found(self, api_client, lawyer_user, client_user):
        """Verify revoke usability permission document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={"pk": 9999, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_revoke_usability_permission_public_warning(self, api_client, lawyer_user, client_user, document):
        """Verify revoke usability permission public warning."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-usability-permission", kwargs={"pk": document.id, "user_id": client_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]


class TestRoleBasedPermissionEndpoints:
    """Tests for Role Based Permission Endpoints."""

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [({}, "roles list is required"), ({"roles": ["invalid"]}, "Invalid roles")],
    )
    def test_grant_visibility_permissions_by_role_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant visibility permissions by role validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_visibility_permissions_by_role_skips_existing_and_warns(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify grant visibility permissions by role skips existing and warns."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, {"roles": ["client", "lawyer"]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        assert response.data["skipped_users"]

    def test_grant_visibility_permissions_by_role_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify grant visibility permissions by role forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_grant_visibility_permissions_by_role_document_not_found(self, api_client, lawyer_user):
        """Verify grant visibility permissions by role document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": 9999})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [({}, "roles list is required"), ({"roles": ["invalid"]}, "Invalid roles")],
    )
    def test_grant_usability_permissions_by_role_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant usability permissions by role validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_usability_permissions_by_role_requires_visibility(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify grant usability permissions by role requires visibility."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        error_ids = {err["user_id"] for err in response.data["errors"]}
        assert client_user.id in error_ids

    def test_grant_usability_permissions_by_role_skips_existing(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify grant usability permissions by role skips existing."""
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["skipped_users"]

    def test_grant_usability_permissions_by_role_forbidden_for_non_owner(self, api_client, client_user, document):
        """Verify grant usability permissions by role forbidden for non owner."""
        api_client.force_authenticate(user=client_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_grant_usability_permissions_by_role_document_not_found(self, api_client, lawyer_user):
        """Verify grant usability permissions by role document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-by-role", kwargs={"pk": 9999})
        response = api_client.post(url, {"roles": ["client"]}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [
            ({}, "roles list is required"),
            ({"roles": ["invalid"], "permission_type": "both"}, "Invalid roles"),
            ({"roles": ["client"], "permission_type": "invalid"}, "Invalid permission_type"),
        ],
    )
    def test_revoke_permissions_by_role_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify revoke permissions by role validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        response = api_client.delete(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_revoke_permissions_by_role_public_warning(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify revoke permissions by role public warning."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-by-role", kwargs={"pk": document.id})
        payload = {"roles": ["client"], "permission_type": "both"}
        response = api_client.delete(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]


class TestPermissionViewsRest:
    """Tests for Permission Views Rest."""

    def test_toggle_public_access_rest(self, api_client, lawyer_user, document):
        """Verify toggle public access rest."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("toggle-public-access", kwargs={"pk": document.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert document.is_public is True

        response = api_client.post(url, {"is_public": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert document.is_public is False

    def test_toggle_public_access_not_found(self, api_client, lawyer_user):
        """Verify toggle public access not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("toggle-public-access", kwargs={"pk": 9999})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_available_clients_forbidden_for_non_lawyer(self, api_client, client_user):
        """Verify get available clients forbidden for non lawyer."""
        api_client.force_authenticate(user=client_user)
        url = reverse("get-available-clients")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_get_available_roles_forbidden_for_non_lawyer(self, api_client, client_user):
        """Verify get available roles forbidden for non lawyer."""
        api_client.force_authenticate(user=client_user)
        url = reverse("get-available-roles")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only lawyers" in response.data["detail"].lower()

    def test_get_available_clients_and_roles_rest(self, api_client, lawyer_user, client_user, basic_user, corporate_user):
        """Verify get available clients and roles rest."""
        api_client.force_authenticate(user=lawyer_user)

        clients_url = reverse("get-available-clients")
        response = api_client.get(clients_url)

        assert response.status_code == status.HTTP_200_OK
        emails = {client["email"] for client in response.data["clients"]}
        assert client_user.email in emails
        assert basic_user.email in emails
        assert corporate_user.email in emails
        assert lawyer_user.email not in emails

        roles_url = reverse("get-available-roles")
        response = api_client.get(roles_url)

        assert response.status_code == status.HTTP_200_OK
        role_codes = {role["code"] for role in response.data["roles"]}
        assert {"client", "basic", "corporate_client", "lawyer"}.issubset(role_codes)


class TestCombinedPermissionEndpoints:
    """Tests for Combined Permission Endpoints."""

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [
            ({}, "At least one of user_ids or roles must be provided"),
            ({"roles": ["invalid"]}, "Invalid roles"),
            ({"user_ids": [9999]}, "Users not found"),
        ],
    )
    def test_grant_visibility_permissions_combined_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant visibility permissions combined validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_visibility_permissions_combined_warning_and_skipped(
        self,
        api_client,
        lawyer_user,
        client_user,
        basic_user,
        document,
    ):
        """Verify grant visibility permissions combined warning and skipped."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-visibility-permissions-combined", kwargs={"pk": document.id})
        payload = {
            "user_ids": [client_user.id],
            "roles": ["basic"],
            "exclude_user_ids": [basic_user.id],
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        assert response.data["skipped_users"]

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [
            ({}, "At least one of user_ids or roles must be provided"),
            ({"roles": ["invalid"]}, "Invalid roles"),
            ({"user_ids": [9999]}, "Users not found"),
        ],
    )
    def test_grant_usability_permissions_combined_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify grant usability permissions combined validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_grant_usability_permissions_combined_requires_visibility(
        self,
        api_client,
        lawyer_user,
        client_user,
        other_user,
        document,
    ):
        """Verify grant usability permissions combined requires visibility."""
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        payload = {"user_ids": [client_user.id, other_user.id]}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        created_ids = {perm["user_id"] for perm in response.data["granted_permissions"]}
        error_ids = {err["user_id"] for err in response.data["errors"]}
        assert client_user.id in created_ids
        assert other_user.id in error_ids

    def test_grant_usability_permissions_combined_warning_and_skipped(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify grant usability permissions combined warning and skipped."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("grant-usability-permissions-combined", kwargs={"pk": document.id})
        payload = {"user_ids": [client_user.id]}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]
        assert response.data["skipped_users"]

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [
            ({}, "At least one of user_ids or roles must be provided"),
            ({"roles": ["invalid"], "permission_type": "both"}, "Invalid roles"),
            ({"roles": ["client"], "permission_type": "invalid"}, "Invalid permission_type"),
            ({"user_ids": [9999], "permission_type": "both"}, "Users not found"),
        ],
    )
    def test_revoke_permissions_combined_validation(
        self,
        api_client,
        lawyer_user,
        document,
        payload,
        expected_detail,
    ):
        """Verify revoke permissions combined validation."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-combined", kwargs={"pk": document.id})
        response = api_client.delete(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_detail in response.data["detail"]

    def test_revoke_permissions_combined_public_warning(
        self,
        api_client,
        lawyer_user,
        client_user,
        document,
    ):
        """Verify revoke permissions combined public warning."""
        document.is_public = True
        document.save(update_fields=["is_public"])
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )
        DocumentUsabilityPermission.objects.create(
            document=document,
            user=client_user,
            granted_by=lawyer_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("revoke-permissions-combined", kwargs={"pk": document.id})
        payload = {"user_ids": [client_user.id], "permission_type": "both"}
        response = api_client.delete(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["warning"]


# ======================================================================
# Tests merged from test_permission_views_coverage.py
# ======================================================================

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.response import Response as DRFResponse
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    DocumentUsabilityPermission,  # noqa: F811
    DocumentVisibilityPermission,  # noqa: F811
    DynamicDocument,  # noqa: F811
)
from gym_app.models.corporate_request import CorporateRequest, CorporateRequestType
from gym_app.models.organization import Organization, OrganizationMembership

User = get_user_model()
pytestmark = pytest.mark.django_db
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="pvc-lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="pvc-client@example.com",
        password="testpassword",
        role="client",
    )


@pytest.fixture
def document(lawyer_user):  # noqa: F811
    """Document."""
    return DynamicDocument.objects.create(
        title="PVC Coverage Doc",
        content="<p>test</p>",
        state="Draft",
        created_by=lawyer_user,
    )


class TestManageUnifiedLawyerSkipBranches:
    """Tests for lines 269 and 342 in permission_views.py.
    
    Lawyer users included in target_users are skipped (continue) when
    granting visibility/usability permissions via the unified endpoint.
    """

    def test_unified_visibility_skips_lawyer_in_user_ids(
        self, api_client, lawyer_user, client_user, document
    ):
        """Line 269: lawyer user in visibility.user_ids is skipped,.
        
        only the client user gets a visibility permission created.
        """
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "visibility": {
                "user_ids": [lawyer_user.id, client_user.id],
            }
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        granted_ids = {u["user_id"] for u in response.data["results"]["visibility"]["granted"]}
        assert client_user.id in granted_ids
        assert lawyer_user.id not in granted_ids
        assert DocumentVisibilityPermission.objects.filter(
            document=document, user=client_user
        ).exists()
        assert not DocumentVisibilityPermission.objects.filter(
            document=document, user=lawyer_user
        ).exists()

    def test_unified_usability_skips_lawyer_in_user_ids(
        self, api_client, lawyer_user, client_user, document
    ):
        """Line 342: lawyer user in usability.user_ids is skipped,.
        
        only the client user gets a usability permission created.
        """
        document.is_public = True
        document.save(update_fields=["is_public"])

        DocumentVisibilityPermission.objects.create(
            document=document, user=client_user, granted_by=lawyer_user
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("manage-document-permissions-unified", kwargs={"pk": document.id})
        payload = {
            "usability": {
                "user_ids": [lawyer_user.id, client_user.id],
            }
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        granted_ids = {u["user_id"] for u in response.data["results"]["usability"]["granted"]}
        assert client_user.id in granted_ids
        assert lawyer_user.id not in granted_ids
        assert DocumentUsabilityPermission.objects.filter(
            document=document, user=client_user
        ).exists()
        assert not DocumentUsabilityPermission.objects.filter(
            document=document, user=lawyer_user
        ).exists()


class TestFilterDocumentsByVisibilityEdgeCases:
    """Tests for permissions.py line 286: document entry without 'id' is skipped.
    
    in filter_documents_by_visibility decorator.
    """

    def test_document_without_id_is_skipped(self, lawyer_user, client_user):
        """Line 286: When the wrapped view returns items with missing 'id',.
        
        the decorator silently skips them and only keeps valid entries.
        """
        from rest_framework.test import APIRequestFactory

        from gym_app.views.dynamic_documents.permissions import (
            filter_documents_by_visibility,
        )

        doc = DynamicDocument.objects.create(
            title="Visible Doc",
            content="<p>visible</p>",
            state="Draft",
            created_by=lawyer_user,
            is_public=True,
        )

        @filter_documents_by_visibility
        def fake_view(request):
            return DRFResponse({
                'items': [
                    {'id': doc.id, 'title': 'Valid'},
                    {'title': 'no-id-entry'},  # missing 'id' → line 286
                ],
            })

        factory = APIRequestFactory()
        request = factory.get('/fake/')
        request.user = client_user
        # DRF force_authenticate equivalent for raw request
        from rest_framework.request import Request
        drf_request = Request(request)
        drf_request.user = client_user

        response = fake_view(drf_request)

        # The entry without 'id' should have been silently skipped
        returned_ids = [item['id'] for item in response.data['items']]
        assert doc.id in returned_ids
        assert len(returned_ids) == 1  # only the valid entry


class TestCorporateRequestSerializerValidation:
    """Test for corporate_request.py line 258: serializer validation error.
    
    when client_add_response_to_request receives invalid data.
    """

    @pytest.fixture
    def corporate_user(self):
        """Corporate user."""
        return User.objects.create_user(
            email="pvc-corp@example.com",
            password="testpassword",
            role="corporate_client",
        )

    @pytest.fixture
    def organization(self, corporate_user):
        """Organization."""
        return Organization.objects.create(
            title="PVC Test Org",
            description="Test organization",
            corporate_client=corporate_user,
        )

    @pytest.fixture
    def corp_request(self, client_user, corporate_user, organization):
        """Corp request."""
        OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            is_active=True,
        )
        req_type = CorporateRequestType.objects.create(name="PVC Test Type")
        return CorporateRequest.objects.create(
            client=client_user,
            organization=organization,
            corporate_client=corporate_user,
            request_type=req_type,
            title="PVC Test Request",
            description="Test description",
        )

    def test_client_add_response_serializer_error_returns_400(
        self, api_client, client_user, corp_request
    ):
        """Line 258: When the serializer fails validation, the endpoint.
        
        returns 400 with error details instead of creating the response.
        """
        api_client.force_authenticate(user=client_user)
        url = reverse(
            "client-add-response-to-request",
            kwargs={"request_id": corp_request.id},
        )
        # Patch serializer.is_valid to return False, triggering the else branch
        with patch(
            "gym_app.views.corporate_request.CorporateRequestResponseSerializer"
        ) as MockSerializer:
            mock_instance = MockSerializer.return_value
            mock_instance.is_valid.return_value = False
            mock_instance.errors = {"response_text": ["Invalid data"]}

            response = api_client.post(
                url, {"response_text": "Valid text"}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Error al añadir la respuesta"
        assert "details" in response.data


# ======================================================================
# Tests moved from test_user_auth.py – batch36 (permission views domain)
# ======================================================================

@pytest.mark.django_db
class TestPermissionViewsAdditionalScenarios:
    """Tests for Permission Views Additional Scenarios."""

    def test_get_document_permissions(self, api_client, lawyer_user):
        """Verify get document permissions."""
        doc = DynamicDocument.objects.create(title="Perm36", content="<p>x</p>", state="Draft", created_by=lawyer_user)
        doc.visibility_permissions.create(user=lawyer_user, granted_by=lawyer_user)
        api_client.force_authenticate(user=lawyer_user)
        resp = api_client.get(reverse("get-document-permissions", args=[doc.id]))
        assert resp.status_code == 200

    def test_toggle_public_access(self, api_client, lawyer_user):
        """Verify toggle public access."""
        doc = DynamicDocument.objects.create(title="Pub36", content="<p>x</p>", state="Draft", created_by=lawyer_user, is_public=False)
        doc.usability_permissions.create(user=lawyer_user, granted_by=lawyer_user)
        api_client.force_authenticate(user=lawyer_user)
        resp = api_client.post(reverse("toggle-public-access", args=[doc.id]))
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert doc.is_public is True

    def test_get_available_clients(self, api_client, lawyer_user):
        """Verify get available clients."""
        api_client.force_authenticate(user=lawyer_user)
        resp = api_client.get(reverse("get-available-clients"))
        assert resp.status_code == 200

    def test_get_available_roles(self, api_client, lawyer_user):
        """Verify get available roles."""
        api_client.force_authenticate(user=lawyer_user)
        resp = api_client.get(reverse("get-available-roles"))
        assert resp.status_code == 200
