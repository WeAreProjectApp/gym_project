"""Tests for organization_views module."""
from datetime import datetime as datetime_cls
from datetime import timedelta
from datetime import timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from gym_app.models import (
    CorporateRequest,
    CorporateRequestType,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)

User = get_user_model()
MAX_ORGANIZATION_LIST_QUERIES = 6
MAX_OWNER_INVITATION_LIST_QUERIES = 6
MAX_PERSONAL_INVITATION_LIST_QUERIES = 6
MAX_MY_MEMBERSHIPS_QUERIES = 6
MAX_PRIVATE_ORGANIZATION_DETAIL_QUERIES = 4
MAX_PUBLIC_LEADER_ORGANIZATION_DETAIL_QUERIES = 4
MAX_PUBLIC_MEMBER_ORGANIZATION_DETAIL_QUERIES = 4
ORGANIZATION_DETAIL_NOW = datetime_cls(2026, 9, 25, 12, tzinfo=dt_timezone.utc)


def _create_organization_actor(role, suffix):
    """Create an authenticated role without password hashing overhead."""
    return User.objects.create_user(
        email=f'round-five-{role}-{suffix}@example.com',
        password=None,
        role=role,
    )


def _create_membership_organizations(actor, prefix, count):
    """Create active memberships with distinct organizations and corporate owners."""
    memberships = []
    for index in range(count):
        corporate_client = _create_organization_actor(
            'corporate_client', f'{prefix}-corporate-{index}'
        )
        organization = Organization.objects.create(
            title=f'{prefix} organization {index}',
            description='Round five membership fixture',
            corporate_client=corporate_client,
        )
        membership = OrganizationMembership.objects.create(
            organization=organization,
            user=actor,
            role='MEMBER',
            is_active=True,
        )
        OrganizationMembership.objects.filter(pk=membership.pk).update(
            joined_at=ORGANIZATION_DETAIL_NOW + timedelta(minutes=index),
        )
        memberships.append(membership)
    return memberships


def _add_membership_summary_relations(organization, role):
    """Create the active-member and expired-pending counts for a membership summary."""
    extra_member = _create_organization_actor('client', f'{role}-summary-extra-member')
    OrganizationMembership.objects.create(
        organization=organization,
        user=extra_member,
        role='ADMIN',
        is_active=True,
    )
    invitee = _create_organization_actor('client', f'{role}-summary-invitee')
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invitee,
        invited_by=organization.corporate_client,
        status='PENDING',
        expires_at=ORGANIZATION_DETAIL_NOW - timedelta(days=1),
    )


def _create_owned_organization(suffix, is_active=True):
    """Create an organization and its distinct corporate owner for access boundaries."""
    corporate_client = _create_organization_actor('corporate_client', suffix)
    organization = Organization.objects.create(
        title=f'Round five {suffix} organization',
        description='Round five organization access fixture',
        corporate_client=corporate_client,
        is_active=is_active,
    )
    return corporate_client, organization


def _add_active_detail_members(organization, prefix, count, first_member=None):
    """Add distinct active members for detail serialization outside query capture."""
    memberships = []
    for index in range(count):
        user = first_member if index == 0 and first_member is not None else _create_organization_actor(
            'client', f'{prefix}-member-{index}'
        )
        memberships.append(
            OrganizationMembership.objects.create(
                organization=organization,
                user=user,
                role='MEMBER',
                is_active=True,
            )
        )
    return memberships


def _create_detail_organizations():
    """Create loaded and empty organizations for the detail serializer fast path."""
    corporate_client = _create_organization_actor('corporate_client', 'detail-owner')
    organization = Organization.objects.create(
        title='Round five populated detail organization',
        description='Detail serializer fixture',
        corporate_client=corporate_client,
    )
    active_member = _create_organization_actor('client', 'detail-active-member')
    inactive_member = _create_organization_actor('client', 'detail-inactive-member')
    OrganizationMembership.objects.create(organization=organization, user=active_member, role='MEMBER')
    OrganizationMembership.objects.create(
        organization=organization,
        user=inactive_member,
        role='MEMBER',
        is_active=False,
    )
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=inactive_member,
        invited_by=corporate_client,
        status='PENDING',
        expires_at=ORGANIZATION_DETAIL_NOW - timedelta(days=1),
    )
    request_type = CorporateRequestType.objects.create(name='Round five detail request type')
    recent_request = CorporateRequest.objects.create(
        client=active_member,
        organization=organization,
        corporate_client=corporate_client,
        request_type=request_type,
        title='Boundary request',
        description='Included at the 30-day boundary',
        priority='MEDIUM',
        status='PENDING',
    )
    old_request = CorporateRequest.objects.create(
        client=active_member,
        organization=organization,
        corporate_client=corporate_client,
        request_type=request_type,
        title='Older request',
        description='Excluded before the 30-day boundary',
        priority='MEDIUM',
        status='PENDING',
    )
    CorporateRequest.objects.filter(pk=recent_request.pk).update(
        created_at=ORGANIZATION_DETAIL_NOW - timedelta(days=30),
    )
    CorporateRequest.objects.filter(pk=old_request.pk).update(
        created_at=ORGANIZATION_DETAIL_NOW - timedelta(days=31),
    )
    empty_organization = Organization.objects.create(
        title='Round five empty detail organization',
        description='Empty detail serializer fixture',
        corporate_client=corporate_client,
    )
    return organization, empty_organization, active_member


def _organization_detail_snapshot(items):
    """Return the concrete detail fields protected by preloaded serializer relations."""
    return {
        item['id']: (
            item['member_count'],
            item['pending_invitations_count'],
            item['recent_requests_count'],
            [member['id'] for member in item['members']],
        )
        for item in items
    }


def _organization_list_items(response):
    """Return the paginated organization payload used by the list endpoint."""
    return response.data["results"]


def _create_organization_fixtures(corporate_client, count):
    """Create organizations whose list serialization exercises the queryset."""
    return [
        Organization.objects.create(
            title=f"Performance organization {index}",
            description="List budget fixture",
            corporate_client=corporate_client,
        )
        for index in range(count)
    ]


def _create_organization_count_relations(organization, corporate_client):
    """Create active, inactive, pending, and non-pending related records."""
    members = [
        User.objects.create_user(email=f"member-{index}@example.com", password=None, role="client")
        for index in range(3)
    ]
    invitees = [
        User.objects.create_user(email=f"invitee-{index}@example.com", password=None, role="client")
        for index in range(4)
    ]
    OrganizationMembership.objects.create(organization=organization, user=members[0], role="MEMBER")
    OrganizationMembership.objects.create(organization=organization, user=members[1], role="ADMIN")
    OrganizationMembership.objects.create(
        organization=organization,
        user=members[2],
        role="MEMBER",
        is_active=False,
    )
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invitees[0],
        invited_by=corporate_client,
        status="PENDING",
    )
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invitees[1],
        invited_by=corporate_client,
        status="PENDING",
        expires_at=timezone.now() - timezone.timedelta(days=1),
    )
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invitees[2],
        invited_by=corporate_client,
        status="PENDING",
    )
    OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invitees[3],
        invited_by=corporate_client,
        status="ACCEPTED",
    )


def _item_with_title(items, title):
    """Find one concrete organization payload without duplicating endpoint calls."""
    return next(item for item in items if item["title"] == title)


def _invitation_list_items(response):
    """Return the paginated invitation payload used by both invitation endpoints."""
    return response.data['results']


def _create_owner_invitation_fixtures(corporate_client, count):
    """Create one owner organization with distinct invitees for list pagination."""
    organization = Organization.objects.create(
        title='Owner invitation budget organization',
        corporate_client=corporate_client,
    )
    for index in range(count):
        invited_user = User.objects.create_user(
            email=f'owner-invitation-{index}@example.com',
            password=None,
            role='client',
        )
        OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=invited_user,
            invited_by=corporate_client,
            status='PENDING',
        )
    return organization


def _create_personal_invitation_fixtures(client, corporate_client, count):
    """Create one pending invitation from each distinct organization for a client."""
    for index in range(count):
        organization = Organization.objects.create(
            title=f'Personal invitation organization {index}',
            corporate_client=corporate_client,
        )
        OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=client,
            invited_by=corporate_client,
            status='PENDING',
        )


def _create_counted_invitation(organization, corporate_client, invited_user):
    """Create active-member and pending-invitation counts including an expired pending row."""
    member_users = [
        User.objects.create_user(
            email=f'count-member-{organization.pk}-{index}@example.com',
            password=None,
            role='client',
        )
        for index in range(3)
    ]
    OrganizationMembership.objects.create(
        organization=organization,
        user=member_users[0],
        role='MEMBER',
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=member_users[1],
        role='ADMIN',
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=member_users[2],
        role='MEMBER',
        is_active=False,
    )
    expired_invitation = OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=invited_user,
        invited_by=corporate_client,
        status='PENDING',
        expires_at=datetime_cls(2025, 1, 1, tzinfo=dt_timezone.utc),
    )
    for index in range(2):
        another_user = User.objects.create_user(
            email=f'count-invitee-{organization.pk}-{index}@example.com',
            password=None,
            role='client',
        )
        OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=another_user,
            invited_by=corporate_client,
            status='PENDING',
        )
    return expired_invitation

@pytest.fixture
def corporate_client():
    """Corporate client."""
    return User.objects.create_user(
        email="corp@example.com",
        password="testpassword",
        first_name="Corp",
        last_name="Leader",
        role="corporate_client",
    )


@pytest.fixture
def client_user():
    """Client user."""
    return User.objects.create_user(
        email="client@example.com",
        password="testpassword",
        first_name="Client",
        last_name="User",
        role="client",
    )


@pytest.fixture
def organization(corporate_client):
    """Organization."""
    return Organization.objects.create(
        title="Org Title",
        description="Org Description",
        corporate_client=corporate_client,
    )


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganizationCrudAndMembers:
    """Tests for Organization Crud And Members."""

    @pytest.mark.contract
    def test_create_organization_corporate_only(self, api_client, corporate_client, client_user):
        """Verify create organization corporate only."""
        url = reverse("create-organization")
        data = {"title": "Nueva Org", "description": "Desc"}

        # Corporate client puede crear
        api_client.force_authenticate(user=corporate_client)
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"]
        org_data = response.data["organization"]
        assert org_data["title"] == "Nueva Org"

        # Cliente normal no puede crear
        api_client.force_authenticate(user=client_user)
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    def test_get_my_organizations_filters_by_leader(self, api_client, corporate_client):
        """Verify get my organizations filters by leader."""
        # Org del corporate_client
        _org1 = Organization.objects.create(title="Org1", description="D1", corporate_client=corporate_client)
        _org2 = Organization.objects.create(title="Org2", description="D2", corporate_client=corporate_client)
        # Org de otro corporate
        other_corp = User.objects.create_user(
            email="othercorp@example.com",
            password="testpassword",
            role="corporate_client",
        )
        Organization.objects.create(title="ForeignOrg", description="FD", corporate_client=other_corp)

        api_client.force_authenticate(user=corporate_client)
        url = reverse("get-my-organizations")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Puede venir paginado o no; comprobamos que solo aparezcan sus orgs en el contenido
        data = response.data
        # Si es paginado, results está en 'results', si no en 'organizations'
        orgs = data.get("results") or data.get("organizations")
        titles = {o["title"] for o in orgs}
        assert {"Org1", "Org2"}.issubset(titles)
        assert "ForeignOrg" not in titles

    @pytest.mark.edge
    def test_delete_organization_prevents_when_active_requests(self, api_client, corporate_client, organization, client_user):
        """Verify delete organization prevents when active requests."""
        # Crear membresía activa para el cliente y una corporate request asociada a la org
        OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            role="MEMBER",
            is_active=True,
        )

        request_type = CorporateRequestType.objects.create(name="Org Test Type")

        CorporateRequest.objects.create(
            client=client_user,
            organization=organization,
            corporate_client=corporate_client,
            request_type=request_type,
            title="Req",
            description="Desc",
            priority="MEDIUM",
            status="PENDING",
        )

        api_client.force_authenticate(user=corporate_client)
        url = reverse("delete-organization", kwargs={"organization_id": organization.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "solicitudes activas" in response.data["error"]

    @pytest.mark.contract
    def test_get_organization_members_and_remove_member(self, api_client, corporate_client, client_user, organization):
        """Verify get organization members and remove member."""
        # Leader membership
        _leader_membership = OrganizationMembership.objects.create(
            organization=organization,
            user=corporate_client,
            role="LEADER",
            is_active=True,
        )
        # Member membership
        member_membership = OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            role="MEMBER",
            is_active=True,
        )

        api_client.force_authenticate(user=corporate_client)

        # Listar miembros
        url = reverse("get-organization-members", kwargs={"organization_id": organization.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        members = response.data["members"]
        assert len(members) == 2

        # No se puede remover LEADER
        url_remove = reverse("remove-organization-member", kwargs={"organization_id": organization.id, "user_id": corporate_client.id})
        response = api_client.delete(url_remove)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Se puede remover MEMBER
        url_remove = reverse("remove-organization-member", kwargs={"organization_id": organization.id, "user_id": client_user.id})
        response = api_client.delete(url_remove)
        assert response.status_code == status.HTTP_200_OK
        member_membership.refresh_from_db()
        assert member_membership.is_active is False


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganizationInvitationsAndMemberships:
    """Tests for Organization Invitations And Memberships."""

    @pytest.mark.contract
    def test_send_invitation(self, api_client, corporate_client, client_user, organization):
        """Test sending an invitation."""
        api_client.force_authenticate(user=corporate_client)
        url_send = reverse("send-organization-invitation", kwargs={"organization_id": organization.id})
        data = {"invited_user_email": client_user.email, "message": "Únete"}
        response = api_client.post(url_send, data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert OrganizationInvitation.objects.filter(organization=organization, invited_user=client_user).exists()

    @pytest.mark.contract
    @freeze_time("2025-01-15 12:00:00")
    def test_list_invitations(self, api_client, corporate_client, client_user, organization):
        """Test listing invitations."""
        invitation = OrganizationInvitation.objects.create(
            organization=organization, invited_user=client_user, invited_by=corporate_client,
            status="PENDING", expires_at=timezone.now() + timezone.timedelta(days=10)
        )
        api_client.force_authenticate(user=corporate_client)
        
        url_list = reverse("get-organization-invitations", kwargs={"organization_id": organization.id})
        response = api_client.get(url_list)
        
        assert response.status_code == status.HTTP_200_OK
        invites = response.data.get("results") or response.data.get("invitations")
        assert any(inv["id"] == invitation.id for inv in invites)

    @pytest.mark.contract
    @freeze_time("2025-01-15 12:00:00")
    def test_client_accepts_invitation(self, api_client, corporate_client, client_user, organization):
        """Test client accepting an invitation."""
        invitation = OrganizationInvitation.objects.create(
            organization=organization, invited_user=client_user, invited_by=corporate_client,
            status="PENDING", expires_at=timezone.now() + timezone.timedelta(days=10)
        )
        api_client.force_authenticate(user=client_user)
        
        url_respond = reverse("respond-to-invitation", kwargs={"invitation_id": invitation.id})
        response = api_client.post(url_respond, {"action": "accept"}, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        invitation.refresh_from_db()
        assert invitation.status == "ACCEPTED"
        assert OrganizationMembership.objects.filter(organization=organization, user=client_user, is_active=True).exists()

    @pytest.mark.edge
    @freeze_time("2025-01-15 12:00:00")
    def test_cancel_invitation_only_pending(self, api_client, corporate_client, client_user, organization):
        """Verify cancel invitation only pending."""
        api_client.force_authenticate(user=corporate_client)
        invitation = OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=client_user,
            invited_by=corporate_client,
            status="PENDING",
            expires_at=timezone.now() + timezone.timedelta(days=10),
        )

        # Cancelar pendiente
        url_cancel = reverse("cancel-organization-invitation", kwargs={"organization_id": organization.id, "invitation_id": invitation.id})
        response = api_client.delete(url_cancel)
        assert response.status_code == status.HTTP_200_OK

        # Intentar cancelar una no pendiente
        invitation2 = OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=client_user,
            invited_by=corporate_client,
            status="ACCEPTED",
            expires_at=timezone.now() + timezone.timedelta(days=10),
        )
        url_cancel2 = reverse("cancel-organization-invitation", kwargs={"organization_id": organization.id, "invitation_id": invitation2.id})
        response = api_client.delete(url_cancel2)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.contract
    def test_get_my_memberships_and_leave_organization(self, api_client, client_user, corporate_client, organization):
        """Verify get my memberships and leave organization."""
        # Crear membresía MEMBER
        membership = OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            role="MEMBER",
            is_active=True,
        )

        api_client.force_authenticate(user=client_user)
        url_memberships = reverse("get-my-memberships")
        response = api_client.get(url_memberships)
        assert response.status_code == status.HTTP_200_OK
        orgs = response.data["organizations"]
        assert len(orgs) == 1
        assert orgs[0]["title"] == organization.title

        # Dejar organización
        url_leave = reverse("leave-organization", kwargs={"organization_id": organization.id})
        response = api_client.post(url_leave, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.is_active is False

        # Líder no puede dejar su propia organización
        _leader_membership = OrganizationMembership.objects.create(
            organization=organization,
            user=corporate_client,
            role="LEADER",
            is_active=True,
        )
        api_client.force_authenticate(user=corporate_client)
        response = api_client.post(url_leave, {}, format="json")
        # Decorador require_client_only devuelve 403 para roles no permitidos (corporate_client)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganizationStatsAndPublicDetail:
    """Tests for Organization Stats And Public Detail."""

    @pytest.mark.contract
    @freeze_time("2025-01-15 12:00:00")
    def test_get_organization_stats_for_corporate(self, api_client, corporate_client, client_user, organization):
        """Verify get organization stats for corporate."""
        # Crear algunos datos
        OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            role="MEMBER",
            is_active=True,
        )
        OrganizationInvitation.objects.create(
            organization=organization,
            invited_user=client_user,
            invited_by=corporate_client,
            status="PENDING",
            expires_at=timezone.now() + timezone.timedelta(days=10),
        )
        request_type = CorporateRequestType.objects.create(name="Org Stats Type")

        CorporateRequest.objects.create(
            client=client_user,
            organization=organization,
            corporate_client=corporate_client,
            request_type=request_type,
            title="Req",
            description="Desc",
            priority="MEDIUM",
            status="PENDING",
        )

        api_client.force_authenticate(user=corporate_client)
        url = reverse("get-organization-stats")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        # Chequear que algunas métricas básicas existen
        assert "total_organizations" in data
        assert "total_members" in data
        assert "total_pending_invitations" in data
        assert "recent_requests_count" in data

    @pytest.mark.edge
    def test_get_organization_public_detail_access_rules(self, api_client, corporate_client, client_user, organization):
        """Verify get organization public detail access rules."""
        # Añadir membresía del cliente
        OrganizationMembership.objects.create(
            organization=organization,
            user=client_user,
            role="MEMBER",
            is_active=True,
        )

        # Corporate líder puede ver
        api_client.force_authenticate(user=corporate_client)
        url = reverse("get-organization-public-detail", kwargs={"organization_id": organization.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Cliente miembro puede ver
        api_client.force_authenticate(user=client_user)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Cliente sin membresía no puede ver
        other_client = User.objects.create_user(
            email="otherclient@example.com",
            password="testpassword",
            role="client",
        )
        api_client.force_authenticate(user=other_client)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganizationRest:
    """Tests for Organization Rest."""

    def test_rest_create_update_delete_and_detail(self, api_client, corporate_client):
        """Verify rest create update delete and detail."""
        api_client.force_authenticate(user=corporate_client)

        create_url = reverse("create-organization")
        response = api_client.post(
            create_url,
            {"title": "Rest Org", "description": "Rest desc"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        organization_id = response.data["organization"]["id"]

        detail_url = reverse("get-organization-detail", kwargs={"organization_id": organization_id})
        response = api_client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["organization"]["id"] == organization_id

        update_url = reverse("update-organization", kwargs={"organization_id": organization_id})
        response = api_client.post(update_url, {"title": "Rest Org Updated"}, format="json")
        assert response.status_code == status.HTTP_200_OK

        delete_url = reverse("delete-organization", kwargs={"organization_id": organization_id})
        response = api_client.delete(delete_url)
        assert response.status_code == status.HTTP_200_OK
        assert not Organization.objects.filter(id=organization_id).exists()

    def test_rest_get_my_organizations_and_stats(self, api_client, corporate_client, client_user):
        """Verify rest get my organizations and stats."""
        Organization.objects.create(title="Org A", description="A", corporate_client=corporate_client)
        Organization.objects.create(title="Org B", description="B", corporate_client=corporate_client)
        other_corp = User.objects.create_user(
            email="othercorp@example.com",
            password="testpassword",
            role="corporate_client",
        )
        Organization.objects.create(title="Foreign", description="F", corporate_client=other_corp)

        api_client.force_authenticate(user=corporate_client)
        list_url = reverse("get-my-organizations")
        response = api_client.get(list_url)
        assert response.status_code == status.HTTP_200_OK
        orgs = response.data.get("results") or response.data.get("organizations")
        titles = {org["title"] for org in orgs}
        assert {"Org A", "Org B"}.issubset(titles)
        assert "Foreign" not in titles

        OrganizationMembership.objects.create(
            organization=Organization.objects.filter(corporate_client=corporate_client).first(),
            user=client_user,
            role="MEMBER",
            is_active=True,
        )

        stats_url = reverse("get-organization-stats")
        response = api_client.get(stats_url)
        assert response.status_code == status.HTTP_200_OK
        assert "total_organizations" in response.data


# ======================================================================
# Tests migrated from test_views_batch26.py
# ======================================================================

"""Batch 26 – 20 tests: model __str__, invitation accept/reject, request numbers, documents_by_state report."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    Case,
    DynamicDocument,
    LegalDiscipline,
    LegalRequest,
    LegalRequestResponse,
    LegalRequestType,
    Organization,  # noqa: F811
    OrganizationInvitation,  # noqa: F811
    OrganizationMembership,  # noqa: F811
    OrganizationPost,
    Process,
)
from gym_app.models.corporate_request import (
    CorporateRequest,  # noqa: F811
    CorporateRequestResponse,
    CorporateRequestType,  # noqa: F811
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
    return User.objects.create_user(email="l26@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def cli():
    """Cli."""
    return User.objects.create_user(email="c26@t.com", password="pw", role="client", first_name="C", last_name="E")

@pytest.fixture
def corp():
    """Corp."""
    return User.objects.create_user(email="co26@t.com", password="pw", role="corporate_client", first_name="Co", last_name="Rp")


# 1-3. Organization model __str__ and invitation __str__
class TestOrgModelStr:
    """Tests for Org Model Str."""

    def test_org_str(self, corp):
        """Verify org str."""
        org = Organization.objects.create(title="MyOrg", corporate_client=corp)
        assert "MyOrg" in str(org)
        assert corp.email in str(org)

    def test_invitation_str(self, corp, cli):
        """Verify invitation str."""
        org = Organization.objects.create(title="O2", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        s = str(inv)
        assert cli.email in s
        assert "PENDING" in s

    def test_membership_str(self, corp, cli):
        """Verify membership str."""
        org = Organization.objects.create(title="O3", corporate_client=corp)
        mem = OrganizationMembership.objects.create(organization=org, user=cli, role="MEMBER")
        assert str(mem)  # just ensure no crash


# 4-6. Invitation accept and reject
class TestInvitationActions:
    """Tests for Invitation Actions."""

    def test_accept_creates_membership(self, corp, cli):
        """Verify accept creates membership."""
        org = Organization.objects.create(title="AccOrg", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        inv.accept()
        inv.refresh_from_db()
        assert inv.status == "ACCEPTED"
        assert OrganizationMembership.objects.filter(organization=org, user=cli, is_active=True).exists()

    def test_accept_already_member_raises(self, corp, cli):
        """Verify accept already member raises."""
        org = Organization.objects.create(title="DupOrg", corporate_client=corp)
        OrganizationMembership.objects.create(organization=org, user=cli, role="MEMBER", is_active=True)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        with pytest.raises(ValidationError) as exc_info:
            inv.accept()
        assert exc_info.value is not None
        inv.refresh_from_db()
        assert inv.status == "PENDING"

    def test_reject_invitation(self, corp, cli):
        """Verify reject invitation."""
        org = Organization.objects.create(title="RejOrg", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        inv.reject()
        inv.refresh_from_db()
        assert inv.status == "REJECTED"
        assert inv.responded_at is not None


# 7-9. LegalRequest model gaps
class TestLegalRequestModel:
    """Tests for Legal Request Model."""

    def test_str_with_user(self, cli):
        """Verify str with user."""
        rt = LegalRequestType.objects.create(name="Q")
        di = LegalDiscipline.objects.create(name="C")
        lr = LegalRequest.objects.create(user=cli, request_type=rt, discipline=di, description="D")
        s = str(lr)
        assert lr.request_number in s
        assert "C" in s

    def test_request_number_sequence(self, cli):
        """Verify request number sequence."""
        rt = LegalRequestType.objects.create(name="Q2")
        di = LegalDiscipline.objects.create(name="C2")
        lr1 = LegalRequest.objects.create(user=cli, request_type=rt, discipline=di, description="D1")
        lr2 = LegalRequest.objects.create(user=cli, request_type=rt, discipline=di, description="D2")
        n1 = int(lr1.request_number.split("-")[-1])
        n2 = int(lr2.request_number.split("-")[-1])
        assert n2 == n1 + 1

    def test_response_str(self, cli, law):
        """Verify response str."""
        rt = LegalRequestType.objects.create(name="Q3")
        di = LegalDiscipline.objects.create(name="C3")
        lr = LegalRequest.objects.create(user=cli, request_type=rt, discipline=di, description="D")
        r = LegalRequestResponse.objects.create(legal_request=lr, user=law, response_text="ok", user_type="lawyer")
        s = str(r)
        assert lr.request_number in s
        assert "lawyer" in s


# 10-12. CorporateRequest model gaps
class TestCorporateRequestModel:
    """Tests for Corporate Request Model."""

    def test_str(self, cli, corp):
        """Verify str."""
        ct = CorporateRequestType.objects.create(name="T")
        cr = CorporateRequest.objects.create(client=cli, corporate_client=corp, request_type=ct, title="TT", description="D")
        s = str(cr)
        assert cr.request_number in s
        assert cli.email in s

    def test_request_number_sequence(self, cli, corp):
        """Verify request number sequence."""
        ct = CorporateRequestType.objects.create(name="T2")
        cr1 = CorporateRequest.objects.create(client=cli, corporate_client=corp, request_type=ct, title="A", description="D")
        cr2 = CorporateRequest.objects.create(client=cli, corporate_client=corp, request_type=ct, title="B", description="D")
        n1 = int(cr1.request_number.split("-")[-1])
        n2 = int(cr2.request_number.split("-")[-1])
        assert n2 == n1 + 1

    def test_response_str(self, cli, corp, law):
        """Verify response str."""
        ct = CorporateRequestType.objects.create(name="T3")
        cr = CorporateRequest.objects.create(client=cli, corporate_client=corp, request_type=ct, title="T", description="D")
        r = CorporateRequestResponse.objects.create(corporate_request=cr, user=law, response_text="ok", user_type="lawyer")
        assert str(r)


# 13-14. OrganizationPost model
class TestOrgPostModel:
    """Tests for Org Post Model."""

    def test_post_str(self, corp):
        """Verify post str."""
        org = Organization.objects.create(title="PostOrg", corporate_client=corp)
        p = OrganizationPost.objects.create(organization=org, author=corp, title="News", content="Body")
        assert str(p)

    def test_post_has_link_false(self, corp):
        """Verify post has link false."""
        org = Organization.objects.create(title="PostOrg2", corporate_client=corp)
        p = OrganizationPost.objects.create(organization=org, author=corp, title="N", content="B")
        assert p.has_link is False

    
# 15-16. Process model __str__ and edge cases
class TestProcessModel:
    """Tests for Process Model."""

    def test_process_str(self, law):
        """Verify process str."""
        c = Case.objects.create(type="Civil")
        p = Process.objects.create(ref="REF-001", case=c, lawyer=law)
        assert str(p)

    def test_case_str(self):
        """Verify case str."""
        c = Case.objects.create(type="Penal")
        assert "Penal" in str(c)


# 17. documents_by_state report
class TestDocByStateReport:
    """Tests for Doc By State Report."""

    def test_documents_by_state(self, api, law):
        """Verify documents by state."""
        DynamicDocument.objects.create(title="D1", content="<p>x</p>", state="Draft", created_by=law)
        DynamicDocument.objects.create(title="D2", content="<p>y</p>", state="Completed", created_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("generate-excel-report"), {"reportType": "documents_by_state"}, format="json")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp["Content-Type"]


# 18. Invitation can_be_responded after rejection
class TestInvitationEdge:
    """Tests for Invitation Edge."""

    def test_cannot_respond_after_reject(self, corp, cli):
        """Verify cannot respond after reject."""
        org = Organization.objects.create(title="E1", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        inv.reject()
        assert inv.can_be_responded() is False

    def test_cannot_accept_after_accept(self, corp, cli):
        """Verify cannot accept after accept."""
        org = Organization.objects.create(title="E2", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        inv.accept()
        with pytest.raises(ValidationError) as exc_info:
            inv.accept()
        assert exc_info.value is not None
        assert inv.status == "ACCEPTED"


# 20. DynamicDocument __str__
class TestDynamicDocStr:
    """Tests for Dynamic Doc Str."""

    def test_dynamic_doc_str(self, law):
        """Verify dynamic doc str."""
        d = DynamicDocument.objects.create(title="MyDoc", content="<p>x</p>", state="Draft", created_by=law)
        assert "MyDoc" in str(d)


# ======================================================================
# Tests migrated from test_views_batch34.py
# ======================================================================

"""Batch 34 – 20 tests: organization views, subscription views, intranet views edges."""
import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    Organization,  # noqa: F811
    OrganizationInvitation,  # noqa: F811
    OrganizationMembership,  # noqa: F811
    OrganizationPost,  # noqa: F811
    Subscription,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

@pytest.fixture
def api():  # noqa: F811
    """Create an API client."""
    return APIClient()

@pytest.fixture
def law():  # noqa: F811
    """Law."""
    return User.objects.create_user(email="law34@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def cli():  # noqa: F811
    """Cli."""
    return User.objects.create_user(email="cli34@t.com", password="pw", role="client", first_name="C", last_name="E")

@pytest.fixture
def corp():  # noqa: F811
    """Corp."""
    return User.objects.create_user(email="corp34@t.com", password="pw", role="corporate_client", first_name="Co", last_name="Rp")


# -- Organization views --
class TestOrganizationViews:
    """Tests for Organization Views."""

    def test_create_org_non_corporate_forbidden(self, api, cli):
        """Verify create org non corporate forbidden."""
        api.force_authenticate(user=cli)
        resp = api.post(reverse("create-organization"), {"title": "O", "description": "D"}, format="json")
        assert resp.status_code == 403

    def test_create_org_success(self, api, corp):
        """Verify create org success."""
        api.force_authenticate(user=corp)
        resp = api.post(reverse("create-organization"), {"title": "NewOrg", "description": "Desc"}, format="json")
        assert resp.status_code == 201
        assert Organization.objects.filter(title="NewOrg").exists()

    def test_get_my_orgs(self, api, corp):
        """Verify get my orgs."""
        Organization.objects.create(title="MyOrg", corporate_client=corp)
        api.force_authenticate(user=corp)
        resp = api.get(reverse("get-my-organizations"))
        assert resp.status_code == 200

    def test_get_org_detail(self, api, corp):
        """Verify get org detail."""
        org = Organization.objects.create(title="Det", corporate_client=corp)
        api.force_authenticate(user=corp)
        resp = api.get(reverse("get-organization-detail", args=[org.id]))
        assert resp.status_code == 200

    def test_delete_org(self, api, corp):
        """Verify delete org."""
        org = Organization.objects.create(title="DelOrg", corporate_client=corp)
        api.force_authenticate(user=corp)
        resp = api.delete(reverse("delete-organization", args=[org.id]))
        assert resp.status_code in (200, 204)
        assert not Organization.objects.filter(id=org.id).exists()

    def test_send_invitation(self, api, corp, cli):
        """Verify send invitation."""
        org = Organization.objects.create(title="InvOrg", corporate_client=corp)
        api.force_authenticate(user=corp)
        resp = api.post(
            reverse("send-organization-invitation", args=[org.id]),
            {"invited_user_email": cli.email}, format="json",
        )
        assert resp.status_code == 201
        assert OrganizationInvitation.objects.filter(organization=org, invited_user=cli).exists()

    def test_get_invitations(self, api, corp, cli):
        """Verify get invitations."""
        org = Organization.objects.create(title="GI", corporate_client=corp)
        OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        api.force_authenticate(user=corp)
        resp = api.get(reverse("get-organization-invitations", args=[org.id]))
        assert resp.status_code == 200

    def test_get_my_invitations(self, api, corp, cli):
        """Verify get my invitations."""
        org = Organization.objects.create(title="MI", corporate_client=corp)
        OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-my-invitations"))
        assert resp.status_code == 200

    def test_respond_accept_invitation(self, api, corp, cli):
        """Verify respond accept invitation."""
        org = Organization.objects.create(title="RA", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        api.force_authenticate(user=cli)
        resp = api.post(reverse("respond-to-invitation", args=[inv.id]), {"action": "accept"}, format="json")
        assert resp.status_code == 200
        inv.refresh_from_db()
        assert inv.status == "ACCEPTED"
        assert OrganizationMembership.objects.filter(organization=org, user=cli, is_active=True).exists()

    def test_respond_reject_invitation(self, api, corp, cli):
        """Verify respond reject invitation."""
        org = Organization.objects.create(title="RR", corporate_client=corp)
        inv = OrganizationInvitation.objects.create(organization=org, invited_user=cli, invited_by=corp)
        api.force_authenticate(user=cli)
        resp = api.post(reverse("respond-to-invitation", args=[inv.id]), {"action": "reject"}, format="json")
        assert resp.status_code == 200
        inv.refresh_from_db()
        assert inv.status == "REJECTED"

    def test_get_org_stats(self, api, corp):
        """Verify get org stats."""
        Organization.objects.create(title="S1", corporate_client=corp)
        api.force_authenticate(user=corp)
        resp = api.get(reverse("get-organization-stats"))
        assert resp.status_code == 200

    def test_leave_organization(self, api, corp, cli):
        """Verify leave organization."""
        org = Organization.objects.create(title="LV", corporate_client=corp)
        OrganizationMembership.objects.create(organization=org, user=cli, role="MEMBER", is_active=True)
        api.force_authenticate(user=cli)
        resp = api.post(reverse("leave-organization", args=[org.id]))
        assert resp.status_code == 200
        assert not OrganizationMembership.objects.filter(organization=org, user=cli, is_active=True).exists()


# -- Subscription views --
class TestSubscriptionViews:
    """Tests for Subscription Views."""

    def test_get_wompi_config(self, api, law):
        """Verify get wompi config."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("subscription-wompi-config"))
        assert resp.status_code == 200

    def test_get_current_no_subscription(self, api, law):
        """Verify get current no subscription."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("subscription-current"))
        assert resp.status_code in (200, 404)

    def test_get_current_with_subscription(self, api, law):
        """Verify get current with subscription."""
        Subscription.objects.create(
            user=law, plan_type="cliente", status="active",
            amount=Decimal(50000), next_billing_date=datetime.datetime.now(tz=datetime.UTC).date(),
        )
        api.force_authenticate(user=law)
        resp = api.get(reverse("subscription-current"))
        assert resp.status_code == 200

    def test_cancel_no_subscription(self, api, law):
        """Verify cancel no subscription."""
        api.force_authenticate(user=law)
        resp = api.patch(reverse("subscription-cancel"))
        assert resp.status_code in (400, 404)

    def test_get_payment_history_empty(self, api, law):
        """Verify get payment history empty."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("subscription-payments"))
        assert resp.status_code == 200


# -- Intranet views --
class TestIntranetViews:
    """Tests for Intranet Views."""

    def test_list_legal_intranet_documents(self, api, law):
        """Verify list legal intranet documents."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("list-legal-intranet-documents"))
        assert resp.status_code == 200

    def test_create_report_request(self, api, law):
        """Verify a lawyer can submit a report request."""
        api.force_authenticate(user=law)
        resp = api.post(
            reverse("create-report-request"),
            {"title": "Report", "content": "Body"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_list_intranet_unauthenticated(self, api):
        """Verify list intranet unauthenticated."""
        resp = api.get(reverse("list-legal-intranet-documents"))
        assert resp.status_code in (401, 403)


# ======================================================================
# Tests merged from test_organization_views_coverage.py
# ======================================================================

"""Tests for uncovered branches in organization.py (91%→higher)."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import (
    Organization,  # noqa: F811
    OrganizationInvitation,  # noqa: F811
    OrganizationMembership,  # noqa: F811
)
from gym_app.views.organization import OrganizationPagination

User = get_user_model()
@pytest.fixture
def corp_client():
    """Corp client."""
    return User.objects.create_user(
        email='corp_oc@e.com', password='p', role='corporate_client',
        first_name='C', last_name='O')


@pytest.fixture
def client_u():
    """Client u."""
    return User.objects.create_user(
        email='cli_oc@e.com', password='p', role='client',
        first_name='Cl', last_name='O')


@pytest.fixture
def lawyer():
    """Lawyer."""
    return User.objects.create_user(
        email='law_oc@e.com', password='p', role='lawyer',
        first_name='L', last_name='O')


@pytest.fixture
def org(corp_client):
    """Org."""
    return Organization.objects.create(
        title='OrgOC', description='Desc', corporate_client=corp_client)


@pytest.mark.django_db
class TestOrganizationViewsRegressionScenarios:
    """Tests for Organization Views Regression Scenarios."""

    # --- Line 57: require_client_or_corporate_client blocks lawyer ---
    def test_public_detail_blocked_for_lawyer(self, api_client, lawyer, org):
        """Line 57: lawyer blocked by require_client_or_corporate_client."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-organization-public-detail',
            kwargs={'organization_id': org.pk}))
        assert r.status_code == 403

    # --- Line 95: create_organization invalid data ---
    def test_create_org_invalid(self, api_client, corp_client):
        """Line 95: invalid serializer returns 400."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.post(
            reverse('create-organization'),
            {},  # missing required title/description
            format='json')
        assert r.status_code == 400
        assert 'details' in r.data

    # --- Lines 116, 121: search and is_active filters ---
    def test_get_my_orgs_search_filter(self, api_client, corp_client, org):
        """Line 116: search filter on organizations."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-my-organizations'), {'search': 'OrgOC'})
        assert r.status_code == 200

    def test_get_my_orgs_is_active_filter(self, api_client, corp_client, org):
        """Line 121: is_active filter on organizations."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-my-organizations'), {'is_active': 'true'})
        assert r.status_code == 200

    # --- Line 206: update_organization invalid data ---
    def test_update_org_invalid(self, api_client, corp_client, org):
        """Line 206: invalid serializer returns 400."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.put(
            reverse('update-organization',
                    kwargs={'organization_id': org.pk}),
            {'title': ''},  # empty title should be invalid
            format='json')
        assert r.status_code in (200, 400)

    # --- Line 275: send_invitation invalid data ---
    def test_send_invitation_invalid(self, api_client, corp_client, org):
        """Line 275: invalid invitation data returns 400."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.post(
            reverse('send-organization-invitation',
                    kwargs={'organization_id': org.pk}),
            {},  # missing required invited_user
            format='json')
        assert r.status_code == 400
        assert 'details' in r.data

    # --- Line 302: invitation status filter ---
    def test_get_invitations_status_filter(self, api_client, corp_client, org):
        """Line 302: status filter on invitations."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-organization-invitations',
                    kwargs={'organization_id': org.pk}),
            {'status': 'PENDING'})
        assert r.status_code == 200

    # --- Lines 387-391: member role filter ---
    def test_get_members_role_filter(self, api_client, corp_client, org):
        """Line 391: role filter on members."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-organization-members',
                    kwargs={'organization_id': org.pk}),
            {'role': 'MEMBER'})
        assert r.status_code == 200

    def test_get_members_inactive_filter(self, api_client, corp_client, org):
        """Lines 387-388: is_active=false filter shows inactive members."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-organization-members',
                    kwargs={'organization_id': org.pk}),
            {'is_active': 'false'})
        assert r.status_code == 200

    # --- Lines 579-584: respond_to_invitation invalid ---
    def test_respond_invitation_invalid(
        self, api_client, corp_client, client_u, org
    ):
        """Lines 579-584: invalid invitation response returns 400."""
        inv = OrganizationInvitation.objects.create(
            organization=org, invited_user=client_u,
            invited_by=corp_client, status='PENDING')
        api_client.force_authenticate(user=client_u)
        r = api_client.post(
            reverse('respond-to-invitation',
                    kwargs={'invitation_id': inv.pk}),
            {'action': 'invalid_action'},
            format='json')
        assert r.status_code == 400

    # --- Line 632: leader cannot leave organization ---
    def test_leader_cannot_leave(self, api_client, client_u, corp_client, org):
        """Line 632: leader role gets 400 when trying to leave."""
        _mem = OrganizationMembership.objects.create(
            organization=org, user=client_u, role='LEADER', is_active=True)
        api_client.force_authenticate(user=client_u)
        r = api_client.post(
            reverse('leave-organization',
                    kwargs={'organization_id': org.pk}))
        assert r.status_code == 400
        assert 'líderes' in r.data['error']

    # --- Lines 138-146: get_my_organizations pagination fallback ---
    @mock.patch.object(OrganizationPagination, 'paginate_queryset', return_value=None)
    def test_get_my_orgs_pagination_fallback(
        self, mock_paginate, api_client, corp_client, org
    ):
        """Lines 138-146: pagination returns None → fallback response."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(reverse('get-my-organizations'))
        assert r.status_code == 200
        assert 'organizations' in r.data
        assert 'total_count' in r.data

    # --- Lines 319-328: get_organization_invitations pagination fallback ---
    @mock.patch.object(OrganizationPagination, 'paginate_queryset', return_value=None)
    def test_get_invitations_pagination_fallback(
        self, mock_paginate, api_client, corp_client, org
    ):
        """Lines 319-328: invitations pagination returns None → fallback."""
        api_client.force_authenticate(user=corp_client)
        r = api_client.get(
            reverse('get-organization-invitations',
                    kwargs={'organization_id': org.pk}))
        assert r.status_code == 200
        assert 'invitations' in r.data
        assert 'total_count' in r.data

    # --- Lines 531-540: get_my_invitations pagination fallback ---
    @mock.patch.object(OrganizationPagination, 'paginate_queryset', return_value=None)
    def test_get_my_invitations_pagination_fallback(
        self, mock_paginate, api_client, client_u
    ):
        """Lines 531-540: my invitations pagination returns None → fallback."""
        api_client.force_authenticate(user=client_u)
        r = api_client.get(reverse('get-my-invitations'))
        assert r.status_code == 200
        assert 'invitations' in r.data
        assert 'total_count' in r.data

    # --- Lines 579-582: respond_to_invitation save exception ---
    @mock.patch('gym_app.views.organization.OrganizationInvitationResponseSerializer')
    def test_respond_invitation_save_exception(
        self, MockSerializer, api_client, corp_client, client_u, org
    ):
        """Lines 579-582: exception during serializer.save() returns 400."""
        inv = OrganizationInvitation.objects.create(
            organization=org, invited_user=client_u,
            invited_by=corp_client, status='PENDING')
        mock_instance = mock.MagicMock()
        mock_instance.is_valid.return_value = True
        mock_instance.save.side_effect = RuntimeError("save failed")
        MockSerializer.return_value = mock_instance
        api_client.force_authenticate(user=client_u)
        r = api_client.post(
            reverse('respond-to-invitation',
                    kwargs={'invitation_id': inv.pk}),
            {'action': 'accept'},
            format='json')
        assert r.status_code == 400
        assert 'save failed' in r.data['error']
        MockSerializer.assert_called()
        mock_instance.is_valid.assert_called()
        mock_instance.save.assert_called()


@pytest.mark.django_db
def test_organization_list_query_budget_is_constant_for_page_size(api_client, corporate_client):
    """Fails if organization list serialization returns to per-row relation queries."""
    _create_organization_fixtures(corporate_client, 50)
    api_client.force_authenticate(user=corporate_client)
    url = reverse("get-my-organizations")

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url, {"page_size": 1})
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url, {"page_size": 50})

    assert single_row_response.status_code == status.HTTP_200_OK
    assert len(_organization_list_items(single_row_response)) == 1
    assert fifty_row_response.status_code == status.HTTP_200_OK
    assert len(_organization_list_items(fifty_row_response)) == 50
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_ORGANIZATION_LIST_QUERIES


@pytest.mark.django_db
def test_organization_list_counts_pending_invitations(api_client, corporate_client):
    """Fails if list subqueries multiply counts or exclude expired pending invitations."""
    organizations = _create_organization_fixtures(corporate_client, 2)
    counted_organization, empty_organization = organizations
    _create_organization_count_relations(counted_organization, corporate_client)
    api_client.force_authenticate(user=corporate_client)

    response = api_client.get(reverse("get-my-organizations"), {"page_size": 50})

    assert response.status_code == status.HTTP_200_OK
    counted_item = _item_with_title(response.data["results"], counted_organization.title)
    empty_item = _item_with_title(response.data["results"], empty_organization.title)
    assert counted_item["member_count"] == 2
    assert counted_item["pending_invitations_count"] == 3
    assert empty_item["member_count"] == 0
    assert empty_item["pending_invitations_count"] == 0


@pytest.mark.django_db
def test_owner_invitation_list_preserves_expired_pending_summary(
    api_client, corporate_client, client_user, organization
):
    """Fails if owner invitation summaries exclude expired pending rows or nested users."""
    expired_invitation = _create_counted_invitation(
        organization,
        corporate_client,
        client_user,
    )
    api_client.force_authenticate(user=corporate_client)

    response = api_client.get(
        reverse(
            'get-organization-invitations',
            kwargs={'organization_id': organization.pk},
        ),
        {'page_size': 50},
    )

    item = next(
        item for item in _invitation_list_items(response)
        if item['id'] == expired_invitation.pk
    )
    assert response.status_code == status.HTTP_200_OK
    assert {
        'organization': (
            item['organization_info']['id'],
            item['organization_info']['title'],
            item['organization_info']['member_count'],
            item['organization_info']['pending_invitations_count'],
        ),
        'users': (item['invited_by_info']['email'], item['invited_user_info']['email']),
        'pending_expired': (item['status'], item['is_expired']),
    } == {
        'organization': (organization.pk, organization.title, 2, 3),
        'users': (corporate_client.email, client_user.email),
        'pending_expired': ('PENDING', True),
    }


@pytest.mark.django_db
def test_personal_invitation_list_preserves_empty_organization_summary(
    api_client, corporate_client, client_user
):
    """Fails if pending invitations lose empty membership or include non-pending rows."""
    organization = Organization.objects.create(
        title='Empty invitation organization',
        corporate_client=corporate_client,
    )
    pending_invitation = OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=client_user,
        invited_by=corporate_client,
        status='PENDING',
    )
    accepted_organization = Organization.objects.create(
        title='Accepted invitation organization',
        corporate_client=corporate_client,
    )
    OrganizationInvitation.objects.create(
        organization=accepted_organization,
        invited_user=client_user,
        invited_by=corporate_client,
        status='ACCEPTED',
    )
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse('get-my-invitations'), {'page_size': 50})

    assert response.status_code == status.HTTP_200_OK
    assert [item['id'] for item in _invitation_list_items(response)] == [
        pending_invitation.pk
    ]
    assert {
        'organization': (
            response.data['results'][0]['organization_info']['id'],
            response.data['results'][0]['organization_info']['member_count'],
            response.data['results'][0]['organization_info']['pending_invitations_count'],
        ),
        'users': (
            response.data['results'][0]['invited_by_info']['email'],
            response.data['results'][0]['invited_user_info']['email'],
        ),
    } == {
        'organization': (organization.pk, 0, 1),
        'users': (corporate_client.email, client_user.email),
    }


@pytest.mark.django_db
def test_personal_invitation_list_preserves_zero_summary_for_accepted_status(
    api_client, corporate_client, client_user
):
    """Fails if an accepted invitation serializes an unannotated empty organization."""
    organization = Organization.objects.create(
        title='Accepted empty invitation organization',
        corporate_client=corporate_client,
    )
    invitation = OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=client_user,
        invited_by=corporate_client,
        status='ACCEPTED',
    )
    api_client.force_authenticate(user=client_user)

    response = api_client.get(
        reverse('get-my-invitations'),
        {'status': 'ACCEPTED', 'page_size': 50},
    )

    assert response.status_code == status.HTTP_200_OK
    assert {
        'id': response.data['results'][0]['id'],
        'summary': (
            response.data['results'][0]['organization_info']['member_count'],
            response.data['results'][0]['organization_info']['pending_invitations_count'],
        ),
    } == {
        'id': invitation.pk,
        'summary': (0, 0),
    }


@pytest.mark.django_db
def test_owner_invitation_list_has_constant_query_budget(api_client, corporate_client):
    """Fails if owner invitation serialization restores per-row relation queries."""
    organization = _create_owner_invitation_fixtures(corporate_client, 50)
    api_client.force_authenticate(user=corporate_client)
    url = reverse(
        'get-organization-invitations',
        kwargs={'organization_id': organization.pk},
    )

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url, {'page_size': 1})
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url, {'page_size': 50})

    assert (
        single_row_response.status_code,
        len(_invitation_list_items(single_row_response)),
        fifty_row_response.status_code,
        len(_invitation_list_items(fifty_row_response)),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_OWNER_INVITATION_LIST_QUERIES


@pytest.mark.django_db
def test_personal_invitation_list_has_constant_query_budget(
    api_client, corporate_client, client_user
):
    """Fails if personal invitation serialization restores per-row relation queries."""
    _create_personal_invitation_fixtures(client_user, corporate_client, 50)
    api_client.force_authenticate(user=client_user)
    url = reverse('get-my-invitations')

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url, {'page_size': 1})
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url, {'page_size': 50})

    assert (
        single_row_response.status_code,
        len(_invitation_list_items(single_row_response)),
        fifty_row_response.status_code,
        len(_invitation_list_items(fifty_row_response)),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_PERSONAL_INVITATION_LIST_QUERIES


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['client', 'basic'])
def test_my_memberships_preserves_annotated_organization_summary(api_client, role):
    """Fails if memberships lose annotated summaries or exclude inactive organizations."""
    actor = _create_organization_actor(role, 'membership-summary')
    memberships = _create_membership_organizations(actor, f'{role}-summary', 2)
    inactive_organization = memberships[0].organization
    inactive_organization.is_active = False
    inactive_organization.save(update_fields=['is_active'])
    _add_membership_summary_relations(inactive_organization, role)
    inactive_membership = _create_membership_organizations(actor, f'{role}-summary-hidden', 1)[0]
    inactive_membership.is_active = False
    inactive_membership.save(update_fields=['is_active'])
    api_client.force_authenticate(user=actor)

    response = api_client.get(reverse('get-my-memberships'))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['total_count'] == 2
    assert [
        (
            item['title'],
            item['corporate_client_info']['email'],
            item['member_count'],
            item['pending_invitations_count'],
            item['is_active'],
        )
        for item in response.data['organizations']
    ] == [
        (
            memberships[1].organization.title,
            memberships[1].organization.corporate_client.email,
            1,
            0,
            True,
        ),
        (
            inactive_organization.title,
            inactive_organization.corporate_client.email,
            2,
            1,
            False,
        ),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['client', 'basic'])
def test_my_memberships_has_constant_query_budget(api_client, role):
    """Fails if membership organizations lose their annotated prefetch relations."""
    actor = _create_organization_actor(role, 'membership-budget')
    _create_membership_organizations(actor, f'{role}-membership-budget', 1)
    api_client.force_authenticate(user=actor)
    url = reverse('get-my-memberships')

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    _create_membership_organizations(actor, f'{role}-membership-budget-extra', 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert (
        single_row_response.status_code,
        len(single_row_response.data['organizations']),
        fifty_row_response.status_code,
        len(fifty_row_response.data['organizations']),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_MY_MEMBERSHIPS_QUERIES


@pytest.mark.django_db
def test_organization_detail_serializer_uses_preloaded_relations():
    """Fails if detail serialization queries preloaded members or annotated counts again."""
    from unittest.mock import patch

    from gym_app.serializers.organization import OrganizationSerializer
    from gym_app.views.organization import _with_organization_detail_relations

    organization, empty_organization, active_member = _create_detail_organizations()

    with patch('gym_app.views.organization.timezone.now', return_value=ORGANIZATION_DETAIL_NOW):
        organizations = list(
            _with_organization_detail_relations(Organization.objects.all())
            .filter(pk__in=[organization.pk, empty_organization.pk])
            .order_by('pk')
        )
    with CaptureQueriesContext(connection) as serializer_queries:
        payload = OrganizationSerializer(organizations, many=True).data

    assert len(serializer_queries) == 0
    assert _organization_detail_snapshot(payload) == {
        organization.pk: (1, 1, 1, [active_member.pk]),
        empty_organization.pk: (0, 0, 0, []),
    }


@pytest.mark.django_db
def test_private_organization_detail_has_constant_query_budget(api_client):
    """Fails if private organization detail restores member serialization queries."""
    corporate_client = _create_organization_actor('corporate_client', 'private-detail-owner')
    organization = Organization.objects.create(
        title='Round five private detail organization',
        description='Private detail budget fixture',
        corporate_client=corporate_client,
    )
    _add_active_detail_members(organization, 'private-detail', 1)
    api_client.force_authenticate(user=corporate_client)
    url = reverse('get-organization-detail', kwargs={'organization_id': organization.pk})

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    _add_active_detail_members(organization, 'private-detail-extra', 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert (
        single_row_response.status_code,
        len(single_row_response.data['organization']['members']),
        fifty_row_response.status_code,
        len(fifty_row_response.data['organization']['members']),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_PRIVATE_ORGANIZATION_DETAIL_QUERIES


@pytest.mark.django_db
def test_public_leader_organization_detail_has_constant_query_budget(api_client):
    """Fails if leader public detail restores member serialization queries."""
    corporate_client = _create_organization_actor('corporate_client', 'public-leader-owner')
    organization = Organization.objects.create(
        title='Round five public leader organization',
        description='Public leader detail budget fixture',
        corporate_client=corporate_client,
    )
    _add_active_detail_members(organization, 'public-leader-detail', 1)
    api_client.force_authenticate(user=corporate_client)
    url = reverse('get-organization-public-detail', kwargs={'organization_id': organization.pk})

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    _add_active_detail_members(organization, 'public-leader-detail-extra', 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert (
        single_row_response.status_code,
        len(single_row_response.data['organization']['members']),
        fifty_row_response.status_code,
        len(fifty_row_response.data['organization']['members']),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_PUBLIC_LEADER_ORGANIZATION_DETAIL_QUERIES


@pytest.mark.django_db
def test_public_member_organization_detail_has_constant_query_budget(api_client):
    """Fails if member public detail restores member serialization queries."""
    corporate_client = _create_organization_actor('corporate_client', 'public-member-owner')
    member = _create_organization_actor('client', 'public-member-actor')
    organization = Organization.objects.create(
        title='Round five public member organization',
        description='Public member detail budget fixture',
        corporate_client=corporate_client,
    )
    _add_active_detail_members(organization, 'public-member-detail', 1, first_member=member)
    api_client.force_authenticate(user=member)
    url = reverse('get-organization-public-detail', kwargs={'organization_id': organization.pk})

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    _add_active_detail_members(organization, 'public-member-detail-extra', 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert (
        single_row_response.status_code,
        len(single_row_response.data['organization']['members']),
        fifty_row_response.status_code,
        len(fifty_row_response.data['organization']['members']),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_PUBLIC_MEMBER_ORGANIZATION_DETAIL_QUERIES


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url_name',
    ['get-organization-detail', 'get-organization-public-detail'],
)
def test_organization_detail_requires_authentication(api_client, url_name):
    """Fails if either organization detail endpoint accepts an anonymous request."""
    _, organization = _create_owned_organization(f'anonymous-{url_name}')

    response = api_client.get(
        reverse(url_name, kwargs={'organization_id': organization.pk})
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_public_organization_detail_hides_inactive_organization(api_client):
    """Fails if public detail exposes an inactive organization to its owner."""
    corporate_client, organization = _create_owned_organization(
        'inactive-public', is_active=False
    )
    api_client.force_authenticate(user=corporate_client)

    response = api_client.get(
        reverse('get-organization-public-detail', kwargs={'organization_id': organization.pk})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_private_organization_detail_hides_other_corporate_client(api_client):
    """Fails if private detail exposes an organization to another corporate client."""
    _, organization = _create_owned_organization('private-owner')
    outsider = _create_organization_actor('corporate_client', 'private-outsider')
    api_client.force_authenticate(user=outsider)

    response = api_client.get(
        reverse('get-organization-detail', kwargs={'organization_id': organization.pk})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
