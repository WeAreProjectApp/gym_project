"""Tests for dynamic_document_letterhead module."""
import io
import os

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from gym_app.models import DynamicDocument

User = get_user_model()
@pytest.fixture
def lawyer_user():
    """Lawyer user."""
    return User.objects.create_user(
        email="lawyer@example.com",
        password="testpassword",
        role="lawyer",
    )


@pytest.fixture
def basic_user():
    """Create a basic user."""
    return User.objects.create_user(
        email="basic@example.com",
        password="testpassword",
        role="basic",
    )


@pytest.fixture
def document(lawyer_user):
    """Document."""
    return DynamicDocument.objects.create(
        title="Doc letterhead",
        content="<p>x</p>",
        state="Draft",
        created_by=lawyer_user,
    )


@pytest.mark.django_db
class TestUserGlobalLetterhead:
    """Tests for User Global Letterhead."""

    def test_upload_user_letterhead_image_basic_user_forbidden(self, api_client, basic_user):
        """Verify upload user letterhead image basic user forbidden."""
        api_client.force_authenticate(user=basic_user)

        url = reverse("upload-user-letterhead-image")
        image = SimpleUploadedFile("membrete.png", b"fake-bytes", content_type="image/png")
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Los usuarios básicos" in response.data["error"]

    def test_upload_user_letterhead_image_no_image(self, api_client, lawyer_user):
        """Verify upload user letterhead image no image."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-user-letterhead-image")
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Se requiere un archivo de imagen" in response.data["detail"]

    def test_upload_user_letterhead_image_wrong_extension(self, api_client, lawyer_user):
        """Verify upload user letterhead image wrong extension."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-user-letterhead-image")
        image = SimpleUploadedFile("membrete.jpg", b"fake-bytes", content_type="image/jpeg")
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Solo se permiten archivos PNG" in response.data["detail"]

    def test_upload_user_letterhead_image_too_large(self, api_client, lawyer_user):
        """Verify upload user letterhead image too large."""
        api_client.force_authenticate(user=lawyer_user)

        large_content = b"0" * (10 * 1024 * 1024 + 1)
        image = SimpleUploadedFile("membrete.png", large_content, content_type="image/png")

        url = reverse("upload-user-letterhead-image")
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "demasiado grande" in response.data["detail"].lower()

    def test_upload_user_letterhead_image_invalid_image(self, api_client, lawyer_user):
        """Verify upload user letterhead image invalid image."""
        api_client.force_authenticate(user=lawyer_user)

        image = SimpleUploadedFile("membrete.png", b"not-an-image", content_type="image/png")

        url = reverse("upload-user-letterhead-image")
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "imagen inválido" in response.data["detail"].lower()

    def test_get_user_letterhead_image_not_configured(self, api_client, lawyer_user):
        """Verify get user letterhead image not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-user-letterhead-image")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No tienes una imagen de membrete global configurada" in response.data["detail"]

    def test_delete_user_letterhead_image_not_configured(self, api_client, lawyer_user):
        """Verify delete user letterhead image not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-user-letterhead-image")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "para eliminar" in response.data["detail"].lower()

    def test_delete_user_letterhead_image_basic_user_forbidden(self, api_client, basic_user):
        """Verify delete user letterhead image basic user forbidden."""
        api_client.force_authenticate(user=basic_user)

        url = reverse("delete-user-letterhead-image")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Los usuarios básicos" in response.data["error"]

    def test_get_user_letterhead_image_internal_error(self, api_client, lawyer_user, settings, tmp_path, monkeypatch):
        """Verify get user letterhead image internal error."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")
        lawyer_user.letterhead_image = image
        lawyer_user.save(update_fields=["letterhead_image"])

        url = reverse("get-user-letterhead-image")

        def raise_error(*args, **kwargs):
            raise Exception("boom")

        monkeypatch.setattr(os.path, "exists", raise_error)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error al obtener la imagen" in response.data["detail"]

    def test_delete_user_letterhead_image_internal_error(self, api_client, lawyer_user, settings, tmp_path, monkeypatch):
        """Verify delete user letterhead image internal error."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")
        lawyer_user.letterhead_image = image
        lawyer_user.save(update_fields=["letterhead_image"])

        def raise_error(*args, **kwargs):
            raise Exception("boom")

        monkeypatch.setattr(User, "save", raise_error)

        url = reverse("delete-user-letterhead-image")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error al eliminar la imagen" in response.data["detail"]

    def test_upload_get_delete_user_letterhead_image_success(self, api_client, lawyer_user, settings, tmp_path):
        """Verify upload get delete user letterhead image success."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")

        upload_url = reverse("upload-user-letterhead-image")
        response = api_client.post(upload_url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        lawyer_user.refresh_from_db()
        assert lawyer_user.letterhead_image is not None
        assert lawyer_user.letterhead_image.name != ""

        get_url = reverse("get-user-letterhead-image")
        response = api_client.get(get_url)

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/png"

        delete_url = reverse("delete-user-letterhead-image")
        response = api_client.delete(delete_url)

        assert response.status_code == status.HTTP_200_OK
        lawyer_user.refresh_from_db()
        assert not lawyer_user.letterhead_image

    def test_upload_user_letterhead_image_warning_aspect_ratio(self, api_client, lawyer_user, settings, tmp_path):
        """Verify upload user letterhead image warning aspect ratio."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (800, 800), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")

        upload_url = reverse("upload-user-letterhead-image")
        response = api_client.post(upload_url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert "warnings" in response.data

    def test_get_user_letterhead_image_missing_file(self, api_client, lawyer_user, settings, tmp_path):
        """Verify get user letterhead image missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")
        lawyer_user.letterhead_image = image
        lawyer_user.save(update_fields=["letterhead_image"])

        file_path = lawyer_user.letterhead_image.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("get-user-letterhead-image")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no se encuentra en el servidor" in response.data["detail"].lower()

    def test_delete_document_word_template_missing_file(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify delete document word template missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile(
            "doc-template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        document.letterhead_word_template = template
        document.save(update_fields=["letterhead_word_template"])

        file_path = document.letterhead_word_template.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert not document.letterhead_word_template

    def test_delete_user_word_template_missing_file(self, api_client, lawyer_user, settings, tmp_path):
        """Verify delete user word template missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile(
            "template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        lawyer_user.letterhead_word_template = template
        lawyer_user.save(update_fields=["letterhead_word_template"])

        file_path = lawyer_user.letterhead_word_template.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("delete-user-letterhead-word-template")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        lawyer_user.refresh_from_db()
        assert not lawyer_user.letterhead_word_template

    def test_delete_letterhead_image_missing_file(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify delete letterhead image missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("doc.png", buffer.read(), content_type="image/png")
        document.letterhead_image = image
        document.save(update_fields=["letterhead_image"])

        file_path = document.letterhead_image.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("delete-letterhead-image", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert not document.letterhead_image

    def test_delete_user_letterhead_image_missing_file(self, api_client, lawyer_user, settings, tmp_path):
        """Verify delete user letterhead image missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("membrete.png", buffer.read(), content_type="image/png")
        lawyer_user.letterhead_image = image
        lawyer_user.save(update_fields=["letterhead_image"])

        file_path = lawyer_user.letterhead_image.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("delete-user-letterhead-image")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        lawyer_user.refresh_from_db()
        assert not lawyer_user.letterhead_image


@pytest.mark.django_db
class TestDocumentLetterhead:
    """Tests for Document Letterhead."""

    def test_upload_letterhead_image_no_image(self, api_client, lawyer_user, document):
        """Verify upload letterhead image no image."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No se proporcionó ninguna imagen" in response.data["detail"]

    def test_upload_letterhead_image_wrong_extension(self, api_client, lawyer_user, document):
        """Verify upload letterhead image wrong extension."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        image = SimpleUploadedFile("doc.jpg", b"fake-bytes", content_type="image/jpeg")
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Solo se permiten archivos PNG" in response.data["detail"]

    def test_upload_letterhead_image_too_large(self, api_client, lawyer_user, document):
        """Verify upload letterhead image too large."""
        api_client.force_authenticate(user=lawyer_user)

        large_content = b"0" * (10 * 1024 * 1024 + 1)
        image = SimpleUploadedFile("doc.png", large_content, content_type="image/png")

        url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "demasiado grande" in response.data["detail"].lower()

    def test_upload_letterhead_image_invalid_image(self, api_client, lawyer_user, document):
        """Verify upload letterhead image invalid image."""
        api_client.force_authenticate(user=lawyer_user)

        image = SimpleUploadedFile("doc.png", b"not-an-image", content_type="image/png")

        url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "imagen inválido" in response.data["detail"].lower()

    def test_get_letterhead_image_not_configured(self, api_client, lawyer_user, document):
        """Verify get letterhead image not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-letterhead-image", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no tiene imagen de membrete" in response.data["detail"]

    def test_get_letterhead_image_not_found(self, api_client, lawyer_user):
        """Verify get letterhead image not found."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-letterhead-image", kwargs={"pk": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_get_letterhead_image_forbidden_when_no_visibility(self, api_client, lawyer_user, document):
        """Verify get letterhead image forbidden when no visibility."""
        client_user = User.objects.create_user(
            email="client@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("get-letterhead-image", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to view" in response.data["detail"].lower()

    def test_delete_letterhead_image_not_configured(self, api_client, lawyer_user, document):
        """Verify delete letterhead image not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-letterhead-image", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "para eliminar" in response.data["detail"].lower()

    def test_delete_letterhead_image_not_found(self, api_client, lawyer_user):
        """Verify delete letterhead image not found."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-letterhead-image", kwargs={"pk": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_delete_letterhead_image_forbidden_when_no_usability(self, api_client, lawyer_user, document):
        """Verify delete letterhead image forbidden when no usability."""
        client_user = User.objects.create_user(
            email="client2@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("delete-letterhead-image", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to access" in response.data["detail"].lower()

    def test_upload_letterhead_image_not_found(self, api_client, lawyer_user):
        """Verify upload letterhead image not found."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-letterhead-image", kwargs={"pk": 9999})
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_upload_letterhead_image_forbidden_when_no_usability(self, api_client, lawyer_user, document):
        """Verify upload letterhead image forbidden when no usability."""
        client_user = User.objects.create_user(
            email="client3@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to access" in response.data["detail"].lower()

    def test_upload_get_delete_letterhead_image_success(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify upload get delete letterhead image success."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("doc.png", buffer.read(), content_type="image/png")

        upload_url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(upload_url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        document.refresh_from_db()
        assert document.letterhead_image is not None
        assert document.letterhead_image.name != ""

        get_url = reverse("get-letterhead-image", kwargs={"pk": document.id})
        response = api_client.get(get_url)

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/png"

        delete_url = reverse("delete-letterhead-image", kwargs={"pk": document.id})
        response = api_client.delete(delete_url)

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert not document.letterhead_image

    def test_upload_letterhead_image_warning_aspect_ratio(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify upload letterhead image warning aspect ratio."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (800, 800), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("doc.png", buffer.read(), content_type="image/png")

        upload_url = reverse("upload-letterhead-image", kwargs={"pk": document.id})
        response = api_client.post(upload_url, {"image": image}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert "warnings" in response.data

    def test_get_letterhead_image_missing_file(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify get letterhead image missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        img = Image.new("RGB", (612, 792), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        image = SimpleUploadedFile("doc.png", buffer.read(), content_type="image/png")
        document.letterhead_image = image
        document.save(update_fields=["letterhead_image"])

        file_path = document.letterhead_image.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("get-letterhead-image", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no se encuentra en el servidor" in response.data["detail"].lower()


@pytest.mark.django_db
class TestUserWordLetterheadTemplate:
    """Tests for User Word Letterhead Template."""

    def test_upload_user_word_template_basic_user_forbidden(self, api_client, basic_user):
        """Verify upload user word template basic user forbidden."""
        api_client.force_authenticate(user=basic_user)

        url = reverse("upload-user-letterhead-word-template")
        template = SimpleUploadedFile(
            "template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Los usuarios básicos" in response.data["error"]

    def test_delete_user_word_template_basic_user_forbidden(self, api_client, basic_user):
        """Verify delete user word template basic user forbidden."""
        api_client.force_authenticate(user=basic_user)

        url = reverse("delete-user-letterhead-word-template")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Los usuarios básicos" in response.data["error"]

    def test_upload_user_word_template_missing_file(self, api_client, lawyer_user):
        """Verify upload user word template missing file."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-user-letterhead-word-template")
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Se requiere un archivo de plantilla" in response.data["detail"]

    def test_upload_user_word_template_invalid_extension(self, api_client, lawyer_user):
        """Verify upload user word template invalid extension."""
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile("template.txt", b"docx-content", content_type="text/plain")

        url = reverse("upload-user-letterhead-word-template")
        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Solo se permiten archivos .docx" in response.data["detail"]

    def test_get_user_word_template_not_configured(self, api_client, lawyer_user):
        """Verify get user word template not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-user-letterhead-word-template")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "plantilla word de membrete global configurada" in response.data["detail"].lower()

    def test_delete_user_word_template_not_configured(self, api_client, lawyer_user):
        """Verify delete user word template not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-user-letterhead-word-template")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "para eliminar" in response.data["detail"].lower()

    def test_upload_get_delete_user_word_template(self, api_client, lawyer_user, settings, tmp_path):
        """Verify upload get delete user word template."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        upload_url = reverse("upload-user-letterhead-word-template")
        template = SimpleUploadedFile(
            "template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = api_client.post(upload_url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        lawyer_user.refresh_from_db()
        assert lawyer_user.letterhead_word_template is not None
        assert lawyer_user.letterhead_word_template.name != ""

        get_url = reverse("get-user-letterhead-word-template")
        response = api_client.get(get_url)

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        delete_url = reverse("delete-user-letterhead-word-template")
        response = api_client.delete(delete_url)

        assert response.status_code == status.HTTP_200_OK
        lawyer_user.refresh_from_db()
        assert not lawyer_user.letterhead_word_template

    def test_upload_user_word_template_too_large(self, api_client, lawyer_user):
        """Verify upload user word template too large."""
        api_client.force_authenticate(user=lawyer_user)

        large_content = b"0" * (10 * 1024 * 1024 + 1)
        template = SimpleUploadedFile(
            "template.docx",
            large_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        url = reverse("upload-user-letterhead-word-template")
        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "demasiado grande" in response.data["detail"].lower()

    def test_get_user_word_template_missing_file(self, api_client, lawyer_user, settings, tmp_path):
        """Verify get user word template missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile(
            "template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        lawyer_user.letterhead_word_template = template
        lawyer_user.save(update_fields=["letterhead_word_template"])

        file_path = lawyer_user.letterhead_word_template.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("get-user-letterhead-word-template")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no se encuentra en el servidor" in response.data["detail"].lower()


@pytest.mark.django_db
class TestDocumentWordLetterheadTemplate:
    """Tests for Document Word Letterhead Template."""

    def test_get_document_word_template_forbidden_when_no_visibility(self, api_client, lawyer_user, document):
        """Verify get document word template forbidden when no visibility."""
        client_user = User.objects.create_user(
            email="client4@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("get-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to view" in response.data["detail"].lower()

    def test_delete_document_word_template_forbidden_when_no_usability(self, api_client, lawyer_user, document):
        """Verify delete document word template forbidden when no usability."""
        client_user = User.objects.create_user(
            email="client5@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to access" in response.data["detail"].lower()

    def test_upload_document_word_template_forbidden_when_no_usability(self, api_client, lawyer_user, document):
        """Verify upload document word template forbidden when no usability."""
        client_user = User.objects.create_user(
            email="client6@example.com",
            password="testpassword",
            role="client",
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to access" in response.data["detail"].lower()
    def test_upload_document_word_template_missing_file(self, api_client, lawyer_user, document):
        """Verify upload document word template missing file."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.post(url, {}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Se requiere un archivo de plantilla" in response.data["detail"]

    def test_upload_document_word_template_invalid_extension(self, api_client, lawyer_user, document):
        """Verify upload document word template invalid extension."""
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile("doc-template.txt", b"docx-content", content_type="text/plain")

        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Solo se permiten archivos .docx" in response.data["detail"]

    def test_get_document_word_template_not_configured(self, api_client, lawyer_user, document):
        """Verify get document word template not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "plantilla word de membrete" in response.data["detail"].lower()

    def test_delete_document_word_template_not_configured(self, api_client, lawyer_user, document):
        """Verify delete document word template not configured."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "para eliminar" in response.data["detail"].lower()

    def test_get_document_word_template_not_found(self, api_client, lawyer_user):
        """Verify get document word template not found."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("get-document-letterhead-word-template", kwargs={"pk": 9999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_delete_document_word_template_not_found(self, api_client, lawyer_user):
        """Verify delete document word template not found."""
        api_client.force_authenticate(user=lawyer_user)

        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": 9999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_upload_document_word_template_not_found(self, api_client, lawyer_user):
        """Verify upload document word template not found."""
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile(
            "doc-template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": 9999})
        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "document not found" in response.data["detail"].lower()

    def test_upload_get_delete_document_word_template(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify upload get delete document word template."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        upload_url = reverse("upload-document-letterhead-word-template", kwargs={"pk": document.id})
        template = SimpleUploadedFile(
            "doc-template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = api_client.post(upload_url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        document.refresh_from_db()
        assert document.letterhead_word_template is not None
        assert document.letterhead_word_template.name != ""

        get_url = reverse("get-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.get(get_url)

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        delete_url = reverse("delete-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.delete(delete_url)

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert not document.letterhead_word_template

    def test_upload_document_word_template_too_large(self, api_client, lawyer_user, document):
        """Verify upload document word template too large."""
        api_client.force_authenticate(user=lawyer_user)

        large_content = b"0" * (10 * 1024 * 1024 + 1)
        template = SimpleUploadedFile(
            "doc-template.docx",
            large_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.post(url, {"template": template}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "demasiado grande" in response.data["detail"].lower()

    def test_get_document_word_template_missing_file(self, api_client, lawyer_user, document, settings, tmp_path):
        """Verify get document word template missing file."""
        settings.MEDIA_ROOT = tmp_path
        api_client.force_authenticate(user=lawyer_user)

        template = SimpleUploadedFile(
            "doc-template.docx",
            b"docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        document.letterhead_word_template = template
        document.save(update_fields=["letterhead_word_template"])

        file_path = document.letterhead_word_template.path
        if os.path.exists(file_path):
            os.remove(file_path)

        url = reverse("get-document-letterhead-word-template", kwargs={"pk": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no se encuentra en el servidor" in response.data["detail"].lower()


# ======================================================================
# Tests migrated from test_views_batch10.py
# ======================================================================

"""
Batch 10 – 20 tests for document_views.py letterhead and word template endpoints.

Targets uncovered lines:
  - upload/get/delete_letterhead_image DoesNotExist paths (925-931, 967-973, 998-999, 1010-1016)
  - upload/get/delete_document_letterhead_word_template DoesNotExist (1059-1063, 1080-1086, 1119-1125, 1148-1149, 1159-1165)
  - upload/get/delete_user_letterhead_word_template (1208-1212, 1229-1230, 1262-1263, 1290-1291, 1301-1302)
  - upload/get/delete_user_letterhead_image (1328, 1332, 1421-1425, 1448-1449, 1525-1526)
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models.dynamic_document import DynamicDocument  # noqa: F811

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def b10_lawyer_user():
    """B10 lawyer user."""
    return User.objects.create_user(
        email="lawyer_b10@test.com", password="pw", role="lawyer",
        first_name="Law", last_name="Yer",
    )


@pytest.fixture
def b10_basic_user():
    """B10 basic user."""
    return User.objects.create_user(
        email="basic_b10@test.com", password="pw", role="basic",
    )


@pytest.fixture
def b10_document(b10_lawyer_user):
    """B10 document."""
    return DynamicDocument.objects.create(
        title="Doc B10", content="<p>Hello</p>", state="Draft",
        created_by=b10_lawyer_user, is_public=True,
    )


# ===========================================================================
# 1. Document letterhead image – DoesNotExist / error paths
# ===========================================================================

@pytest.mark.django_db
class TestDocumentLetterheadImage:
    """Tests for Document Letterhead Image."""

    def test_upload_letterhead_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 925-931: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-letterhead-image", kwargs={"pk": 99999})
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_letterhead_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 967-973: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-letterhead-image", kwargs={"pk": 99999})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_letterhead_no_image(self, api_client, b10_lawyer_user, b10_document):
        """Line 946-950: document has no letterhead image."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-letterhead-image", kwargs={"pk": b10_document.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_letterhead_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 1010-1016: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-letterhead-image", kwargs={"pk": 99999})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_letterhead_no_image(self, api_client, b10_lawyer_user, b10_document):
        """Line 988-992: document has no letterhead to delete."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-letterhead-image", kwargs={"pk": b10_document.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 2. Document word template – DoesNotExist / error paths
# ===========================================================================

@pytest.mark.django_db
class TestDocumentWordTemplate:
    """Tests for Document Word Template."""

    def test_upload_word_template_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 1080-1086: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": 99999})
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_word_template_no_file(self, api_client, b10_lawyer_user, b10_document):
        """Line 1034-1038: no template file provided."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": b10_document.id})
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_word_template_wrong_extension(self, api_client, b10_lawyer_user, b10_document):
        """Line 1043-1047: non-docx extension."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": b10_document.id})
        f = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        resp = api_client.post(url, {"template": f}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_word_template_too_large(self, api_client, b10_lawyer_user, b10_document):
        """Line 1050-1055: file too large."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-document-letterhead-word-template", kwargs={"pk": b10_document.id})
        # Create a file > 10MB
        f = SimpleUploadedFile("big.docx", b"x" * (11 * 1024 * 1024), content_type="application/octet-stream")
        resp = api_client.post(url, {"template": f}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_word_template_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 1119-1125: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-document-letterhead-word-template", kwargs={"pk": 99999})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_word_template_no_template(self, api_client, b10_lawyer_user, b10_document):
        """Line 1100-1104: no template configured."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-document-letterhead-word-template", kwargs={"pk": b10_document.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_word_template_doc_not_found(self, api_client, b10_lawyer_user):
        """Line 1159-1165: document not found."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": 99999})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_word_template_no_template(self, api_client, b10_lawyer_user, b10_document):
        """Line 1139-1143: no template to delete."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-document-letterhead-word-template", kwargs={"pk": b10_document.id})
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 3. User global word template endpoints
# ===========================================================================

@pytest.mark.django_db
class TestUserWordTemplate:
    """Tests for User Word Template."""

    def test_upload_user_word_template_no_file(self, api_client, b10_lawyer_user):
        """Line 1183-1187: no template file provided."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-user-letterhead-word-template")
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_user_word_template_wrong_ext(self, api_client, b10_lawyer_user):
        """Line 1192-1196: non-docx extension."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-user-letterhead-word-template")
        f = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        resp = api_client.post(url, {"template": f}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_user_word_template_too_large(self, api_client, b10_lawyer_user):
        """Line 1200-1204: file too large."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("upload-user-letterhead-word-template")
        f = SimpleUploadedFile("big.docx", b"x" * (11 * 1024 * 1024), content_type="application/octet-stream")
        resp = api_client.post(url, {"template": f}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_user_word_template_no_template(self, api_client, b10_lawyer_user):
        """Line 1243-1247: no template configured."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-user-letterhead-word-template")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_word_template_no_template(self, api_client, b10_lawyer_user):
        """Line 1281-1285: no template to delete."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-user-letterhead-word-template")
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_word_template_basic_forbidden(self, api_client, b10_basic_user):
        """Line 1273-1276: basic user forbidden."""
        api_client.force_authenticate(user=b10_basic_user)
        url = reverse("delete-user-letterhead-word-template")
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# 4. User global letterhead image endpoints
# ===========================================================================

@pytest.mark.django_db
class TestUserLetterheadImage:
    """Tests for User Letterhead Image."""

    def test_upload_user_letterhead_basic_forbidden(self, api_client, b10_basic_user):
        """Line 1359-1362: basic user forbidden."""
        api_client.force_authenticate(user=b10_basic_user)
        url = reverse("upload-user-letterhead-image")
        resp = api_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_letterhead_no_image(self, api_client, b10_lawyer_user):
        """Line 1469-1473: no letterhead image."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("get-user-letterhead-image")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_letterhead_basic_forbidden(self, api_client, b10_basic_user):
        """Line 1507-1510: basic user forbidden."""
        api_client.force_authenticate(user=b10_basic_user)
        url = reverse("delete-user-letterhead-image")
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_letterhead_no_image(self, api_client, b10_lawyer_user):
        """Line 1515-1519: no letterhead to delete."""
        api_client.force_authenticate(user=b10_lawyer_user)
        url = reverse("delete-user-letterhead-image")
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ======================================================================
# Tests migrated from test_views_batch20.py
# ======================================================================

"""Batch 20 – 20 tests: user letterhead image/word CRUD + helper."""
import io  # noqa: F811
import os  # noqa: F811

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from PIL import Image as PILImage
from rest_framework import status  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models import DynamicDocument  # noqa: F811

User = get_user_model()

@pytest.fixture
def b20_api():
    """B20 api."""
    return APIClient()

@pytest.fixture
def lawyer():
    """Lawyer."""
    return User.objects.create_user(email="law_b20@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def b20_basic_user():
    """B20 basic user."""
    return User.objects.create_user(email="basic_b20@t.com", password="pw", role="basic", first_name="B", last_name="U")

def _png(w=100, h=100):
    buf = io.BytesIO()
    PILImage.new("RGB", (w, h), color="white").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("t.png", buf.read(), content_type="image/png")

def _docx():
    from docx import Document as D
    buf = io.BytesIO(); D().save(buf); buf.seek(0)
    return SimpleUploadedFile("t.docx", buf.read(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@pytest.mark.django_db
class TestUploadUserLetterhead:
    """Tests for Upload User Letterhead."""

    def test_success(self, b20_api, lawyer):
        """Verify success."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {"image": _png()}, format="multipart").status_code == 201

    def test_no_file(self, b20_api, lawyer):
        """Verify no file."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {}, format="multipart").status_code == 400

    def test_bad_ext(self, b20_api, lawyer):
        """Verify bad ext."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {"image": SimpleUploadedFile("b.jpg", b"d", content_type="image/jpeg")}, format="multipart").status_code == 400

    def test_too_large(self, b20_api, lawyer):
        """Verify too large."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {"image": SimpleUploadedFile("b.png", b"x"*(11*1024*1024), content_type="image/png")}, format="multipart").status_code == 400

    def test_invalid_img(self, b20_api, lawyer):
        """Verify invalid img."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {"image": SimpleUploadedFile("b.png", b"bad", content_type="image/png")}, format="multipart").status_code == 400

    def test_basic_forbidden(self, b20_api, b20_basic_user):
        """Verify basic forbidden."""
        b20_api.force_authenticate(user=b20_basic_user)
        assert b20_api.post(reverse("upload-user-letterhead-image"), {"image": _png()}, format="multipart").status_code == 403

    def test_aspect_warning(self, b20_api, lawyer):
        """Verify aspect warning."""
        b20_api.force_authenticate(user=lawyer)
        r = b20_api.post(reverse("upload-user-letterhead-image"), {"image": _png(500, 100)}, format="multipart")
        assert r.status_code == 201
        assert "warnings" in r.data

@pytest.mark.django_db
class TestGetUserLetterhead:
    """Tests for Get User Letterhead."""

    def test_no_image(self, b20_api, lawyer):
        """Verify no image."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.get(reverse("get-user-letterhead-image")).status_code == 404

@pytest.mark.django_db
class TestDeleteUserLetterhead:
    """Tests for Delete User Letterhead."""

    def test_no_image(self, b20_api, lawyer):
        """Verify no image."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.delete(reverse("delete-user-letterhead-image")).status_code == 404

    def test_basic_forbidden(self, b20_api, b20_basic_user):
        """Verify basic forbidden."""
        b20_api.force_authenticate(user=b20_basic_user)
        assert b20_api.delete(reverse("delete-user-letterhead-image")).status_code == 403

    def test_success(self, b20_api, lawyer):
        """Verify success."""
        b20_api.force_authenticate(user=lawyer)
        b20_api.post(reverse("upload-user-letterhead-image"), {"image": _png()}, format="multipart")
        assert b20_api.delete(reverse("delete-user-letterhead-image")).status_code == 200

@pytest.mark.django_db
class TestUploadUserWordTpl:
    """Tests for Upload User Word Tpl."""

    def test_success(self, b20_api, lawyer):
        """Verify success."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-word-template"), {"template": _docx()}, format="multipart").status_code == 201

    def test_no_file(self, b20_api, lawyer):
        """Verify no file."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-word-template"), {}, format="multipart").status_code == 400

    def test_bad_ext(self, b20_api, lawyer):
        """Verify bad ext."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.post(reverse("upload-user-letterhead-word-template"), {"template": SimpleUploadedFile("b.txt", b"d")}, format="multipart").status_code == 400

    def test_basic_forbidden(self, b20_api, b20_basic_user):
        """Verify basic forbidden."""
        b20_api.force_authenticate(user=b20_basic_user)
        assert b20_api.post(reverse("upload-user-letterhead-word-template"), {"template": _docx()}, format="multipart").status_code == 403

@pytest.mark.django_db
class TestGetUserWordTpl:
    """Tests for Get User Word Tpl."""

    def test_no_tpl(self, b20_api, lawyer):
        """Verify no tpl."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.get(reverse("get-user-letterhead-word-template")).status_code == 404

@pytest.mark.django_db
class TestDeleteUserWordTpl:
    """Tests for Delete User Word Tpl."""

    def test_no_tpl(self, b20_api, lawyer):
        """Verify no tpl."""
        b20_api.force_authenticate(user=lawyer)
        assert b20_api.delete(reverse("delete-user-letterhead-word-template")).status_code == 404

    def test_basic_forbidden(self, b20_api, b20_basic_user):
        """Verify basic forbidden."""
        b20_api.force_authenticate(user=b20_basic_user)
        assert b20_api.delete(reverse("delete-user-letterhead-word-template")).status_code == 403

    def test_success(self, b20_api, lawyer):
        """Verify success."""
        b20_api.force_authenticate(user=lawyer)
        b20_api.post(reverse("upload-user-letterhead-word-template"), {"template": _docx()}, format="multipart")
        assert b20_api.delete(reverse("delete-user-letterhead-word-template")).status_code == 200


# ======================================================================
# Tests migrated from test_views_batch32.py
# ======================================================================

"""Batch 32 – 20 tests: document_views.py Part 2 – letterhead upload/delete, word template, user letterhead, create doc edges."""
import io  # noqa: F811

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: F811
from django.urls import reverse  # noqa: F811
from PIL import Image as PILImage  # noqa: F811
from rest_framework.test import APIClient  # noqa: F811

from gym_app.models.dynamic_document import DynamicDocument  # noqa: F811

User = get_user_model()
pytestmark = pytest.mark.django_db

@pytest.fixture
def api():
    """Create an API client."""
    return APIClient()

@pytest.fixture
def law():
    """Law."""
    return User.objects.create_user(email="law32@t.com", password="pw", role="lawyer", first_name="L", last_name="W")

@pytest.fixture
def cli():
    """Cli."""
    return User.objects.create_user(email="cli32@t.com", password="pw", role="client", first_name="C", last_name="E")

@pytest.fixture
def basic():
    """Create a basic fixture."""
    return User.objects.create_user(email="bas32@t.com", password="pw", role="basic", first_name="B", last_name="U")

def _png_file(name="test.png", w=100, h=100):
    buf = io.BytesIO()
    PILImage.new("RGB", (w, h), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


# -- upload_letterhead_image (document) --
class TestUploadDocLetterhead:
    """Tests for Upload Doc Letterhead."""

    def test_upload_no_image(self, api, law):
        """Verify upload no image."""
        doc = DynamicDocument.objects.create(title="UL1", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-letterhead-image", args=[doc.id]))
        assert resp.status_code == 400
        assert "imagen" in resp.data["detail"].lower() or "image" in resp.data["detail"].lower()

    def test_upload_wrong_extension(self, api, law):
        """Verify upload wrong extension."""
        doc = DynamicDocument.objects.create(title="UL2", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        f = SimpleUploadedFile("test.jpg", b"fake", content_type="image/jpeg")
        resp = api.post(reverse("upload-letterhead-image", args=[doc.id]), {"image": f})
        assert resp.status_code == 400
        assert "PNG" in resp.data["detail"]

    def test_upload_success(self, api, law):
        """Verify upload success."""
        doc = DynamicDocument.objects.create(title="UL3", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-letterhead-image", args=[doc.id]), {"image": _png_file()})
        assert resp.status_code == 201
        assert "message" in resp.data
        doc.refresh_from_db()
        assert doc.letterhead_image is not None


# -- delete_letterhead_image (document) --
class TestDeleteDocLetterhead:
    """Tests for Delete Doc Letterhead."""

    def test_delete_no_image(self, api, law):
        """Verify delete no image."""
        doc = DynamicDocument.objects.create(title="DL1", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-letterhead-image", args=[doc.id]))
        assert resp.status_code == 404

    def test_delete_success(self, api, law):
        """Verify delete success."""
        doc = DynamicDocument.objects.create(title="DL2", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        doc.letterhead_image = _png_file("lh.png")
        doc.save()
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-letterhead-image", args=[doc.id]))
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert not doc.letterhead_image


# -- upload_user_letterhead_image --
class TestUploadUserLetterhead:  # noqa: F811
    """Tests for Upload User Letterhead."""

    def test_basic_user_forbidden(self, api, basic):
        """Verify basic user forbidden."""
        api.force_authenticate(user=basic)
        resp = api.post(reverse("upload-user-letterhead-image"), {"image": _png_file()})
        assert resp.status_code == 403

    def test_no_image_field(self, api, law):
        """Verify no image field."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-user-letterhead-image"))
        assert resp.status_code == 400

    def test_wrong_extension(self, api, law):
        """Verify wrong extension."""
        api.force_authenticate(user=law)
        f = SimpleUploadedFile("test.gif", b"fake", content_type="image/gif")
        resp = api.post(reverse("upload-user-letterhead-image"), {"image": f})
        assert resp.status_code == 400

    def test_upload_success(self, api, law):
        """Verify upload success."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-user-letterhead-image"), {"image": _png_file()})
        assert resp.status_code == 201
        assert "message" in resp.data
        law.refresh_from_db()
        assert law.letterhead_image is not None


# -- delete_user_letterhead_image --
class TestDeleteUserLetterhead:  # noqa: F811
    """Tests for Delete User Letterhead."""

    def test_basic_user_forbidden(self, api, basic):
        """Verify basic user forbidden."""
        api.force_authenticate(user=basic)
        resp = api.delete(reverse("delete-user-letterhead-image"))
        assert resp.status_code == 403

    def test_no_image_to_delete(self, api, law):
        """Verify no image to delete."""
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-user-letterhead-image"))
        assert resp.status_code == 404

    def test_delete_success(self, api, law):
        """Verify delete success."""
        law.letterhead_image = _png_file("ulh.png")
        law.save()
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-user-letterhead-image"))
        assert resp.status_code == 200
        law.refresh_from_db()
        assert not law.letterhead_image


# -- upload_document_letterhead_word_template --
class TestUploadDocWordTemplate:
    """Tests for Upload Doc Word Template."""

    def test_no_template_field(self, api, law):
        """Verify no template field."""
        doc = DynamicDocument.objects.create(title="WT1", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-document-letterhead-word-template", args=[doc.id]))
        assert resp.status_code == 400

    def test_wrong_extension(self, api, law):
        """Verify wrong extension."""
        doc = DynamicDocument.objects.create(title="WT2", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        f = SimpleUploadedFile("test.pdf", b"fake", content_type="application/pdf")
        resp = api.post(reverse("upload-document-letterhead-word-template", args=[doc.id]), {"template": f})
        assert resp.status_code == 400

    def test_upload_success(self, api, law):
        """Verify upload success."""
        doc = DynamicDocument.objects.create(title="WT3", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        f = SimpleUploadedFile("tpl.docx", b"PK\x03\x04fakecontent", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        resp = api.post(reverse("upload-document-letterhead-word-template", args=[doc.id]), {"template": f})
        assert resp.status_code == 201
        doc.refresh_from_db()
        assert doc.letterhead_word_template is not None


# -- get/delete document word template --
class TestDocWordTemplateGetDelete:
    """Tests for Doc Word Template Get Delete."""

    def test_get_no_template(self, api, law):
        """Verify get no template."""
        doc = DynamicDocument.objects.create(title="GT1", content="<p>x</p>", state="Draft", created_by=law)
        doc.visibility_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.get(reverse("get-document-letterhead-word-template", args=[doc.id]))
        assert resp.status_code == 404

    def test_delete_no_template(self, api, law):
        """Verify delete no template."""
        doc = DynamicDocument.objects.create(title="DT1", content="<p>x</p>", state="Draft", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-document-letterhead-word-template", args=[doc.id]))
        assert resp.status_code == 404


# -- create_dynamic_document edge --
class TestCreateDynDocEdge:
    """Tests for Create Dyn Doc Edge."""

    def test_create_assigns_to_self_on_progress(self, api, cli):
        """Verify create assigns to self on progress."""
        api.force_authenticate(user=cli)
        resp = api.post(
            reverse("create_dynamic_document"),
            {"title": "CliDoc", "content": "<p>x</p>", "state": "Progress"},
            format="json",
        )
        assert resp.status_code == 201
        doc = DynamicDocument.objects.get(title="CliDoc")
        assert doc.assigned_to == cli


# -- upload_user_letterhead_word_template --
class TestUploadUserWordTemplate:
    """Tests for Upload User Word Template."""

    def test_basic_user_forbidden(self, api, basic):
        """Verify basic user forbidden."""
        api.force_authenticate(user=basic)
        f = SimpleUploadedFile("tpl.docx", b"PK\x03\x04fake", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        resp = api.post(reverse("upload-user-letterhead-word-template"), {"template": f})
        assert resp.status_code == 403

    def test_no_template_field(self, api, law):
        """Verify no template field."""
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-user-letterhead-word-template"))
        assert resp.status_code == 400


class TestLockedDocumentLetterhead:
    """HTTP 403 guard on all 4 letterhead mutation endpoints for signed documents."""

    def test_upload_png_blocked_when_pending_signatures(self, api, law):
        """Block PNG letterhead upload when document has pending signatures."""
        doc = DynamicDocument.objects.create(title="L1", content="<p>x</p>", state="PendingSignatures", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-letterhead-image", args=[doc.id]), {"image": _png_file()})
        assert resp.status_code == 403
        assert "firma" in resp.data["detail"].lower()

    def test_delete_png_blocked_when_fully_signed(self, api, law):
        """Block PNG letterhead deletion when document is fully signed."""
        doc = DynamicDocument.objects.create(title="L2", content="<p>x</p>", state="FullySigned", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-letterhead-image", args=[doc.id]))
        assert resp.status_code == 403
        assert "firma" in resp.data["detail"].lower()

    def test_upload_word_template_blocked_when_pending_signatures(self, api, law):
        """Block Word template upload when document has pending signatures."""
        doc = DynamicDocument.objects.create(title="L3", content="<p>x</p>", state="PendingSignatures", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.post(reverse("upload-document-letterhead-word-template", args=[doc.id]), {"template": _docx()}, format="multipart")
        assert resp.status_code == 403
        assert "firma" in resp.data["detail"].lower()

    def test_delete_word_template_blocked_when_fully_signed(self, api, law):
        """Block Word template deletion when document is fully signed."""
        doc = DynamicDocument.objects.create(title="L4", content="<p>x</p>", state="FullySigned", created_by=law)
        doc.usability_permissions.create(user=law, granted_by=law)
        api.force_authenticate(user=law)
        resp = api.delete(reverse("delete-document-letterhead-word-template", args=[doc.id]))
        assert resp.status_code == 403
        assert "firma" in resp.data["detail"].lower()
