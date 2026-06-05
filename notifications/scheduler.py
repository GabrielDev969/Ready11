"""
Lightweight in-process scheduler for notification cleanup.

A daemon thread runs the retention purge periodically — no Celery, cron daemon or
extra service required. It only runs in the long-lived server process (guarded in
``apps.ready``), not during management commands like migrate/collectstatic.

Caveat: with multiple server replicas, each runs its own thread. The purge is
idempotent so that's harmless (just redundant). At larger scale, prefer an external
scheduler (cron / Celery beat) calling ``manage.py cleanup_notifications`` and
disable this with ``NOTIFICATION_CLEANUP_ENABLED=False``.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

_started = False


def _run_loop(interval_seconds):
    from django.db import close_old_connections
    from .locks import distributed_lock
    from .services import purge_old_notifications

    # Small initial delay so startup (and any boot-time work) settles first.
    time.sleep(min(60, interval_seconds))
    while True:
        try:
            close_old_connections()
            # Across replicas, only one runs the purge per interval. The lock is held
            # (not released) for ~the interval via TTL, so others skip this window.
            with distributed_lock('notif-cleanup', timeout=max(60, interval_seconds - 60), release=False) as acquired:
                if acquired:
                    n_invites, n_others = purge_old_notifications()
                    if n_invites or n_others:
                        logger.info("Notification cleanup: deleted %s invite + %s other.", n_invites, n_others)
        except Exception:
            logger.exception("Notification cleanup run failed.")
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
        target=_run_loop, args=(interval_seconds,), daemon=True, name='notif-cleanup',
    )
    thread.start()
    logger.info("Notification cleanup scheduler started (every %ss).", interval_seconds)
