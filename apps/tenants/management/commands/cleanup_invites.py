from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tenants.models import InviteStatus, WorkspaceInvite
from apps.tenants.services import expire_stale_invites


class Command(BaseCommand):
    help = (
        "Mark pending workspace invites past their expiration date as expired. "
        "Invites are also expired lazily when their link is opened; use this "
        "command for manual runs or external cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would be expired without updating.",
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            count = WorkspaceInvite.objects.filter(
                status=InviteStatus.PENDING,
                expires_at__lt=timezone.now(),
            ).count()
            self.stdout.write(f"[dry-run] would expire {count} stale invite(s).")
            return

        count = expire_stale_invites()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} stale invite(s)."))
