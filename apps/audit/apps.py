import os
import sys

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Audit'

    def ready(self):
        self._maybe_start_cleanup_scheduler()

    def _maybe_start_cleanup_scheduler(self):
        from django.conf import settings

        if not getattr(settings, 'AUDIT_CLEANUP_ENABLED', True):
            return

        argv = sys.argv
        is_runserver = 'runserver' in argv and os.environ.get('RUN_MAIN') == 'true'
        is_server = os.environ.get('RUN_CLEANUP_SCHEDULER') == '1'
        if not (is_runserver or is_server):
            return

        from . import scheduler
        hours = getattr(settings, 'AUDIT_CLEANUP_INTERVAL_HOURS', 24)
        scheduler.start(int(hours) * 3600)
