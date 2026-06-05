from .services import recent_notifications


def notifications(request):
    """Expose the bell's unread count and a few recent notifications to templates."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'notif_unread_count': 0, 'notif_recent': []}

    recent, unread_count = recent_notifications(user)
    return {'notif_unread_count': unread_count, 'notif_recent': recent}
