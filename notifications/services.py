from datetime import timedelta

from django.utils import timezone

from .models import Notification, NotificationRead, NotificationType, NOTIFICATION_RETENTION_DAYS


def purge_old_notifications():
    """
    Delete notifications past their retention window. Returns ``(invites, others)``
    counts. Idempotent — safe to run repeatedly. Used by the management command and
    the in-process scheduler.
    """
    now = timezone.now()
    invite_cutoff = now - timedelta(days=NOTIFICATION_RETENTION_DAYS['invite'])
    other_cutoff = now - timedelta(days=NOTIFICATION_RETENTION_DAYS['default'])

    invites = Notification.objects.filter(
        notification_type=NotificationType.INVITE, created_at__lt=invite_cutoff,
    )
    others = Notification.objects.filter(created_at__lt=other_cutoff).exclude(
        notification_type=NotificationType.INVITE,
    )
    n_invites, n_others = invites.count(), others.count()
    invites.delete()
    others.delete()
    return n_invites, n_others


def recent_notifications(user, limit=8):
    """
    Return ``(items, unread_count)`` for the current user, where each item has an
    ``unread`` attribute. Shared by the bell context processor and the live feed.
    """
    visible = Notification.objects.visible_to(user).select_related('workspace', 'invite', 'invite__role')
    read_ids = set(user.notification_reads.values_list('notification_id', flat=True))

    items = list(visible[:limit])
    for n in items:
        n.unread = n.id not in read_ids

    unread_count = visible.exclude(reads__user=user).count()
    return items, unread_count


def create_invite_notification(invite):
    """
    If the invited email already has an account, surface the invite as an in-app
    notification (with Accept/Decline). New emails use the email-link flow instead.

    Idempotent per invite: reuses the existing notification if there is one.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = User.objects.filter(email__iexact=invite.email).first()
    if not user:
        return None

    notification, _created = Notification.objects.get_or_create(
        invite=invite,
        notification_type=NotificationType.INVITE,
        defaults={
            'recipient': user,
            'workspace': invite.workspace,
            'title': f"Invitation to {invite.workspace.name}",
        },
    )
    # If the invite was resent, make sure the notification is unread again.
    NotificationRead.objects.filter(notification=notification, user=user).delete()
    return notification


def delete_invite_notifications(invite):
    """Remove the in-app notification(s) tied to an invite (e.g. on cancel)."""
    Notification.objects.filter(invite=invite).delete()


def mark_read(user, notification):
    NotificationRead.objects.get_or_create(notification=notification, user=user)


def mark_all_read(user):
    unread = Notification.objects.unread_for(user)
    NotificationRead.objects.bulk_create(
        [NotificationRead(notification=n, user=user) for n in unread],
        ignore_conflicts=True,
    )
