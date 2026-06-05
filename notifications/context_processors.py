from .models import Notification


def notifications(request):
    """Expose the bell's unread count and a few recent notifications to templates."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'notif_unread_count': 0, 'notif_recent': []}

    visible = Notification.objects.visible_to(user).select_related('workspace', 'invite', 'invite__role')
    read_ids = set(user.notification_reads.values_list('notification_id', flat=True))

    recent = list(visible[:8])
    for n in recent:
        n.unread = n.id not in read_ids

    unread_count = visible.exclude(reads__user=user).count()

    return {'notif_unread_count': unread_count, 'notif_recent': recent}
