"""Query and tenant contracts for legal-request list responses."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from gym_app.models import (
    LegalDiscipline,
    LegalRequest,
    LegalRequestFiles,
    LegalRequestResponse,
    LegalRequestType,
)

User = get_user_model()
MAX_LEGAL_REQUEST_LIST_QUERIES = 1
MAX_LAWYER_LEGAL_REQUEST_LIST_QUERIES = 1


def _create_user(role, suffix):
    """Create an actor with stable list-visible identity fields."""
    return User.objects.create_user(
        email=f"legal-list-{role}-{suffix}@example.com",
        password=None,
        first_name="Legal",
        last_name=suffix,
        role=role,
    )


def _create_catalog(suffix):
    """Create the related objects traversed by the list serializer."""
    return (
        LegalRequestType.objects.create(name=f"List type {suffix}"),
        LegalDiscipline.objects.create(name=f"List discipline {suffix}"),
    )


def _create_requests(owner, request_type, discipline, start, count, prefix):
    """Create unmeasured legal requests used to compare one and fifty rows."""
    return [
        LegalRequest.objects.create(
            user=owner,
            request_type=request_type,
            discipline=discipline,
            description=f"{prefix} request {index}",
        )
        for index in range(start, start + count)
    ]


def _create_distinct_client_requests(request_type, discipline, start, count):
    """Create requests with separate owners to expose per-row user reads."""
    requests = []
    for index in range(start, start + count):
        client = _create_user("client", f"lawyer-{index}")
        requests.append(
            LegalRequest.objects.create(
                user=client,
                request_type=request_type,
                discipline=discipline,
                description=f"Lawyer list request {index}",
            )
        )
    return requests


def _add_response(legal_request, author, text):
    """Create a counted response outside the captured endpoint request."""
    LegalRequestResponse.objects.create(
        legal_request=legal_request,
        response_text=text,
        user=author,
        user_type="lawyer",
    )


def _row_identity(row):
    """Return the list fields that must survive serializer relation loading."""
    return tuple(row[field] for field in ("email", "first_name", "last_name", "response_count"))


@pytest.fixture
def temporary_media_root(settings, tmp_path):
    """Scope uploaded test files to pytest's per-test temporary directory."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.mark.django_db
def test_client_legal_request_list_keeps_owned_rows_constant(api_client, temporary_media_root):
    """Fails if list rows regain N-plus-one reads or expose another client's request."""
    client = _create_user("client", "owner")
    lawyer = _create_user("lawyer", "responder")
    foreign_client = _create_user("client", "foreign")
    request_type, discipline = _create_catalog("client")
    zero_response_request = _create_requests(client, request_type, discipline, 0, 1, "Owned")[0]
    foreign_request = _create_requests(foreign_client, request_type, discipline, 0, 1, "Foreign")[0]
    attached_file = LegalRequestFiles.objects.create(
        file=SimpleUploadedFile("list-contract.txt", b"list attachment"),
    )
    zero_response_request.files.add(attached_file)
    api_client.force_authenticate(user=client)
    url = reverse("list-legal-requests")

    with CaptureQueriesContext(connection) as one_row_queries:
        one_row_response = api_client.get(url)
    remaining_requests = _create_requests(client, request_type, discipline, 1, 49, "Owned")
    _add_response(remaining_requests[0], lawyer, "Counted response")
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    one_row_ids = {item["id"] for item in one_row_response.data["requests"]}
    fifty_row_counts = {
        item["id"]: item["response_count"] for item in fifty_row_response.data["requests"]
    }
    assert (
        one_row_response.status_code,
        one_row_response.data["count"],
        len(one_row_response.data["requests"]),
        one_row_ids,
    ) == (status.HTTP_200_OK, 1, 1, {zero_response_request.id})
    assert (
        fifty_row_response.status_code,
        fifty_row_response.data["count"],
        len(fifty_row_response.data["requests"]),
    ) == (status.HTTP_200_OK, 50, 50)
    assert foreign_request.id not in fifty_row_counts
    assert {
        zero_response_request.id: fifty_row_counts[zero_response_request.id],
        remaining_requests[0].id: fifty_row_counts[remaining_requests[0].id],
    } == {zero_response_request.id: 0, remaining_requests[0].id: 1}
    assert len(one_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_LEGAL_REQUEST_LIST_QUERIES


@pytest.mark.django_db
def test_lawyer_legal_request_list_keeps_distinct_client_fields_constant(api_client, temporary_media_root):
    """Fails if lawyer rows lose client identity, response totals, or constant query behavior."""
    lawyer = _create_user("lawyer", "list-reader")
    request_type, discipline = _create_catalog("lawyer")
    first_request = _create_distinct_client_requests(request_type, discipline, 0, 1)[0]
    first_attachment = LegalRequestFiles.objects.create(file=SimpleUploadedFile("lawyer-list.txt", b"lawyer list attachment"))
    first_request.files.add(first_attachment)
    _add_response(first_request, lawyer, "First positive response")
    api_client.force_authenticate(user=lawyer)
    url = reverse("list-legal-requests")

    with CaptureQueriesContext(connection) as one_row_queries:
        one_row_response = api_client.get(url)
    remaining_requests = _create_distinct_client_requests(request_type, discipline, 1, 49)
    _add_response(remaining_requests[0], lawyer, "Second positive response")
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    first_row = one_row_response.data["requests"][0]
    fifty_rows = {item["id"]: item for item in fifty_row_response.data["requests"]}
    first_client = first_request.user
    second_client = remaining_requests[0].user
    zero_count_client = remaining_requests[-1].user
    assert (one_row_response.status_code, one_row_response.data["count"], _row_identity(first_row)) == (
        status.HTTP_200_OK, 1, (first_client.email, first_client.first_name, first_client.last_name, 1)
    )
    assert (
        fifty_row_response.status_code,
        fifty_row_response.data["count"],
        len(fifty_rows),
    ) == (status.HTTP_200_OK, 50, 50)
    assert {
        request.pk: _row_identity(fifty_rows[request.pk])
        for request in (remaining_requests[0], remaining_requests[-1])
    } == {
        remaining_requests[0].id: (second_client.email, second_client.first_name, second_client.last_name, 1),
        remaining_requests[-1].id: (zero_count_client.email, zero_count_client.first_name, zero_count_client.last_name, 0),
    }
    assert len(one_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_LAWYER_LEGAL_REQUEST_LIST_QUERIES
