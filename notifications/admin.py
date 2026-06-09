from django.contrib import admin

from .models import Notification, NotificationRead


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'recipient', 'workspace', 'created_at')
    list_filter = ('notification_type', 'created_at')
    search_fields = ('title', 'body')
    autocomplete_fields = ()

    fieldsets = (
        (None, {
            'fields': ('notification_type', 'title', 'body'),
        }),
        ('Targeting', {
            'description': (
                "GLOBAL: leave recipient and workspace empty (shown to everyone). "
                "WORKSPACE: set a workspace (shown to its members). "
                "PERSONAL: set a recipient."
            ),
            'fields': ('recipient', 'workspace'),
        }),
    )

    def get_exclude(self, request, obj=None):
        # 'invite' is managed by the system (invite notifications), not set by hand.
        return ('invite',)


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'read_at')
    search_fields = ('user__email',)
