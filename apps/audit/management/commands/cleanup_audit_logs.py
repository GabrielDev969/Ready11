from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import AUDIT_LOG_RETENTION_DAYS, purge_old_audit_logs


class Command(BaseCommand):
    help = "Delete audit logs older than 90 days."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            cutoff = timezone.now() - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
            count = AuditLog.objects.filter(created_at__lt=cutoff).count()
            self.stdout.write(f"[dry-run] would delete {count} audit log entries.")
            return

        count = purge_old_audit_logs()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} audit log entries."))
