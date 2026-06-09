from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

# Retention policy (days) used by the cleanup_notifications command.
NOTIFICATION_RETENTION_DAYS = {
    'invite': 7,
    'default': 30,  # global / tenant / personal
}
BODY_MAX_LENGTH = 1000


class NotificationType(models.TextChoices):
    INVITE = 'invite', _('Invitation')
    GLOBAL = 'global', _('Global')
    TENANT = 'tenant', _('Workspace')
    PERSONAL = 'personal', _('Personal')


class NotificationQuerySet(models.QuerySet):
    def visible_to(self, user):
        """
        Notifications a user can see:
        - targeted directly at them (recipient == user), or
        - global broadcasts created after the user registered, or
        - workspace broadcasts created after the user joined that workspace.

        The date guards prevent newly joined users from seeing a backlog of
        announcements that predate their membership.
        """
        from apps.tenants.models import WorkspaceMembership
        memberships = list(
            WorkspaceMembership.objects.filter(user=user).values('workspace_id', 'joined_at')
        )

        # One Q clause per workspace so we can gate on the exact join date.
        tenant_q = Q()
        for m in memberships:
            tenant_q |= Q(
                notification_type=NotificationType.TENANT,
                recipient__isnull=True,
                workspace_id=m['workspace_id'],
                created_at__gte=m['joined_at'],
            )

        return self.filter(
            Q(recipient=user)
            | Q(notification_type=NotificationType.GLOBAL, recipient__isnull=True, created_at__gte=user.created_at)
            | tenant_q
        )

    def unread_for(self, user):
        """Visible notifications the user hasn't read yet."""
        return self.visible_to(user).exclude(reads__user=user)


class Notification(models.Model):
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)

    # Targeted notifications set a recipient; broadcasts (global/tenant) leave it null.
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    # Context workspace (for tenant/invite notifications).
    workspace = models.ForeignKey(
        'tenants.Workspace',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    # For INVITE notifications: the invite to accept/decline.
    invite = models.ForeignKey(
        'tenants.WorkspaceInvite',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=150)
    body = models.TextField(blank=True, validators=[MaxLengthValidator(BODY_MAX_LENGTH)])
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

    def is_read_by(self, user):
        return self.reads.filter(user=user).exists()


class NotificationRead(models.Model):
    """Per-user read state, uniform across all notification types (incl. broadcasts)."""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_reads')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('notification', 'user')
