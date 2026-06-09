from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'workspace_name', 'resource_type', 'ip_address')
    list_filter = ('action', 'workspace_schema')
    search_fields = ('user__email', 'workspace_name', 'action', 'resource_type', 'resource_id')
    readonly_fields = (
        'user', 'workspace_schema', 'workspace_name',
        'action', 'resource_type', 'resource_id', 'detail',
        'ip_address', 'created_at',
    )
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
