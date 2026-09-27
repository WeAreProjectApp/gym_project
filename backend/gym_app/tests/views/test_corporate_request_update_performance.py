"""Performance and access contracts for corporate request updates."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from gym_app.models import (
    CorporateRequest,
    CorporateRequestFiles,
    CorporateRequestResponse,
    CorporateRequestType,
    Organization,
    OrganizationMembership,
)

User = get_user_model()
MAX_CORPORATE_REQUEST_UPDATE_QUERIES = 8


def _create_user(role, suffix):
    """Create one actor with a unique identity for an update contract."""
    return User.objects.create_user(
        email=f"corporate-update-{role}-{suffix}@example.com",
        password=None,
        role=role,
        first_name="Update",
        last_name=suffix,
    )


def _create_request(corporate_client, client, suffix):
    """Create a request whose model validation requires an active membership."""
    organization = Organization.objects.create(
        title=f"Update organization {suffix}",
        description="Corporate request update budget fixture",
        corporate_client=corporate_client,
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=client,
        role="MEMBER",
        is_active=True,
    )
    request_type = CorporateRequestType.objects.create(name=f"Update type {suffix}")
    return CorporateRequest.objects.create(
        client=client,
        corporate_client=corporate_client,
        organization=organization,
        request_type=request_type,
        title="Assignment update",
        description="Response serialization fixture",
        priority="MEDIUM",
        status="PENDING",
    )


def _add_responses(corporate_request, start, count, response_file):
    """Add distinct response authors so relation caches cannot hide N plus one queries."""
    responses = []
    for index in range(start, start + count):
        author = _create_user("client", f"response-{index}")
        response = CorporateRequestResponse.objects.create(
            corporate_request=corporate_request,
            response_text=f"Response text {index}",
            user=author,
            user_type="client",
        )
        responses.append(response)
    responses[0].response_files.add(response_file)
    return responses


@pytest.mark.django_db
def test_corporate_request_update_keeps_detail_queries_constant(api_client, settings, tmp_path):
    """Fails if update serialization restores per-response author or attachment queries."""
    settings.MEDIA_ROOT = tmp_path
    corporate_client = _create_user("corporate_client", "owner")
    client = _create_user("client", "requester")
    assignee = _create_user("lawyer", "assignee")
    corporate_request = _create_request(corporate_client, client, "budget")
    response_file = CorporateRequestFiles.objects.create(
        file=SimpleUploadedFile("update-response.txt", b"response attachment"),
    )
    _add_responses(corporate_request, 0, 1, response_file)
    api_client.force_authenticate(user=corporate_client)
    url = reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk})

    with CaptureQueriesContext(connection) as one_response_queries:
        one_response = api_client.put(url, {"assigned_to": assignee.pk}, format="json")
    _add_responses(corporate_request, 1, 49, response_file)
    with CaptureQueriesContext(connection) as fifty_response_queries:
        fifty_response = api_client.put(url, {"assigned_to": assignee.pk}, format="json")

    assert one_response.status_code == status.HTTP_200_OK
    assert one_response.data["corporate_request"]["response_count"] == 1
    assert (
        one_response.data["corporate_request"]["responses"][0]["user_email"],
        one_response.data["corporate_request"]["responses"][0]["response_files"][0]["file_name"],
    ) == ("corporate-update-client-response-0@example.com", "update-response.txt")
    assert fifty_response.status_code == status.HTTP_200_OK
    assert fifty_response.data["corporate_request"]["response_count"] == 50
    assert len(one_response_queries) == len(fifty_response_queries)
    assert len(fifty_response_queries) <= MAX_CORPORATE_REQUEST_UPDATE_QUERIES


@pytest.mark.django_db
def test_corporate_request_update_returns_empty_detail_relations(api_client):
    """Fails if an update of a request without responses serializes nullable relations incorrectly."""
    corporate_client = _create_user("corporate_client", "empty")
    client = _create_user("client", "empty-requester")
    assignee = _create_user("lawyer", "empty-assignee")
    corporate_request = _create_request(corporate_client, client, "empty")
    api_client.force_authenticate(user=corporate_client)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"assigned_to": assignee.pk},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["corporate_request"]["responses"] == []
    assert response.data["corporate_request"]["response_count"] == 0


@pytest.mark.django_db
def test_corporate_request_update_clears_assignment(api_client):
    """Fails if a corporate user cannot remove an existing request assignment."""
    corporate_client = _create_user("corporate_client", "clear-owner")
    client = _create_user("client", "clear-requester")
    assignee = _create_user("lawyer", "clear-assignee")
    corporate_request = _create_request(corporate_client, client, "clear")
    corporate_request.assigned_to = assignee
    corporate_request.save()
    api_client.force_authenticate(user=corporate_client)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"assigned_to": None},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["corporate_request"]["assigned_to_info"] is None
    corporate_request.refresh_from_db()
    assert corporate_request.assigned_to is None


@pytest.mark.django_db
def test_corporate_request_update_replaces_existing_assignment(api_client):
    """Fails if a second assignment does not persist the newly selected handler."""
    corporate_client = _create_user("corporate_client", "replace-owner")
    client = _create_user("client", "replace-requester")
    first_assignee = _create_user("lawyer", "first-assignee")
    second_assignee = _create_user("lawyer", "second-assignee")
    corporate_request = _create_request(corporate_client, client, "replace")
    corporate_request.assigned_to = first_assignee
    corporate_request.save()
    api_client.force_authenticate(user=corporate_client)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"assigned_to": second_assignee.pk},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["corporate_request"]["assigned_to_info"]["id"] == second_assignee.pk
    corporate_request.refresh_from_db()
    assert corporate_request.assigned_to_id == second_assignee.pk


@pytest.mark.django_db
def test_corporate_request_update_hides_other_tenant(api_client):
    """Fails if a corporate tenant can update another tenant's request."""
    owner = _create_user("corporate_client", "owner-tenant")
    client = _create_user("client", "tenant-requester")
    corporate_request = _create_request(owner, client, "tenant")
    outsider = _create_user("corporate_client", "outsider-tenant")
    api_client.force_authenticate(user=outsider)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"status": "RESPONDED"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_corporate_request_update_rejects_invalid_status(api_client):
    """Fails if an invalid status changes the request after serializer validation fails."""
    corporate_client = _create_user("corporate_client", "invalid-owner")
    client = _create_user("client", "invalid-requester")
    corporate_request = _create_request(corporate_client, client, "invalid")
    api_client.force_authenticate(user=corporate_client)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"status": "NOT_A_STATUS"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "status" in response.data["details"]
    corporate_request.refresh_from_db()
    assert corporate_request.status == "PENDING"


@pytest.mark.django_db
def test_corporate_request_update_rejects_client_role(api_client):
    """Fails if a normal client can change corporate request management fields."""
    corporate_client = _create_user("corporate_client", "permission-owner")
    client = _create_user("client", "permission-requester")
    corporate_request = _create_request(corporate_client, client, "permission")
    api_client.force_authenticate(user=client)

    response = api_client.put(
        reverse("corporate-update-request-status", kwargs={"request_id": corporate_request.pk}),
        {"status": "RESPONDED"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
