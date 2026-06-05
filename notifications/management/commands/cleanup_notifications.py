from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification, NotificationType, NOTIFICATION_RETENTION_DAYS
from notifications.services import purge_old_notifications


class Command(BaseCommand):
    help = (
        "Delete notifications past their retention window (invites: 7 days; "
        "global/tenant/personal: 30 days). The app also runs this automatically via "
        "an in-process scheduler; use this command for manual runs or external cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            now = timezone.now()
            invite_cutoff = now - timedelta(days=NOTIFICATION_RETENTION_DAYS['invite'])
            other_cutoff = now - timedelta(days=NOTIFICATION_RETENTION_DAYS['default'])
            n_invites = Notification.objects.filter(
                notification_type=NotificationType.INVITE, created_at__lt=invite_cutoff,
            ).count()
            n_others = Notification.objects.filter(created_at__lt=other_cutoff).exclude(
                notification_type=NotificationType.INVITE,
            ).count()
            self.stdout.write(f"[dry-run] would delete {n_invites} invite + {n_others} other notifications.")
            return

        n_invites, n_others = purge_old_notifications()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {n_invites} invite + {n_others} other notifications."
        ))
