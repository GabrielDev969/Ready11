from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


def user_group(user_id):
    return f'notif_user_{user_id}'


def workspace_group(workspace_id):
    return f'notif_ws_{workspace_id}'


GLOBAL_GROUP = 'notif_global'


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Per-connection WebSocket. On connect, an authenticated user joins:
    - their personal group (targeted/invite/personal notifications),
    - the global group (global broadcasts),
    - one group per workspace they belong to (workspace broadcasts).
    """

    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.groups_joined = await self.get_groups(user)
        for group in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        for group in getattr(self, 'groups_joined', []):
            await self.channel_layer.group_discard(group, self.channel_name)

    @database_sync_to_async
    def get_groups(self, user):
        from tenants.models import WorkspaceMembership
        groups = [user_group(user.id), GLOBAL_GROUP]
        for wid in WorkspaceMembership.objects.filter(user=user).values_list('workspace_id', flat=True):
            groups.append(workspace_group(wid))
        return groups

    # Handler for messages sent to the group with {'type': 'notify', ...}.
    async def notify(self, event):
        await self.send_json(event['payload'])
