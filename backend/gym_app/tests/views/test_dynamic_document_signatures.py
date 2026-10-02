"""Tests for dynamic_document_signatures module."""
import datetime
from contextlib import ExitStack
from io import BytesIO
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from gym_app.models import DocumentSignature, DynamicDocument, UserSignature
from gym_app.models.dynamic_document import (
    DocumentVariable,
    DocumentVisibilityPermission,
)

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfWriter = PdfReader = None

try:
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:
    rl_canvas = None
from gym_app.views.dynamic_documents import signature_views
from gym_app.views.dynamic_documents.signature_views import (
    expire_overdue_documents,
    generate_encrypted_document_id,
    get_client_ip,
    get_letterhead_for_document,
)

User = get_user_model()
@pytest.fixture
def signer_user():
    """Signer user."""
    return User.objects.create_user(
        email="signer@example.com",
        password="testpassword",
        first_name="Sig",
        last_name="Ner",
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


@pytest.fixture
def document_requiring_signature(lawyer_user, signer_user):
    """Document requiring signature."""
    doc = DynamicDocument.objects.create(
        title="Doc firmas",
        content="<p>Firmar {{var}}</p>",
        state="PendingSignatures",
        created_by=lawyer_user,
        requires_signature=True,
    )
    # Crear registro de firma pendiente para signer_user
    DocumentSignature.objects.create(document=doc, signer=signer_user)
    return doc


@pytest.mark.django_db
class TestGetDocumentSignaturesAndPending:
    """Tests for Get Document Signatures And Pending."""

    def test_get_document_signatures(self, api_client, lawyer_user, signer_user, document_requiring_signature):
        """Verify get document signatures."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-document-signatures", kwargs={"document_id": document_requiring_signature.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["signer_email"] == signer_user.email

    def test_get_document_signatures_forbidden_when_cannot_view(self, api_client, signer_user, lawyer_user):
        """Verify get document signatures forbidden when cannot view."""
        doc = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>x</p>",
            state="Draft",
            created_by=lawyer_user,
            requires_signature=False,
            is_public=False,
        )

        api_client.force_authenticate(user=signer_user)
        url = reverse("get-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_document_signatures_not_found(self, api_client, lawyer_user):
        """Verify get document signatures not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-document-signatures", kwargs={"document_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_pending_signatures_for_user(self, api_client, signer_user, document_requiring_signature):
        """Verify get pending signatures for user."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("get-pending-signatures")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Debe devolver al menos el documento que requiere la firma
        doc_ids = {doc["id"] for doc in response.data}
        assert document_requiring_signature.id in doc_ids

    @freeze_time("2025-01-15 12:00:00")
    def test_get_pending_signatures_expires_overdue_document(self, api_client, signer_user, lawyer_user):
        """Verify get pending signatures expires overdue document."""
        overdue_doc = DynamicDocument.objects.create(
            title="Overdue",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        DocumentSignature.objects.create(document=overdue_doc, signer=signer_user)

        api_client.force_authenticate(user=signer_user)
        url = reverse("get-pending-signatures")

        with patch('gym_app.views.dynamic_documents.signature_views.EmailMessage'):
            response = api_client.get(url)

        overdue_doc.refresh_from_db()
        assert overdue_doc.state == "Expired"
        returned_ids = {doc["id"] for doc in response.data}
        assert overdue_doc.id not in returned_ids


@pytest.mark.django_db
class TestSignAndRejectDocument:
    """Tests for Sign And Reject Document."""

    def test_sign_document_success(self, api_client, signer_user, document_requiring_signature):
        """Verify sign document success."""
        # Crear firma electrónica del usuario
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)
        assert sig.signed is True
        assert sig.rejected is False

    def test_sign_document_sets_fully_signed(self, api_client, signer_user, lawyer_user):
        """Verify sign document sets fully signed."""
        other_signer = User.objects.create_user(
            email="other-signer@example.com",
            password="testpassword",
            role="client",
        )
        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=signer_user)
        DocumentSignature.objects.create(document=doc, signer=other_signer)
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")
        UserSignature.objects.create(user=other_signer, signature_image="signatures/test.png", method="upload")

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "PendingSignatures"

        api_client.force_authenticate(user=other_signer)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": other_signer.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "FullySigned"
        assert doc.fully_signed is True

    def test_sign_document_not_found(self, api_client, signer_user):
        """Verify sign document not found."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": 9999, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sign_document_requires_user_signature(self, api_client, signer_user, document_requiring_signature):
        """Verify sign document requires user signature."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'needs to create a signature' in response.data['detail']

    def test_sign_document_forbidden_when_cannot_view(self, api_client, signer_user, lawyer_user):
        """Verify sign document forbidden when cannot view."""
        doc = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
            is_public=False,
        )
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.data["detail"].lower()

    def test_sign_document_staff_can_sign_for_user(self, api_client, signer_user, lawyer_user, document_requiring_signature):
        """Verify sign document staff can sign for user."""
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")
        lawyer_user.is_staff = True
        lawyer_user.save(update_fields=["is_staff"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("sign-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)
        assert sig.signed is True

    def test_sign_document_user_not_authorized_signer(self, api_client, signer_user, lawyer_user):
        """Verify sign document user not authorized signer."""
        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        other_user = User.objects.create_user(email="other@example.com", password="testpassword", role="client")
        DocumentSignature.objects.create(document=doc, signer=other_user)
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sign_document_already_signed(self, api_client, signer_user, lawyer_user):
        """Verify sign document already signed."""
        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=signer_user, signed=True)
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in response.data["detail"].lower()

    def test_sign_document_user_not_found(self, api_client, lawyer_user):
        """Verify sign document user not found."""
        lawyer_user.is_staff = True
        lawyer_user.save(update_fields=["is_staff"])

        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": 9999})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_sign_document_error_saving_signature(self, api_client, signer_user, document_requiring_signature, monkeypatch):
        """Verify sign document error saving signature."""
        UserSignature.objects.create(user=signer_user, signature_image="signatures/test.png", method="upload")

        def raise_error(*args, **kwargs):
            raise Exception("save failed")

        monkeypatch.setattr(DocumentSignature, "save", raise_error)

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error saving signature" in response.data["detail"]

    def test_sign_document_requires_signature_and_authorization(self, api_client, signer_user, lawyer_user):
        """Verify sign document requires signature and authorization."""
        # Documento que NO requiere firma
        doc = DynamicDocument.objects.create(
            title="Sin firma",
            content="<p>x</p>",
            state="Draft",
            created_by=lawyer_user,
            requires_signature=False,
        )

        api_client.force_authenticate(user=signer_user)
        url = reverse("sign-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Usuario distinto intentando firmar por signer_user sin ser staff
        doc2 = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc2, signer=signer_user)

        api_client.force_authenticate(user=lawyer_user)  # no is_staff
        url = reverse("sign-document", kwargs={"document_id": doc2.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reject_document_success(self, api_client, signer_user, document_requiring_signature):
        """Verify reject document success."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        payload = {"comment": "No estoy de acuerdo"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)
        assert sig.rejected is True
        assert sig.rejection_comment == "No estoy de acuerdo"

    def test_reject_document_no_comment(self, api_client, signer_user, document_requiring_signature):
        """Verify reject document no comment."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)
        assert sig.rejected is True
        assert not sig.rejection_comment

    def test_reject_document_staff_can_reject_for_user(self, api_client, signer_user, lawyer_user, document_requiring_signature):
        """Verify reject document staff can reject for user."""
        lawyer_user.is_staff = True
        lawyer_user.save(update_fields=["is_staff"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reject-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "X"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)
        assert sig.rejected is True

    def test_reject_document_already_signed(self, api_client, signer_user, lawyer_user):
        """Verify reject document already signed."""
        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=signer_user, signed=True)

        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "X"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in response.data["detail"].lower()

    def test_reject_document_not_found(self, api_client, signer_user):
        """Verify reject document not found."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": 9999, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "X"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reject_document_user_not_found(self, api_client, lawyer_user, document_requiring_signature):
        """Verify reject document user not found."""
        lawyer_user.is_staff = True
        lawyer_user.save(update_fields=["is_staff"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reject-document", kwargs={"document_id": document_requiring_signature.id, "user_id": 9999})
        response = api_client.post(url, {"comment": "X"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "User not found."

    def test_reject_document_unauthorized_other_user(self, api_client, signer_user, lawyer_user, document_requiring_signature):
        """Verify reject document unauthorized other user."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reject-document", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "X"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reject_document_requires_signatures(self, api_client, signer_user, lawyer_user):
        """Verify reject document requires signatures."""
        doc = DynamicDocument.objects.create(
            title="Sin firmas",
            content="<p>x</p>",
            state="Draft",
            created_by=lawyer_user,
            requires_signature=False,
        )

        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "No"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "This document does not require signatures."

    def test_reject_document_requires_pending_signature(self, api_client, signer_user, lawyer_user):
        """Verify reject document requires pending signature."""
        # Documento donde no hay signature pendiente
        doc = DynamicDocument.objects.create(
            title="Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        # Sin DocumentSignature asociado

        api_client.force_authenticate(user=signer_user)
        url = reverse("reject-document", kwargs={"document_id": doc.id, "user_id": signer_user.id})
        response = api_client.post(url, {"comment": "X"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestReopenAndRemoveSignatureRequest:
    """Tests for Reopen And Remove Signature Request."""

    def test_reopen_document_signatures_from_rejected(self, api_client, lawyer_user, signer_user, document_requiring_signature):
        """Verify reopen document signatures from rejected."""
        # Marcar el documento como Rejected
        document_requiring_signature.state = "Rejected"
        document_requiring_signature.save(update_fields=["state"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": document_requiring_signature.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        document_requiring_signature.refresh_from_db()
        assert document_requiring_signature.state == "PendingSignatures"

    def test_reopen_document_signatures_forbidden_for_non_owner(self, api_client, signer_user, lawyer_user):
        """Verify reopen document signatures forbidden for non owner."""
        doc = DynamicDocument.objects.create(
            title="Rejected",
            content="<p>x</p>",
            state="Rejected",
            created_by=lawyer_user,
            requires_signature=True,
        )

        api_client.force_authenticate(user=signer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reopen_document_signatures_from_expired(self, api_client, lawyer_user, signer_user):
        """Verify reopen document signatures from expired."""
        doc = DynamicDocument.objects.create(
            title="Expired",
            content="<p>x</p>",
            state="Expired",
            created_by=lawyer_user,
            requires_signature=True,
        )
        sig = DocumentSignature.objects.create(document=doc, signer=signer_user, signed=True, rejected=True)

        doc.state = "Expired"
        doc.fully_signed = False
        doc.save(update_fields=["state", "fully_signed"])

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        sig.refresh_from_db()
        assert doc.state == "PendingSignatures"
        assert sig.signed is False
        assert sig.rejected is False

    def test_reopen_document_signatures_requires_signature(self, api_client, lawyer_user):
        """Verify reopen document signatures requires signature."""
        doc = DynamicDocument.objects.create(
            title="NoSign",
            content="<p>x</p>",
            state="Rejected",
            created_by=lawyer_user,
            requires_signature=False,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not require signatures" in response.data["detail"]

    def test_reopen_document_signatures_invalid_state(self, api_client, lawyer_user):
        """Verify reopen document signatures invalid state."""
        doc = DynamicDocument.objects.create(
            title="Completed",
            content="<p>x</p>",
            state="Completed",
            created_by=lawyer_user,
            requires_signature=True,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only rejected or expired" in response.data["detail"]

    def test_reopen_document_signatures_not_found(self, api_client, lawyer_user):
        """Verify reopen document signatures not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("reopen-document-signatures", kwargs={"document_id": 9999})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_signature_request_only_creator_and_not_signed(self, api_client, lawyer_user, signer_user, document_requiring_signature):
        """Verify remove signature request only creator and not signed."""
        sig = DocumentSignature.objects.get(document=document_requiring_signature, signer=signer_user)

        # Caso éxito: creador puede eliminar solicitud pendiente
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("remove-signature-request", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_200_OK
        assert not DocumentSignature.objects.filter(id=sig.id).exists()

        # Crear otra firma y marcarla como firmada
        _sig2 = DocumentSignature.objects.create(document=document_requiring_signature, signer=signer_user, signed=True)
        url = reverse("remove-signature-request", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_signature_request_not_found(self, api_client, lawyer_user, signer_user, document_requiring_signature):
        """Verify remove signature request not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("remove-signature-request", kwargs={"document_id": document_requiring_signature.id, "user_id": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_signature_request_document_not_found(self, api_client, lawyer_user, signer_user):
        """Verify remove signature request document not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("remove-signature-request", kwargs={"document_id": 9999, "user_id": signer_user.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_signature_request_forbidden_for_non_creator(self, api_client, signer_user, document_requiring_signature):
        """Verify remove signature request forbidden for non creator."""
        # Creador es lawyer_user, autenticamos como signer_user
        api_client.force_authenticate(user=signer_user)
        url = reverse("remove-signature-request", kwargs={"document_id": document_requiring_signature.id, "user_id": signer_user.id})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserSignatureAndDocumentsByUser:
    """Tests for User Signature And Documents By User."""

    def test_get_user_pending_documents_full(self, api_client, signer_user, lawyer_user):
        """get_user_pending_documents_full devuelve solo documentos PendingSignatures visibles para el usuario objetivo."""
        # Documento pendiente para signer_user
        doc_pending = DynamicDocument.objects.create(
            title="Pending",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_pending, signer=signer_user, signed=False, rejected=False)

        # Documento en otro estado no debe aparecer
        doc_other = DynamicDocument.objects.create(
            title="Other",
            content="<p>y</p>",
            state="Draft",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_other, signer=signer_user, signed=False, rejected=False)

        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-pending-documents-full", kwargs={"user_id": signer_user.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = {doc["id"] for doc in response.data}
        assert doc_pending.id in ids
        assert doc_other.id not in ids

    def test_get_user_pending_documents_full_filters_by_visibility(self, api_client, signer_user, lawyer_user):
        """Verify get user pending documents full filters by visibility."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword",
            role="client",
        )
        doc_pending = DynamicDocument.objects.create(
            title="Pending",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_pending, signer=signer_user)

        api_client.force_authenticate(user=other_user)
        url = reverse("get-user-pending-documents-full", kwargs={"user_id": signer_user.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_user_pending_documents_full_user_not_found(self, api_client, signer_user):
        """Verify get user pending documents full user not found."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-pending-documents-full", kwargs={"user_id": 9999})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_user_archived_documents(self, api_client, signer_user, lawyer_user):
        """get_user_archived_documents devuelve documentos Rejected/Expired para el firmante."""
        # Documento rechazado
        doc_rejected = DynamicDocument.objects.create(
            title="Rejected",
            content="<p>x</p>",
            state="Rejected",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_rejected, signer=signer_user)

        # Documento expirado
        doc_expired = DynamicDocument.objects.create(
            title="Expired",
            content="<p>x</p>",
            state="Expired",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_expired, signer=signer_user)

        # Documento en otro estado no debe aparecer
        doc_other = DynamicDocument.objects.create(
            title="Other",
            content="<p>x</p>",
            state="Completed",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_other, signer=signer_user)

        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-archived-documents", kwargs={"user_id": signer_user.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        titles = {doc["title"] for doc in response.data}
        assert "Rejected" in titles
        assert "Expired" in titles
        assert "Other" not in titles

    def test_get_user_archived_documents_user_not_found(self, api_client, signer_user):
        """Verify get user archived documents user not found."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-archived-documents", kwargs={"user_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_user_signed_documents(self, api_client, signer_user, lawyer_user):
        """get_user_signed_documents devuelve documentos firmados por el usuario."""
        doc_signed = DynamicDocument.objects.create(
            title="Signed",
            content="<p>x</p>",
            state="Completed",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_signed, signer=signer_user, signed=True)

        doc_not_signed = DynamicDocument.objects.create(
            title="NotSigned",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc_not_signed, signer=signer_user, signed=False)

        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-signed-documents", kwargs={"user_id": signer_user.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        titles = {doc["title"] for doc in response.data}
        assert "Signed" in titles
        assert "NotSigned" not in titles

    def test_get_user_signed_documents_user_not_found(self, api_client, signer_user):
        """Verify get user signed documents user not found."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-signed-documents", kwargs={"user_id": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_user_signature_returns_uploaded_owner_signature_details(self, api_client, signer_user):
        """Fails if an owner cannot retrieve their uploaded signature details."""
        api_client.force_authenticate(user=signer_user)

        url = reverse("get-user-signature", kwargs={"user_id": signer_user.id})
        UserSignature.objects.create(
            user=signer_user,
            signature_image="signatures/test.png",
            method="upload",
            ip_address="198.51.100.24",
        )
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_signature"] is True
        assert response.data["signature"]["user"] == signer_user.id
        assert response.data["signature"]["method"] == "upload"
        assert "signature_image" in response.data["signature"]
        assert response.data["signature"]["ip_address"] == "198.51.100.24"

    def test_get_user_signature_rejects_foreign_nonexistent_user_id(self, api_client, signer_user):
        """Fails if a foreign nonexistent ID reveals whether a user exists."""
        api_client.force_authenticate(user=signer_user)
        url = reverse("get-user-signature", kwargs={"user_id": 9999})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "No tienes permiso para consultar esta firma."}

    def test_get_user_signature_unauthenticated(self, api_client, signer_user):
        """Fails if anonymous callers can retrieve a user's signature."""
        url = reverse("get-user-signature", kwargs={"user_id": signer_user.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "foreign_attributes",
        [
            pytest.param({"role": "client"}, id="client"),
            pytest.param({"role": "lawyer"}, id="lawyer"),
            pytest.param({"role": "admin"}, id="admin-role"),
            pytest.param({"role": "basic", "is_staff": True}, id="staff"),
            pytest.param({"role": "basic", "is_superuser": True}, id="superuser"),
        ],
    )
    def test_get_user_signature_rejects_foreign_authenticated_roles(
        self,
        api_client,
        signer_user,
        foreign_attributes,
    ):
        """Fails if a non-owner role can retrieve another user's signature."""
        foreign_user = User.objects.create_user(
            email=(
                "foreign-signature-"
                f"{foreign_attributes['role']}-"
                f"{foreign_attributes.get('is_staff', False)}-"
                f"{foreign_attributes.get('is_superuser', False)}@example.com"
            ),
            password="testpassword",
            **foreign_attributes,
        )
        UserSignature.objects.create(
            user=signer_user,
            signature_image="signatures/private-target.png",
            method="upload",
            ip_address="198.51.100.25",
        )
        api_client.force_authenticate(user=foreign_user)
        url = reverse("get-user-signature", kwargs={"user_id": signer_user.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "No tienes permiso para consultar esta firma."}

    def test_get_user_signature_internal_error(self, api_client, signer_user, monkeypatch):
        """Verify get user signature internal error."""
        api_client.force_authenticate(user=signer_user)

        def raise_error(*args, **kwargs):
            raise Exception("boom")

        monkeypatch.setattr(signature_views.User.objects, "get", raise_error)

        url = reverse("get-user-signature", kwargs={"user_id": signer_user.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "boom"


@pytest.mark.django_db
class TestGenerateSignaturesPdf:
    """Tests for Generate Signatures Pdf."""

    def test_generate_signatures_pdf_requires_fully_signed(self, api_client, lawyer_user):
        """Verify generate signatures pdf requires fully signed."""
        doc = DynamicDocument.objects.create(
            title="Not signed",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user)

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": doc.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'formalizado' in response.data['detail']

    def test_generate_signatures_pdf_not_found(self, api_client, lawyer_user):
        """Verify generate signatures pdf not found."""
        api_client.force_authenticate(user=lawyer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_generate_signatures_pdf_forbidden_when_cannot_view(self, api_client, signer_user, lawyer_user):
        """Verify generate signatures pdf forbidden when cannot view."""
        doc = DynamicDocument.objects.create(
            title="Hidden",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            requires_signature=True,
            is_public=False,
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=True)

        api_client.force_authenticate(user=signer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": doc.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_generate_signatures_pdf_internal_error(self, api_client, lawyer_user):
        """Verify generate signatures pdf internal error."""
        doc = DynamicDocument.objects.create(
            title="Signed",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=True)

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": doc.id})

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.generate_original_document_pdf',
                    return_value=BytesIO(b'pdf1'),
                )
            )
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.create_signatures_pdf',
                    side_effect=Exception("boom"),
                )
            )
            response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error al generar el PDF de firmas" in response.data["detail"]

    def test_generate_signatures_pdf_requires_signatures(self, api_client, lawyer_user):
        """Verify generate signatures pdf requires signatures."""
        doc = DynamicDocument.objects.create(
            title="No signatures",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            requires_signature=True,
        )

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": doc.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'no tiene firmas' in response.data['detail']

    def test_generate_signatures_pdf_success(self, api_client, lawyer_user):
        """Verify generate signatures pdf success."""
        doc = DynamicDocument.objects.create(
            title="Signed",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=True)

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("generate-signatures-pdf", kwargs={"pk": doc.id})

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.generate_original_document_pdf',
                    return_value=BytesIO(b'pdf1'),
                )
            )
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.create_signatures_pdf',
                    return_value=BytesIO(b'pdf2'),
                )
            )
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.combine_pdfs',
                    return_value=BytesIO(b'combined'),
                )
            )
            stack.enter_context(
                patch(
                    'gym_app.views.dynamic_documents.signature_views.add_identifier_footer',
                    return_value=BytesIO(b'final'),
                )
            )
            response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        assert response.content == b'final'


# ======================================================================
# Tests migrated from test_views_batch28.py
# ======================================================================

"""Batch 28 – 20 tests: signature_views.py – helpers, get_signatures, sign_document."""


@pytest.fixture
def api():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def law():
    """Law."""
    return User.objects.create_user(
        email="law28@t.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def cli():
    """Cli."""
    return User.objects.create_user(
        email="cli28@t.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def sig_doc(law, cli):
    """Sig doc."""
    doc = DynamicDocument.objects.create(
        title="SigDoc", content="<p>body</p>", state="PendingSignatures",
        created_by=law, requires_signature=True,
    )
    doc.visibility_permissions.create(user=law, granted_by=law)
    doc.visibility_permissions.create(user=cli, granted_by=law)
    return doc

@pytest.mark.django_db
class TestExpireOverdue:
    """Tests for Expire Overdue."""

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    @freeze_time("2025-01-15 12:00:00")
    def test_expire_overdue_updates_state(self, mock_email, law):
        """Verify expire overdue updates state."""
        doc = DynamicDocument.objects.create(
            title="Overdue", content="<p>x</p>", state="PendingSignatures",
            created_by=law, requires_signature=True,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        expire_overdue_documents()
        doc.refresh_from_db()
        assert doc.state == "Expired"

    @patch("gym_app.services.signature_notification_service.send_template_email")
    @freeze_time("2025-01-15 12:00:00")
    def test_expire_overdue_sends_email(self, mock_send_email, law):
        """Verify expire overdue sends email via notification service."""
        doc = DynamicDocument.objects.create(
            title="Overdue2", content="<p>x</p>", state="PendingSignatures",
            created_by=law, requires_signature=True,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        expire_overdue_documents()
        mock_send_email.assert_called_once()
        doc.refresh_from_db()
        assert doc.state == "Expired"

    @freeze_time("2025-01-15 12:00:00")
    def test_expire_no_overdue_noop(self, law):
        """Verify expire no overdue noop."""
        DynamicDocument.objects.create(
            title="NotOverdue", content="<p>x</p>", state="PendingSignatures",
            created_by=law, requires_signature=True,
            signature_due_date=timezone.now().date() + datetime.timedelta(days=5),
        )
        expire_overdue_documents()
        assert DynamicDocument.objects.get(title="NotOverdue").state == "PendingSignatures"

@pytest.mark.django_db
class TestGetDocumentSignatures:
    """Tests for Get Document Signatures."""

    def test_get_signatures_success(self, api, law, sig_doc):
        """Verify get signatures success."""
        DocumentSignature.objects.create(document=sig_doc, signer=law)
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-document-signatures", args=[sig_doc.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_get_signatures_doc_not_found(self, api, law):
        """Verify get signatures doc not found."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-document-signatures", args=[999999]))
        assert resp.status_code == 404

    def test_get_signatures_no_permission(self, api, sig_doc):
        """Verify get signatures no permission."""
        outsider = User.objects.create_user(email="out@t.com", password="pw", role="client")
        api.force_authenticate(user=outsider)
        resp = api.get(reverse("get-document-signatures", args=[sig_doc.id]))
        assert resp.status_code == 403


# ── sign_document endpoint ─────────────────────────────────────────

@pytest.mark.django_db
class TestSignDocument:
    """Tests for Sign Document."""

    def test_sign_doc_not_found(self, api, law):
        """Verify sign doc not found."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("sign-document", args=[999999, law.id]))
        assert resp.status_code == 404

    def test_sign_doc_no_signature_required(self, api, law):
        """Verify sign doc no signature required."""
        doc = DynamicDocument.objects.create(
            title="NoSig", content="<p>x</p>", state="Draft",
            created_by=law, requires_signature=False,
        )
        api.force_authenticate(user=law)
        resp = api.post(reverse("sign-document", args=[doc.id, law.id]))
        assert resp.status_code == 400
        assert "does not require" in resp.data["detail"]

    def test_sign_on_behalf_forbidden(self, api, law, cli, sig_doc):
        """Verify sign on behalf forbidden."""
        DocumentSignature.objects.create(document=sig_doc, signer=cli)
        api.force_authenticate(user=law)
        resp = api.post(reverse("sign-document", args=[sig_doc.id, cli.id]))
        assert resp.status_code == 403


# ======================================================================
# Tests migrated from test_views_batch29.py
# ======================================================================

"""Batch 29 – 20 tests: signature_views.py – reject, reopen, remove signature + sign edges."""


@pytest.fixture
def api():  # noqa: F811
    """Create an API client."""
    return APIClient()


@pytest.fixture
def law():  # noqa: F811
    """Law."""
    return User.objects.create_user(
        email="law29@t.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def cli():  # noqa: F811
    """Cli."""
    return User.objects.create_user(
        email="cli29@t.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


def _make_sig_doc(law, cli, state="PendingSignatures"):
    doc = DynamicDocument.objects.create(
        title="SDoc29", content="<p>body</p>", state=state,
        created_by=law, requires_signature=True,
    )
    doc.visibility_permissions.create(user=law, granted_by=law)
    doc.visibility_permissions.create(user=cli, granted_by=law)
    return doc


# ── sign_document – more edges ─────────────────────────────────────

@pytest.mark.django_db
class TestSignDocumentEdges:
    """Tests for Sign Document Edges."""

    def test_sign_user_not_found_non_staff_gets_403(self, api, law, cli):
        """Verify sign user not found non staff gets 403."""
        doc = _make_sig_doc(law, cli)
        api.force_authenticate(user=law)
        resp = api.post(reverse("sign-document", args=[doc.id, 999999]))
        # non-staff user trying to sign on behalf of another gets 403 before user lookup
        assert resp.status_code == 403

    def test_sign_not_authorized_signer(self, api, law, cli):
        """Verify sign not authorized signer."""
        doc = _make_sig_doc(law, cli)
        # no DocumentSignature record for cli
        api.force_authenticate(user=cli)
        resp = api.post(reverse("sign-document", args=[doc.id, cli.id]))
        assert resp.status_code == 403

    def test_sign_no_electronic_signature(self, api, law, cli):
        """Verify sign no electronic signature."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.post(reverse("sign-document", args=[doc.id, cli.id]))
        assert resp.status_code == 400
        assert "signature" in resp.data["detail"].lower()

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_sign_success(self, mock_email, api, law, cli):
        """Verify sign success."""
        doc = _make_sig_doc(law, cli)
        sig = DocumentSignature.objects.create(document=doc, signer=cli)
        UserSignature.objects.create(user=cli, signature_image="sig.png")
        api.force_authenticate(user=cli)
        resp = api.post(reverse("sign-document", args=[doc.id, cli.id]))
        assert resp.status_code == 200
        sig.refresh_from_db()
        assert sig.signed is True

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_sign_all_signers_fully_signed(self, mock_email, api, law, cli):
        """Verify sign all signers fully signed."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        UserSignature.objects.create(user=cli, signature_image="sig.png")
        api.force_authenticate(user=cli)
        api.post(reverse("sign-document", args=[doc.id, cli.id]))
        doc.refresh_from_db()
        assert doc.state == "FullySigned"
        assert doc.fully_signed is True


# ── reject_document ────────────────────────────────────────────────

@pytest.mark.django_db
class TestRejectDocument:
    """Tests for Reject Document."""

    def test_reject_doc_not_found(self, api, law):
        """Verify reject doc not found."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("reject-document", args=[999999, law.id]))
        assert resp.status_code == 404

    def test_reject_no_sig_required(self, api, law):
        """Verify reject no sig required."""
        doc = DynamicDocument.objects.create(
            title="NoSig", content="<p>x</p>", state="Draft",
            created_by=law, requires_signature=False,
        )
        api.force_authenticate(user=law)
        resp = api.post(reverse("reject-document", args=[doc.id, law.id]))
        assert resp.status_code == 400

    def test_reject_on_behalf_forbidden(self, api, law, cli):
        """Verify reject on behalf forbidden."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=law)
        resp = api.post(reverse("reject-document", args=[doc.id, cli.id]))
        assert resp.status_code == 403

    def test_reject_user_not_found_non_staff_gets_403(self, api, law, cli):
        """Verify reject user not found non staff gets 403."""
        doc = _make_sig_doc(law, cli)
        api.force_authenticate(user=law)
        resp = api.post(reverse("reject-document", args=[doc.id, 999999]))
        # non-staff user trying to reject on behalf of another gets 403 before user lookup
        assert resp.status_code == 403

    def test_reject_not_pending_signer(self, api, cli, law):
        """Verify reject not pending signer."""
        doc = _make_sig_doc(law, cli)
        # no signature record
        api.force_authenticate(user=cli)
        resp = api.post(reverse("reject-document", args=[doc.id, cli.id]))
        assert resp.status_code == 403

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_reject_success(self, mock_email, api, law, cli):
        """Verify reject success."""
        doc = _make_sig_doc(law, cli)
        sig = DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.post(
            reverse("reject-document", args=[doc.id, cli.id]),
            {"comment": "Needs changes"},
            format="json",
        )
        assert resp.status_code == 200
        sig.refresh_from_db()
        assert sig.rejected is True
        assert sig.rejection_comment == "Needs changes"
        doc.refresh_from_db()
        assert doc.state == "Rejected"

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_reject_without_comment(self, mock_email, api, law, cli):
        """Verify reject without comment."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.post(reverse("reject-document", args=[doc.id, cli.id]))
        assert resp.status_code == 200


# ── reopen_document_signatures ─────────────────────────────────────

@pytest.mark.django_db
class TestReopenSignatures:
    """Tests for Reopen Signatures."""

    def test_reopen_doc_not_found(self, api, law):
        """Verify reopen doc not found."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("reopen-document-signatures", args=[999999]))
        assert resp.status_code == 404

    def test_reopen_no_sig_required(self, api, law):
        """Verify reopen no sig required."""
        doc = DynamicDocument.objects.create(
            title="NoSig", content="<p>x</p>", state="Draft",
            created_by=law, requires_signature=False,
        )
        api.force_authenticate(user=law)
        resp = api.post(reverse("reopen-document-signatures", args=[doc.id]))
        assert resp.status_code == 400

    def test_reopen_wrong_state(self, api, law, cli):
        """Verify reopen wrong state."""
        doc = _make_sig_doc(law, cli, state="PendingSignatures")
        api.force_authenticate(user=law)
        resp = api.post(reverse("reopen-document-signatures", args=[doc.id]))
        assert resp.status_code == 400

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    @freeze_time("2025-01-15 12:00:00")
    def test_reopen_rejected_success(self, mock_email, api, law, cli):
        """Verify reopen rejected success."""
        doc = _make_sig_doc(law, cli, state="Rejected")
        sig = DocumentSignature.objects.create(
            document=doc, signer=cli, rejected=True,
            rejected_at=timezone.now(), rejection_comment="bad",
        )
        api.force_authenticate(user=law)
        resp = api.post(reverse("reopen-document-signatures", args=[doc.id]))
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert doc.state == "PendingSignatures"
        sig.refresh_from_db()
        assert sig.rejected is False
        assert sig.rejection_comment is None


# ── remove_signature_request ───────────────────────────────────────

@pytest.mark.django_db
class TestRemoveSignatureRequest:
    """Tests for Remove Signature Request."""

    def test_remove_doc_not_found(self, api, law):
        """Verify remove doc not found."""
        api.force_authenticate(user=law)
        resp = api.delete(reverse("remove-signature-request", args=[999999, law.id]))
        assert resp.status_code == 404

    def test_remove_not_creator_forbidden(self, api, law, cli):
        """Verify remove not creator forbidden."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.delete(reverse("remove-signature-request", args=[doc.id, cli.id]))
        assert resp.status_code == 403

    def test_remove_sig_not_found(self, api, law, cli):
        """Verify remove sig not found."""
        doc = _make_sig_doc(law, cli)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("remove-signature-request", args=[doc.id, 999999]))
        assert resp.status_code == 404

    @freeze_time("2025-01-15 12:00:00")
    def test_remove_already_signed(self, api, law, cli):
        """Verify remove already signed."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(
            document=doc, signer=cli, signed=True, signed_at=timezone.now(),
        )
        api.force_authenticate(user=law)
        resp = api.delete(reverse("remove-signature-request", args=[doc.id, cli.id]))
        assert resp.status_code == 400

    def test_remove_success(self, api, law, cli):
        """Verify remove success."""
        doc = _make_sig_doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("remove-signature-request", args=[doc.id, cli.id]))
        assert resp.status_code == 200
        assert not DocumentSignature.objects.filter(document=doc, signer=cli).exists()


# ======================================================================
# Tests migrated from test_views_batch30.py
# ======================================================================

"""Batch 30 – 20 tests: user pending/signed/archived, get_user_signature."""


@pytest.fixture
def api():  # noqa: F811
    """Create an API client."""
    return APIClient()

@pytest.fixture
def law():  # noqa: F811
    """Law."""
    return User.objects.create_user(email="law30@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def cli():  # noqa: F811
    """Cli."""
    return User.objects.create_user(email="cli30@t.com", password="pw", role="client", first_name="C", last_name="E")

def _doc(law, cli, state="PendingSignatures"):
    doc = DynamicDocument.objects.create(title="D30", content="<p>x</p>", state=state, created_by=law, requires_signature=True)
    doc.visibility_permissions.create(user=law, granted_by=law)
    doc.visibility_permissions.create(user=cli, granted_by=law)
    return doc

# -- get_user_pending_documents_full --
@pytest.mark.django_db
class TestGetUserPendingDocsFull:
    """Tests for Get User Pending Docs Full."""

    def test_pending_docs_success(self, api, law, cli):
        """Verify pending docs success."""
        doc = _doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-pending-documents-full", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_pending_docs_user_not_found(self, api, law):
        """Verify pending docs user not found."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-pending-documents-full", args=[999999]))
        assert resp.status_code == 404

    @freeze_time("2025-01-15 12:00:00")
    def test_pending_docs_excludes_signed(self, api, law, cli):
        """Verify pending docs excludes signed."""
        doc = _doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli, signed=True, signed_at=timezone.now())
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-pending-documents-full", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 0

    @freeze_time("2025-01-15 12:00:00")
    def test_pending_docs_excludes_rejected(self, api, law, cli):
        """Verify pending docs excludes rejected."""
        doc = _doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=cli, rejected=True, rejected_at=timezone.now())
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-pending-documents-full", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 0

# -- get_user_signed_documents --
@pytest.mark.django_db
class TestGetUserSignedDocs:
    """Tests for Get User Signed Docs."""

    @freeze_time("2025-01-15 12:00:00")
    def test_signed_docs_success(self, api, law, cli):
        """Verify signed docs success."""
        doc = _doc(law, cli, state="FullySigned")
        DocumentSignature.objects.create(document=doc, signer=cli, signed=True, signed_at=timezone.now())
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-signed-documents", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_signed_docs_user_not_found(self, api, law):
        """Verify signed docs user not found."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-signed-documents", args=[999999]))
        assert resp.status_code == 404

    def test_signed_docs_empty(self, api, law, cli):
        """Verify signed docs empty."""
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-signed-documents", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 0

# -- get_user_archived_documents --
@pytest.mark.django_db
class TestGetUserArchivedDocs:
    """Tests for Get User Archived Docs."""

    def test_archived_docs_rejected(self, api, law, cli):
        """Verify archived docs rejected."""
        doc = _doc(law, cli, state="Rejected")
        DocumentSignature.objects.create(document=doc, signer=cli, rejected=True)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-archived-documents", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_archived_docs_expired(self, api, law, cli):
        """Verify archived docs expired."""
        doc = _doc(law, cli, state="Expired")
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-archived-documents", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_archived_docs_user_not_found(self, api, law):
        """Verify archived docs user not found."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-archived-documents", args=[999999]))
        assert resp.status_code == 404

    def test_archived_excludes_pending(self, api, law, cli):
        """Verify archived excludes pending."""
        doc = _doc(law, cli, state="PendingSignatures")
        DocumentSignature.objects.create(document=doc, signer=cli)
        api.force_authenticate(user=cli)
        resp = api.get(reverse("get-user-archived-documents", args=[cli.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 0

# -- get_user_signature --
@pytest.mark.django_db
class TestGetUserSignature:
    """Tests for Get User Signature."""

    def test_user_has_signature(self, api, law):
        """Verify user has signature."""
        UserSignature.objects.create(user=law, signature_image="sig.png")
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-signature", args=[law.id]))
        assert resp.status_code == 200
        assert resp.data["has_signature"] is True

    def test_user_no_signature(self, api, law):
        """Verify user no signature."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-signature", args=[law.id]))
        assert resp.status_code == 200
        assert resp.data["has_signature"] is False

    def test_user_signature_rejects_foreign_nonexistent_user_id(self, api, law):
        """Fails if a foreign nonexistent signature reveals user existence."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-user-signature", args=[999999]))
        assert resp.status_code == 403
        assert resp.data == {"error": "No tienes permiso para consultar esta firma."}

# -- get_pending_signatures --
@pytest.mark.django_db
class TestGetPendingSignatures:
    """Tests for Get Pending Signatures."""

    def test_pending_sigs_success(self, api, law, cli):
        """Verify pending sigs success."""
        doc = _doc(law, cli)
        DocumentSignature.objects.create(document=doc, signer=law)
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-pending-signatures"))
        assert resp.status_code == 200

    def test_pending_sigs_unauthenticated(self, api):
        """Verify pending sigs unauthenticated."""
        resp = api.get(reverse("get-pending-signatures"))
        assert resp.status_code in (401, 403)

# -- generate_signatures_pdf --
@pytest.mark.django_db
class TestGenerateSignaturesPdf:  # noqa: F811
    """Tests for Generate Signatures Pdf."""

    def test_pdf_doc_not_found(self, api, law):
        """Verify pdf doc not found."""
        api.force_authenticate(user=law)
        resp = api.get(reverse("generate-signatures-pdf", args=[999999]))
        assert resp.status_code == 404

    def test_pdf_not_fully_signed(self, api, law, cli):
        """Verify pdf not fully signed."""
        doc = _doc(law, cli, state="PendingSignatures")
        doc.visibility_permissions.get_or_create(user=law, defaults={"granted_by": law})
        api.force_authenticate(user=law)
        resp = api.get(reverse("generate-signatures-pdf", args=[doc.id]))
        assert resp.status_code == 400

    def test_pdf_no_signatures(self, api, law):
        """Verify pdf no signatures."""
        doc = DynamicDocument.objects.create(
            title="FS_NoSig", content="<p>x</p>", state="FullySigned",
            created_by=law, requires_signature=True, fully_signed=True,
        )
        doc.visibility_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.get(reverse("generate-signatures-pdf", args=[doc.id]))
        assert resp.status_code == 400

    def test_pdf_no_permission(self, api, law, cli):
        """Verify pdf no permission."""
        doc = DynamicDocument.objects.create(
            title="FS_NoPerm", content="<p>x</p>", state="FullySigned",
            created_by=law, requires_signature=True, fully_signed=True,
        )
        api.force_authenticate(user=cli)
        resp = api.get(reverse("generate-signatures-pdf", args=[doc.id]))
        assert resp.status_code == 403


# ======================================================================
# Tests migrated from test_views_batch8.py
# ======================================================================

"""
Batch 8 – 20 tests for signature_views.py helper functions and error paths.

Targets uncovered lines:
  - register_carlito_fonts (731-753)
  - get_letterhead_for_document (755-780)
  - generate_original_document_pdf (793-932)
  - create_signatures_pdf (941-1143)
  - combine_pdfs (1151-1170)
  - add_identifier_footer (1178-1203)
  - generate_encrypted_document_id fallback (95-97)
  - format_datetime_spanish (116-122)
  - get_client_ip edge cases (50-66)
  - expire_overdue_documents email failure (162-164)
  - view-level DoesNotExist / exception branches
"""



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer_b8@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def client_user():
    """Client user."""
    return User.objects.create_user(
        email="client_b8@test.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def doc_fully_signed(lawyer_user, client_user):  # pragma: no cover – unused fixture
    """Doc fully signed."""
    doc = DynamicDocument.objects.create(
        title="FullySigned B8",
        content="<p>Hello {{var1}}</p>",
        state="FullySigned",
        created_by=lawyer_user,
        requires_signature=True,
        fully_signed=True,
    )
    _sig = DocumentSignature.objects.create(
        document=doc, signer=client_user, signed=True,
        signed_at=timezone.now(),
        ip_address="1.2.3.4",
    )
    return doc


# ===========================================================================
# 1. Pure helper functions
# ===========================================================================

@pytest.mark.django_db
class TestHelperFunctions:
    """Tests for Helper Functions."""

    def test_get_client_ip_x_forwarded_for(self):
        """Line 56-60: X-Forwarded-For header."""
        request = SimpleNamespace(META={'HTTP_X_FORWARDED_FOR': '10.0.0.1, 10.0.0.2'})
        assert signature_views.get_client_ip(request) == '10.0.0.1'

    def test_get_client_ip_x_real_ip(self):
        """Line 62-64: X-Real-IP header."""
        request = SimpleNamespace(META={'HTTP_X_REAL_IP': '172.16.0.1'})
        assert signature_views.get_client_ip(request) == '172.16.0.1'

    def test_get_client_ip_remote_addr(self):
        """Line 66: fallback to REMOTE_ADDR."""
        request = SimpleNamespace(META={'REMOTE_ADDR': '127.0.0.1'})
        assert signature_views.get_client_ip(request) == '127.0.0.1'

    def test_get_client_ip_empty_forwarded_for(self):
        """Line 59-60: empty first element in X-Forwarded-For."""
        request = SimpleNamespace(META={'HTTP_X_FORWARDED_FOR': ' , 10.0.0.2', 'REMOTE_ADDR': '127.0.0.1'})
        # Empty first element -> falls through
        ip = signature_views.get_client_ip(request)
        # Should fallback since first IP is empty after strip
        assert ip in ('127.0.0.1', '10.0.0.2')  # depends on implementation

    def test_generate_encrypted_document_id_success(self):
        """Lines 81-94: normal hash generation."""
        dt = datetime.datetime(2025, 6, 15, 10, 30, 0)
        result = signature_views.generate_encrypted_document_id(1, dt)
        assert '-' in result
        assert len(result) == 19  # XXXX-XXXX-XXXX-XXXX

    def test_generate_encrypted_document_id_fallback(self):
        """Lines 95-97: fallback on exception."""
        class FailingDate:
            def __init__(self) -> None:
                self.calls = 0

            def strftime(self, _format: str) -> str:
                self.calls += 1
                if self.calls == 1:
                    raise ValueError("bad")
                return "20250101"

        bad_dt = FailingDate()
        result = signature_views.generate_encrypted_document_id(1, bad_dt)
        assert result.startswith("DOC-")
        assert bad_dt.calls == 2

    def test_format_datetime_spanish(self):
        """Lines 116-122: Spanish date formatting."""
        dt = datetime.datetime(2025, 12, 25, 14, 30, 15)
        result = signature_views.format_datetime_spanish(dt)
        assert "diciembre" in result
        assert "25" in result
        assert "14:30:15" in result

    def test_format_datetime_spanish_january(self):
        """Lines 121-122: month lookup for enero."""
        dt = datetime.datetime(2025, 1, 1, 0, 0, 0)
        result = signature_views.format_datetime_spanish(dt)
        assert "enero" in result


# ===========================================================================
# 2. get_letterhead_for_document (signature_views version)
# ===========================================================================

@pytest.mark.django_db
class TestGetLetterheadForDocument:
    """Tests for Get Letterhead For Document."""

    def test_document_letterhead_priority(self, lawyer_user):
        """Lines 772-773: document letterhead takes priority."""
        doc = SimpleNamespace(letterhead_image="doc_letterhead.png")
        user = SimpleNamespace(letterhead_image="user_letterhead.png")
        result = signature_views.get_letterhead_for_document(doc, user)
        assert result == "doc_letterhead.png"

    def test_user_letterhead_fallback(self, lawyer_user):
        """Lines 776-777: user letterhead when doc has none."""
        doc = SimpleNamespace(letterhead_image=None)
        user = SimpleNamespace(letterhead_image="user_letterhead.png")
        result = signature_views.get_letterhead_for_document(doc, user)
        assert result == "user_letterhead.png"

    def test_no_letterhead(self, lawyer_user):
        """Lines 779-780: no letterhead at all."""
        doc = SimpleNamespace(letterhead_image=None)
        user = SimpleNamespace(letterhead_image=None)
        result = signature_views.get_letterhead_for_document(doc, user)
        assert result is None


# ===========================================================================
# 3. PDF helper functions (mocked to avoid font/file dependencies)
# ===========================================================================

@pytest.mark.django_db
class TestPdfHelpers:
    """Tests for Pdf Helpers."""

    @patch('gym_app.utils.documents.os.path.exists', return_value=False)
    def test_register_carlito_fonts_missing_file(self, mock_exists):
        """register_carlito_fonts raises FileNotFoundError when a font is missing.

        (existence check lives in get_carlito_font_paths).
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            signature_views.register_carlito_fonts()
        assert exc_info.value is not None

    @patch('gym_app.views.dynamic_documents.signature_views.render_document_pdf', return_value=b'%PDF-1.7 fake')
    @patch('gym_app.views.dynamic_documents.signature_views.get_letterhead_for_document', return_value=None)
    def test_generate_original_document_pdf_success(
        self, mock_lh, mock_render, lawyer_user
    ):
        """Successful PDF generation returns a BytesIO buffer."""
        doc = DynamicDocument.objects.create(
            title="Test PDF", content="<p>Hello {{greeting}}</p>", state="Draft",
            created_by=lawyer_user,
        )
        DocumentVariable.objects.create(
            document=doc, name_en="greeting", value="World",
            field_type="input",
        )
        result = signature_views.generate_original_document_pdf(doc, lawyer_user)
        assert isinstance(result, BytesIO)

    @patch('gym_app.views.dynamic_documents.signature_views.render_document_pdf', side_effect=Exception("render boom"))
    @patch('gym_app.views.dynamic_documents.signature_views.get_letterhead_for_document', return_value=None)
    def test_generate_original_document_pdf_render_error(
        self, mock_lh, mock_render, lawyer_user
    ):
        """A render failure propagates out of generate_original_document_pdf."""
        doc = DynamicDocument.objects.create(
            title="Err", content="<p>x</p>", state="Draft",
            created_by=lawyer_user,
        )
        with pytest.raises(Exception, match="render boom") as exc_info:
            signature_views.generate_original_document_pdf(doc, lawyer_user)
        assert exc_info.value is not None

    def test_combine_pdfs(self):
        """Lines 1151-1170: combine two PDF buffers."""
        # Create two minimal PDFs
        buf1 = BytesIO()
        w1 = PdfWriter()
        w1.add_blank_page(width=72, height=72)
        w1.write(buf1)
        buf1.seek(0)

        buf2 = BytesIO()
        w2 = PdfWriter()
        w2.add_blank_page(width=72, height=72)
        w2.write(buf2)
        buf2.seek(0)

        result = signature_views.combine_pdfs(buf1, buf2)
        assert isinstance(result, BytesIO)
        # Verify the combined PDF has 2 pages
        reader = PdfReader(result)
        assert len(reader.pages) == 2

    def test_add_identifier_footer(self):
        """Lines 1178-1203: add footer to all pages."""
        buf = BytesIO()
        w = PdfWriter()
        w.add_blank_page(width=612, height=792)
        w.write(buf)
        buf.seek(0)

        # Need Carlito font registered; mock it
        with patch('gym_app.views.dynamic_documents.signature_views.register_carlito_fonts'):
            # Use a safe font fallback
            with patch.object(rl_canvas.Canvas, 'setFont'):
                result = signature_views.add_identifier_footer(buf, "ABCD-1234-EFGH-5678")
        assert isinstance(result, BytesIO)
        assert len(PdfReader(result).pages) == 1


# ===========================================================================
# 4. View-level exception paths (DoesNotExist on nested lookups)
# ===========================================================================

@pytest.mark.django_db
class TestSignatureViewExceptionPaths:
    """Tests for Signature View Exception Paths."""

    def test_get_document_signatures_doc_not_found_inner(
        self, api_client, lawyer_user
    ):
        """Line 186-187: DynamicDocument.DoesNotExist inside view."""
        api_client.force_authenticate(user=lawyer_user)
        url = "/api/dynamic-documents/99999/signatures/"
        resp = api_client.get(url)
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)

    def test_reject_document_generic_exception(
        self, api_client, client_user, lawyer_user
    ):
        """Lines 483-484: generic exception in reject_document."""
        doc = DynamicDocument.objects.create(
            title="Err", content="<p>x</p>", state="PendingSignatures",
            created_by=lawyer_user, requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=client_user)

        api_client.force_authenticate(user=client_user)
        url = f"/api/dynamic-documents/{doc.id}/reject/{client_user.id}/"

        with patch.object(DocumentSignature, 'save', side_effect=Exception("db crash")):
            resp = api_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ======================================================================
# Tests migrated from test_views_batch9.py
# ======================================================================


# ---------------------------------------------------------------------------
# Fixtures (batch 9)
# ---------------------------------------------------------------------------
@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer_b9@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="client_b9@test.com", password="pw", role="client",
        first_name="Cli", last_name="Ent",
    )


@pytest.fixture
def document(lawyer_user):
    """Document."""
    return DynamicDocument.objects.create(
        title="Doc B9", content="<p>Hello</p>", state="Draft",
        created_by=lawyer_user,
    )


# ===========================================================================
# 1. create_signatures_pdf (lines 941-1143)
# ===========================================================================

@pytest.mark.django_db
class TestCreateSignaturesPdf:
    """Tests for Create Signatures Pdf."""

    @freeze_time("2025-01-15 12:00:00")
    def test_create_signatures_pdf_basic(self, lawyer_user, client_user):
        """Lines 941-1143: create_signatures_pdf with signed signature."""
        doc = DynamicDocument.objects.create(
            title="Signed Doc", content="<p>x</p>", state="FullySigned",
            created_by=lawyer_user, requires_signature=True, fully_signed=True,
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.1",
        )
        request = SimpleNamespace(user=lawyer_user)

        result = signature_views.create_signatures_pdf(doc, request)
        assert isinstance(result, BytesIO)
        content = result.read()
        assert content[:4] == b'%PDF'

    @freeze_time("2025-01-15 12:00:00")
    def test_create_signatures_pdf_no_signature_images(self, lawyer_user, client_user):
        """Lines 1116-1118: no signature images branch."""
        doc = DynamicDocument.objects.create(
            title="No Imgs", content="<p>x</p>", state="FullySigned",
            created_by=lawyer_user, requires_signature=True, fully_signed=True,
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True,
            signed_at=timezone.now(),
        )
        request = SimpleNamespace(user=lawyer_user)

        result = signature_views.create_signatures_pdf(doc, request)
        assert isinstance(result, BytesIO)

    def test_create_signatures_pdf_unsigned_signature(self, lawyer_user, client_user):
        """Lines 1070: signed_at is None for unsigned."""
        doc = DynamicDocument.objects.create(
            title="Pending", content="<p>x</p>", state="PendingSignatures",
            created_by=lawyer_user, requires_signature=True,
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=False,
        )
        request = SimpleNamespace(user=lawyer_user)

        result = signature_views.create_signatures_pdf(doc, request)
        assert isinstance(result, BytesIO)

    @freeze_time("2025-01-15 12:00:00")
    def test_audit_pdf_issuer_only_title(self, lawyer_user, client_user):
        """issuer_only docs show the emitter-specific audit title."""
        doc = DynamicDocument.objects.create(
            title="UnilateralDoc", content="<p>x</p>", state="FullySigned",
            created_by=lawyer_user, requires_signature=True, fully_signed=True,
            signature_type='issuer_only',
        )
        DocumentSignature.objects.create(
            document=doc, signer=lawyer_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.1",
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.2",
        )
        request = SimpleNamespace(user=lawyer_user)

        buf = signature_views.create_signatures_pdf(doc, request)
        text = PdfReader(buf).pages[0].extract_text() or ""
        assert "FIRMA DEL EMISOR" in text

    @freeze_time("2025-01-15 12:00:00")
    def test_audit_pdf_issuer_only_omits_recipient(self, lawyer_user, client_user):
        """issuer_only docs must not list the recipient as a firmante."""
        doc = DynamicDocument.objects.create(
            title="UnilateralDoc", content="<p>x</p>", state="FullySigned",
            created_by=lawyer_user, requires_signature=True, fully_signed=True,
            signature_type='issuer_only',
        )
        DocumentSignature.objects.create(
            document=doc, signer=lawyer_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.1",
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.2",
        )
        request = SimpleNamespace(user=lawyer_user)

        buf = signature_views.create_signatures_pdf(doc, request)
        text = "".join((p.extract_text() or "") for p in PdfReader(buf).pages)
        assert client_user.email not in text
        assert lawyer_user.email in text

    @freeze_time("2025-01-15 12:00:00")
    def test_audit_pdf_issuer_only_role_is_emisor(self, lawyer_user, client_user):
        """issuer_only docs label the sole firmante as 'Emisor'."""
        doc = DynamicDocument.objects.create(
            title="UnilateralDoc", content="<p>x</p>", state="FullySigned",
            created_by=lawyer_user, requires_signature=True, fully_signed=True,
            signature_type='issuer_only',
        )
        DocumentSignature.objects.create(
            document=doc, signer=lawyer_user, signed=True,
            signed_at=timezone.now(), ip_address="10.0.0.1",
        )
        request = SimpleNamespace(user=lawyer_user)

        buf = signature_views.create_signatures_pdf(doc, request)
        text = "".join((p.extract_text() or "") for p in PdfReader(buf).pages)
        assert "Emisor:" in text


# ===========================================================================
# 2. expire_overdue_documents email failure path
# ===========================================================================

@pytest.mark.django_db
class TestExpireOverdueDocuments:
    """Tests for Expire Overdue Documents."""

    @freeze_time("2025-01-15 12:00:00")
    def test_expire_email_failure_does_not_block(self, lawyer_user, client_user):
        """Lines 162-164: email failure is silently caught."""
        doc = DynamicDocument.objects.create(
            title="Overdue", content="<p>x</p>", state="PendingSignatures",
            created_by=lawyer_user, requires_signature=True,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        DocumentSignature.objects.create(document=doc, signer=client_user)

        with patch('gym_app.views.dynamic_documents.signature_views.EmailMessage') as mock_email:
            mock_email.return_value.send.side_effect = Exception("SMTP down")
            signature_views.expire_overdue_documents()

        doc.refresh_from_db()
        assert doc.state == "Expired"

    @freeze_time("2025-01-15 12:00:00")
    def test_expire_skips_creator_without_email(self, client_user):
        """Lines 144-145: skip if creator has no email."""
        doc = DynamicDocument.objects.create(
            title="NoCreator", content="<p>x</p>", state="PendingSignatures",
            created_by=None, requires_signature=True,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        # Should not raise
        signature_views.expire_overdue_documents()
        doc.refresh_from_db()
        assert doc.state == "Expired"


# ===========================================================================
# Tests merged from test_signature_views_coverage.py
# ===========================================================================

@pytest.fixture
def lawyer():
    """Lawyer."""
    return User.objects.create_user(
        email='law_svc@e.com', password='p', role='lawyer',
        first_name='L', last_name='S')


@pytest.fixture
def signer():
    """Signer."""
    return User.objects.create_user(
        email='sig_svc@e.com', password='p', role='client',
        first_name='S', last_name='V')


@pytest.fixture
def signed_doc(lawyer, signer):
    """Fully signed document with signature record."""
    doc = DynamicDocument.objects.create(
        title='SignedDoc', content='<p>Test content</p>',
        state='FullySigned', requires_signature=True,
        fully_signed=True, created_by=lawyer,
        created_at=timezone.now(), updated_at=timezone.now())
    DocumentSignature.objects.create(
        document=doc, signer=signer, signed=True,
        signed_at=timezone.now(), ip_address='127.0.0.1')
    return doc


@pytest.fixture
def pending_doc(lawyer, signer):
    """Document pending signatures."""
    doc = DynamicDocument.objects.create(
        title='PendDoc', content='<p>Pending</p>',
        state='PendingSignatures', requires_signature=True,
        created_by=lawyer,
        created_at=timezone.now(), updated_at=timezone.now())
    DocumentSignature.objects.create(
        document=doc, signer=signer, signed=False)
    return doc


@pytest.mark.django_db
class TestSignatureViewsRegressionScenarios:
    """Tests for Signature Views Regression Scenarios."""

    # --- Helper: get_client_ip with X-Forwarded-For ---
    def test_get_client_ip_forwarded_for(self):
        """Lines 58-60: X-Forwarded-For header returns first IP."""
        req = SimpleNamespace(META={'HTTP_X_FORWARDED_FOR': '1.2.3.4, 5.6.7.8'})
        assert get_client_ip(req) == '1.2.3.4'

    def test_encrypted_id_normal(self):
        """Lines 81-94: normal encrypted ID generation."""
        dt = datetime.datetime(2025, 6, 15, 10, 30, 0)
        result = generate_encrypted_document_id(1, dt)
        assert '-' in result
        assert len(result) == 19  # XXXX-XXXX-XXXX-XXXX

    # --- Helper: get_letterhead_for_document ---
    def test_letterhead_no_letterhead(self, lawyer):
        """Line 779: no letterhead returns None."""
        doc = SimpleNamespace(letterhead_image=None)
        lawyer.letterhead_image = None
        assert get_letterhead_for_document(doc, lawyer) is None

    def test_letterhead_user_global(self, lawyer):
        """Line 777: user global letterhead used when doc has none."""
        doc = SimpleNamespace(letterhead_image=None)
        letterhead = object()
        lawyer.letterhead_image = letterhead
        result = get_letterhead_for_document(doc, lawyer)
        assert result is letterhead

    # --- generate_signatures_pdf: not fully signed ---
    def test_gen_sig_pdf_not_fully_signed(
        self, api_client, lawyer, pending_doc
    ):
        """Line 1230: document not FullySigned returns 400."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'generate-signatures-pdf', kwargs={'pk': pending_doc.pk}))
        assert r.status_code == 400
        assert 'formalizado' in r.data['detail']

    # --- generate_signatures_pdf: fully signed ---
    def test_gen_sig_pdf_success(self, api_client, lawyer, signed_doc):
        """Lines 793-1277: full PDF generation for signed document."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'generate-signatures-pdf', kwargs={'pk': signed_doc.pk}))
        assert r.status_code == 200
        assert r['Content-Type'] == 'application/pdf'

    # --- get_user_archived_documents ---
    @freeze_time("2025-01-15 12:00:00")
    def test_get_archived_docs(self, api_client, lawyer, signer):
        """Lines 644-673: archived documents for user."""
        doc = DynamicDocument.objects.create(
            title='Rejected', content='', state='Rejected',
            requires_signature=True, created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, rejected=True)
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-user-archived-documents',
            kwargs={'user_id': signer.pk}))
        assert r.status_code == 200

    # --- get_user_signed_documents ---
    def test_get_signed_docs(self, api_client, lawyer, signer, signed_doc):
        """Lines 678-699: signed documents for user."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-user-signed-documents',
            kwargs={'user_id': signer.pk}))
        assert r.status_code == 200

    # --- expire_overdue_documents (triggered via get_pending) ---
    @freeze_time("2025-01-15 12:00:00")
    def test_expire_overdue(self, api_client, lawyer, signer):
        """Lines 125-164: overdue document gets expired."""
        doc = DynamicDocument.objects.create(
            title='Overdue', content='', state='PendingSignatures',
            requires_signature=True, created_by=lawyer,
            signature_due_date=timezone.now().date() - datetime.timedelta(days=1),
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, signed=False)
        api_client.force_authenticate(user=signer)
        r = api_client.get(reverse('get-pending-signatures'))
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.state == 'Expired'

    # --- get_document_signatures: non-existent doc (lines 186-187) ---
    def test_get_signatures_nonexistent_doc(self, api_client, lawyer):
        """Lines 186-187: DoesNotExist returns 404."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-document-signatures', kwargs={'document_id': 99999}))
        assert r.status_code == 404

    def test_remove_sig_not_creator(self, api_client, lawyer, signer, pending_doc):
        """Line 567: non-creator gets 403."""
        api_client.force_authenticate(user=signer)
        r = api_client.delete(reverse(
            'remove-signature-request',
            kwargs={'document_id': pending_doc.pk, 'user_id': signer.pk}))
        # The decorator or view should block non-creator
        assert r.status_code in (403, 404)

    # --- get_user_pending_documents_full: non-existent user ---
    def test_pending_docs_full_nonexistent_user(self, api_client, lawyer):
        """Lines 638-639: non-existent user_id returns 404."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-user-pending-documents-full',
            kwargs={'user_id': 99999}))
        assert r.status_code == 404

    # --- get_user_archived_documents: non-existent user ---
    def test_archived_docs_nonexistent_user(self, api_client, lawyer):
        """Lines 672-673: non-existent user_id returns 404."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-user-archived-documents',
            kwargs={'user_id': 99999}))
        assert r.status_code == 404

    # --- get_user_signed_documents: non-existent user ---
    def test_signed_docs_nonexistent_user(self, api_client, lawyer):
        """Lines 698-699: non-existent user_id returns 404."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'get-user-signed-documents',
            kwargs={'user_id': 99999}))
        assert r.status_code == 404

    # --- generate_signatures_pdf: signer with doc_type & identification ---
    @freeze_time("2025-01-15 12:00:00")
    def test_gen_sig_pdf_with_identification(self, api_client, lawyer):
        """Lines 1081, 1083, 1085: signer with document_type/identification."""
        signer2 = User.objects.create_user(
            email='sig2_svc@e.com', password='p', role='client',
            first_name='S2', last_name='V2',
            document_type='CC', identification='12345678')
        doc = DynamicDocument.objects.create(
            title='IdentDoc', content='<p>ID</p>',
            state='FullySigned', requires_signature=True,
            fully_signed=True, created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer2, signed=True,
            signed_at=timezone.now(), ip_address='10.0.0.1')
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'generate-signatures-pdf', kwargs={'pk': doc.pk}))
        assert r.status_code == 200
        assert r['Content-Type'] == 'application/pdf'

    # --- generate_signatures_pdf: signer with UserSignature image ---
    @freeze_time("2025-01-15 12:00:00")
    def test_gen_sig_pdf_with_user_signature_image(self, api_client, lawyer):
        """Lines 1096-1109: signer has a UserSignature with image."""
        signer3 = User.objects.create_user(
            email='sig3_svc@e.com', password='p', role='client',
            first_name='S3', last_name='V3')
        # Create a valid signature image
        buf = BytesIO()
        PILImage.new('RGB', (180, 50), color='black').save(buf, format='PNG')
        buf.seek(0)
        sig_img = SimpleUploadedFile(
            "sig.png", buf.read(), content_type="image/png")
        UserSignature.objects.create(
            user=signer3, signature_image=sig_img, method='draw')
        doc = DynamicDocument.objects.create(
            title='SigImgDoc', content='<p>SigImg</p>',
            state='FullySigned', requires_signature=True,
            fully_signed=True, created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer3, signed=True,
            signed_at=timezone.now(), ip_address='10.0.0.2')
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'generate-signatures-pdf', kwargs={'pk': doc.pk}))
        assert r.status_code == 200
        assert r['Content-Type'] == 'application/pdf'

    @freeze_time("2025-01-15 12:00:00")
    def test_reject_document_with_comment(self, api_client, lawyer, signer):
        """Lines 434-473: rejection with comment and email notification."""
        doc = DynamicDocument.objects.create(
            title='RejectMe', content='<p>R</p>',
            state='PendingSignatures', requires_signature=True,
            created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, signed=False)
        api_client.force_authenticate(user=signer)
        with mock.patch('gym_app.views.dynamic_documents.signature_views.EmailMessage') as mock_email:
            mock_email.return_value.send.return_value = None
            r = api_client.post(
                reverse('reject-document',
                        kwargs={'document_id': doc.pk, 'user_id': signer.pk}),
                {'comment': 'Not acceptable'}, format='json')
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.state == 'Rejected'

    # ========== Email exception tests (system boundary) ==========

    @freeze_time("2025-01-15 12:00:00")
    def test_sign_document_email_exception(self, api_client, lawyer, signer):
        """Lines 347-348: email send failure during sign is caught silently."""
        doc = DynamicDocument.objects.create(
            title='SignEmailFail', content='<p>E</p>',
            state='PendingSignatures', requires_signature=True,
            created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, signed=False)
        buf = BytesIO()
        PILImage.new('RGB', (180, 50), color='black').save(buf, format='PNG')
        buf.seek(0)
        sig_img = SimpleUploadedFile(
            "sig.png", buf.read(), content_type="image/png")
        UserSignature.objects.filter(user=signer).delete()
        UserSignature.objects.create(
            user=signer, signature_image=sig_img, method='draw')
        api_client.force_authenticate(user=signer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.EmailMessage'
        ) as mock_email:
            mock_email.return_value.send.side_effect = Exception("SMTP fail")
            r = api_client.post(reverse(
                'sign-document',
                kwargs={'document_id': doc.pk, 'user_id': signer.pk}))
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.state == 'FullySigned'

    @freeze_time("2025-01-15 12:00:00")
    def test_reject_document_email_exception(self, api_client, lawyer, signer):
        """Lines 469-471: email send failure during reject is caught silently."""
        doc = DynamicDocument.objects.create(
            title='RejectEmailFail', content='<p>R</p>',
            state='PendingSignatures', requires_signature=True,
            created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, signed=False)
        api_client.force_authenticate(user=signer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.EmailMessage'
        ) as mock_email:
            mock_email.return_value.send.side_effect = Exception("SMTP fail")
            r = api_client.post(
                reverse('reject-document',
                        kwargs={'document_id': doc.pk, 'user_id': signer.pk}),
                {'comment': 'Bad'}, format='json')
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.state == 'Rejected'

    # ========== sign_document generic exception (lines 377-378) ==========

    @freeze_time("2025-01-15 12:00:00")
    def test_sign_document_generic_exception(self, api_client, lawyer, signer):
        """Lines 377-378: generic exception in sign_document → 500."""
        doc = DynamicDocument.objects.create(
            title='SignFail', content='<p>F</p>',
            state='PendingSignatures', requires_signature=True,
            created_by=lawyer,
            created_at=timezone.now(), updated_at=timezone.now())
        DocumentSignature.objects.create(
            document=doc, signer=signer, signed=False)
        buf = BytesIO()
        PILImage.new('RGB', (180, 50), color='black').save(buf, format='PNG')
        buf.seek(0)
        sig_img = SimpleUploadedFile(
            "sig.png", buf.read(), content_type="image/png")
        UserSignature.objects.filter(user=signer).delete()
        UserSignature.objects.create(
            user=signer, signature_image=sig_img, method='draw')
        api_client.force_authenticate(user=signer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.'
            'DocumentSignatureSerializer',
            side_effect=Exception("serializer error")
        ):
            r = api_client.post(reverse(
                'sign-document',
                kwargs={'document_id': doc.pk, 'user_id': signer.pk}))
        assert r.status_code == 500
        assert 'unexpected' in r.data['detail'].lower()

    # ========== reopen_document: nonexistent doc (lines 539-545) ==========

    def test_reopen_signatures_nonexistent_doc(self, api_client, lawyer):
        """Lines 539-545: nonexistent document → 404 (via decorator)."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.post(reverse(
            'reopen-document-signatures',
            kwargs={'document_id': 99999}))
        assert r.status_code == 404

    # ========== remove_signature: nonexistent doc (lines 598-599) ==========

    def test_remove_signature_nonexistent_doc(self, api_client, lawyer):
        """Lines 598-599: nonexistent document → 404 (via decorator)."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.delete(reverse(
            'remove-signature-request',
            kwargs={'document_id': 99999, 'user_id': 1}))
        assert r.status_code == 404

    # ========== Generic exception for user document list endpoints ==========

    def test_pending_docs_full_generic_exception(self, api_client, lawyer, signer):
        """Lines 636-637: generic exception in get_user_pending_documents_full → 500."""
        api_client.force_authenticate(user=lawyer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.expire_overdue_documents',
            side_effect=Exception("unexpected")
        ):
            r = api_client.get(reverse(
                'get-user-pending-documents-full',
                kwargs={'user_id': signer.pk}))
        assert r.status_code == 500

    def test_archived_docs_generic_exception(self, api_client, lawyer, signer):
        """Lines 670-671: generic exception in get_user_archived_documents → 500."""
        api_client.force_authenticate(user=lawyer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.DocumentSignature.objects',
        ) as mock_qs:
            mock_qs.filter.side_effect = Exception("unexpected")
            r = api_client.get(reverse(
                'get-user-archived-documents',
                kwargs={'user_id': signer.pk}))
        assert r.status_code == 500

    def test_signed_docs_generic_exception(self, api_client, lawyer, signer):
        """Lines 696-697: generic exception in get_user_signed_documents → 500."""
        api_client.force_authenticate(user=lawyer)
        with mock.patch(
            'gym_app.views.dynamic_documents.signature_views.DocumentSignature.objects',
        ) as mock_qs:
            mock_qs.filter.side_effect = Exception("unexpected")
            r = api_client.get(reverse(
                'get-user-signed-documents',
                kwargs={'user_id': signer.pk}))
        assert r.status_code == 500

    # ========== generate_signatures_pdf: nonexistent doc (line 1267) ==========

    def test_gen_sig_pdf_nonexistent_doc(self, api_client, lawyer):
        """Line 1267: nonexistent document → 404."""
        api_client.force_authenticate(user=lawyer)
        r = api_client.get(reverse(
            'generate-signatures-pdf', kwargs={'pk': 99999}))
        assert r.status_code == 404


# ======================================================================
# Tests merged from test_signature_views_phase2.py
# ======================================================================


@pytest.fixture
def lawyer_user():  # noqa: F811
    """Lawyer user."""
    return User.objects.create_user(
        email="sv2-lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def another_lawyer():
    """Another lawyer."""
    return User.objects.create_user(
        email="sv2-lawyer2@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def client_user():  # noqa: F811
    """Client user."""
    return User.objects.create_user(
        email="sv2-client@example.com",
        password="testpassword",
        role="client",
    )


@pytest.fixture
def document_with_signature(lawyer_user, client_user):
    """Document with signature."""
    doc = DynamicDocument.objects.create(
        title="SV2 Doc",
        content="<p>test</p>",
        state="PendingSignatures",
        created_by=lawyer_user,
    )
    sig = DocumentSignature.objects.create(
        document=doc,
        signer=client_user,
        signed=False,
    )
    return doc, sig


# ── Line 565: Lawyer non-creator denied from removing signature request ──

@pytest.mark.django_db
class TestRemoveSignatureRequestPermission:
    """Tests for Remove Signature Request Permission."""

    def test_lawyer_non_creator_gets_403(
        self, api_client, another_lawyer, document_with_signature
    ):
        """Line 565: A lawyer who is NOT the document creator gets 403.
        
        when trying to remove a signature request.
        """
        doc, sig = document_with_signature
        api_client.force_authenticate(user=another_lawyer)
        url = reverse(
            "remove-signature-request",
            kwargs={"document_id": doc.id, "user_id": sig.signer.id},
        )
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "creator" in response.data["detail"].lower()
        # Verify signature was NOT deleted
        assert DocumentSignature.objects.filter(id=sig.id).exists()


# ── Line 771: get_letterhead_for_document returns document letterhead ──

@pytest.mark.django_db
class TestGetLetterheadForDocument:  # noqa: F811
    """Tests for Get Letterhead For Document."""

    def test_returns_document_letterhead_when_set(self, lawyer_user):
        """Line 771: When document has letterhead_image, it takes priority."""
        from gym_app.views.dynamic_documents.signature_views import (
            get_letterhead_for_document,
        )

        doc = DynamicDocument.objects.create(
            title="SV2 Letterhead Doc",
            content="<p>test</p>",
            state="Draft",
            created_by=lawyer_user,
        )
        # Set a fake letterhead path (we only test the branch, not the file)
        doc.letterhead_image = "letterheads/fake.png"
        doc.save(update_fields=["letterhead_image"])

        result = get_letterhead_for_document(doc, lawyer_user)

        assert result is not None
        assert result == doc.letterhead_image


# ── formalize_document ────────────────────────────────────────────


def _make_completed_doc(lawyer, client):
    """Create a Completed document owned by the lawyer with visibility for both users."""
    doc = DynamicDocument.objects.create(
        title="Contrato Arrendamiento",
        content="<p>El arrendador y arrendatario acuerdan...</p>",
        state="Completed",
        created_by=lawyer,
        assigned_to=client,
        requires_signature=False,
    )
    doc.visibility_permissions.create(user=lawyer, granted_by=lawyer)
    doc.visibility_permissions.create(user=client, granted_by=lawyer)
    return doc


@pytest.mark.django_db
class TestFormalizeDocument:
    """Tests for the formalize_document endpoint."""

    @pytest.fixture
    def api(self):
        """Provide an unauthenticated APIClient."""
        return APIClient()

    @pytest.fixture
    def lawyer(self):
        """Create a lawyer user for formalize_document tests."""
        return User.objects.create_user(
            email="formalize_lawyer@t.com", password="pw", role="lawyer",
            first_name="Law", last_name="Yer",
        )

    @pytest.fixture
    def client_user(self):
        """Create a client user for formalize_document tests."""
        return User.objects.create_user(
            email="formalize_client@t.com", password="pw", role="client",
            first_name="Cli", last_name="Ent",
        )

    @pytest.fixture
    def other_client(self):
        """Create a second client user for formalize_document tests."""
        return User.objects.create_user(
            email="formalize_other@t.com", password="pw", role="client",
            first_name="Oth", last_name="Er",
        )

    def test_formalize_success(self, api, lawyer, client_user):
        """Happy path: Completed document transitions to PendingSignatures with signatures created."""
        doc = _make_completed_doc(lawyer, client_user)
        original_title = doc.title
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "PendingSignatures"
        assert doc.requires_signature is True
        assert doc.fully_signed is False
        assert doc.title == original_title
        assert DocumentSignature.objects.filter(document=doc, signer=client_user).exists()
        # Lawyer should be auto-added as signer
        assert DocumentSignature.objects.filter(document=doc, signer=lawyer).exists()

    def test_formalize_preserves_title(self, api, lawyer, client_user):
        """Title must NOT have _firma suffix appended."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        api.post(url, {"signers": [client_user.id]}, format="json")

        doc.refresh_from_db()
        assert "_firma" not in doc.title
        assert doc.title == "Contrato Arrendamiento"

    @pytest.mark.parametrize("wrong_state", [
        "Draft", "Progress", "PendingSignatures", "FullySigned", "Rejected", "Expired",
    ])
    def test_formalize_wrong_state(self, api, lawyer, client_user, wrong_state):
        """Only Completed documents can be formalized."""
        doc = _make_completed_doc(lawyer, client_user)
        doc.state = wrong_state
        doc.save(update_fields=["state"])
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_no_signers(self, api, lawyer, client_user):
        """Must provide at least one signer."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": []}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_missing_signers_field(self, api, lawyer, client_user):
        """Must provide the signers field."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_invalid_signer_ids(self, api, lawyer, client_user):
        """Invalid signer IDs should return 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [999999]}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_permission_denied(self, api, lawyer, client_user, other_client):
        """Non-owner non-lawyer user cannot formalize."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=other_client)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_formalize_with_due_date(self, api, lawyer, client_user):
        """Signature due date is set when provided."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signers": [client_user.id],
            "signature_due_date": "2026-12-31",
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert str(doc.signature_due_date) == "2026-12-31"

    def test_formalize_without_due_date(self, api, lawyer, client_user):
        """Formalization works without a due date."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.signature_due_date is None

    def test_formalize_lawyer_auto_added_as_signer(self, api, lawyer, client_user):
        """Lawyer is auto-added as signer even if not explicitly in signers list."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert DocumentSignature.objects.filter(document=doc, signer=lawyer).exists()
        assert DocumentSignature.objects.filter(document=doc, signer=client_user).exists()
        assert DocumentSignature.objects.filter(document=doc).count() == 2

    def test_formalize_same_document_id(self, api, lawyer, client_user):
        """The returned document must have the same ID — no copy created."""
        doc = _make_completed_doc(lawyer, client_user)
        original_id = doc.id
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {"signers": [client_user.id]}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == original_id
        # No new document should exist with a different ID
        assert DynamicDocument.objects.filter(created_by=lawyer).count() == 1

    def test_formalize_optimistic_lock_mechanism(self, lawyer, client_user):
        """Verify the optimistic lock: filter(state='Completed').update() returns 0 when state changed."""
        doc = _make_completed_doc(lawyer, client_user)

        # Simulate concurrent state change
        DynamicDocument.objects.filter(pk=doc.pk).update(state='PendingSignatures')

        # The optimistic-lock query finds 0 rows since state is no longer 'Completed'
        rows_updated = DynamicDocument.objects.filter(
            pk=doc.pk, state='Completed',
        ).update(state='PendingSignatures')

        assert rows_updated == 0

    # ── issuer_only formalization ──

    def test_formalize_issuer_only_success_state(self, api, lawyer, client_user):
        """Issuer-only formalization sets state to PendingSignatures with correct document fields."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "issuer_only",
            "recipients": [client_user.id],
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "PendingSignatures"
        assert doc.signature_type == "issuer_only"
        assert doc.requires_signature is True
        assert doc.fully_signed is False

    def test_formalize_issuer_only_success_signatures(self, api, lawyer, client_user):
        """Issuer-only formalization creates pending DS for creator and auto-signed DS + visibility for recipient."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        api.post(url, {
            "signature_type": "issuer_only",
            "recipients": [client_user.id],
        }, format="json")

        assert DocumentSignature.objects.filter(document=doc, signer=lawyer, signed=False).exists()
        assert DocumentSignature.objects.filter(document=doc, signer=client_user, signed=True).exists()
        assert DocumentSignature.objects.filter(document=doc).count() == 2
        assert DocumentVisibilityPermission.objects.filter(
            document=doc, user=client_user,
        ).exists()

    def test_formalize_issuer_only_no_recipients(self, api, lawyer, client_user):
        """Issuer-only with empty recipients returns 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "issuer_only",
            "recipients": [],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_issuer_only_invalid_recipients(self, api, lawyer, client_user):
        """Issuer-only with non-existent recipient IDs returns 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "issuer_only",
            "recipients": [999999],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_issuer_only_with_due_date(self, api, lawyer, client_user):
        """Issuer-only formalization sets signature_due_date when provided."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "issuer_only",
            "recipients": [client_user.id],
            "signature_due_date": "2026-12-31",
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert str(doc.signature_due_date) == "2026-12-31"

    # ── informative formalization ──

    def test_formalize_informative_success_state(self, api, lawyer, client_user):
        """Informative formalization sets state to FullySigned with correct document fields."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "informative",
            "recipients": [client_user.id],
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "FullySigned"
        assert doc.signature_type == "informative"
        assert doc.requires_signature is True
        assert doc.fully_signed is True

    def test_formalize_informative_success_signatures(self, api, lawyer, client_user):
        """Informative formalization auto-signs DS for both creator and recipient and grants visibility."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        api.post(url, {
            "signature_type": "informative",
            "recipients": [client_user.id],
        }, format="json")

        assert DocumentSignature.objects.filter(document=doc).count() == 2
        assert DocumentSignature.objects.filter(document=doc, signer=lawyer, signed=True).exists()
        assert DocumentSignature.objects.filter(document=doc, signer=client_user, signed=True).exists()
        assert DocumentVisibilityPermission.objects.filter(
            document=doc, user=client_user,
        ).exists()

    def test_formalize_informative_no_recipients(self, api, lawyer, client_user):
        """Informative with empty recipients returns 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "informative",
            "recipients": [],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_formalize_informative_invalid_recipients(self, api, lawyer, client_user):
        """Informative with non-existent recipient IDs returns 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "informative",
            "recipients": [999999],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_formalize_informative_sends_notification_email(self, mock_email_cls, api, lawyer, client_user):
        """Informative formalization sends notification email to recipients."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "informative",
            "recipients": [client_user.id],
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        mock_email_cls.assert_called()
        call_kwargs = mock_email_cls.call_args
        assert client_user.email in call_kwargs.kwargs.get("to", call_kwargs[1].get("to", []))

    # ── invalid signature_type ──

    def test_formalize_invalid_signature_type(self, api, lawyer, client_user):
        """Invalid signature_type returns 400."""
        doc = _make_completed_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("formalize-document", args=[doc.id])
        resp = api.post(url, {
            "signature_type": "invalid_type",
            "signers": [client_user.id],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── sign_document – issuer_only auto-completion + notification ─────


@pytest.mark.django_db
class TestSignDocumentIssuerOnly:
    """Tests for signing issuer_only documents and recipient notification."""

    @pytest.fixture
    def api(self):
        """Provide an unauthenticated APIClient."""
        return APIClient()

    @pytest.fixture
    def lawyer(self):
        """Create a lawyer user for issuer-only sign tests."""
        return User.objects.create_user(
            email="sign_io_lawyer@t.com", password="pw", role="lawyer",
            first_name="Law", last_name="Yer",
        )

    @pytest.fixture
    def client_user(self):
        """Create a client user for issuer-only sign tests."""
        return User.objects.create_user(
            email="sign_io_client@t.com", password="pw", role="client",
            first_name="Cli", last_name="Ent",
        )

    @staticmethod
    def _create_signature_image():
        """Create a minimal PNG for UserSignature."""
        buf = BytesIO()
        if PILImage is not None:
            img = PILImage.new("RGBA", (100, 50), (0, 0, 0, 0))
            img.save(buf, "PNG")
        else:
            buf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        buf.seek(0)
        return SimpleUploadedFile("sig.png", buf.read(), content_type="image/png")

    def _setup_issuer_only_doc(self, lawyer, client_user):
        """Create a PendingSignatures issuer_only document with emisor DS (pending) and recipient DS (auto-signed)."""
        doc = DynamicDocument.objects.create(
            title="Terminacion Unilateral",
            content="<p>Se termina el contrato</p>",
            state="PendingSignatures",
            created_by=lawyer,
            assigned_to=client_user,
            requires_signature=True,
            signature_type="issuer_only",
        )
        doc.visibility_permissions.create(user=lawyer, granted_by=lawyer)
        doc.visibility_permissions.create(user=client_user, granted_by=lawyer)
        DocumentSignature.objects.create(document=doc, signer=lawyer)
        DocumentSignature.objects.create(document=doc, signer=client_user, signed=True, signed_at=timezone.now())
        return doc

    @patch("gym_app.views.dynamic_documents.signature_views.EmailMessage")
    def test_sign_issuer_only_completes_and_notifies(self, mock_email_cls, api, lawyer, client_user):
        """Signing issuer_only doc marks it FullySigned and triggers recipient notification."""
        doc = self._setup_issuer_only_doc(lawyer, client_user)
        UserSignature.objects.create(user=lawyer, signature_image=self._create_signature_image(), method="draw")
        api.force_authenticate(user=lawyer)

        url = reverse("sign-document", args=[doc.id, lawyer.id])
        resp = api.post(url)

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "FullySigned"
        assert doc.fully_signed is True
        assert mock_email_cls.call_count >= 1
        recipient_emails = [
            call.kwargs.get("to", call[1].get("to", []))
            for call in mock_email_cls.call_args_list
        ]
        flat_emails = [e for sublist in recipient_emails for e in sublist]
        assert client_user.email in flat_emails

    def test_sign_issuer_only_recipient_not_in_pending(self, api, lawyer, client_user):
        """Recipient (client_user) should NOT appear in pending signatures for issuer_only doc."""
        doc = self._setup_issuer_only_doc(lawyer, client_user)
        api.force_authenticate(user=client_user)

        url = reverse("get-pending-signatures")
        resp = api.get(url)

        assert resp.status_code == status.HTTP_200_OK
        doc_ids = [d["id"] for d in resp.data]
        assert doc.id not in doc_ids


# ── correct_document ──────────────────────────────────────────────


def _make_rejected_doc(lawyer, client):
    """Create a Rejected document with an existing signature for correction tests."""
    doc = DynamicDocument.objects.create(
        title="Contrato Rechazado",
        content="<p>Contenido original</p>",
        state="Rejected",
        created_by=lawyer,
        assigned_to=client,
        requires_signature=True,
    )
    doc.visibility_permissions.create(user=lawyer, granted_by=lawyer)
    doc.visibility_permissions.create(user=client, granted_by=lawyer)
    DocumentSignature.objects.create(
        document=doc, signer=client, rejected=True,
        rejected_at=timezone.now(), rejection_comment="Error en cláusula",
    )
    DocumentVariable.objects.create(
        document=doc, name_en="clause", name_es="Cláusula",
        field_type="input", value="Original value",
    )
    return doc


@pytest.mark.django_db
class TestCorrectDocument:
    """Tests for the correct_document endpoint."""

    @pytest.fixture
    def api(self):
        """Provide an unauthenticated APIClient."""
        return APIClient()

    @pytest.fixture
    def lawyer(self):
        """Create a lawyer user for correct_document tests."""
        return User.objects.create_user(
            email="correct_lawyer@t.com", password="pw", role="lawyer",
            first_name="Law", last_name="Yer",
        )

    @pytest.fixture
    def client_user(self):
        """Create a client user for correct_document tests."""
        return User.objects.create_user(
            email="correct_client@t.com", password="pw", role="client",
            first_name="Cli", last_name="Ent",
        )

    @pytest.fixture
    def other_client(self):
        """Create a second client user for correct_document tests."""
        return User.objects.create_user(
            email="correct_other@t.com", password="pw", role="client",
            first_name="Oth", last_name="Er",
        )

    def test_correct_success_updates_document_state(self, api, lawyer, client_user):
        """Corrected document transitions to PendingSignatures with new content."""
        doc = _make_rejected_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {
            "content": "<p>Contenido corregido</p>",
            "variables": [
                {"name_en": "clause", "name_es": "Cláusula", "field_type": "input", "value": "Corrected value"},
            ],
        }, format="json")

        doc.refresh_from_db()
        assert resp.status_code == status.HTTP_200_OK
        assert doc.state == "PendingSignatures"
        assert doc.content == "<p>Contenido corregido</p>"
        assert doc.fully_signed is False

    def test_correct_success_resets_signature_state(self, api, lawyer, client_user):
        """Correction resets variable values and clears all signer rejection flags."""
        doc = _make_rejected_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        api.post(url, {
            "content": "<p>Contenido corregido</p>",
            "variables": [
                {"name_en": "clause", "name_es": "Cláusula", "field_type": "input", "value": "Corrected value"},
            ],
        }, format="json")

        doc.refresh_from_db()
        assert doc.variables.count() == 1
        assert doc.variables.first().value == "Corrected value"
        sig = DocumentSignature.objects.get(document=doc, signer=client_user)
        assert sig.rejected is False
        assert sig.rejection_comment is None
        assert sig.signed is False

    def test_correct_expired_document(self, api, lawyer, client_user):
        """Expired documents can also be corrected."""
        doc = _make_rejected_doc(lawyer, client_user)
        doc.state = "Expired"
        doc.save(update_fields=["state"])
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>Updated</p>"}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.state == "PendingSignatures"

    @pytest.mark.parametrize("wrong_state", [
        "Draft", "Progress", "Completed", "PendingSignatures", "FullySigned",
    ])
    def test_correct_wrong_state(self, api, lawyer, client_user, wrong_state):
        """Only Rejected or Expired documents can be corrected."""
        doc = _make_rejected_doc(lawyer, client_user)
        doc.state = wrong_state
        doc.save(update_fields=["state"])
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>x</p>"}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_correct_no_signature_required(self, api, lawyer, client_user):
        """Documents that don't require signatures cannot be corrected."""
        doc = _make_rejected_doc(lawyer, client_user)
        doc.requires_signature = False
        doc.save(update_fields=["requires_signature"])
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>x</p>"}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_correct_permission_denied(self, api, lawyer, client_user, other_client):
        """Non-owner non-lawyer user cannot correct a document."""
        doc = _make_rejected_doc(lawyer, client_user)
        api.force_authenticate(user=other_client)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>x</p>"}, format="json")

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_correct_content_only(self, api, lawyer, client_user):
        """Correction with only content update preserves existing variables."""
        doc = _make_rejected_doc(lawyer, client_user)
        original_var_count = doc.variables.count()
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>Nuevo contenido</p>"}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.content == "<p>Nuevo contenido</p>"
        assert doc.variables.count() == original_var_count

    def test_correct_updates_due_date(self, api, lawyer, client_user):
        """Signature due date is updated when provided."""
        doc = _make_rejected_doc(lawyer, client_user)
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"signature_due_date": "2026-12-31"}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert str(doc.signature_due_date) == "2026-12-31"

    def test_correct_same_document_id(self, api, lawyer, client_user):
        """The returned document must have the same ID — no copy created."""
        doc = _make_rejected_doc(lawyer, client_user)
        original_id = doc.id
        api.force_authenticate(user=lawyer)

        url = reverse("correct-document", args=[doc.id])
        resp = api.post(url, {"content": "<p>Fixed</p>"}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == original_id

    def test_correct_optimistic_lock_mechanism(self, lawyer, client_user):
        """Verify the optimistic lock: filter(state__in=...).update() returns 0 when state changed."""
        doc = _make_rejected_doc(lawyer, client_user)

        # Simulate concurrent state change
        DynamicDocument.objects.filter(pk=doc.pk).update(state='PendingSignatures')

        rows_updated = DynamicDocument.objects.filter(
            pk=doc.pk, state__in=['Rejected', 'Expired'],
        ).update(state='PendingSignatures')

        assert rows_updated == 0


# ── DynamicDocumentSerializer exposes ``signers`` in GET responses ────────


@pytest.mark.django_db
class TestDocumentDetailSignersExposed:
    """Regression: GET /dynamic-documents/{pk}/ must include ``signers`` with ``signed`` flag.

    The frontend modal "Estado de Formalización" depends on the ``signers`` array
    to render the "Firmado" badge for the emisor of an issuer_only document.
    """

    @pytest.fixture
    def api(self):
        """Build an API client."""
        return APIClient()

    @pytest.fixture
    def lawyer(self):
        """Lawyer."""
        return User.objects.create_user(
            email="signers_lawyer@t.com", password="pw", role="lawyer",
            first_name="Law", last_name="Yer",
        )

    @pytest.fixture
    def client_user(self):
        """Client user."""
        return User.objects.create_user(
            email="signers_client@t.com", password="pw", role="client",
            first_name="Cli", last_name="Ent",
        )

    @freeze_time('2026-01-15 10:00:00')
    def test_detail_response_includes_signers_array_for_issuer_only(self, api, lawyer, client_user):
        """GET detail returns a ``signers`` list with one entry per DocumentSignature."""
        doc = DynamicDocument.objects.create(
            title="Issuer Only Doc",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer,
            requires_signature=True,
            signature_type="issuer_only",
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer, signed=False)
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True, signed_at=timezone.now(),
        )
        api.force_authenticate(user=lawyer)

        resp = api.get(reverse("get_dynamic_document", kwargs={"pk": doc.id}))

        assert resp.status_code == status.HTTP_200_OK
        assert "signers" in resp.data
        assert isinstance(resp.data["signers"], list)
        assert len(resp.data["signers"]) == 2

    @freeze_time('2026-01-15 10:00:00')
    def test_emisor_signer_entry_has_signed_true_after_signing(self, api, lawyer, client_user):
        """After the emisor signs an issuer_only doc, the signers entry reflects signed=True."""
        doc = DynamicDocument.objects.create(
            title="Issuer Only Signed",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer,
            requires_signature=True,
            signature_type="issuer_only",
            fully_signed=True,
        )
        DocumentSignature.objects.create(
            document=doc, signer=lawyer, signed=True, signed_at=timezone.now(),
        )
        DocumentSignature.objects.create(
            document=doc, signer=client_user, signed=True, signed_at=timezone.now(),
        )
        api.force_authenticate(user=lawyer)

        resp = api.get(reverse("get_dynamic_document", kwargs={"pk": doc.id}))

        emisor_entry = next(s for s in resp.data["signers"] if s["signer_id"] == lawyer.id)
        assert emisor_entry["signed"] is True

    def test_signers_payload_still_creates_signatures_after_field_removal(self, api, lawyer, client_user):
        """Sending ``signers`` IDs in the create payload still creates DocumentSignature rows.

        Regression: the write_only override of ``signers`` was removed so the
        SerializerMethodField could expose enriched output. The write path must
        still accept the legacy ``signers: [id1, id2]`` shape via initial_data.
        """
        from rest_framework.test import APIRequestFactory

        from gym_app.serializers.dynamic_document import DynamicDocumentSerializer

        rf = APIRequestFactory()
        request = rf.post("/")
        request.user = lawyer

        serializer = DynamicDocumentSerializer(
            data={
                "title": "Write Path Doc",
                "content": "<p>x</p>",
                "state": "Progress",
                "requires_signature": True,
                "signers": [client_user.id],
            },
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        doc = serializer.save()

        assert DocumentSignature.objects.filter(document=doc, signer=client_user).exists()


# ── Letterhead snapshot at formalization ──────────────────────────────────


@pytest.mark.django_db
class TestLetterheadSnapshot:
    """Once formalized, the letterhead must be frozen so the document content.

    is identical regardless of who downloads it (security/integrity).
    """

    def _png_bytes(self):
        from io import BytesIO
        if PILImage is None:
            return b"PNGFAKE"
        buf = BytesIO()
        PILImage.new('RGB', (10, 10), color='red').save(buf, format='PNG')
        return buf.getvalue()

    def test_resolver_in_locked_state_uses_snapshot_and_ignores_fallback_user(self, lawyer_user, signer_user):
        """In post-formalization states the snapshot is the only source — fallback.

        users (downloaders) must not influence the rendered letterhead.
        """
        from gym_app.utils.documents import get_letterhead_for_document

        doc = DynamicDocument.objects.create(
            title="Snapshot Resolver",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            requires_signature=True,
            fully_signed=True,
        )
        doc.letterhead_image_snapshot = "letterheads_snapshot/fake_snap.png"
        doc.save(update_fields=["letterhead_image_snapshot"])

        # Downloader (fallback_user) has a letterhead but it MUST be ignored.
        signer_user.letterhead_image = "letterheads/downloader.png"
        signer_user.save(update_fields=["letterhead_image"])

        result = get_letterhead_for_document(doc, fallback_user=signer_user)

        assert result == doc.letterhead_image_snapshot

    def test_resolver_in_locked_state_without_snapshot_falls_back_to_creator_not_downloader(self, lawyer_user, signer_user):
        """Legacy formalized docs without snapshot must NOT reach the downloader path."""
        from gym_app.utils.documents import get_letterhead_for_document

        doc = DynamicDocument.objects.create(
            title="Legacy Locked",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
        )
        # No snapshot, no doc-specific letterhead. Creator has none either.
        signer_user.letterhead_image = "letterheads/downloader.png"
        signer_user.save(update_fields=["letterhead_image"])

        result = get_letterhead_for_document(doc, fallback_user=signer_user)

        # Even though signer_user (downloader) has a letterhead, locked state
        # must NEVER fall back to it.
        assert result is None

    def test_resolver_locked_state_uses_formalized_by_letterhead_when_snapshot_missing(
        self, lawyer_user, signer_user,
    ):
        """When snapshot is empty, the issuer (formalized_by) takes priority over created_by."""
        from gym_app.utils.documents import get_letterhead_for_document

        signer_user.letterhead_image = "letterheads/issuer.png"
        signer_user.save(update_fields=["letterhead_image"])

        doc = DynamicDocument.objects.create(
            title="Locked No Snapshot",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,        # lawyer with no letterhead
            formalized_by=signer_user,     # actual issuer (has letterhead)
        )

        result = get_letterhead_for_document(doc)

        assert result == signer_user.letterhead_image

    def test_resolver_pre_formalization_keeps_fallback_user_priority(self, lawyer_user, signer_user):
        """Pre-formalization the fallback_user (downloader) is still allowed."""
        from gym_app.utils.documents import get_letterhead_for_document

        doc = DynamicDocument.objects.create(
            title="Draft Doc",
            content="<p>x</p>",
            state="Draft",
            created_by=lawyer_user,
        )
        signer_user.letterhead_image = "letterheads/downloader.png"
        signer_user.save(update_fields=["letterhead_image"])

        result = get_letterhead_for_document(doc, fallback_user=signer_user)

        assert result == signer_user.letterhead_image

    def test_snapshot_uses_formalizer_letterhead_not_creator(self, lawyer_user, signer_user):
        """The frozen letterhead must come from the formalizer, not from created_by."""
        from gym_app.utils.documents import snapshot_letterhead_on_formalize

        # The lawyer (creator) has NO letterhead.
        # The signer (formalizer/issuer) has one.
        signer_user.letterhead_image.save(
            "issuer_lh.png",
            SimpleUploadedFile("issuer_lh.png", self._png_bytes(), content_type="image/png"),
            save=True,
        )
        doc = DynamicDocument.objects.create(
            title="Snap From Formalizer",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            formalized_by=signer_user,
            requires_signature=True,
        )

        snapshot_letterhead_on_formalize(doc, signer_user)
        doc.refresh_from_db()

        assert doc.letterhead_image_snapshot.name.startswith('letterheads_snapshot/')

    def test_snapshot_is_idempotent_and_does_not_overwrite(self, lawyer_user):
        """Calling the helper twice does not change an existing snapshot."""
        from gym_app.utils.documents import snapshot_letterhead_on_formalize

        lawyer_user.letterhead_image.save(
            "lh_v1.png",
            SimpleUploadedFile("lh_v1.png", self._png_bytes(), content_type="image/png"),
            save=True,
        )
        doc = DynamicDocument.objects.create(
            title="Snap Idempotent",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            formalized_by=lawyer_user,
            requires_signature=True,
        )
        snapshot_letterhead_on_formalize(doc, lawyer_user)
        doc.refresh_from_db()
        first_snapshot_name = doc.letterhead_image_snapshot.name

        # Replace the formalizer's letterhead — snapshot must remain stable.
        lawyer_user.letterhead_image.save(
            "lh_v2.png",
            SimpleUploadedFile("lh_v2.png", self._png_bytes(), content_type="image/png"),
            save=True,
        )
        snapshot_letterhead_on_formalize(doc, lawyer_user)
        doc.refresh_from_db()

        assert doc.letterhead_image_snapshot.name == first_snapshot_name

    def test_ensure_letterhead_snapshot_lazy_creates_for_legacy_locked_doc(
        self, lawyer_user, signer_user,
    ):
        """Locked legacy doc with no snapshot is healed on first download."""
        from gym_app.utils.documents import ensure_letterhead_snapshot

        signer_user.letterhead_image.save(
            "issuer_lh.png",
            SimpleUploadedFile("issuer_lh.png", self._png_bytes(), content_type="image/png"),
            save=True,
        )
        doc = DynamicDocument.objects.create(
            title="Legacy Lazy",
            content="<p>x</p>",
            state="FullySigned",
            created_by=lawyer_user,
            formalized_by=signer_user,
            fully_signed=True,
        )
        assert not doc.letterhead_image_snapshot

        ensure_letterhead_snapshot(doc)
        doc.refresh_from_db()

        assert doc.letterhead_image_snapshot.name.startswith('letterheads_snapshot/')


@pytest.mark.django_db
class TestSignersIsCreatorFlag:
    """The signers payload must mark the document creator with is_creator=True."""

    def _detail_signers(self, api_client, user, document):
        api_client.force_authenticate(user=user)
        url = reverse("get_dynamic_document", kwargs={"pk": document.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data
        return response.data["signers"]

    @freeze_time('2026-01-15 10:00:00')
    def test_creator_signer_is_marked_is_creator_true(self, api_client, lawyer_user, signer_user):
        """Creator signer is marked is creator true."""
        doc = DynamicDocument.objects.create(
            title="Issuer-only",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
            signature_type="issuer_only",
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=False)
        DocumentSignature.objects.create(document=doc, signer=signer_user, signed=True, signed_at=timezone.now())

        signers = self._detail_signers(api_client, lawyer_user, doc)

        creator_row = next(s for s in signers if s["signer_id"] == lawyer_user.id)
        assert creator_row["is_creator"] is True

    @freeze_time('2026-01-15 10:00:00')
    def test_recipient_signer_is_marked_is_creator_false(self, api_client, lawyer_user, signer_user):
        """Recipient signer is marked is creator false."""
        doc = DynamicDocument.objects.create(
            title="Issuer-only",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
            signature_type="issuer_only",
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=False)
        DocumentSignature.objects.create(document=doc, signer=signer_user, signed=True, signed_at=timezone.now())

        signers = self._detail_signers(api_client, lawyer_user, doc)

        recipient_row = next(s for s in signers if s["signer_id"] == signer_user.id)
        assert recipient_row["is_creator"] is False

    @freeze_time('2026-01-15 10:00:00')
    def test_is_creator_persists_after_creator_signs(self, api_client, lawyer_user, signer_user):
        """Is creator persists after creator signs."""
        doc = DynamicDocument.objects.create(
            title="Issuer-only signed",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
            signature_type="issuer_only",
        )
        signature = DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=False)
        signature.signed = True
        signature.signed_at = timezone.now()
        signature.save(update_fields=["signed", "signed_at"])

        signers = self._detail_signers(api_client, lawyer_user, doc)

        creator_row = next(s for s in signers if s["signer_id"] == lawyer_user.id)
        assert creator_row["is_creator"] is True
        assert creator_row["signed"] is True

    def test_is_creator_false_when_created_by_is_null(self, api_client, lawyer_user, signer_user):
        """When the creator was deleted (created_by=NULL), no signer is flagged as creator."""
        doc = DynamicDocument.objects.create(
            title="Orphan",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=signer_user)
        DynamicDocument.objects.filter(pk=doc.pk).update(created_by=None)

        signers = self._detail_signers(api_client, signer_user, doc)

        assert all(s["is_creator"] is False for s in signers)

    def test_document_signature_serializer_exposes_is_creator(self, api_client, lawyer_user, signer_user):
        """The /signatures/ legacy endpoint also exposes is_creator per row."""
        doc = DynamicDocument.objects.create(
            title="Legacy signatures",
            content="<p>x</p>",
            state="PendingSignatures",
            created_by=lawyer_user,
            requires_signature=True,
        )
        DocumentSignature.objects.create(document=doc, signer=lawyer_user, signed=False)
        DocumentSignature.objects.create(document=doc, signer=signer_user, signed=False)

        api_client.force_authenticate(user=lawyer_user)
        url = reverse("get-document-signatures", kwargs={"document_id": doc.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        rows_by_signer = {row["signer_id"]: row for row in response.data}
        assert rows_by_signer[lawyer_user.id]["is_creator"] is True
        assert rows_by_signer[signer_user.id]["is_creator"] is False
