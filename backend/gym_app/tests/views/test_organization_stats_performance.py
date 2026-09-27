"""Performance contracts for the organization statistics endpoint."""
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from gym_app.models import (
    CorporateRequest,
    CorporateRequestType,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)

User = get_user_model()
MAX_ORGANIZATION_STATS_QUERIES = 4
STATS_NOW = datetime(2026, 9, 27, 12, tzinfo=dt_timezone.utc)


def _create_user(role, suffix):
    """Create one role-specific actor for the statistics contract."""
    return User.objects.create_user(
        email=f"organization-stats-{role}-{suffix}@example.com",
        password=None,
        role=role,
    )


def _create_organizations(corporate_client, start, count, active=True):
    """Create tenant-owned organizations outside the query capture."""
    return [
        Organization.objects.create(
            title=f"Stats organization {index}",
            description="Organization statistics budget fixture",
            corporate_client=corporate_client,
            is_active=active,
        )
        for index in range(start, start + count)
    ]


def _create_adversarial_relations(corporate_client, organization, suffix):
    """Create inclusive and exclusive time boundaries on an inactive organization."""
    included_member = _create_user("client", f"{suffix}-included")
    excluded_member = _create_user("client", f"{suffix}-excluded")
    OrganizationMembership.objects.create(
        organization=organization,
        user=included_member,
        role="MEMBER",
        is_active=True,
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=excluded_member,
        role="MEMBER",
        is_active=True,
    )
    invitation = OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=included_member,
        invited_by=corporate_client,
        status="PENDING",
        expires_at=STATS_NOW - timedelta(days=1),
    )
    OrganizationInvitation.objects.filter(pk=invitation.pk).update(
        created_at=STATS_NOW - timedelta(days=7),
    )
    old_invitation = OrganizationInvitation.objects.create(
        organization=organization,
        invited_user=excluded_member,
        invited_by=corporate_client,
        status="PENDING",
        expires_at=STATS_NOW - timedelta(days=1),
    )
    OrganizationInvitation.objects.filter(pk=old_invitation.pk).update(
        created_at=STATS_NOW - timedelta(days=7, microseconds=1),
    )
    request_type = CorporateRequestType.objects.create(name=f"Statistics request type {suffix}")
    recent_request = CorporateRequest.objects.create(
        client=included_member,
        organization=organization,
        corporate_client=corporate_client,
        request_type=request_type,
        title="Recent organization request",
        description="Request on the inclusive thirty day boundary",
        priority="MEDIUM",
        status="PENDING",
    )
    CorporateRequest.objects.filter(pk=recent_request.pk).update(
        created_at=STATS_NOW - timedelta(days=30),
    )
    old_request = CorporateRequest.objects.create(
        client=excluded_member,
        organization=organization,
        corporate_client=corporate_client,
        request_type=request_type,
        title="Old organization request",
        description="Request just before the thirty day boundary",
        priority="MEDIUM",
        status="PENDING",
    )
    CorporateRequest.objects.filter(pk=old_request.pk).update(
        created_at=STATS_NOW - timedelta(days=30, microseconds=1),
    )


@pytest.mark.django_db
def test_organization_stats_keeps_tenant_counts_with_constant_queries(api_client):
    """Fails if statistics restore separate counts or drop inactive pending records."""
    corporate_client = _create_user("corporate_client", "owner")
    _create_organizations(corporate_client, 0, 1)
    api_client.force_authenticate(user=corporate_client)
    url = reverse("get-organization-stats")

    with patch("gym_app.views.organization.timezone.now", return_value=STATS_NOW):
        with CaptureQueriesContext(connection) as one_organization_queries:
            one_organization_response = api_client.get(url)
        _create_organizations(corporate_client, 1, 48)
        inactive_organization = _create_organizations(corporate_client, 49, 1, active=False)[0]
        _create_adversarial_relations(corporate_client, inactive_organization, "owner")
        with CaptureQueriesContext(connection) as fifty_organization_queries:
            fifty_organization_response = api_client.get(url)

    assert one_organization_response.status_code == status.HTTP_200_OK
    assert one_organization_response.data["total_organizations"] == 1
    assert fifty_organization_response.status_code == status.HTTP_200_OK
    assert fifty_organization_response.data == {
        "total_organizations": 50,
        "total_members": 2,
        "total_pending_invitations": 2,
        "recent_requests_count": 1,
        "active_organizations_count": 49,
        "organizations_by_status": {"active": 49, "inactive": 1},
        "recent_invitations_count": 1,
    }
    assert len(one_organization_queries) == len(fifty_organization_queries)
    assert len(fifty_organization_queries) <= MAX_ORGANIZATION_STATS_QUERIES


@pytest.mark.django_db
def test_organization_stats_returns_zero_counts_for_empty_tenant(api_client):
    """Fails if an empty tenant receives nulls or rows from another organization owner."""
    corporate_client = _create_user("corporate_client", "empty")
    other_corporate_client = _create_user("corporate_client", "other-tenant")
    other_organization = _create_organizations(other_corporate_client, 0, 1, active=False)[0]
    _create_adversarial_relations(other_corporate_client, other_organization, "other-tenant")
    api_client.force_authenticate(user=corporate_client)

    response = api_client.get(reverse("get-organization-stats"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "total_organizations": 0,
        "total_members": 0,
        "total_pending_invitations": 0,
        "recent_requests_count": 0,
        "active_organizations_count": 0,
        "organizations_by_status": {"active": 0, "inactive": 0},
        "recent_invitations_count": 0,
    }
