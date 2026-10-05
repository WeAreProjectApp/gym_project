"""Query-growth regressions for document-folder payloads."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from gym_app.models import (
    DocumentFolder,
    DocumentPaymentRecord,
    DocumentRelationship,
    DocumentSignature,
    DocumentUsabilityPermission,
    DocumentVariable,
    DocumentVisibilityPermission,
    DynamicDocument,
    Tag,
)
from gym_app.serializers.dynamic_document import DocumentFolderSerializer
from gym_app.views.dynamic_documents.tag_folder_views import _folder_queryset

User = get_user_model()


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    """Keep nested document uploads inside pytest's disposable directory."""
    settings.MEDIA_ROOT = str(tmp_path)


def _document_with_nested_relations(owner, lawyer, number):
    creator = User.objects.create(email=f"creator-{number}@test.local", first_name="Creator", last_name=str(number))
    assignee = User.objects.create(email=f"assignee-{number}@test.local", first_name="Assignee", last_name=str(number))
    signer = User.objects.create(email=f"signer-{number}@test.local", first_name="Signer", last_name=str(number))
    tag_creator = User.objects.create(email=f"tagger-{number}@test.local")
    uploader = User.objects.create(email=f"uploader-{number}@test.local")
    document = DynamicDocument.objects.create(
        title=f"Nested {number}", content=f"<p>Nested {number}</p>", state="FullySigned",
        fully_signed=True, created_by=creator, assigned_to=assignee, managed_by=lawyer,
        requires_signature=True,
    )
    tag = Tag.objects.create(name=f"tag-{number}", color_id=number % 6, created_by=tag_creator)
    document.tags.add(tag)
    DocumentVariable.objects.create(
        document=document, name_es=f"Variable {number}", value="1",
        field_type="number", summary_field="payment_installments",
    )
    DocumentSignature.objects.create(document=document, signer=signer)
    DocumentVisibilityPermission.objects.create(document=document, user=owner, granted_by=lawyer)
    DocumentUsabilityPermission.objects.create(document=document, user=owner, granted_by=lawyer)
    DocumentPaymentRecord.objects.create(
        document=document, installment_number=1,
        file=SimpleUploadedFile(f"record-{number}.pdf", b"record", content_type="application/pdf"),
        original_name=f"record-{number}.pdf", uploaded_by=uploader,
    )
    target = DynamicDocument.objects.create(title=f"Target {number}", content="<p>Target</p>", created_by=creator)
    DocumentRelationship.objects.create(source_document=document, target_document=target, created_by=creator)
    return document


def _add_folders(owner, lawyer, start, stop, target=None):
    for number in range(start, stop + 1):
        folder = target or DocumentFolder.objects.create(name=f"Folder {number}", color_id=number % 6, owner=owner)
        folder.documents.add(_document_with_nested_relations(owner, lawyer, number))


def _get_with_query_count(api_client, url):
    with CaptureQueriesContext(connection) as captured:
        response = api_client.get(url)
    return response, len(captured)


@pytest.mark.django_db
def test_folder_list_keeps_nested_documents_at_constant_query_cost(api_client, client_user, lawyer_user, record_property):
    """Fails if folder list stops applying the nested document query plan."""
    _add_folders(client_user, lawyer_user, 1, 1)
    api_client.force_authenticate(user=client_user)
    url = reverse("list-folders")

    one_response, one_count = _get_with_query_count(api_client, url)
    _add_folders(client_user, lawyer_user, 2, 50)
    fifty_response, fifty_count = _get_with_query_count(api_client, url)

    expected_ids = list(DocumentFolder.objects.filter(owner=client_user).order_by("-created_at").values_list("id", flat=True))
    retained = next(folder for folder in fifty_response.data if folder["name"] == "Folder 1")
    seed = DynamicDocument.objects.get(title="Nested 1")
    document = retained["documents"][0]
    record_property("queries_one", one_count)
    record_property("queries_fifty", fifty_count)
    assert (one_response.status_code, fifty_response.status_code) == (200, 200)
    assert one_count == fifty_count
    assert [folder["id"] for folder in fifty_response.data] == expected_ids
    assert (
        document["title"], document["content"], document["created_by_name"], document["assigned_to"],
        document["signatures"][0]["signer_name"], document["tags"][0]["name"],
        document["tags"][0]["created_by"], document["relationships_count"],
        document["payments_summary"]["in_review"], document["user_permission_level"],
        document["can_view"], document["can_edit"], document["can_delete"],
    ) == ("Nested 1", "<p>Nested 1</p>", "Creator 1", seed.assigned_to_id, "Signer 1", "tag-1",
          User.objects.get(email="tagger-1@test.local").id, 1, True, None, False, False, False)


@pytest.mark.django_db
def test_folder_detail_keeps_nested_documents_at_constant_query_cost(api_client, client_user, lawyer_user, record_property):
    """Fails if folder detail serializes one query per related document."""
    folder = DocumentFolder.objects.create(name="Detail", color_id=1, owner=client_user)
    _add_folders(client_user, lawyer_user, 1, 1, target=folder)
    api_client.force_authenticate(user=client_user)
    url = reverse("get-folder", kwargs={"pk": folder.pk})

    one_response, one_count = _get_with_query_count(api_client, url)
    _add_folders(client_user, lawyer_user, 2, 50, target=folder)
    fifty_response, fifty_count = _get_with_query_count(api_client, url)

    record_property("queries_one", one_count)
    record_property("queries_fifty", fifty_count)
    assert (one_response.status_code, fifty_response.status_code) == (200, 200)
    assert one_count == fifty_count
    assert len(fifty_response.data["documents"]) == 50
    assert fifty_response.data["documents"][0]["variables"][0]["name_es"] == "Variable 1"


@pytest.mark.django_db
def test_prefetched_folder_serializer_emits_no_sql(client_user, lawyer_user, record_property):
    """Fails if the folder serializer reaches the database after its query plan loads."""
    folder = DocumentFolder.objects.create(name="Serialized", color_id=2, owner=client_user)
    _add_folders(client_user, lawyer_user, 1, 2, target=folder)
    loaded = _folder_queryset().get(pk=folder.pk)

    with CaptureQueriesContext(connection) as captured:
        data = DocumentFolderSerializer(loaded).data

    record_property("serialization_queries", len(captured))
    assert len(captured) == 0
    assert [document["title"] for document in data["documents"]] == ["Nested 1", "Nested 2"]


@pytest.mark.django_db
def test_folder_detail_denies_non_owner_before_document_prefetch(api_client, client_user, lawyer_user):
    """Fails if a denied folder request loads documents after the owner check."""
    folder = DocumentFolder.objects.create(name="Private", color_id=3, owner=client_user)
    _add_folders(client_user, lawyer_user, 1, 1, target=folder)
    other = User.objects.create_user(email="other-folder@test.local", password="pass", role="client")
    api_client.force_authenticate(user=other)

    with CaptureQueriesContext(connection) as captured:
        response = api_client.get(reverse("get-folder", kwargs={"pk": folder.pk}))

    assert response.status_code == 403
    assert not any("gym_app_dynamicdocument" in query["sql"].lower() for query in captured.captured_queries)
