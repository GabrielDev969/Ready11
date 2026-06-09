import logging
from datetime import timedelta

from django.utils import timezone

from .models import AuditLog

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, resource=None, detail=None, request=None):
    """
    Record a workspace event. Silently no-ops on error to avoid disrupting the request.

    Args:
        user: the user performing the action (CustomUser instance or None for system)
        action: one of the constants in audit.actions
        resource: the affected object (optional; its type and pk are recorded)
        detail: dict with extra context (email, name, etc.)
        request: the current HttpRequest (used to extract IP and tenant)
    """
    try:
        tenant = getattr(request, 'tenant', None) if request else None
        workspace_schema = getattr(tenant, 'schema_name', '') if tenant else ''
        workspace_name = getattr(tenant, 'name', '') if tenant else ''

        resource_type = ''
        resource_id = ''
        if resource is not None:
            resource_type = type(resource).__name__
            resource_id = str(getattr(resource, 'pk', '') or '')

        AuditLog.objects.create(
            user=user,
            workspace_schema=workspace_schema,
            workspace_name=workspace_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
            ip_address=_get_client_ip(request),
        )
    except Exception:
        logger.exception("Failed to write audit log for action %s", action)


AUDIT_LOG_RETENTION_DAYS = 90


def purge_old_audit_logs(retention_days=AUDIT_LOG_RETENTION_DAYS):
    """Delete audit log entries older than ``retention_days``. Returns count deleted."""
    cutoff = timezone.now() - timedelta(days=retention_days)
    count, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    return count
