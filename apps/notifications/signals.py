from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification


@receiver(post_save, sender=Notification)
def push_on_create(sender, instance, created, **kwargs):
    """Push newly created notifications to connected clients in real time."""
    if not created:
        return
    # Import here to avoid loading channels at app-registry build time.
    from .realtime import push_notification
    push_notification(instance)
