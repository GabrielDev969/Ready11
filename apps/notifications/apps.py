import os
import sys

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        from . import signals  # noqa: F401  (connects post_save handler)
        self._maybe_start_cleanup_scheduler()

    def _maybe_start_cleanup_scheduler(self):
        from django.conf import settings

        if not getattr(settings, 'NOTIFICATION_CLEANUP_ENABLED', True):
            return

        # Only run inside the long-lived server process — never during management
        # commands (migrate, collectstatic, shell, tests, ...).
        argv = sys.argv
        is_runserver = 'runserver' in argv and os.environ.get('RUN_MAIN') == 'true'
        is_server = os.environ.get('RUN_CLEANUP_SCHEDULER') == '1'  # set by entrypoint (daphne)
        if not (is_runserver or is_server):
            return

        from . import scheduler
        hours = getattr(settings, 'NOTIFICATION_CLEANUP_INTERVAL_HOURS', 24)
        scheduler.start(int(hours) * 3600)
