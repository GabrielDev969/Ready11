import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from .models import Workspace, Domain, Role, WorkspaceMembership, WorkspaceInvite, AVAILABLE_PERMISSIONS
from .services import provision_workspace_defaults

logger = logging.getLogger(__name__)


class TenantScopedAdmin(admin.ModelAdmin):
    """
    Restrict shared (public-schema) tenant data to the current tenant when the
    admin is accessed from a tenant subdomain. On the public domain the platform
    super-admin still sees everything.
    """
    tenant_lookup = 'workspace'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        tenant = getattr(request, 'tenant', None)
        if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            return qs.filter(**{self.tenant_lookup: tenant})
        return qs


@admin.register(Workspace)
class WorkspaceAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'owner', 'created_at')
    search_fields = ('name', 'schema_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        tenant = getattr(request, 'tenant', None)
        if tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            return qs.filter(pk=tenant.pk)
        return qs

    def save_model(self, request, obj, form, change):
        # Saving a new Workspace creates its schema (auto_create_schema). We also
        # provision the default roles, a primary domain and the owner membership,
        # so a workspace created here behaves like one from the genesis flow.
        super().save_model(request, obj, form, change)
        if not change:
            provision_workspace_defaults(obj)


@admin.register(Domain)
class DomainAdmin(TenantScopedAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    list_filter = ('is_primary',)
    search_fields = ('domain',)
    tenant_lookup = 'tenant'


class RoleAdminForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Pick the permissions this role grants.",
    )

    class Meta:
        model = Role
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = list(AVAILABLE_PERMISSIONS)
        # Preserve any non-standard values already stored (e.g. 'all_access' on the
        # owner role) so editing an existing role never fails validation.
        current = (self.instance.permissions if self.instance and self.instance.pk else []) or []
        for perm in current:
            if perm not in choices:
                choices.append(perm)
        self.fields['permissions'].choices = [(c, c) for c in choices]

    def clean_permissions(self):
        return self.cleaned_data.get('permissions', [])


@admin.register(Role)
class RoleAdmin(TenantScopedAdmin):
    form = RoleAdminForm
    list_display = ('name', 'workspace', 'is_system_owner', 'is_default')
    list_filter = ('workspace', 'is_system_owner')
    search_fields = ('name',)


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(TenantScopedAdmin):
    list_display = ('user', 'workspace', 'role', 'joined_at')
    list_filter = ('workspace',)
    search_fields = ('user__email',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only offer roles from the same workspace as the membership being edited.
        tenant = getattr(request, 'tenant', None)
        if db_field.name == 'role' and tenant is not None and getattr(tenant, 'schema_name', 'public') != 'public':
            kwargs['queryset'] = Role.objects.filter(workspace=tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(WorkspaceInvite)
class WorkspaceInviteAdmin(TenantScopedAdmin):
    list_display = ('email', 'workspace', 'role', 'status', 'created_at')
    list_filter = ('status', 'workspace')
    search_fields = ('email',)
    readonly_fields = ('token',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if not change and not obj.workspace:
            link = f"http://{settings.TENANT_BASE_DOMAIN}:8000/invite/{obj.token}/"
            logger.info("Genesis invite link generated: %s", link)
