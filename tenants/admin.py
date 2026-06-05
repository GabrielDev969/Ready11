from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Workspace, Domain, Role, WorkspaceMembership, WorkspaceInvite

@admin.register(Workspace)
class WorkspaceAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'owner', 'created_at')
    search_fields = ('name', 'schema_name')

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'is_system_owner', 'is_default')
    list_filter = ('workspace', 'is_system_owner')
    search_fields = ('name',)

@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'workspace', 'role', 'joined_at')
    list_filter = ('workspace',)
    search_fields = ('user__email',)

@admin.register(WorkspaceInvite)
class WorkspaceInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'workspace', 'role', 'status', 'created_at')
    list_filter = ('status', 'workspace')
    search_fields = ('email',)

    readonly_fields = ('token',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        if not change and not obj.workspace:
            print("\n" + "="*60)
            print("🚀 LINK DO CONVITE GÊNESIS GERADO:")
            print(f"http://localhost:8000/convite/{obj.token}/")
            print("="*60 + "\n")