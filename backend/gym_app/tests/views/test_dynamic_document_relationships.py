"""Tests for dynamic_document_relationships module."""
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from gym_app.models import (
    DocumentPaymentRecord,
    DocumentRelationship,
    DocumentSignature,
    DocumentVariable,
    DocumentVisibilityPermission,
    DynamicDocument,
)
from gym_app.serializers.dynamic_document import DynamicDocumentSerializer

User = get_user_model()


def _picker_visible_document(user, creator, visibility):
    """Create each existing visibility route without changing the assigned-owner rule."""
    created_by = {"creator": user}.get(visibility, creator)
    document = DynamicDocument.objects.create(
        title="Visible target", content="<p>Full terms</p>", state="Completed",
        created_by=created_by, assigned_to=user, is_public=visibility == "public",
        requires_signature=True,
    )
    if visibility in {"signed", "unsigned"}:
        DocumentSignature.objects.create(document=document, signer=user, signed=visibility == "signed")
    if visibility == "permission":
        DocumentVisibilityPermission.objects.create(document=document, user=user, granted_by=creator)
    DocumentVariable.objects.create(document=document, name_es="Objeto", summary_field="object", value="Representation")
    counterpart = DynamicDocument.objects.create(title="Other", content="<p>Other</p>", created_by=creator)
    DocumentRelationship.objects.create(source_document=document, target_document=counterpart, created_by=creator)
    DocumentRelationship.objects.create(source_document=counterpart, target_document=document, created_by=creator)
    return document


def _picker_expected_payload(document, user):
    """Use the established serializer on a fresh, unannotated document instance."""
    request = RequestFactory().get("/")
    request.user = user
    original = DynamicDocument.objects.get(pk=document.pk)
    return DynamicDocumentSerializer(original, context={"request": request}).data


@pytest.mark.django_db
@pytest.mark.parametrize("visibility", ["creator", "signed", "unsigned", "permission", "public"])
def test_relationship_picker_preserves_visible_document_payload(api_client, client_user, other_user, visibility):
    """Fails if optimized selection changes visibility or any field of the established serializer."""
    source = DynamicDocument.objects.create(title="Source", content="<p>Source</p>", state="Completed", created_by=client_user)
    document = _picker_visible_document(client_user, other_user, visibility)
    expected = _picker_expected_payload(document, client_user)
    api_client.force_authenticate(user=client_user)
    response = api_client.get(reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk}))
    assert response.status_code == 200
    assert response.data == [expected]
    assert response.data[0]["summary_object"] == "Representation"
    assert response.data[0]["relationships_count"] == 2


@pytest.mark.django_db
@pytest.mark.parametrize("flag", ["1", "true", "yes", "TRUE", "Yes"])
def test_relationship_picker_preserves_formalization_states(api_client, client_user, flag):
    """Fails if a supported formalization flag loses pending or signed targets and their payment summary."""
    source = DynamicDocument.objects.create(title="Source", content="<p>Source</p>", state="PendingSignatures", created_by=client_user)
    pending = DynamicDocument.objects.create(title="Pending", content="<p>Pending</p>", state="PendingSignatures", created_by=client_user)
    signed = DynamicDocument.objects.create(title="Signed", content="<p>Signed</p>", state="FullySigned", created_by=client_user)
    DocumentVariable.objects.create(document=signed, name_es="Cuotas", summary_field="payment_installments", value="2")
    DocumentPaymentRecord.objects.create(document=signed, installment_number=1, file="picker/signed.pdf", status="accepted", amount="12.00")
    api_client.force_authenticate(user=client_user)
    url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk})
    response = api_client.get(f"{url}?allow_pending_signatures={flag}")
    rows = {row["id"]: row for row in response.data}
    assert response.status_code == 200
    assert set(rows) == {pending.pk, signed.pk}
    assert rows[signed.pk]["payments_summary"] == {
        "accepted_count": 1, "in_review": False, "next_uploadable": 2, "total_amount_accepted": "12.00",
    }


@pytest.mark.django_db
def test_relationship_picker_visible_foreign_source_keeps_owned_universe(api_client, client_user, other_user):
    """Fails if source ownership is newly required or a visible foreign target enters the picker."""
    source = DynamicDocument.objects.create(title="Foreign source", content="<p>Source</p>", state="Completed", created_by=other_user, is_public=True)
    own = DynamicDocument.objects.create(title="Own", content="<p>Own</p>", state="Completed", created_by=client_user)
    DynamicDocument.objects.create(title="Foreign public", content="<p>Other</p>", state="Completed", created_by=other_user, is_public=True)
    api_client.force_authenticate(user=client_user)
    response = api_client.get(reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk}))
    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [own.pk]


@pytest.mark.django_db
@pytest.mark.parametrize("source_visibility", ["unsigned", "permission"])
def test_relationship_picker_preserves_source_visibility(api_client, client_user, other_user, source_visibility):
    """Fails if source visibility no longer accepts an unsigned signer or explicit permission."""
    source = _picker_visible_document(client_user, other_user, source_visibility)
    own = DynamicDocument.objects.create(title="Own", content="<p>Own</p>", state="Completed", created_by=client_user)
    api_client.force_authenticate(user=client_user)
    response = api_client.get(reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk}))
    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [own.pk]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("actor_fields", "expected_status"),
    [
        ({"role": "lawyer"}, 200), ({"role": "Lawyer"}, 403),
        ({"role": "admin"}, 200), ({"role": "Admin"}, 403),
        ({"role": "client", "is_gym_lawyer": True}, 200),
        ({"role": "client", "is_staff": True}, 200),
        ({"role": "client", "is_superuser": True}, 200),
    ],
    ids=["lawyer", "legacy-lawyer", "admin", "legacy-admin", "gym-lawyer", "staff", "superuser"],
)
def test_relationship_picker_preserves_internal_source_policy(api_client, other_user, actor_fields, expected_status):
    """Fails if the performance change silently normalizes the existing document role policy."""
    actor = User.objects.create_user(email="source-policy@example.com", password=None, **actor_fields)
    source = DynamicDocument.objects.create(title="Private source", content="<p>Private</p>", created_by=other_user)
    api_client.force_authenticate(user=actor)
    response = api_client.get(reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk}))
    assert response.status_code == expected_status


@pytest.fixture
def client_user():
    """Client user."""
    return User.objects.create_user(
        email="client@example.com",
        password="testpassword",
        role="client",
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
def lawyer_user():
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.mark.django_db
@pytest.mark.integration
class TestListDocumentRelationships:
    """Tests for List Document Relationships."""

    @pytest.mark.contract
    def test_list_document_relationships_success(self, api_client, client_user):
        """Debe listar las relaciones de un documento cuando el usuario puede verlo."""
        doc1 = DynamicDocument.objects.create(
            title="Doc 1",
            content="<p>1</p>",
            state="Draft",
            created_by=client_user,
        )
        doc2 = DynamicDocument.objects.create(
            title="Doc 2",
            content="<p>2</p>",
            state="Completed",
            created_by=client_user,
        )

        _rel = DocumentRelationship.objects.create(
            source_document=doc1,
            target_document=doc2,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": doc1.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        data = response.data[0]
        assert data["source_document"] == doc1.id
        assert data["target_document"] == doc2.id
        assert data["source_document_title"] == doc1.title
        assert data["target_document_title"] == doc2.title

    @pytest.mark.edge
    def test_list_document_relationships_empty(self, api_client, client_user):
        """Verify list document relationships empty."""
        doc1 = DynamicDocument.objects.create(
            title="Doc Empty",
            content="<p>x</p>",
            state="Draft",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": doc1.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    @pytest.mark.edge
    def test_list_document_relationships_includes_target_side(self, api_client, client_user):
        """Verify list document relationships includes target side."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Draft",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": target.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        data = response.data[0]
        assert data["source_document"] == source.id
        assert data["target_document"] == target.id

    @pytest.mark.edge
    def test_list_document_relationships_forbidden_when_cannot_view(self, api_client, client_user, other_user):
        """Si el usuario no puede ver el documento, obtiene 403."""
        doc1 = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>secret</p>",
            state="Draft",
            created_by=other_user,
            is_public=False,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": doc1.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.edge
    def test_list_document_relationships_not_found(self, api_client, client_user):
        """Verify list document relationships not found."""
        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestListRelatedAndAvailableDocuments:
    """Tests for List Related And Available Documents."""

    @pytest.mark.contract
    def test_list_related_documents_returns_related_docs(self, api_client, client_user):
        """list_related_documents debe devolver documentos relacionados y filtrados por permisos."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Draft",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-related-documents", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == target.id

    @pytest.mark.edge
    def test_list_related_documents_filters_non_final_state(self, api_client, client_user):
        """Verify list related documents filters non final state."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Draft",
            content="<p>draft</p>",
            state="Draft",
            created_by=client_user,
        )
        DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-related-documents", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    @pytest.mark.edge
    def test_list_related_documents_empty(self, api_client, client_user):
        """Verify list related documents empty."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-related-documents", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    @pytest.mark.edge
    def test_list_related_documents_forbidden_when_cannot_view(self, api_client, client_user, other_user):
        """Verify list related documents forbidden when cannot view."""
        source = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>hidden</p>",
            state="Completed",
            created_by=other_user,
            is_public=False,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-related-documents", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.edge
    def test_list_related_documents_not_found(self, api_client, client_user):
        """Verify list related documents not found."""
        api_client.force_authenticate(user=client_user)
        url = reverse("list-related-documents", kwargs={"document_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.contract
    def test_list_available_documents_excludes_related(self, api_client, client_user):
        """list_available_documents excludes already related documents."""
        source = DynamicDocument.objects.create(title="Source", content="<p>src</p>", state="Completed", created_by=client_user)
        candidate_ok = DynamicDocument.objects.create(title="OK", content="<p>ok</p>", state="Completed", created_by=client_user)
        candidate_related = DynamicDocument.objects.create(title="Related", content="<p>rel</p>", state="Completed", created_by=client_user)
        DocumentRelationship.objects.create(source_document=source, target_document=candidate_related, created_by=client_user)

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = {doc["id"] for doc in response.data}
        assert candidate_ok.id in ids
        assert candidate_related.id not in ids

    @pytest.mark.edge
    def test_list_available_documents_skips_unviewable_target(self, api_client, client_user, other_user):
        """Unviewable documents assigned to the user should be skipped in results."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        candidate_visible = DynamicDocument.objects.create(
            title="Visible",
            content="<p>ok</p>",
            state="Completed",
            created_by=client_user,
        )
        candidate_unviewable = DynamicDocument.objects.create(
            title="Assigned",
            content="<p>assigned</p>",
            state="Completed",
            created_by=other_user,
            assigned_to=client_user,
            is_public=False,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = {doc["id"] for doc in response.data}
        assert candidate_visible.id in ids
        assert candidate_unviewable.id not in ids

    @pytest.mark.contract
    def test_list_available_documents_excludes_invalid_states(self, api_client, client_user):
        """list_available_documents excludes documents with invalid states."""
        source = DynamicDocument.objects.create(title="Source", content="<p>src</p>", state="Completed", created_by=client_user)
        DynamicDocument.objects.create(title="Draft", content="<p>x</p>", state="Draft", created_by=client_user)
        DynamicDocument.objects.create(title="Pending", content="<p>x</p>", state="PendingSignatures", created_by=client_user)

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        titles = {doc["title"] for doc in response.data}
        assert "Draft" not in titles
        assert "Pending" not in titles

    @pytest.mark.edge
    def test_list_available_documents_excludes_reverse_relationship(self, api_client, client_user):
        """Verify list available documents excludes reverse relationship."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        candidate = DynamicDocument.objects.create(
            title="Candidate",
            content="<p>cand</p>",
            state="Completed",
            created_by=client_user,
        )
        DocumentRelationship.objects.create(
            source_document=candidate,
            target_document=source,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = {doc["id"] for doc in response.data}
        assert candidate.id not in ids

        response = api_client.get(f"{url}?allow_pending_signatures=true")

        assert response.status_code == status.HTTP_200_OK
        ids = {doc["id"] for doc in response.data}
        assert candidate.id not in ids

    @pytest.mark.edge
    def test_list_available_documents_forbidden_when_cannot_view(self, api_client, client_user, other_user):
        """Verify list available documents forbidden when cannot view."""
        source = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>hidden</p>",
            state="Completed",
            created_by=other_user,
            is_public=False,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.edge
    def test_list_available_documents_not_found(self, api_client, client_user):
        """Verify list available documents not found."""
        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.edge
    def test_list_available_documents_empty(self, api_client, client_user):
        """Verify list available documents empty."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


@pytest.mark.django_db
@pytest.mark.integration
class TestCreateDocumentRelationship:
    """Tests for Create Document Relationship."""

    @pytest.mark.contract
    def test_create_document_relationship_success(self, api_client, client_user):
        """Verify create document relationship success."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DocumentRelationship.objects.count() == 1
        rel = DocumentRelationship.objects.first()
        assert rel.created_by == client_user

    @pytest.mark.edge
    def test_create_document_relationship_missing_payload(self, api_client, client_user):
        """Verify create document relationship missing payload."""
        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "source_document" in response.data

    @pytest.mark.edge
    def test_create_document_relationship_target_not_found(self, api_client, client_user):
        """Verify create document relationship target not found."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": 9999}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "target_document" in response.data

    @pytest.mark.edge
    def test_create_document_relationship_pending_signatures_requires_flag(self, api_client, client_user):
        """Verify create document relationship pending signatures requires flag."""
        source = DynamicDocument.objects.create(
            title="Pending",
            content="<p>pending</p>",
            state="PendingSignatures",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "pending" in response.data["detail"].lower()

    @pytest.mark.contract
    @pytest.mark.parametrize("target_state", ["Completed", "PendingSignatures", "FullySigned"])
    def test_create_document_relationship_pending_signatures_allowed_with_flag(
        self,
        api_client,
        client_user,
        target_state,
    ):
        """Verify create document relationship pending signatures allowed with flag."""
        source = DynamicDocument.objects.create(
            title="Pending",
            content="<p>pending</p>",
            state="PendingSignatures",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state=target_state,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {
            "source_document": source.id,
            "target_document": target.id,
            "allow_pending_signatures": True
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DocumentRelationship.objects.count() == 1

    @pytest.mark.edge
    def test_create_document_relationship_blocks_fully_signed_source(self, api_client, client_user):
        """Verify create document relationship blocks fully signed source."""
        source = DynamicDocument.objects.create(
            title="Signed",
            content="<p>signed</p>",
            state="FullySigned",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "fully signed" in response.data["detail"].lower()

    @pytest.mark.edge
    @pytest.mark.parametrize("target_state", ["PendingSignatures", "FullySigned"])
    def test_create_document_relationship_blocks_locked_target(self, api_client, client_user, target_state):
        """Verify create document relationship blocks locked target."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state=target_state,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "pending signatures" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_forbidden_when_cannot_view_source(self, api_client, client_user, other_user):
        """Verify create document relationship forbidden when cannot view source."""
        source = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>secret</p>",
            state="Completed",
            created_by=other_user,
            is_public=False,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "source document" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_forbidden_when_cannot_view_target(self, api_client, client_user, other_user):
        """Verify create document relationship forbidden when cannot view target."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Hidden Target",
            content="<p>hidden</p>",
            state="Completed",
            created_by=other_user,
            is_public=False,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "target document" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_forbidden_when_source_not_owned(self, api_client, client_user, other_user):
        """Verify create document relationship forbidden when source not owned."""
        source = DynamicDocument.objects.create(
            title="Public Source",
            content="<p>src</p>",
            state="Completed",
            created_by=other_user,
            is_public=True,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "own documents" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_forbidden_when_target_not_owned(self, api_client, client_user, other_user):
        """Verify create document relationship forbidden when target not owned."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Public Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=other_user,
            is_public=True,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "own documents" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_requires_final_states(self, api_client, client_user):
        """Verify create document relationship requires final states."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Draft",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "final state" in response.data["detail"]

    @pytest.mark.edge
    def test_create_document_relationship_rejects_invalid_target_state(self, api_client, client_user):
        """Verify create document relationship rejects invalid target state."""
        source = DynamicDocument.objects.create(
            title="Pending",
            content="<p>pending</p>",
            state="PendingSignatures",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Draft Target",
            content="<p>draft</p>",
            state="Draft",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {
            "source_document": source.id,
            "target_document": target.id,
            "allow_pending_signatures": True,
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "target document is in state" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_prevents_duplicates(self, api_client, client_user):
        """Verify create document relationship prevents duplicates."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_prevents_reverse_duplicate(self, api_client, client_user):
        """Verify create document relationship prevents reverse duplicate."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        DocumentRelationship.objects.create(
            source_document=target,
            target_document=source,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": target.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.data["detail"].lower()

    @pytest.mark.edge
    def test_create_document_relationship_rejects_self_relationship(self, api_client, client_user):
        """Verify create document relationship rejects self relationship."""
        source = DynamicDocument.objects.create(
            title="Self",
            content="<p>self</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        payload = {"source_document": source.id, "target_document": source.id}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be related to itself" in response.data["non_field_errors"][0].lower()


@pytest.mark.django_db
@pytest.mark.integration
class TestDeleteDocumentRelationship:
    """Tests for Delete Document Relationship."""

    @pytest.mark.contract
    def test_delete_relationship_as_creator(self, api_client, client_user):
        """Verify delete relationship as creator."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        rel = DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("delete-document-relationship", kwargs={"relationship_id": rel.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert DocumentRelationship.objects.count() == 0

    @pytest.mark.edge
    def test_delete_relationship_forbidden_for_non_creator_non_lawyer(self, api_client, client_user, other_user):
        """Verify delete relationship forbidden for non creator non lawyer."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        rel = DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=other_user)
        url = reverse("delete-document-relationship", kwargs={"relationship_id": rel.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    def test_delete_relationship_as_lawyer(self, api_client, client_user, lawyer_user):
        """Verify delete relationship as lawyer."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        rel = DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("delete-document-relationship", kwargs={"relationship_id": rel.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert DocumentRelationship.objects.count() == 0

    def test_delete_relationship_not_found(self, api_client, lawyer_user):
        """Verify delete relationship not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("delete-document-relationship", kwargs={"relationship_id": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        ("locked_state", "lock_on"),
        [("PendingSignatures", "source"), ("FullySigned", "target")]
    )
    def test_delete_relationship_blocked_for_locked_documents(
        self,
        api_client,
        client_user,
        locked_state,
        lock_on,
    ):
        """Verify delete relationship blocked for locked documents."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        rel = DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        if lock_on == "source":
            source.state = locked_state
            source.save(update_fields=["state"])
        else:
            target.state = locked_state
            target.save(update_fields=["state"])

        api_client.force_authenticate(user=client_user)
        url = reverse("delete-document-relationship", kwargs={"relationship_id": rel.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "pending signatures" in response.data["detail"].lower()
        assert DocumentRelationship.objects.filter(id=rel.id).exists()


@pytest.mark.django_db
class TestDocumentRelationshipsRest:
    """Tests for Document Relationships Rest."""

    def test_rest_list_document_relationships(self, api_client, client_user):
        """Verify rest list document relationships."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )
        DocumentRelationship.objects.create(
            source_document=source,
            target_document=target,
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("list-document-relationships", kwargs={"document_id": source.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        item = response.data[0]
        assert item["source_document"] == source.id
        assert item["target_document"] == target.id
        assert item["source_document_title"] == source.title
        assert item["target_document_title"] == target.title

    def test_rest_create_document_relationship(self, api_client, client_user):
        """Verify rest create document relationship."""
        source = DynamicDocument.objects.create(
            title="Source",
            content="<p>src</p>",
            state="Completed",
            created_by=client_user,
        )
        target = DynamicDocument.objects.create(
            title="Target",
            content="<p>tgt</p>",
            state="Completed",
            created_by=client_user,
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("create-document-relationship")
        response = api_client.post(
            url,
            {"source_document": source.id, "target_document": target.id},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["source_document_title"] == source.title
        assert response.data["target_document_title"] == target.title
        assert response.data["created_by_email"] == client_user.email
