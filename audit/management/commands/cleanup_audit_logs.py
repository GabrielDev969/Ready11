from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLog

AUDIT_LOG_RETENTION_DAYS = 90


class Command(BaseCommand):
    help = "Delete audit logs older than 90 days."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
        qs = AuditLog.objects.filter(created_at__lt=cutoff)

        if options['dry_run']:
            self.stdout.write(f"[dry-run] would delete {qs.count()} audit log entries.")
            return

        count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} audit log entries."))
