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
# This list powers the checkboxes on the "create role" screen.
AVAILABLE_PERMISSIONS = [
    'tenant.update',          # Can edit company data
    'tenant.delete',          # Can delete the company (usually owner-only)
    'users.view',             # Can view the team
    'users.invite',           # Can invite new people
    'users.remove',           # Can remove members
    'roles.manage',           # Can create/edit roles
]

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
