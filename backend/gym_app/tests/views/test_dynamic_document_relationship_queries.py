"""Query budgets for the full document relationship picker response."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from gym_app.models import (
    DocumentPaymentRecord,
    DocumentRelationship,
    DocumentSignature,
    DocumentVariable,
    DynamicDocument,
    Tag,
    User,
)

MAX_RELATIONSHIP_PICKER_QUERIES = 6


def _create_picker_document(user, state, index):
    """Populate serializer relations outside query measurement."""
    creator = User.objects.create_user(
        email=f"picker-creator-{index}@example.com", password=None,
        first_name="Creator", last_name=str(index), role="client",
    )
    document = DynamicDocument.objects.create(
        title=f"Contract {index}", content="<p>Contract terms</p>", state=state,
        created_by=creator, assigned_to=user, requires_signature=True,
        fully_signed=state == "FullySigned",
    )
    DocumentVariable.objects.create(
        document=document, name_es="Objeto", summary_field="object", value="Legal advice",
    )
    DocumentVariable.objects.create(
        document=document, name_es="Cuotas", summary_field="payment_installments", value="2",
    )
    document.tags.add(Tag.objects.create(name=f"Tag {index}", created_by=creator))
    DocumentSignature.objects.create(document=document, signer=user, signed=False)
    DocumentSignature.objects.create(document=document, signer=creator, signed=True)
    counterpart = DynamicDocument.objects.create(
        title=f"Other {index}", content="<p>Other</p>", created_by=creator,
    )
    DocumentRelationship.objects.create(
        source_document=document, target_document=counterpart, created_by=creator,
    )
    DocumentRelationship.objects.create(
        source_document=counterpart, target_document=document, created_by=creator,
    )
    DocumentPaymentRecord.objects.create(
        document=document, installment_number=1, file="budget/payment.pdf",
        uploaded_by=creator, status="accepted", amount="25.50",
    )
    return document


def _create_picker_documents(user, state, start, count):
    """Expand the serializer fixture without including setup queries."""
    return [_create_picker_document(user, state, index) for index in range(start, start + count)]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("state", "query", "expected_payment"),
    [
        ("Completed", "", None),
        ("FullySigned", "?allow_pending_signatures=true", {
            "accepted_count": 1, "in_review": False, "next_uploadable": 2,
            "total_amount_accepted": "25.50",
        }),
    ],
)
def test_relationship_picker_query_budget(api_client, client_user, state, query, expected_payment, record_property):
    """Fails if a populated picker regains per-document queries or loses its payload."""
    source = DynamicDocument.objects.create(
        title="Source", content="<p>Source</p>", state="Completed", created_by=client_user,
    )
    first = _create_picker_documents(client_user, state, 0, 1)[0]
    api_client.force_authenticate(user=client_user)
    url = reverse("list-available-documents-for-relationship", kwargs={"document_id": source.pk}) + query
    api_client.get(url)

    with CaptureQueriesContext(connection) as one_queries:
        one_response = api_client.get(url)
    _create_picker_documents(client_user, state, 1, 49)
    api_client.get(url)
    with CaptureQueriesContext(connection) as fifty_queries:
        fifty_response = api_client.get(url)

    record_property("queries_one", len(one_queries))
    record_property("queries_fifty", len(fifty_queries))

    rows = {row["id"]: row for row in fifty_response.data}
    first_row = rows[first.pk]
    assert (one_response.status_code, fifty_response.status_code) == (200, 200)
    assert (len(one_response.data), len(rows)) == (1, 50)
    assert (first_row["content"], first_row["summary_object"], first_row["relationships_count"]) == (
        "<p>Contract terms</p>", "Legal advice", 2,
    )
    assert (first_row["can_view"], first_row["user_permission_level"], first_row["payments_summary"]) == (
        True, "usability", expected_payment,
    )
    assert (first_row["total_signatures"], first_row["completed_signatures"], first_row["tags"][0]["name"]) == (2, 1, "Tag 0")
    assert len(one_queries) == len(fifty_queries)
    assert len(fifty_queries) <= MAX_RELATIONSHIP_PICKER_QUERIES
