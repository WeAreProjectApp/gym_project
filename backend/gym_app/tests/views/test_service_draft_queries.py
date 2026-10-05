"""Query-growth regressions for service-request draft serialization."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from gym_app.models import (
    Service,
    ServiceField,
    ServiceRequest,
    ServiceRequestAnswer,
    ServiceRequestFieldFile,
    ServiceRequestLawyerResponse,
    ServiceRequestLawyerResponseFile,
    ServiceStage,
)
from gym_app.serializers.service_tramite import ServiceRequestDetailSerializer
from gym_app.views.service_tramite import _request_queryset

User = get_user_model()


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    """Keep service-request attachments inside pytest's disposable directory."""
    settings.MEDIA_ROOT = str(tmp_path)


def _service_with_stage():
    service = Service.objects.create(
        name="Consulted service", short_title="Consulted", slug="consulted-service",
        description="Query regression service", is_active=True,
    )
    stage = ServiceStage.objects.create(service=service, title="Data", order=1)
    return service, stage


def _add_draft_relations(draft, stage, start, stop):
    for number in range(start, stop + 1):
        field = ServiceField.objects.create(
            stage=stage, key=f"field-{number}", label=f"Field {number}",
            field_type="file", order=number,
        )
        ServiceRequestAnswer.objects.create(
            service_request=draft, field=field, field_key=field.key,
            field_label=field.label, field_type=field.field_type,
            stage_title=stage.title, stage_order=stage.order, value_text=f"value {number}",
        )
        ServiceRequestFieldFile.objects.create(
            service_request=draft, field=field,
            file=SimpleUploadedFile(f"field-{number}.pdf", b"field", content_type="application/pdf"),
            original_name=f"field-{number}.pdf",
        )
        responder = None if number == 1 else User.objects.create_user(
            email=f"responder-{number}@test.local", password="pass",
        )
        response = ServiceRequestLawyerResponse.objects.create(
            service_request=draft, responder=responder, message=f"reply {number}",
            status_before="DRAFT", status_after="IN_STUDY",
        )
        ServiceRequestLawyerResponseFile.objects.create(
            response=response,
            file=SimpleUploadedFile(f"reply-{number}.pdf", b"reply", content_type="application/pdf"),
            original_name=f"reply-{number}.pdf",
        )


def _service_detail_url(service):
    return reverse("services-detail", kwargs={"service_id": service.pk})


def _latest_draft_url(service):
    return reverse("service-request-draft", kwargs={"service_id": service.pk})


def _get_with_query_count(api_client, url):
    with CaptureQueriesContext(connection) as captured:
        response = api_client.get(url)
    return response, len(captured)


def _answer_file_pairs(payload):
    return [(answer["field_key"], [file["file_name"] for file in answer["files"]]) for answer in payload["answers"]]


def _expected_answer_file_pairs(stop):
    return [(f"field-{number}", [f"field-{number}.pdf"]) for number in range(1, stop + 1)]


@pytest.mark.django_db
@pytest.mark.parametrize("url_builder", [_service_detail_url, _latest_draft_url])
def test_draft_endpoint_keeps_related_payload_at_constant_query_cost(api_client, client_user, url_builder, record_property):
    """Fails if a draft endpoint bypasses the preloaded request queryset."""
    service, stage = _service_with_stage()
    other = User.objects.create_user(email="other-draft@test.local", password="pass")
    ServiceRequest.objects.create(service=service, requester=client_user, is_submitted=False)
    ServiceRequest.objects.create(service=service, requester=client_user, status="OPEN", is_submitted=True)
    ServiceRequest.objects.create(service=service, requester=other, is_submitted=False)
    draft = ServiceRequest.objects.create(service=service, requester=client_user, is_submitted=False)
    _add_draft_relations(draft, stage, 1, 1)
    api_client.force_authenticate(user=client_user)

    one_response, one_count = _get_with_query_count(api_client, url_builder(service))
    _add_draft_relations(draft, stage, 2, 50)
    fifty_response, fifty_count = _get_with_query_count(api_client, url_builder(service))

    payload = fifty_response.data["draft"]
    first_answer = payload["answers"][0]
    first_response = payload["lawyer_responses"][0]
    last_response = payload["lawyer_responses"][-1]
    record_property("queries_one", one_count)
    record_property("queries_fifty", fifty_count)
    assert (one_response.status_code, fifty_response.status_code) == (200, 200)
    assert one_count == fifty_count
    assert _answer_file_pairs(payload) == _expected_answer_file_pairs(50)
    assert (
        payload["id"], first_answer["value_text"], first_answer["files"][0]["file_name"],
        first_answer["files"][0]["download_url"].endswith(f"/field-files/{first_answer['files'][0]['id']}/download/"),
        first_response["responder_name"], first_response["message"], first_response["status_before"],
        first_response["status_after"], first_response["files"][0]["file_name"],
        first_response["files"][0]["download_url"].endswith(f"/responses/{first_response['id']}/files/{first_response['files'][0]['id']}/download/"),
        last_response["responder_name"],
    ) == (draft.id, "value 1", "field-1.pdf", True, "", "reply 1", "DRAFT", "IN_STUDY",
          "reply-1.pdf", True, "responder-50@test.local")


@pytest.mark.django_db
def test_prefetched_draft_serializer_emits_no_sql(client_user, rf, record_property):
    """Fails if the draft serializer queries relations after the request plan loads."""
    service, stage = _service_with_stage()
    draft = ServiceRequest.objects.create(service=service, requester=client_user, is_submitted=False)
    _add_draft_relations(draft, stage, 1, 2)
    request = rf.get("/")
    request.user = client_user
    loaded = _request_queryset().get(pk=draft.pk)

    with CaptureQueriesContext(connection) as captured:
        data = ServiceRequestDetailSerializer(loaded, context={"request": request}).data

    record_property("serialization_queries", len(captured))
    assert len(captured) == 0
    assert [answer["field_key"] for answer in data["answers"]] == ["field-1", "field-2"]
    assert data["lawyer_responses"][0]["responder_name"] == ""
