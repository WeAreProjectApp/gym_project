"""
REST API views for the contract-execution submodule (cuentas de cobro).

Fully signed documents with a 'Forma de pago (N cuotas)' variable expose N
sequential installment slots. Every sequencing rule is enforced HERE — the
frontend only renders what this API returns:

- slot N+1 becomes uploadable only when slot N was ACCEPTED by the lawyer;
- a slot under review ('uploaded') blocks every upload;
- a rejected slot is re-submitted by updating the SAME record.
"""

import logging
import mimetypes
import os
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gym_app.models import DocumentPaymentRecord, DynamicDocument
from gym_app.serializers.dynamic_document import DocumentPaymentRecordSerializer
from gym_app.services import payment_notification_service
from gym_app.utils.auth_utils import is_gym_staff

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx'}


def _is_document_party(document, user):
    """The two contract parties: creator lawyer and assigned client."""
    return user == document.created_by or user == document.assigned_to


def _can_read(document, user):
    return _is_document_party(document, user) or is_gym_staff(user)


def _get_document(pk):
    return get_object_or_404(
        DynamicDocument.objects.select_related('created_by', 'assigned_to')
        .prefetch_related(
            'variables',
            Prefetch(
                'payment_records',
                queryset=DocumentPaymentRecord.objects.select_related('uploaded_by'),
            ),
        ),
        pk=pk,
    )


def _payments_payload(document, user):
    """Single response shape shared by every endpoint in this module."""
    progress = document.get_payment_progress()
    if progress is None:
        return {'document_id': document.id, 'configured': False, 'slots': []}

    records = {
        record.installment_number: record
        for record in document.payment_records.all()
    }
    slots = []
    for number in range(1, progress['total_installments'] + 1):
        record = records.get(number)
        slots.append({
            'installment_number': number,
            'status': record.status if record else 'pending',
            'record': DocumentPaymentRecordSerializer(record).data if record else None,
        })

    total_amount = progress['total_amount_accepted']
    return {
        'document_id': document.id,
        'configured': True,
        'total_installments': progress['total_installments'],
        'accepted_count': progress['accepted_count'],
        'total_amount_accepted': str(total_amount) if total_amount is not None else None,
        'in_review': progress['in_review'],
        'next_uploadable': progress['next_uploadable'],
        'can_review': user == document.created_by,
        'can_upload': _is_document_party(document, user)
        and progress['next_uploadable'] is not None,
        'slots': slots,
    }


# ── List ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_payment_records(request, pk):
    """Return every installment slot with its record (if any)."""
    document = _get_document(pk)
    if not _can_read(document, request.user):
        return Response(
            {'detail': 'No tienes permiso para ver las cuentas de cobro de este documento.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(_payments_payload(document, request.user))


# ── Upload ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_payment_record(request, pk):
    """Upload (or re-upload after rejection) the cuenta de cobro of a slot.

    Multipart body: file (required), installment_number (required),
    amount (optional), notes (optional).
    """
    document = _get_document(pk)
    if not _is_document_party(document, request.user):
        return Response(
            {'detail': 'Solo las partes del documento pueden cargar cuentas de cobro.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    progress = document.get_payment_progress()
    if progress is None:
        return Response(
            {'detail': 'El documento no tiene forma de pago configurada o no está completamente firmado.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        installment_number = int(request.data.get('installment_number'))
    except (TypeError, ValueError):
        return Response({'detail': 'Número de cuota inválido.'}, status=status.HTTP_400_BAD_REQUEST)
    if not 1 <= installment_number <= progress['total_installments']:
        return Response({'detail': 'Número de cuota fuera de rango.'}, status=status.HTTP_400_BAD_REQUEST)

    if progress['next_uploadable'] != installment_number:
        detail = (
            'Hay una cuenta de cobro en revisión; espera la decisión del abogado.'
            if progress['in_review']
            else 'Esta cuota aún no está disponible para carga.'
        )
        return Response({'detail': detail}, status=status.HTTP_409_CONFLICT)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response(
            {'detail': 'Debes adjuntar el archivo de la cuenta de cobro.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    extension = os.path.splitext(uploaded_file.name or '')[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return Response(
            {'detail': 'Formato no permitido. Usa PDF, JPG, PNG o DOCX.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return Response(
            {'detail': 'El archivo supera el tamaño máximo de 20 MB.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    amount = None
    amount_raw = request.data.get('amount')
    if amount_raw not in (None, ''):
        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, ValueError):
            return Response({'detail': 'Monto inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if amount < 0:
            return Response({'detail': 'El monto no puede ser negativo.'}, status=status.HTTP_400_BAD_REQUEST)

    notes = (request.data.get('notes') or '').strip() or None

    existing = document.payment_records.filter(
        installment_number=installment_number
    ).first()

    if existing:
        # Re-upload after rejection: same row, new file. The old physical
        # file is removed manually (post_delete only fires on row deletes).
        old_path = existing.file.path if existing.file else None
        existing.file = uploaded_file
        existing.original_name = uploaded_file.name
        existing.status = DocumentPaymentRecord.STATUS_UPLOADED
        existing.uploaded_by = request.user
        existing.uploaded_at = timezone.now()
        if amount is not None:
            existing.amount = amount
        if notes is not None:
            existing.notes = notes
        existing.save()
        record = existing
        if old_path and old_path != record.file.path and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError as exc:
                logger.warning(f"Could not remove replaced payment file {old_path}: {exc}")
    else:
        try:
            record = DocumentPaymentRecord.objects.create(
                document=document,
                installment_number=installment_number,
                file=uploaded_file,
                original_name=uploaded_file.name,
                amount=amount,
                notes=notes,
                uploaded_by=request.user,
            )
        except IntegrityError:
            # Concurrent upload for the same slot lost the race
            return Response(
                {'detail': 'Esta cuota ya tiene una cuenta de cobro cargada.'},
                status=status.HTTP_409_CONFLICT,
            )

    payment_notification_service.notify_payment_record_uploaded(document, record)

    document = _get_document(pk)  # refresh prefetch cache after the mutation
    return Response(_payments_payload(document, request.user), status=status.HTTP_201_CREATED)


# ── Review (accept / reject) ────────────────────────────────────────

def _get_reviewable_record(document, record_id):
    """Record scoped to the document (anti-IDOR); 409 handled by caller."""
    return get_object_or_404(DocumentPaymentRecord, id=record_id, document=document)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_payment_record(request, pk, record_id):
    """Accept a cuenta de cobro, enabling the next installment slot."""
    document = _get_document(pk)
    if request.user != document.created_by:
        return Response(
            {'detail': 'Solo el abogado creador puede revisar cuentas de cobro.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    record = _get_reviewable_record(document, record_id)
    if record.status != DocumentPaymentRecord.STATUS_UPLOADED:
        return Response(
            {'detail': 'Esta cuenta de cobro ya fue revisada.'},
            status=status.HTTP_409_CONFLICT,
        )

    record.status = DocumentPaymentRecord.STATUS_ACCEPTED
    record.save(update_fields=['status'])

    payment_notification_service.notify_payment_record_reviewed(document, record, accepted=True)

    document = _get_document(pk)
    return Response(_payments_payload(document, request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_payment_record(request, pk, record_id):
    """Reject a cuenta de cobro with a mandatory reason; the slot reopens."""
    document = _get_document(pk)
    if request.user != document.created_by:
        return Response(
            {'detail': 'Solo el abogado creador puede revisar cuentas de cobro.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    record = _get_reviewable_record(document, record_id)
    if record.status != DocumentPaymentRecord.STATUS_UPLOADED:
        return Response(
            {'detail': 'Esta cuenta de cobro ya fue revisada.'},
            status=status.HTTP_409_CONFLICT,
        )

    reason = (request.data.get('rejection_reason') or '').strip()
    if not reason:
        return Response(
            {'detail': 'Debes indicar el motivo del rechazo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record.status = DocumentPaymentRecord.STATUS_REJECTED
    record.rejection_reason = reason
    record.save(update_fields=['status', 'rejection_reason'])

    payment_notification_service.notify_payment_record_reviewed(document, record, accepted=False)

    document = _get_document(pk)
    return Response(_payments_payload(document, request.user))


# ── Download ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_payment_record_file(request, pk, record_id):
    """Download the cuenta de cobro file of a record."""
    document = _get_document(pk)
    if not _can_read(document, request.user):
        return Response(
            {'detail': 'No tienes permiso para descargar este archivo.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    record = get_object_or_404(DocumentPaymentRecord, id=record_id, document=document)

    file_path = record.file.path if record.file else None
    if not file_path or not os.path.exists(file_path):
        raise Http404('Archivo no encontrado.')

    filename = record.original_name or os.path.basename(file_path)
    content_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type or 'application/octet-stream',
    )
