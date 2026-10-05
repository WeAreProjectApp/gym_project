import json
import logging
import mimetypes
import os
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import IntegrityError, models, transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ServiceRequestPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100

from gym_app.models import (
    Service,
    ServiceField,
    ServiceRequest,
    ServiceRequestAnswer,
    ServiceRequestFieldFile,
    ServiceRequestLawyerResponse,
    ServiceRequestLawyerResponseFile,
)
from gym_app.serializers import (
    ServiceSerializer,
    ServiceListSerializer,
    ServiceRequestListSerializer,
    ServiceRequestDetailSerializer,
)
from gym_app.services.service_tramite_notifications import (
    notify_service_request_status_change,
    notify_service_request_submission,
)
from gym_app.services.service_tramite_pdf import (
    ServiceRequestPDFError,
    generate_service_request_pdf,
)


logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 200 * 1024 * 1024
DEFAULT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
ALLOWED_STATUS_TRANSITIONS = {
    "OPEN": {"IN_STUDY", "IN_PROGRESS", "ANSWERED", "FINALIZED"},
    "IN_STUDY": {"OPEN", "IN_PROGRESS", "ANSWERED", "FINALIZED"},
    "IN_PROGRESS": {"IN_STUDY", "ANSWERED", "FINALIZED"},
    "ANSWERED": {"IN_STUDY", "IN_PROGRESS", "FINALIZED"},
    "FINALIZED": set(),  # terminal state — no transitions allowed
}



def _is_admin(user):
    return bool(user.role == "admin" or user.is_staff or user.is_superuser)



def _is_lawyer(user):
    return bool(user.role == "lawyer" or user.is_gym_lawyer)



def _is_manager(user):
    return _is_admin(user) or _is_lawyer(user)



def _parse_json_payload(request):
    payload = request.data.get("payload", request.data)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            raise DRFValidationError({"payload": "JSON invalido"})
    if hasattr(payload, "dict"):
        payload = payload.dict()
    if not isinstance(payload, dict):
        raise DRFValidationError({"payload": "payload invalido"})
    return payload



def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "si", "on"}



def _uploaded_files_by_field(request):
    files_by_field = {}
    for key in request.FILES.keys():
        if not key.startswith("field_files_"):
            continue
        suffix = key.replace("field_files_", "", 1)
        try:
            field_id = int(suffix)
        except ValueError:
            continue
        files_by_field.setdefault(field_id, []).extend(request.FILES.getlist(key))
    return files_by_field



def _normalize_extensions(extensions):
    if not extensions:
        return DEFAULT_ALLOWED_EXTENSIONS

    normalized = set()
    for ext in extensions:
        ext = str(ext).strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized.add(ext)

    return normalized or DEFAULT_ALLOWED_EXTENSIONS



def _validate_field_file(uploaded_file, field):
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f"El archivo {uploaded_file.name} excede {MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    allowed = _normalize_extensions(field.allowed_extensions)
    if file_ext not in allowed:
        raise ValidationError(
            f"El archivo {uploaded_file.name} tiene extension no permitida. Permitidas: {', '.join(sorted(allowed))}"
        )



def _validate_answer_value(field, value_text, value_json):
    if field.field_type == "email" and value_text:
        validator = EmailValidator()
        validator(value_text)

    if field.field_type == "number" and value_text not in (None, ""):
        try:
            float(value_text)
        except (TypeError, ValueError):
            raise ValidationError(f"El campo {field.label} debe ser un numero valido")

    if field.field_type == "date" and value_text:
        datetime.strptime(value_text, "%Y-%m-%d")

    if field.field_type in {"select_single", "select_multiple"}:
        options = field.options or []
        if field.field_type == "select_single":
            if value_text and value_text not in options:
                raise ValidationError(f"Valor invalido para {field.label}")
        else:
            if value_json is None:
                value_json = []
            if not isinstance(value_json, list):
                raise ValidationError(f"El campo {field.label} requiere una lista")
            invalid = [item for item in value_json if item not in options]
            if invalid:
                raise ValidationError(f"Opciones invalidas para {field.label}: {invalid}")



def _save_answers_and_files(service_request, answers_payload, uploaded_files, is_submit):
    fields = ServiceField.objects.select_related("stage").filter(
        stage__service=service_request.service,
        stage__is_active=True,
    )

    field_map = {field.id: field for field in fields}
    answers_map = {}

    if isinstance(answers_payload, dict):
        iterable = answers_payload.values()
    else:
        iterable = answers_payload or []

    for item in iterable:
        if not isinstance(item, dict):
            continue
        field_id = item.get("field_id")
        try:
            field_id = int(field_id)
        except (TypeError, ValueError):
            continue
        answers_map[field_id] = item

    errors = {}

    with transaction.atomic():
        for field in fields:
            payload_item = answers_map.get(field.id, {})

            value_text = payload_item.get("value_text")
            value_json = payload_item.get("value_json")

            # Allow value fallback from generic "value" key for simpler clients
            if value_text is None and "value" in payload_item:
                if isinstance(payload_item.get("value"), list):
                    value_json = payload_item.get("value")
                else:
                    value_text = payload_item.get("value")

            if value_text is not None:
                value_text = str(value_text).strip()

            if field.field_type != "file":
                try:
                    _validate_answer_value(field, value_text, value_json)
                except (ValidationError, ValueError) as exc:
                    errors[field.key] = str(exc)

            # Required validations
            if field.field_type == "file":
                existing_count = ServiceRequestFieldFile.objects.filter(
                    service_request=service_request,
                    field=field,
                ).count()
                incoming_files = uploaded_files.get(field.id, [])

                if field.is_required and is_submit and not existing_count and not incoming_files:
                    errors[field.key] = "Este campo de archivo es obligatorio"
            else:
                empty_text = value_text in (None, "")
                empty_json = value_json in (None, [], "")
                if field.is_required and is_submit and empty_text and empty_json:
                    errors[field.key] = "Este campo es obligatorio"

            # Skip answer upsert for file fields that have new uploads —
            # the upload loop below will handle their answer after replacing files.
            if field.field_type == "file" and field.id in uploaded_files:
                continue

            answer_defaults = {
                "field": field,
                "field_label": field.label,
                "field_type": field.field_type,
                "stage_title": field.stage.title,
                "stage_order": field.stage.order,
                "value_text": value_text if field.field_type != "select_multiple" else None,
                "value_json": value_json if field.field_type in {"select_multiple", "select_single"} else None,
            }

            if field.field_type == "file":
                filenames = [
                    f.original_name or os.path.basename(f.file.name)
                    for f in ServiceRequestFieldFile.objects.filter(
                        service_request=service_request,
                        field=field,
                    )
                ]
                answer_defaults["value_json"] = filenames
                answer_defaults["value_text"] = None

            ServiceRequestAnswer.objects.update_or_create(
                service_request=service_request,
                field_key=field.key,
                defaults=answer_defaults,
            )

        if errors:
            raise ValidationError(errors)

        for field_id, files in uploaded_files.items():
            field = field_map.get(field_id)
            if not field:
                continue
            if field.field_type != "file":
                raise ValidationError({str(field_id): "Este campo no admite archivos"})

            if not field.allow_multiple_files and len(files) > 1:
                raise ValidationError({field.key: "Este campo solo admite un archivo"})

            if field.allow_multiple_files and len(files) > field.max_files:
                raise ValidationError({field.key: f"Maximo de archivos permitidos: {field.max_files}"})

            # Collect physical file paths before deleting DB records so we can
            # defer physical removal until the transaction commits.  The
            # post_delete signal would remove files immediately, which is
            # dangerous inside an atomic block — on rollback the DB rows
            # reappear but the files are already gone.
            old_qs = ServiceRequestFieldFile.objects.filter(
                service_request=service_request,
                field=field,
            )
            old_file_paths = []
            for old_obj in old_qs:
                if old_obj.file:
                    try:
                        old_file_paths.append(old_obj.file.path)
                    except Exception:
                        pass
            # Bulk-clear file references so the post_delete signal skips removal,
            # then delete the DB records.
            old_qs.update(file="")
            old_qs.delete()

            # Defer physical deletion until commit succeeds
            if old_file_paths:
                def _cleanup(paths=old_file_paths):
                    for path in paths:
                        if os.path.isfile(path):
                            os.remove(path)

                transaction.on_commit(_cleanup)

            for uploaded_file in files:
                _validate_field_file(uploaded_file, field)
                ServiceRequestFieldFile.objects.create(
                    service_request=service_request,
                    field=field,
                    file=uploaded_file,
                    original_name=uploaded_file.name,
                )

            filenames = [
                f.original_name or os.path.basename(f.file.name)
                for f in ServiceRequestFieldFile.objects.filter(
                    service_request=service_request,
                    field=field,
                )
            ]
            ServiceRequestAnswer.objects.update_or_create(
                service_request=service_request,
                field_key=field.key,
                defaults={
                    "field": field,
                    "field_label": field.label,
                    "field_type": field.field_type,
                    "stage_title": field.stage.title,
                    "stage_order": field.stage.order,
                    "value_text": None,
                    "value_json": filenames,
                },
            )



def _request_queryset(detail=True):
    qs = ServiceRequest.objects.select_related("service", "requester")
    if detail:
        qs = qs.prefetch_related(
            "answers",
            Prefetch(
                "field_files",
                queryset=ServiceRequestFieldFile.objects.select_related("field"),
            ),
            Prefetch(
                "lawyer_responses",
                queryset=ServiceRequestLawyerResponse.objects.select_related("responder")
                .prefetch_related("files"),
            ),
        )
    return qs



def _validate_request_access(user, service_request):
    if _is_manager(user):
        return True
    return service_request.requester_id == user.id



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_services(request):
    include_inactive = _to_bool(request.GET.get("include_inactive"))
    queryset = Service.objects.filter(is_deleted=False).order_by("-is_featured", "featured_order", "name")

    if not include_inactive or not _is_manager(request.user):
        queryset = queryset.filter(is_active=True)

    serializer = ServiceListSerializer(queryset, many=True, context={"request": request})
    return Response({"count": len(serializer.data), "services": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_featured_services(request):
    queryset = Service.objects.filter(
        is_active=True, is_featured=True, is_deleted=False,
    ).order_by("featured_order", "name")
    featured = list(queryset[:6])

    if len(featured) < 4:
        needed = 6 - len(featured)
        fallback = list(
            Service.objects.filter(is_active=True, is_deleted=False)
            .exclude(id__in=[srv.id for srv in featured])
            .order_by("name")[:needed]
        )
        featured.extend(fallback)

    serializer = ServiceListSerializer(featured[:6], many=True, context={"request": request})
    return Response({"services": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_service_detail(request, service_id):
    queryset = Service.objects.filter(is_deleted=False).prefetch_related("stages__fields")
    service = get_object_or_404(queryset, id=service_id)

    if not service.is_active and not _is_manager(request.user):
        return Response({"detail": "Servicio no disponible"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ServiceSerializer(service, context={"request": request})

    draft = _request_queryset().filter(
        service=service,
        requester=request.user,
        is_submitted=False,
    ).order_by("-updated_at").first()

    draft_data = None
    if draft:
        draft_data = ServiceRequestDetailSerializer(draft, context={"request": request}).data

    return Response({"service": serializer.data, "draft": draft_data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_list_services(request):
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    queryset = (
        Service.objects.filter(is_deleted=False)
        .prefetch_related("stages__fields")
        .order_by("-is_featured", "featured_order", "name")
    )
    serializer = ServiceSerializer(queryset, many=True, context={"request": request})
    return Response({"services": serializer.data}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_create_service(request):
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    payload = _parse_json_payload(request)
    payload["icon_image"] = request.FILES.get("icon_image") if request.FILES else payload.get("icon_image")

    serializer = ServiceSerializer(data=payload, context={"request": request})
    serializer.is_valid(raise_exception=True)
    try:
        service = serializer.save()
    except ValidationError as exc:
        return Response(
            {
                "detail": "Error de validacion al guardar las etapas o campos.",
                "errors": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except IntegrityError as exc:
        # Catches any DB-level uniqueness/constraint violation that slipped
        # past the serializer guards (e.g. legacy data, race conditions) so
        # the user gets a readable 400 instead of an opaque 500.
        return Response(
            {
                "detail": (
                    "No fue posible guardar el servicio por un conflicto de "
                    "datos (probablemente orden o clave duplicada en un campo)."
                ),
                "errors": {"non_field_errors": [str(exc)]},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(ServiceSerializer(service, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def admin_update_service(request, service_id):
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    service = get_object_or_404(Service, id=service_id)
    payload = _parse_json_payload(request)

    if request.FILES.get("icon_image") is not None:
        payload["icon_image"] = request.FILES.get("icon_image")

    serializer = ServiceSerializer(service, data=payload, context={"request": request})
    serializer.is_valid(raise_exception=True)
    try:
        service = serializer.save()
    except ValidationError as exc:
        return Response(
            {
                "detail": "Error de validacion al guardar las etapas o campos.",
                "errors": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except IntegrityError as exc:
        # Catches any DB-level uniqueness/constraint violation that slipped
        # past the serializer guards (e.g. legacy data, race conditions) so
        # the user gets a readable 400 instead of an opaque 500.
        return Response(
            {
                "detail": (
                    "No fue posible guardar el servicio por un conflicto de "
                    "datos (probablemente orden o clave duplicada en un campo)."
                ),
                "errors": {"non_field_errors": [str(exc)]},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(ServiceSerializer(service, context={"request": request}).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_toggle_service_active(request, service_id):
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    service = get_object_or_404(Service, id=service_id)
    service.is_active = not service.is_active
    service.updated_by = request.user
    service.save(update_fields=["is_active", "updated_by", "updated_at"])

    return Response({"id": service.id, "is_active": service.is_active}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_toggle_service_featured(request, service_id):
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    service = get_object_or_404(Service, id=service_id)
    service.is_featured = not service.is_featured
    service.updated_by = request.user
    service.save(update_fields=["is_featured", "updated_by", "updated_at"])

    return Response({"id": service.id, "is_featured": service.is_featured}, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def admin_delete_service(request, service_id):
    """Soft-delete a service. Existing ServiceRequests stay intact via the
    PROTECT FK; the service simply disappears from public/admin listings.
    """
    if not _is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    service = get_object_or_404(Service, id=service_id, is_deleted=False)
    service.is_deleted = True
    service.is_active = False
    service.updated_by = request.user
    service.save(update_fields=["is_deleted", "is_active", "updated_by", "updated_at"])

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_or_submit_service_request(request):
    try:
        payload = _parse_json_payload(request)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    service_id = payload.get("service_id")
    if not service_id:
        return Response({"detail": "service_id es obligatorio"}, status=status.HTTP_400_BAD_REQUEST)

    service = get_object_or_404(Service.objects.prefetch_related("stages__fields"), id=service_id)

    if not service.is_active and not _is_manager(request.user):
        return Response({"detail": "Servicio inactivo"}, status=status.HTTP_400_BAD_REQUEST)

    request_id = payload.get("request_id")
    is_submit = _to_bool(payload.get("is_submit"))
    current_stage = payload.get("current_stage")

    if request_id:
        service_request = get_object_or_404(ServiceRequest, id=request_id, service=service)
        if service_request.requester_id != request.user.id and not _is_manager(request.user):
            return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    else:
        service_request = ServiceRequest.objects.create(
            service=service,
            requester=request.user,
            status="DRAFT",
            is_submitted=False,
        )

    if service_request.is_submitted and not _is_manager(request.user):
        return Response({"detail": "La solicitud ya fue enviada"}, status=status.HTTP_400_BAD_REQUEST)

    if current_stage:
        try:
            service_request.current_stage = int(current_stage)
        except (TypeError, ValueError):
            pass

    answers_payload = payload.get("answers", [])
    uploaded_files = _uploaded_files_by_field(request)

    try:
        _save_answers_and_files(
            service_request=service_request,
            answers_payload=answers_payload,
            uploaded_files=uploaded_files,
            is_submit=is_submit,
        )
    except ValidationError as exc:
        return Response({"detail": exc.message_dict if hasattr(exc, "message_dict") else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if is_submit and not service_request.is_submitted:
        service_request.mark_submitted()
        try:
            generate_service_request_pdf(service_request)
        except ServiceRequestPDFError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        service_request.save()
        notify_service_request_submission(service_request)
    else:
        service_request.save()

    serializer = ServiceRequestDetailSerializer(service_request, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_latest_service_draft(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    draft = _request_queryset().filter(
        service=service,
        requester=request.user,
        is_submitted=False,
    ).order_by("-updated_at").first()

    if not draft:
        return Response({"draft": None}, status=status.HTTP_200_OK)

    serializer = ServiceRequestDetailSerializer(draft, context={"request": request})
    return Response({"draft": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_my_service_requests(request):
    queryset = _request_queryset(detail=False).filter(requester=request.user, is_submitted=True)

    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    service_filter = request.GET.get("service")
    if service_filter:
        queryset = queryset.filter(service_id=service_filter)

    tracking = request.GET.get("tracking")
    if tracking:
        queryset = queryset.filter(tracking_number__icontains=tracking.strip())

    date_from = request.GET.get("date_from")
    if date_from:
        try:
            queryset = queryset.filter(created_at__date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass

    date_to = request.GET.get("date_to")
    if date_to:
        try:
            queryset = queryset.filter(created_at__date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass

    queryset = queryset.order_by("-created_at")
    paginator = ServiceRequestPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = ServiceRequestListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = ServiceRequestListSerializer(queryset, many=True)
    return Response({"count": len(serializer.data), "results": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_service_requests_inbox(request):
    if not _is_manager(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    queryset = _request_queryset(detail=False).filter(is_submitted=True)

    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    service_filter = request.GET.get("service")
    if service_filter:
        queryset = queryset.filter(service_id=service_filter)

    tracking = request.GET.get("tracking")
    if tracking:
        queryset = queryset.filter(tracking_number__icontains=tracking.strip())

    search = request.GET.get("search")
    if search:
        search = search.strip()
        queryset = queryset.filter(
            models.Q(requester__first_name__icontains=search)
            | models.Q(requester__last_name__icontains=search)
            | models.Q(requester__email__icontains=search)
            | models.Q(tracking_number__icontains=search)
        )

    date_from = request.GET.get("date_from")
    if date_from:
        try:
            queryset = queryset.filter(created_at__date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass

    date_to = request.GET.get("date_to")
    if date_to:
        try:
            queryset = queryset.filter(created_at__date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass

    queryset = queryset.order_by("-created_at")
    paginator = ServiceRequestPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = ServiceRequestListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = ServiceRequestListSerializer(queryset, many=True)
    return Response({"count": len(serializer.data), "results": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_service_request_detail(request, request_id):
    service_request = get_object_or_404(_request_queryset(), id=request_id)

    if not _validate_request_access(request.user, service_request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    serializer = ServiceRequestDetailSerializer(service_request, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manage_service_request(request, request_id):
    if not _is_manager(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    service_request = get_object_or_404(_request_queryset(), id=request_id, is_submitted=True)
    payload = request.data

    new_status = payload.get("status", service_request.status)
    message = str(payload.get("message", "")).strip()

    current = service_request.status
    if current not in ALLOWED_STATUS_TRANSITIONS:
        return Response({"detail": "Estado actual no permite transiciones"}, status=status.HTTP_400_BAD_REQUEST)

    if new_status != current and new_status not in ALLOWED_STATUS_TRANSITIONS.get(current, set()):
        return Response(
            {"detail": f"No se puede cambiar de {current} a {new_status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not message and "response_file" not in request.FILES and new_status == service_request.status:
        return Response(
            {"detail": "Debes enviar mensaje, archivo o cambio de estado"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    response_file = request.FILES.get("response_file")
    if response_file and response_file.size > MAX_UPLOAD_SIZE:
        return Response({"detail": f"Archivo excede {MAX_UPLOAD_SIZE // 1024 // 1024}MB"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        response_obj = ServiceRequestLawyerResponse.objects.create(
            service_request=service_request,
            responder=request.user,
            message=message,
            status_before=service_request.status,
            status_after=new_status,
        )

        if response_file:
            ServiceRequestLawyerResponseFile.objects.create(
                response=response_obj,
                file=response_file,
                original_name=response_file.name,
            )

        service_request.status = new_status
        service_request.save(update_fields=["status", "updated_at"])

    # Refetch with prefetched relations so the new lawyer response is included
    service_request = get_object_or_404(_request_queryset(), id=request_id)
    
    # Send notification after refetch to ensure lawyer_responses are loaded
    notify_service_request_status_change(service_request, message=message)
    
    serializer = ServiceRequestDetailSerializer(service_request, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_service_request_document(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    if not _validate_request_access(request.user, service_request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    if not service_request.generated_document:
        return Response({"detail": "Documento no disponible"}, status=status.HTTP_404_NOT_FOUND)

    file_path = service_request.generated_document.path
    filename = os.path.basename(file_path)
    try:
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename, content_type="application/pdf")
    except FileNotFoundError:
        raise Http404("Documento no encontrado")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_service_request_field_file(request, request_id, file_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    if not _validate_request_access(request.user, service_request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    file_obj = get_object_or_404(ServiceRequestFieldFile, id=file_id, service_request=service_request)
    file_path = file_obj.file.path
    filename = file_obj.original_name or os.path.basename(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    try:
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("Archivo no encontrado")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_service_request_response_file(request, request_id, response_id, file_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    if not _validate_request_access(request.user, service_request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    response_obj = get_object_or_404(ServiceRequestLawyerResponse, id=response_id, service_request=service_request)
    file_obj = get_object_or_404(ServiceRequestLawyerResponseFile, id=file_id, response=response_obj)
    file_path = file_obj.file.path
    filename = file_obj.original_name or os.path.basename(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    try:
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("Archivo no encontrado")
