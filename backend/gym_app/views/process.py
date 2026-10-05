import json
import logging
import traceback
from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from gym_app.models import Process, Stage, StageAlert, CaseFile, Case, User, RecentProcess, Notification
from gym_app.serializers.process import ProcessSerializer, RecentProcessSerializer
from gym_app.services.notification_service import (
    build_process_recipients,
    create_bulk_notifications,
    notify_process_stakeholders,
)
from gym_app.utils.auth_utils import is_gym_staff
from gym_app.views.layouts.sendEmail import send_template_email

logger = logging.getLogger(__name__)


def _send_process_update_email(process, recipients, summary):
    """Send a notification email to *recipients* when a process is updated.

    Mirrors ``_send_alert_email`` (process_alert_tasks): uses the shared
    ``notification`` template so the visual style stays consistent with the
    pre-existing alert reminder email. Failures are swallowed (logged) so the
    update never fails because of an SMTP issue.
    """
    emails = sorted({u.email for u in recipients if getattr(u, 'email', None)})
    if not emails:
        return

    frontend_url = getattr(settings, 'FRONTEND_BASE_URL', 'https://gmconsultoresjuridicos.com')
    process_url = f'{frontend_url}/process_detail/{process.id}'
    process_label = process.ref or process.id

    try:
        send_template_email(
            template_name='notification',
            subject=f'Proceso actualizado — {process_label}',
            to_emails=emails,
            context={
                'title': 'Actualización de Proceso',
                'badge_text': 'Cambios registrados',
                'notification_title': f'Proceso: {process_label}',
                'message': summary,
                'additional_info': (
                    'Ingresa al detalle del proceso para revisar los cambios '
                    'registrados.'
                ),
                'action_url': process_url,
                'action_text': 'Ver Proceso',
            },
        )
    except Exception:
        logger.error(
            'Failed to send process update email for process %s', process.id,
            exc_info=True,
        )


def _user_can_access_process(user, process):
    """A user can access a process if they are gym staff, the assigned lawyer, or one of the clients."""
    if is_gym_staff(user):
        return True
    if process.lawyer_id == user.id:
        return True
    return process.clients.filter(pk=user.id).exists()


class _StageAlertValidationError(Exception):
    """Raised when StageAlert configuration is rejected (e.g. past date)."""


def _validate_alert_config(created_stages, main_data):
    """Reject activating an alert whose target date already lapsed.

    Mirrors the client-side guard so the API rejects past-date activations
    even when the form is bypassed.
    """
    if not created_stages:
        return
    if not main_data.get('alertIsActive', True):
        return
    last_stage = created_stages[-1]
    if not last_stage.date:
        return
    if last_stage.date < timezone.now().date():
        raise _StageAlertValidationError(
            'No se puede activar una alerta cuando la fecha de la última actuación '
            'ya pasó. Actualiza la fecha o desactiva la alerta antes de guardar.'
        )


def _create_stage_alerts(created_stages, main_data, process=None, actor=None):
    """Create a StageAlert for every stage. Only the last receives the
    user-provided configuration (the daily reminder task only evaluates
    the alert of the last stage of each process).

    When the last stage's alert is active, immediately notify the lawyer and
    clients (if ``notify_clients=True``) so the activation is reflected in the
    Notification Center without waiting for the daily Huey reminder.
    """
    if not created_stages:
        return
    for stage in created_stages[:-1]:
        StageAlert.objects.create(stage=stage)

    last_stage = created_stages[-1]
    description = main_data.get('alertDescription', '')
    is_active = main_data.get('alertIsActive', True)
    notify_clients = main_data.get('alertNotifyClients', True)

    StageAlert.objects.create(
        stage=last_stage,
        description=description,
        is_active=is_active,
        notify_clients=notify_clients,
    )

    if is_active and process is not None:
        date_str = last_stage.date.strftime('%d/%m/%Y') if last_stage.date else 'sin fecha'
        title = f"Alerta activada — {process.ref or 'Proceso'}"
        message = (
            f"Se activó una alerta para la etapa '{last_stage.status}' del proceso "
            f"{process.ref or process.id}, programada para {date_str}."
        )
        if description:
            message += f" Detalle: {description}"

        # Include the actor (typically the lawyer who toggled the alert) so the
        # confirmation lands in their notification center too. The user
        # requirement explicitly asked for the lawyer to receive the activation
        # notification — passing actor=None disables the actor-exclusion in
        # ``build_process_recipients``.
        recipients = build_process_recipients(
            process, notify_clients=notify_clients, actor=None,
        )
        if recipients:
            create_bulk_notifications(
                users=recipients,
                title=title,
                message=message,
                category='process_alert',
                priority='high',
                link_type='process',
                link_id=process.id,
            )

            # Send an immediate activation email so BOTH lawyer and clients
            # are informed without waiting for the daily reminder task. The
            # daily Huey task keeps handling the 3-day / 1-day reminders.
            try:
                emails = sorted({u.email for u in recipients if getattr(u, 'email', None)})
                if emails:
                    frontend_url = getattr(
                        settings,
                        'FRONTEND_BASE_URL',
                        'https://gmconsultoresjuridicos.com',
                    )
                    process_url = f'{frontend_url}/process_detail/{process.id}'
                    send_template_email(
                        template_name='notification',
                        subject=f'Alerta activada — {process.ref or process.id}',
                        to_emails=emails,
                        context={
                            'title': 'Alerta de Proceso Activada',
                            'badge_text': 'Alerta activa',
                            'notification_title': f'Proceso: {process.ref or process.id}',
                            'message': message,
                            'additional_info': (
                                'Recibirás recordatorios automáticos 3 días y '
                                '1 día antes de la fecha programada.'
                            ),
                            'action_url': process_url,
                            'action_text': 'Ver Proceso',
                        },
                    )
            except Exception:
                logger.error(
                    'Failed to send alert activation email for process %s',
                    process.id,
                    exc_info=True,
                )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def process_list(request):
    """
    API view to retrieve a list of processes based on the authenticated user's role.
    - If the user is a client, return the processes where the user is the client.
    - If the user is a lawyer, return the processes where the user is the lawyer.
    - If the user has any other role, return all processes.
    """
    user = request.user  # Get the authenticated user

    try:
        base_qs = Process.objects.select_related('lawyer', 'case') \
            .prefetch_related('clients', 'stages__alert', 'case_files') \
            .order_by('-created_at')

        role = (getattr(user, 'role', '') or '').lower()
        if is_gym_staff(user):
            processes = base_qs
        elif role == 'client':
            processes = base_qs.filter(clients=user)
        else:
            # corporate_client / basic / unknown roles cannot list processes directly.
            processes = base_qs.none()

        serializer = ProcessSerializer(processes, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_process(request):
    """
    API view to create a new process.
    This view will:
    - Validate client, lawyer, and case type.
    - Check for unique 'ref' value.
    - Create the process and stages based on the provided data.
    """
    if not is_gym_staff(request.user):
        return Response(
            {'detail': 'No tienes permisos para crear procesos.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        # Parse the main data from the request
        main_data = json.loads(request.data.get('mainData', '{}'))

        # Validate clients and lawyer
        client_ids = main_data.get('clientIds') or []
        if not isinstance(client_ids, list):
            client_ids = [client_ids]

        clients_qs = User.objects.filter(pk__in=client_ids)
        if not client_ids or clients_qs.count() != len(client_ids):
            return Response({'detail': 'Client or Lawyer not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            lawyer = User.objects.get(pk=main_data.get('lawyerId'))
        except User.DoesNotExist:
            return Response({'detail': 'Client or Lawyer not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Validate case type
        try:
            case_type = Case.objects.get(pk=main_data.get('caseTypeId'))
        except Case.DoesNotExist:
            return Response({'detail': 'Case type not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Normalise optional progress value (0-100)
        progress_raw = main_data.get('progress', 0)
        try:
            progress_value = int(progress_raw)
        except (TypeError, ValueError):
            progress_value = 0
        progress_value = max(0, min(progress_value, 100))

        with transaction.atomic():
            process = Process.objects.create(
                authority=main_data.get('authority'),
                authority_email=main_data.get('authorityEmail'),
                plaintiff=main_data.get('plaintiff'),
                defendant=main_data.get('defendant'),
                ref=main_data.get('ref'),
                lawyer=lawyer,
                case=case_type,
                subcase=main_data.get('subcase'),
                progress=progress_value,
            )
            process.clients.set(clients_qs)

            stages_data = main_data.get('stages', [])
            created_stages = []
            for stage_data in stages_data:
                stage_status = stage_data.get('status')
                if not stage_status:
                    continue

                date_value = stage_data.get('date')
                if date_value:
                    try:
                        from datetime import date as _date_cls
                        stage_date = _date_cls.fromisoformat(date_value)
                    except Exception:
                        stage_date = timezone.now().date()
                else:
                    stage_date = timezone.now().date()

                stage = Stage.objects.create(status=stage_status, date=stage_date)
                process.stages.add(stage)
                created_stages.append(stage)

            try:
                _validate_alert_config(created_stages, main_data)
            except _StageAlertValidationError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            _create_stage_alerts(created_stages, main_data, process=process, actor=request.user)

        serializer = ProcessSerializer(process, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Error Traceback:", traceback.format_exc())
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_process(request, pk):
    """
    API view to update an existing process.
    This view will:
    - Update the process data using the provided main data.
    - Retain only the specified case files by 'caseFileIds'.
    - REPLACE ALL existing stages with the ones from frontend.
    """
    process = get_object_or_404(Process, pk=pk)

    # Only gym staff (lawyers/admin) can edit a process. Clients listed on a
    # process do NOT get edit rights — they read via process_list / detail.
    if not is_gym_staff(request.user):
        return Response(
            {'detail': 'No tienes permisos para modificar este proceso.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Check if the request data is already a dict or if it's a string
    if isinstance(request.data, dict) and 'mainData' not in request.data:
        main_data = request.data
    else:
        try:
            # Try to parse mainData as JSON
            main_data_str = request.data.get('mainData', '{}')
            main_data = json.loads(main_data_str)
        except (TypeError, json.JSONDecodeError) as e:
            # If that fails, use request.data directly
            main_data = request.data
    
    # Update basic fields directly
    if 'plaintiff' in main_data:
        process.plaintiff = main_data['plaintiff']
    
    if 'defendant' in main_data:
        process.defendant = main_data['defendant']
    
    if 'ref' in main_data:
        process.ref = main_data['ref']
    
    if 'authority' in main_data:
        process.authority = main_data['authority']
    
    if 'authorityEmail' in main_data:
        process.authority_email = main_data['authorityEmail']
    
    if 'subcase' in main_data:
        process.subcase = main_data['subcase']

    # Optional progress update (0-100)
    if 'progress' in main_data:
        progress_raw = main_data.get('progress')
        try:
            progress_value = int(progress_raw)
        except (TypeError, ValueError):
            progress_value = process.progress or 0
        progress_value = max(0, min(progress_value, 100))
        process.progress = progress_value
    
    # Update clients (ManyToMany)
    client_ids = main_data.get('clientIds', None)
    if client_ids is not None:
        if not isinstance(client_ids, list):
            client_ids = [client_ids]
        # Only update if we have at least one valid client
        clients_qs = User.objects.filter(id__in=client_ids)
        if clients_qs.exists():
            process.clients.set(clients_qs)
    
    # Update lawyer
    lawyer_id = main_data.get('lawyerId')
    if lawyer_id:
        try:
            lawyer = User.objects.get(id=lawyer_id)
            process.lawyer = lawyer
        except User.DoesNotExist:
            pass

    # Update Case Type
    case_type_id = main_data.get('caseTypeId')
    if case_type_id:
        try:
            case = Case.objects.get(id=case_type_id)
            process.case = case
        except Case.DoesNotExist:
            pass
    
    process.save()

    stages_data = main_data.get('stages', [])

    # Process.stages is M2M, so .clear() only unlinks. Hard-delete the rows
    # to avoid orphan Stage / StageAlert rows piling up in the database.
    with transaction.atomic():
        # Snapshot stage signatures (status + date) BEFORE clearing so we can
        # detect newly-added stages after re-creation.
        old_stage_signatures = set(
            (s.status, s.date.isoformat() if s.date else '')
            for s in process.stages.all()
        )

        old_stage_ids = list(process.stages.values_list('id', flat=True))
        process.stages.clear()
        if old_stage_ids:
            Stage.objects.filter(id__in=old_stage_ids).delete()

        created_stages = []
        for stage_data in stages_data:
            stage_status = stage_data.get('status')
            if not stage_status:
                continue

            date_value = stage_data.get('date')
            if date_value:
                try:
                    from datetime import date as _date_cls
                    stage_date = _date_cls.fromisoformat(date_value)
                except Exception:
                    stage_date = timezone.now().date()
            else:
                stage_date = timezone.now().date()

            new_stage = Stage.objects.create(status=stage_status, date=stage_date)
            process.stages.add(new_stage)
            created_stages.append(new_stage)

        try:
            _validate_alert_config(created_stages, main_data)
        except _StageAlertValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        _create_stage_alerts(created_stages, main_data, process=process, actor=request.user)

    case_file_ids = main_data.get('caseFileIds', None)
    if case_file_ids is not None:
        process.case_files.set(CaseFile.objects.filter(id__in=case_file_ids))

    process.save()

    added_stages = [
        s for s in created_stages
        if (s.status, s.date.isoformat() if s.date else '') not in old_stage_signatures
    ]

    # Resolve recipients once and reuse across the per-stage loop to avoid an
    # N+1 on process.clients.all().
    #
    # The lawyer who triggers the edit is intentionally NOT excluded: the
    # business requirement is that BOTH the lawyer and the clients receive
    # the in-app notification + email when a process is updated (so the
    # lawyer also has a record of the action in their notification center
    # and inbox).
    recipients = build_process_recipients(process, actor=None)

    update_message = (
        f"Se actualizó el proceso {process.ref or process.id}"
        + (f" ({process.subcase})" if process.subcase else '')
        + ". Revisa los cambios desde el detalle del proceso."
    )
    notify_process_stakeholders(
        process=process,
        title=f"Proceso actualizado: {process.ref or process.id}",
        message=update_message,
        priority='medium',
        recipients=recipients,
    )

    # Build a single email summary covering the global update plus any newly
    # added stages so stakeholders receive ONE consolidated email instead of
    # one per stage. The in-app notifications above stay one-per-event.
    email_lines = [update_message]

    for added in added_stages:
        date_str = added.date.strftime('%d/%m/%Y') if added.date else 'sin fecha'
        notify_process_stakeholders(
            process=process,
            title=f"Nueva etapa registrada — {process.ref or process.id}",
            message=(
                f"Se registró la etapa '{added.status}' (fecha: {date_str}) en el "
                f"proceso {process.ref or process.id}."
            ),
            priority='medium',
            recipients=recipients,
        )
        email_lines.append(
            f"Nueva etapa: <strong>{added.status}</strong> "
            f"(fecha: <strong>{date_str}</strong>)."
        )

    # Email notification for stakeholders. Wrapped in a helper so transport
    # failures never break the API response.
    _send_process_update_email(
        process=process,
        recipients=recipients,
        summary='<br/>'.join(email_lines),
    )

    # Return the updated process
    serializer = ProcessSerializer(process, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_case_file(request):
    """
    Upload a single file and associate it with an existing process.

    This API endpoint allows authenticated users to upload a file and link it 
    to an existing legal process identified by its `processId`.

    **Request parameters**:
    - `processId` (str): The ID of the process to which the file will be associated.
    - `file` (File): The file to be uploaded.

    **Responses**:
    - `201 Created`: File successfully uploaded and associated with the process.
        - Example response: `{"detail": "File uploaded successfully.", "fileId": 123}`
    - `400 Bad Request`: Missing required parameters or invalid data.
        - Example response: `{"detail": "Process ID is required."}`
    - `404 Not Found`: Process with the specified ID does not exist.
        - Example response: `{"detail": "Not found."}`
    - `500 Internal Server Error`: An unexpected error occurred while processing the request.
        - Example response: `{"detail": "Internal error uploading file."}`

    **Permission required**:
    - Authenticated users only.
    
    """
    # Extract request data
    process_id = request.data.get('processId')  # ID of the process
    file = request.FILES.get('file')  # File to be uploaded

    # Validate required parameters
    if not process_id:
        return Response({'detail': 'Process ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not file:
        return Response({'detail': 'File is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Ensure the process exists
        process = get_object_or_404(Process, pk=process_id)

        if not _user_can_access_process(request.user, process):
            return Response(
                {'detail': 'No tienes permisos para subir archivos a este proceso.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create a new CaseFile instance and associate it with the process
        case_file = CaseFile.objects.create(file=file)
        process.case_files.add(case_file)

        # Notify stakeholders that a new document was attached. The actor (the
        # uploader) is excluded from the recipient list so they don't receive
        # a notification about their own action.
        try:
            file_name = getattr(case_file.file, 'name', '') or ''
            display_name = file_name.rsplit('/', 1)[-1] if file_name else 'documento'
            notify_process_stakeholders(
                process=process,
                title=f"Documento agregado — {process.ref or process.id}",
                message=(
                    f"Se anexó el documento '{display_name}' al proceso "
                    f"{process.ref or process.id}."
                ),
                actor=request.user,
                priority='medium',
            )
        except Exception:  # pragma: no cover — never block the upload on notif failure
            pass

        # Return success response with the ID of the uploaded file
        return Response({'detail': 'File uploaded successfully.', 'fileId': case_file.id}, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Log the exception for debugging purposes
        print("Error uploading file:", str(e))
        return Response({'detail': 'Internal error uploading file.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_processes(request):
    """
    Get the 10 most recently viewed processes by the authenticated user.
    """
    recent_processes = (
        RecentProcess.objects.filter(user=request.user)
        .select_related('process__case', 'process__lawyer')
        .prefetch_related(
            'process__clients',
            'process__case_files',
            Prefetch('process__stages', queryset=Stage.objects.select_related('alert')),
        )
        .order_by('-last_viewed')[:10]
    )
    serializer = RecentProcessSerializer(recent_processes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def process_pending_alerts_count(request):
    """Return the count of unread, non-archived process-related notifications
    for the authenticated user.

    Used by the SlideBar to render a red badge over the "Procesos" item.
    Mirrors the contract of ``/notifications/unread-count/`` but scoped to
    ``category='process_alert'`` so the badge only reflects process activity.
    """
    now = timezone.now()
    count = Notification.objects.filter(
        user=request.user,
        category='process_alert',
        is_read=False,
        is_archived=False,
        is_deleted=False,
    ).exclude(
        snoozed_until__gt=now,
    ).count()
    return Response({'pending_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_recent_process(request, process_id):
    """
    Update or create a recent process entry when a user views a process.
    """
    try:
        process = Process.objects.get(id=process_id)
    except Process.DoesNotExist:
        return Response({'error': 'Process not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get or create the recent process entry
    recent_process, created = RecentProcess.objects.get_or_create(
        user=request.user,
        process=process,
        defaults={'last_viewed': timezone.now()}
    )
    
    if not created:
        recent_process.last_viewed = timezone.now()
        recent_process.save()
    
    return Response({'status': 'success'}, status=status.HTTP_200_OK)
