"""
Operational scheduled tasks with Huey.

Business tasks (subscription billing) live in gym_app/tasks.py.
This module contains infrastructure/operational tasks:
  - Database and media backups
  - Silk profiling data cleanup
  - Weekly slow query reports
"""
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import periodic_task, task

logger = logging.getLogger('backups')


# Retired 2026-06-25: daily backups moved to systemd gym-dbbackup.timer
# (vps-ops-toolkit/config/systemd/) to homogenize gym with the fleet and drop
# the dependency on the Huey worker being up. Still callable on demand via
# manual_backup(); re-enable by uncommenting the decorator below.
# @periodic_task(crontab(hour='3', minute='0'))
def scheduled_backup():
    """
    Daily automated backup of database and media files at 3 AM.
    Storage: configured via BACKUP_STORAGE_PATH env var.
    Retention: 5 DB + 5 media backups (~5 days), synchronized cleanup.
    Compression enabled for both DB (.sql.gz) and media (.tar.gz).

    Skipped when BACKUPS_ENABLED=False (e.g. staging environments).
    """
    if not getattr(settings, 'BACKUPS_ENABLED', True):
        return

    from django.core.management import call_command

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    logger.info(f"=== Starting scheduled backup {timestamp} ===")

    try:
        # Database backup + cleanup old backups in one step
        logger.info("Running database backup...")
        output = StringIO()
        call_command('dbbackup', compress=True, clean=True, stdout=output)
        logger.info(output.getvalue())

        # Media backup + cleanup old media backups in one step
        logger.info("Running media backup...")
        output = StringIO()
        call_command('mediabackup', compress=True, clean=True, stdout=output)
        logger.info(output.getvalue())

        logger.info("=== Backup completed successfully ===")
        return True

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        raise


@task()
def manual_backup():
    """Trigger a manual backup on demand."""
    return scheduled_backup()


# 07:52 UTC: clear of the heavy jobs of the projects that share the staging host (Huey and host timers).
@periodic_task(crontab(hour='7', minute='52'))
def silk_garbage_collection():
    """
    Daily cleanup of Silk profiling data older than 7 days.
    Only runs when Silk is enabled.
    """
    if not getattr(settings, 'ENABLE_SILK', False):
        return

    from django.core.management import call_command

    logger.info("Running Silk garbage collection...")
    output = StringIO()
    call_command('silk_garbage_collect', days=7, stdout=output)
    logger.info(output.getvalue())


@periodic_task(crontab(day_of_week='1', hour='8', minute='0'))
def weekly_slow_queries_report():
    """
    Weekly report of slow queries and potential N+1 patterns.
    Output: backend/logs/silk-weekly-report.log
    Only runs when Silk is enabled and the report gate is on
    (ENABLE_SLOW_QUERIES_REPORT=False disables in staging).
    """
    if not getattr(settings, 'ENABLE_SILK', False):
        return
    if not getattr(settings, 'ENABLE_SLOW_QUERIES_REPORT', True):
        return

    from silk.models import Request, SQLQuery
    from django.db.models import Count

    week_ago = timezone.now() - timedelta(days=7)
    threshold_ms = getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 500)
    n_plus_one_threshold = getattr(settings, 'N_PLUS_ONE_THRESHOLD', 10)

    # Find slow queries
    slow_queries = SQLQuery.objects.filter(
        request__start_time__gte=week_ago,
        time_taken__gte=threshold_ms,
    ).select_related('request').order_by('-time_taken')[:50]

    # Find potential N+1 patterns
    n_plus_one_suspects = Request.objects.filter(
        start_time__gte=week_ago,
    ).annotate(
        query_count=Count('queries'),
    ).filter(
        query_count__gte=n_plus_one_threshold,
    ).order_by('-query_count')[:20]

    # Generate report
    report_lines = [
        "=" * 60,
        f"WEEKLY QUERY REPORT - {timezone.now().strftime('%Y-%m-%d')}",
        "=" * 60,
        "",
        f"## SLOW QUERIES (>{threshold_ms}ms)",
        "-" * 40,
    ]

    if slow_queries:
        for sq in slow_queries:
            report_lines.append(
                f"[{sq.time_taken:.0f}ms] {sq.request.path} - {sq.query[:100]}..."
            )
    else:
        report_lines.append("No slow queries found this week")

    report_lines.extend([
        "",
        f"## POTENTIAL N+1 (>{n_plus_one_threshold} queries/request)",
        "-" * 40,
    ])

    if n_plus_one_suspects:
        for req in n_plus_one_suspects:
            report_lines.append(
                f"[{req.query_count} queries] {req.path}"
            )
    else:
        report_lines.append("No N+1 patterns detected this week")

    report_lines.extend(["", "=" * 60])
    report = "\n".join(report_lines)

    # Save to individual dated report file
    reports_dir = Path(settings.BASE_DIR) / 'logs' / 'silk-reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_date = timezone.now().strftime('%Y-%m-%d')
    log_path = reports_dir / f'silk-report-{report_date}.log'

    with open(log_path, 'w') as f:
        f.write(report + "\n")

    logger.info(
        f"Weekly report generated. Slow queries: {slow_queries.count()}, "
        f"N+1 suspects: {n_plus_one_suspects.count()}"
    )

    return report


# Day 1 at 10:37 UTC: clear of the heavy jobs of the projects that share the staging host (Huey and host timers).
@periodic_task(crontab(day='1', hour='10', minute='37'))
def silk_reports_cleanup():
    """
    Monthly cleanup of Silk report files older than 6 months.
    Only runs when Silk is enabled.
    """
    if not getattr(settings, 'ENABLE_SILK', False):
        return

    reports_dir = Path(settings.BASE_DIR) / 'logs' / 'silk-reports'
    if not reports_dir.exists():
        return

    cutoff = timezone.now() - timedelta(days=180)
    deleted = 0

    for report_file in reports_dir.glob('silk-report-*.log'):
        if report_file.stat().st_mtime < cutoff.timestamp():
            report_file.unlink()
            deleted += 1

    if deleted:
        logger.info(f"Silk reports cleanup: deleted {deleted} reports older than 6 months")
