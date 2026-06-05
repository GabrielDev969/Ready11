from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import GLOBAL_GROUP, user_group, workspace_group
from .models import NotificationType


def _payload(notification):
    if notification.notification_type == NotificationType.INVITE and notification.workspace_id:
        title = str(notification.title) or f"Invitation to {notification.workspace.name}"
        # Invites are action-only: send the user to the list (Accept/Decline live there).
        url = '/notifications/'
    else:
        title = str(notification.title)
        # Content notifications open their detail page.
        url = f'/notifications/{notification.id}/'
    return {
        'id': notification.id,
        'kind': notification.notification_type,
        'title': title,
        'body': notification.body or '',
        'url': url,
    }


def _targets(notification):
    if notification.recipient_id:
        return [user_group(notification.recipient_id)]
    if notification.notification_type == NotificationType.GLOBAL:
        return [GLOBAL_GROUP]
    if notification.notification_type == NotificationType.TENANT and notification.workspace_id:
        return [workspace_group(notification.workspace_id)]
    return []


def push_notification(notification):
    """Push a freshly created notification to the relevant WebSocket group(s)."""
    layer = get_channel_layer()
    if layer is None:
        return
    payload = _payload(notification)
    message = {'type': 'notify', 'payload': payload}
    for group in _targets(notification):
        async_to_sync(layer.group_send)(group, message)
