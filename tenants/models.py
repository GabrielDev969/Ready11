import uuid
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

# ==========================================
# PERMISSION CONSTANTS
# ==========================================
# Granular permissions grouped by area. This single source drives both the
# permission list and the grouped UI on the "create/edit role" screen.
# Each item: (code, label, description).
PERMISSION_GROUPS = [
    {
        'key': 'users',
        'label': _('Team'),
        'permissions': [
            ('users.view', _('View team'), _('See the members list.')),
            ('users.invite', _('Invite members'), _('Send invitations and assign a role.')),
            ('users.remove', _('Remove members'), _('Remove people from the workspace.')),
        ],
    },
    {
        'key': 'roles',
        'label': _('Roles'),
        'permissions': [
            ('roles.view', _('View roles'), _('See roles and pick one when inviting.')),
            ('roles.create', _('Create roles'), _('Add new roles.')),
            ('roles.edit', _('Edit roles'), _('Change roles and their permissions.')),
            ('roles.delete', _('Delete roles'), _('Remove roles.')),
        ],
    },
    {
        'key': 'tenant',
        'label': _('Workspace'),
        'permissions': [
            ('tenant.update', _('Edit workspace'), _('Change the company data.')),
            # Note: deleting a workspace is intentionally NOT a grantable permission.
            # It's restricted to the workspace owner and platform super admins.
        ],
    },
]

# Flat list of permission codes (derived from the groups above).
AVAILABLE_PERMISSIONS = [
    code for group in PERMISSION_GROUPS for (code, _label, _desc) in group['permissions']
]

# Umbrella permissions that imply a set of granular ones. Not offered as new
# checkboxes (assign the granular ones), but still honored if present — e.g. a
# legacy role or one set via the Django admin.
PERMISSION_IMPLIES = {
    'roles.manage': ['roles.view', 'roles.create', 'roles.edit', 'roles.delete'],
    'users.manage': ['users.view', 'users.invite', 'users.remove'],
    'tenant.manage': ['tenant.update'],
}


def expand_permissions(permissions):
    """
    Expand a role's stored permissions into the full effective set, resolving any
    umbrella permissions (e.g. 'roles.manage' -> all 'roles.*' actions).
    """
    effective = set(permissions or [])
    for umbrella, implied in PERMISSION_IMPLIES.items():
        if umbrella in effective:
            effective.update(implied)
    return effective

# ==========================================
# CORE MODELS (TENANT)
# ==========================================

class Workspace(TenantMixin):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    # The single absolute owner of the workspace; the only one that can't be removed.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_workspaces',
        null=True,
        blank=True
    )

    auto_create_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    # DomainMixin already provides the 'domain' and 'tenant' (ForeignKey) fields.
    pass


# ==========================================
# ROLES (RBAC)
# ==========================================

class Role(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50, verbose_name=_("Role name"))

    # System locks
    is_system_owner = models.BooleanField(default=False)  # Locks the "Owner" role from edits
    is_default = models.BooleanField(default=False)  # Default role for new invites

    # Permissions stored as a list: ["users.invite", "roles.manage"]
    permissions = models.JSONField(default=list, verbose_name=_("Permissions"))

    class Meta:
        unique_together = ('workspace', 'name')  # Prevents two roles with the same name per workspace

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"


# ==========================================
# MEMBERS AND INVITES
# ==========================================

class WorkspaceMembership(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')

    # Every member must have a Role. PROTECT prevents deleting a role still in use.
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='members')

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.role.name} in {self.workspace.name}"


class InviteStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    ACCEPTED = 'accepted', _('Accepted')
    EXPIRED = 'expired', _('Expired')
    CANCELLED = 'cancelled', _('Cancelled')

def default_expiration():
    # Invites are valid for 24 hours from creation/resend.
    return timezone.now() + timedelta(hours=24)

class WorkspaceInvite(models.Model):
    email = models.EmailField(verbose_name=_("Invited email"))
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invites', null=True, blank=True)

    # When the invite is accepted, the person receives this role.
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)

    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=InviteStatus.choices, default=InviteStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiration)

    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Invite for {self.email} ({self.status})"

    @property
    def is_expired(self):
        """True if the invite passed its expiration date."""
        return timezone.now() > self.expires_at

    @property
    def is_usable(self):
        """True only if the invite can still be accepted (pending and not expired)."""
        return self.status == InviteStatus.PENDING and not self.is_expired

    def expire(self):
        """Mark this invite as expired and persist the change."""
        if self.status == InviteStatus.PENDING:
            self.status = InviteStatus.EXPIRED
            self.save(update_fields=['status'])

    def cancel(self):
        """Cancel a pending invite (revokes the link)."""
        if self.status == InviteStatus.PENDING:
            self.status = InviteStatus.CANCELLED
            self.save(update_fields=['status'])
