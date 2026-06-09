from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('User'),
    )
    # Workspace identity is stored as strings (not FK) so logs survive tenant deletion.
    workspace_schema = models.CharField(_('Workspace schema'), max_length=63, blank=True, db_index=True)
    workspace_name = models.CharField(_('Workspace name'), max_length=255, blank=True)

    action = models.CharField(_('Action'), max_length=100, db_index=True)
    resource_type = models.CharField(_('Resource type'), max_length=50, blank=True)
    resource_id = models.CharField(_('Resource ID'), max_length=255, blank=True)
    detail = models.JSONField(_('Detail'), default=dict)

    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Audit log')
        verbose_name_plural = _('Audit logs')

    def __str__(self):
        return f"[{self.action}] {self.user} @ {self.workspace_schema or 'public'}"
