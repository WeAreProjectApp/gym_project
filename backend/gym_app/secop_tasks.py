"""
SECOP module scheduled and on-demand tasks with Huey.

Tasks:
  - Daily sync with SECOP API (datos.gov.co)
  - Alert evaluation for new processes
  - Daily/weekly alert summaries
  - Purge old closed processes
"""
import logging
from datetime import timedelta

from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, lock_task

logger = logging.getLogger(__name__)


@periodic_task(crontab(hour='7', minute='0'))
def sync_secop_daily():
    """
    Daily scheduled synchronization with SECOP API.

    Runs at 2 AM Colombia time (07:00 UTC).
    """
    logger.info("Starting scheduled SECOP sync")
    sync_secop_data()


@task(retries=3, retry_delay=60)
@lock_task('secop-sync-lock')
def sync_secop_data():
    """
    Main synchronization task.

    Can be called manually or by the scheduled task.
    Handles the full sync workflow with error handling. The lock lives on this
    task so scheduled and manual executions cannot overlap.
    """
    from gym_app.models import SyncLog
    from gym_app.services.secop_sync_service import SECOPSyncService

    sync_log = SyncLog.objects.create()

    try:
        service = SECOPSyncService()
        result = service.synchronize()

        sync_log.status = SyncLog.Status.SUCCESS
        sync_log.records_processed = result['processed']
        sync_log.records_created = result['created']
        sync_log.records_updated = result['updated']

        # Trigger alert evaluation for new processes
        if result['created'] > 0:
            evaluate_secop_alerts.schedule(
                args=(result['new_ids'],),
                delay=5
            )

        logger.info(
            f"SECOP sync completed: {result['created']} new, "
            f"{result['updated']} updated"
        )

    except Exception as e:
        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_message = str(e)
        logger.error(f"SECOP sync failed: {e}")
        raise

    finally:
        sync_log.finished_at = timezone.now()
        sync_log.save()


@task()
def evaluate_secop_alerts(process_ids):
    """
    Evaluate alerts for newly synced processes.

    Args:
        process_ids: List of new SECOPProcess IDs to evaluate
    """
    from gym_app.services.secop_alert_service import AlertEvaluationService

    logger.info(f"Evaluating SECOP alerts for {len(process_ids)} new processes")

    service = AlertEvaluationService()
    service.evaluate_processes(process_ids)


@periodic_task(crontab(hour='7', minute='0'))
def send_secop_daily_summaries():
    """
    Send daily alert summaries to users.

    Runs daily at 7 AM. Collects all pending notifications
    for users with DAILY frequency and sends summary email.
    """
    from gym_app.services.secop_alert_service import AlertEvaluationService

    logger.info("Sending SECOP daily alert summaries")

    service = AlertEvaluationService()
    service.send_summaries('DAILY')


@periodic_task(crontab(day_of_week='1', hour='7', minute='0'))
def send_secop_weekly_summaries():
    """
    Send weekly alert summaries to users.

    Runs every Monday at 7 AM.
    """
    from gym_app.services.secop_alert_service import AlertEvaluationService

    logger.info("Sending SECOP weekly alert summaries")

    service = AlertEvaluationService()
    service.send_summaries('WEEKLY')


# 08:37 UTC: clear of the heavy jobs of the projects that share the staging host (Huey and host timers).
@periodic_task(crontab(hour='8', minute='37'))
def purge_old_secop_processes():
    """
    Purge old closed processes without classifications.

    Runs daily at 08:37 UTC (03:37 in Colombia). Removes processes that:
    - Have a closing date older than 30 days
    - Have no user classifications

    This keeps the database size manageable.
    """
    from gym_app.models import SECOPProcess

    logger.info("Purging old SECOP processes")

    threshold = timezone.now() - timedelta(days=30)

    deleted_count, _ = SECOPProcess.objects.filter(
        closing_date__lt=threshold
    ).exclude(
        classifications__isnull=False
    ).delete()

    logger.info(f"Purged {deleted_count} old SECOP processes")
