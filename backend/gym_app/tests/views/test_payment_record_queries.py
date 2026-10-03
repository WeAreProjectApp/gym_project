"""Query-growth regressions for payment-record serialization."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from gym_app.models import DocumentPaymentRecord, DocumentVariable, DynamicDocument

User = get_user_model()


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    """Keep payment-record uploads inside pytest's disposable directory."""
    settings.MEDIA_ROOT = str(tmp_path)


def _payment_document(lawyer, client):
    document = DynamicDocument.objects.create(
        title="Cuotas consultadas", content="<p>Contrato</p>", state="FullySigned",
        fully_signed=True, created_by=lawyer, assigned_to=client,
    )
    DocumentVariable.objects.create(
        document=document, name_es="Cuotas", field_type="number",
        summary_field="payment_installments", value="51",
    )
    return document


def _add_records(document, start, stop):
    users = [
        User.objects.create_user(
            email=f"uploader-{number}@test.local", password="pass",
            first_name="Named" if number == 2 else "",
            last_name="Uploader" if number == 2 else "",
        )
        for number in range(start, stop + 1)
    ]
    for number, uploader in zip(range(start, stop + 1), users):
        DocumentPaymentRecord.objects.create(
            document=document, installment_number=number,
            file=SimpleUploadedFile(f"receipt-{number}.pdf", b"receipt", content_type="application/pdf"),
            original_name=f"receipt-{number}.pdf", amount=Decimal(f"{number}.25"),
            notes=f"note {number}", status=DocumentPaymentRecord.STATUS_UPLOADED,
            uploaded_by=uploader if number > 1 else None,
        )


def _request_with_query_count(api_client, document):
    url = reverse("list-payment-records", kwargs={"pk": document.pk})
    with CaptureQueriesContext(connection) as captured:
        response = api_client.get(url)
    return response, len(captured)


@pytest.mark.django_db
def test_payment_record_list_keeps_record_payload_at_constant_query_cost(api_client, lawyer_user, client_user, record_property):
    """Fails if payment records stop preloading their uploader during list serialization."""
    document = _payment_document(lawyer_user, client_user)
    _add_records(document, 1, 1)
    api_client.force_authenticate(user=client_user)

    one_response, one_count = _request_with_query_count(api_client, document)
    _add_records(document, 2, 50)
    stored_last = DocumentPaymentRecord.objects.get(document=document, installment_number=50)
    fifty_response, fifty_count = _request_with_query_count(api_client, document)

    first_record = one_response.data["slots"][0]["record"]
    last_record = fifty_response.data["slots"][49]["record"]
    record_property("queries_one", one_count)
    record_property("queries_fifty", fifty_count)
    assert one_response.status_code == 200
    assert fifty_response.status_code == 200
    assert one_count == fifty_count
    assert fifty_count <= 6
    assert (
        first_record["uploaded_by_name"],
        fifty_response.data["slots"][1]["record"]["uploaded_by_name"],
        fifty_response.data["slots"][50]["status"],
    ) == (None, "Named Uploader", "pending")
    assert last_record == {
        "id": stored_last.id, "installment_number": 50, "status": "uploaded",
        "amount": "50.25", "notes": "note 50", "original_name": "receipt-50.pdf",
        "rejection_reason": None,
        "uploaded_at": stored_last.uploaded_at.isoformat().replace("+00:00", "Z"),
        "uploaded_by_name": "uploader-50@test.local",
    }
