from .models import Notification, NotificationRead, NotificationType


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


def mark_read(user, notification):
    NotificationRead.objects.get_or_create(notification=notification, user=user)


def mark_all_read(user):
    unread = Notification.objects.unread_for(user)
    NotificationRead.objects.bulk_create(
        [NotificationRead(notification=n, user=user) for n in unread],
        ignore_conflicts=True,
    )
