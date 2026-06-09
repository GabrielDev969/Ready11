"""
Lightweight in-process scheduler for audit log cleanup.

Same pattern as notifications/scheduler.py: a daemon thread runs the retention
purge periodically — no Celery, cron daemon or extra service required.

Caveat: with multiple server replicas, each runs its own thread. The purge is
idempotent so that's harmless. At larger scale, disable this
(AUDIT_CLEANUP_ENABLED=False) and call ``manage.py cleanup_audit_logs`` from
an external cron / Celery beat instead.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

_started = False


def _run_loop(interval_seconds):
    from django.db import close_old_connections

    from .services import purge_old_audit_logs

    time.sleep(min(60, interval_seconds))
    while True:
        try:
            close_old_connections()
            n = purge_old_audit_logs()
            if n:
                logger.info("Audit cleanup: deleted %s log entries.", n)
        except Exception:
            logger.exception("Audit cleanup run failed.")
        finally:
            close_old_connections()
        time.sleep(interval_seconds)


def start(interval_seconds):
    """Start the cleanup loop once per process (no-op if already started)."""
    global _started
    if _started:
        return
    _started = True
    thread = threading.Thread(
        target=_run_loop, args=(interval_seconds,), daemon=True, name='audit-cleanup',
    )
    thread.start()
    logger.info("Audit cleanup scheduler started (every %ss).", interval_seconds)
