"""Tests for legal_update_views module."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from gym_app.models import LegalUpdate

User = get_user_model()

INTERNAL_UPDATE_ACTORS = [
    {"role": "lawyer"}, {"role": "Lawyer"}, {"role": "admin"}, {"role": "Admin"},
    {"role": "client", "is_gym_lawyer": True},
    {"role": "client", "is_staff": True},
    {"role": "client", "is_superuser": True},
]


@pytest.fixture(params=INTERNAL_UPDATE_ACTORS, ids=["lawyer", "legacy-lawyer", "admin", "legacy-admin", "gym-lawyer", "staff", "superuser"])
def internal_update_actor(request):
    """Create each internal identity supported by the authorization contract."""
    return User.objects.create_user(email="internal-update@example.com", password=None, **request.param)


@pytest.fixture(params=["client", "basic", "corporate_client"])
def external_update_actor(request):
    """Create an authenticated actor without internal privileges."""
    return User.objects.create_user(email="external-update@example.com", password=None, role=request.param)


@pytest.fixture
def update_payload():
    """Return valid mutation input shared by permission tests."""
    return {"title": "Authorized update", "content": "Updated content", "link_text": "Leer", "link_url": "https://example.com/authorized"}


@pytest.mark.django_db
def test_internal_actor_creates_legal_update(api_client, internal_update_actor, update_payload):
    """Fails if an internal role or privilege flag can no longer publish an update."""
    api_client.force_authenticate(user=internal_update_actor)
    response = api_client.post(reverse("legal-updates-list"), update_payload, format="json")
    assert response.status_code == 201
    assert LegalUpdate.objects.get(pk=response.data["id"]).title == "Authorized update"


@pytest.mark.django_db
def test_internal_actor_updates_legal_update(api_client, internal_update_actor, update_payload, legal_update_active):
    """Fails if an internal identity cannot persist a legal update edit."""
    api_client.force_authenticate(user=internal_update_actor)
    url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.pk})
    response = api_client.put(url, update_payload, format="json")
    legal_update_active.refresh_from_db()
    assert response.status_code == 200
    assert legal_update_active.title == "Authorized update"


@pytest.mark.django_db
def test_internal_actor_deactivates_legal_update(api_client, internal_update_actor, legal_update_active):
    """Fails if an internal identity cannot soft-delete an active update."""
    api_client.force_authenticate(user=internal_update_actor)
    response = api_client.delete(reverse("legal-updates-detail", kwargs={"pk": legal_update_active.pk}))
    legal_update_active.refresh_from_db()
    assert response.status_code == 204
    assert legal_update_active.is_active is False


@pytest.mark.django_db
def test_external_actor_cannot_create_legal_update(api_client, external_update_actor, update_payload):
    """Fails if an external actor publishes a valid legal update."""
    api_client.force_authenticate(user=external_update_actor)
    response = api_client.post(reverse("legal-updates-list"), update_payload, format="json")
    assert response.status_code == 403
    assert LegalUpdate.objects.count() == 0


@pytest.mark.django_db
def test_external_create_authorization_precedes_validation(api_client, external_update_actor):
    """Fails if invalid creation input reaches validation before external-role denial."""
    api_client.force_authenticate(user=external_update_actor)
    response = api_client.post(reverse("legal-updates-list"), {}, format="json")
    assert response.status_code == 403
    assert LegalUpdate.objects.count() == 0


@pytest.mark.django_db
def test_external_actor_cannot_update_legal_update(api_client, external_update_actor, update_payload, legal_update_active):
    """Fails if an authenticated external actor changes an existing update."""
    api_client.force_authenticate(user=external_update_actor)
    response = api_client.put(reverse("legal-updates-detail", kwargs={"pk": legal_update_active.pk}), update_payload, format="json")
    legal_update_active.refresh_from_db()
    assert response.status_code == 403
    assert legal_update_active.title == "Active Update"


@pytest.mark.django_db
def test_external_actor_cannot_deactivate_legal_update(api_client, external_update_actor, legal_update_active):
    """Fails if an external actor disables an active legal update."""
    api_client.force_authenticate(user=external_update_actor)
    response = api_client.delete(reverse("legal-updates-detail", kwargs={"pk": legal_update_active.pk}))
    legal_update_active.refresh_from_db()
    assert response.status_code == 403
    assert legal_update_active.is_active is True


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["put", "delete"])
@pytest.mark.parametrize("target", ["missing", "inactive"])
def test_external_mutation_authorization_precedes_lookup(api_client, external_update_actor, legal_update_inactive, method, target):
    """Fails if an unauthorized mutation reveals whether an update exists."""
    target_id = {"missing": legal_update_inactive.pk + 1000, "inactive": legal_update_inactive.pk}[target]
    api_client.force_authenticate(user=external_update_actor)
    response = getattr(api_client, method)(reverse("legal-updates-detail", kwargs={"pk": target_id}), {}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(("method", "route"), [("post", "legal-updates-list"), ("put", "legal-updates-detail"), ("delete", "legal-updates-detail")])
def test_legal_update_mutation_requires_authentication(api_client, legal_update_active, method, route):
    """Fails if an anonymous request can mutate a legal update."""
    route_kwargs = {"legal-updates-list": {}, "legal-updates-detail": {"pk": legal_update_active.pk}}[route]
    response = getattr(api_client, method)(reverse(route, kwargs=route_kwargs), {}, format="json")
    assert response.status_code == 401


@pytest.fixture
def user():
    """User."""
    return User.objects.create_user(
        email="user@example.com",
        password="testpassword",
        role="client",
    )


@pytest.fixture
def legal_update_active():
    """Legal update active."""
    return LegalUpdate.objects.create(
        title="Active Update",
        content="Content",
        link_text="Ver más",
        link_url="https://example.com/active",
        is_active=True,
    )


@pytest.fixture
def legal_update_inactive():
    """Legal update inactive."""
    return LegalUpdate.objects.create(
        title="Inactive Update",
        content="Content",
        link_text="Ver más",
        link_url="https://example.com/inactive",
        is_active=False,
    )


@pytest.mark.django_db
@pytest.mark.integration
class TestLegalUpdateListAndActive:
    """Tests for Legal Update List And Active."""

    @pytest.mark.edge
    def test_legal_update_list_requires_authentication(self, api_client):
        """Verify legal update list requires authentication."""
        url = reverse("legal-updates-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.contract
    def test_legal_update_list_returns_only_active(self, api_client, user, legal_update_active, legal_update_inactive):
        """Verify legal update list returns only active."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Active Update"

    @pytest.mark.contract
    def test_active_legal_updates_endpoint(self, api_client, user, legal_update_active, legal_update_inactive):
        """Verify active legal updates endpoint."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-active")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Active Update"


    @pytest.mark.edge
    def test_create_legal_update_invalid_payload(self, api_client, lawyer_user):
        """Verify create legal update invalid payload."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("legal-updates-list")

        response = api_client.post(url, {"title": "Missing fields"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "content" in response.data
        assert "link_text" in response.data
        assert "link_url" in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestLegalUpdateDetail:
    """Tests for Legal Update Detail."""

    @pytest.mark.edge
    def test_legal_update_detail_not_found_when_inactive(self, api_client, user, legal_update_inactive):
        """Verify legal update detail not found when inactive."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_inactive.id})

        response = api_client.get(url)

        # Detail view filtra por is_active=True
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.contract
    def test_get_legal_update_detail_success(self, api_client, user, legal_update_active):
        """Verify get legal update detail success."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == legal_update_active.id
        assert response.data["title"] == legal_update_active.title

    @pytest.mark.contract
    def test_update_legal_update_success(self, api_client, lawyer_user, legal_update_active):
        """Verify update legal update success."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.id})
        data = {
            "title": "Updated Title",
            "content": legal_update_active.content,
            "link_text": legal_update_active.link_text,
            "link_url": legal_update_active.link_url,
        }

        response = api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        legal_update_active.refresh_from_db()
        assert legal_update_active.title == "Updated Title"

    @pytest.mark.contract
    def test_delete_legal_update_marks_inactive(self, api_client, lawyer_user, legal_update_active):
        """Verify delete legal update marks inactive."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        legal_update_active.refresh_from_db()
        assert legal_update_active.is_active is False

    @pytest.mark.contract
    def test_create_legal_update_via_list_endpoint(self, api_client, lawyer_user):
        """Verify create legal update via list endpoint."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("legal-updates-list")
        data = {
            "title": "New Update",
            "content": "Contenido",
            "link_text": "Ver más",
            "link_url": "https://example.com/new",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert LegalUpdate.objects.filter(title="New Update").exists()


@pytest.mark.django_db
class TestLegalUpdateValidation:
    """Tests for Legal Update Validation."""

    def test_update_legal_update_invalid_data(self, api_client, lawyer_user, legal_update_active):
        """Line 46: PUT with invalid data returns serializer errors (400)."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.id})
        data = {
            "title": "",
            "content": "",
            "link_text": "",
            "link_url": "not-a-url",
        }
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert isinstance(response.data, dict)


@pytest.mark.django_db
class TestLegalUpdateRest:
    """Tests for Legal Update Rest."""

    def test_legal_update_list_create_and_active_rest(self, api_client, user, lawyer_user, legal_update_active, legal_update_inactive):
        """Verify legal update list create and active rest."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == legal_update_active.id

        active_url = reverse("legal-updates-active")
        response = api_client.get(active_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["id"] == legal_update_active.id

        payload = {
            "title": "Rest Update",
            "content": "Contenido",
            "link_text": "Ver más",
            "link_url": "https://example.com/rest",
        }
        api_client.force_authenticate(user=lawyer_user)
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert LegalUpdate.objects.filter(title="Rest Update").exists()

    def test_legal_update_detail_update_delete_rest(self, api_client, user, lawyer_user, legal_update_active):
        """Verify legal update detail update delete rest."""
        api_client.force_authenticate(user=user)
        url = reverse("legal-updates-detail", kwargs={"pk": legal_update_active.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        payload = {
            "title": "Updated via Rest",
            "content": legal_update_active.content,
            "link_text": legal_update_active.link_text,
            "link_url": legal_update_active.link_url,
        }
        api_client.force_authenticate(user=lawyer_user)
        response = api_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        legal_update_active.refresh_from_db()
        assert legal_update_active.title == "Updated via Rest"

        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        legal_update_active.refresh_from_db()
        assert legal_update_active.is_active is False


# ======================================================================
# Tests moved from test_user_auth.py – batch36 (legal update domain)
# ======================================================================

@pytest.mark.django_db
class TestLegalUpdatesViewsAdditionalScenarios:
    """Tests for Legal Updates Views Additional Scenarios."""

    def test_list_legal_updates(self, api_client, user):
        """Verify list legal updates."""
        LegalUpdate.objects.create(title="LU36", content="Body", is_active=True)
        api_client.force_authenticate(user=user)
        resp = api_client.get(reverse("legal-updates-list"))
        assert resp.status_code == 200

    def test_list_legal_updates_unauthenticated(self, api_client):
        """Verify list legal updates unauthenticated."""
        resp = api_client.get(reverse("legal-updates-list"))
        assert resp.status_code in (401, 403)
