"""Query and external-email failure contracts for legal-request status updates."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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
MAX_LEGAL_REQUEST_STATUS_UPDATE_QUERIES = 8
RESPONSE_START = datetime(2026, 9, 27, 9, tzinfo=timezone.utc)


def _create_user(role, suffix):
    """Create a status-update actor with a unique serializer-visible name."""
    return User.objects.create_user(
        email=f"legal-status-{role}-{suffix}@example.com",
        password=None,
        first_name="Status",
        last_name=suffix,
        role=role,
    )


def _create_legal_request(client, suffix):
    """Create a request with the related FKs read by its notification helper."""
    request_type = LegalRequestType.objects.create(name=f"Status type {suffix}")
    discipline = LegalDiscipline.objects.create(name=f"Status discipline {suffix}")
    return LegalRequest.objects.create(
        user=client,
        request_type=request_type,
        discipline=discipline,
        description="Status update performance fixture",
    )


def _create_responses(legal_request, start, count):
    """Create chronologically stable, separately-authored response fixtures."""
    specs = []
    for index in range(start, start + count):
        author = _create_user("lawyer", f"response-{index}")
        text = f"Chronological response {index}"
        response = LegalRequestResponse.objects.create(
            legal_request=legal_request,
            response_text=text,
            user=author,
            user_type="lawyer",
        )
        LegalRequestResponse.objects.filter(pk=response.pk).update(
            created_at=RESPONSE_START + timedelta(seconds=index),
        )
        specs.append((text, f"{author.first_name} {author.last_name}"))
    return specs


@pytest.fixture
def temporary_media_root(settings, tmp_path):
    """Scope the attached-file fixture to pytest's temporary media directory."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.mark.django_db
def test_lawyer_status_update_keeps_detail_queries_constant(api_client, temporary_media_root):
    """Fails if status responses regain per-author or per-file queries as they grow."""
    client = _create_user("client", "requester")
    lawyer = _create_user("lawyer", "updater")
    legal_request = _create_legal_request(client, "budget")
    attached_file = LegalRequestFiles.objects.create(file=SimpleUploadedFile("status-update.txt", b"status attachment"))
    legal_request.files.add(attached_file)
    one_response_specs = _create_responses(legal_request, 0, 1)
    api_client.force_authenticate(user=lawyer)
    url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.pk})

    with patch("gym_app.utils.email_notifications.send_template_email", return_value=False):
        with CaptureQueriesContext(connection) as one_response_queries:
            one_response = api_client.put(url, {"status": "IN_REVIEW"}, format="json")
        fifty_response_specs = one_response_specs + _create_responses(legal_request, 1, 49)
        with CaptureQueriesContext(connection) as fifty_response_queries:
            fifty_response = api_client.put(url, {"status": "IN_REVIEW"}, format="json")

    one_request = one_response.data["request"]
    fifty_request = fifty_response.data["request"]
    assert (one_response.status_code, one_request["status"], LegalRequest.objects.get(pk=legal_request.pk).status, one_request["files"][0]["file"]) == (status.HTTP_200_OK, "IN_REVIEW", "IN_REVIEW", attached_file.file.url)
    assert (
        [item["response_text"] for item in one_request["responses"]],
        [item["user_name"] for item in one_request["responses"]],
    ) == (
        [spec[0] for spec in one_response_specs],
        [spec[1] for spec in one_response_specs],
    )
    assert (fifty_response.status_code, fifty_request["status"], fifty_request["files"][0]["file"]) == (status.HTTP_200_OK, "IN_REVIEW", attached_file.file.url)
    assert (
        [item["response_text"] for item in fifty_request["responses"]],
        [item["user_name"] for item in fifty_request["responses"]],
    ) == (
        [spec[0] for spec in fifty_response_specs],
        [spec[1] for spec in fifty_response_specs],
    )
    assert len(one_response_queries) == len(fifty_response_queries)
    assert len(fifty_response_queries) <= MAX_LEGAL_REQUEST_STATUS_UPDATE_QUERIES


@pytest.mark.django_db
def test_status_update_survives_email_delivery_exception(api_client):
    """Fails if an external email exception rolls back a valid status update response."""
    client = _create_user("client", "email-failure")
    lawyer = _create_user("lawyer", "email-failure")
    legal_request = _create_legal_request(client, "email-failure")
    api_client.force_authenticate(user=lawyer)
    url = reverse("update-legal-request-status", kwargs={"request_id": legal_request.pk})

    with patch(
        "gym_app.utils.email_notifications.send_template_email",
        side_effect=Exception("SMTP unavailable"),
    ):
        response = api_client.put(url, {"status": "IN_REVIEW"}, format="json")

    legal_request.refresh_from_db()
    returned_request = response.data["request"]
    assert response.status_code == status.HTTP_200_OK
    assert legal_request.status == "IN_REVIEW"
    assert returned_request["status"] == "IN_REVIEW"
    assert returned_request["status_updated_at"] is not None
    assert returned_request["files"] == []
    assert returned_request["responses"] == []
