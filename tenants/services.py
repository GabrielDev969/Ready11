from django.conf import settings

from .models import Role, Domain, WorkspaceMembership


def provision_workspace_defaults(workspace, owner=None):
    """
    Ensure a workspace has everything a freshly provisioned tenant needs:
    the system "Owner" role, the default "Team Member" role, a primary domain,
    and (when an owner is known) the owner's membership.

    Idempotent — only creates what's missing — so it's safe to call on the genesis
    flow, from the admin, or to repair a workspace created without these defaults.
    Returns the owner Role.
    """
    owner_role = Role.objects.filter(workspace=workspace, is_system_owner=True).first()
    if owner_role is None:
        owner_role = Role.objects.create(
            workspace=workspace,
            name='Owner',
            is_system_owner=True,
            permissions=['all_access'],
        )

    if not Role.objects.filter(workspace=workspace, is_default=True).exists():
        Role.objects.create(
            workspace=workspace,
            name='Team Member',
            is_default=True,
            permissions=[],
        )

    if not workspace.domains.exists():
        slug = workspace.schema_name.replace('_', '-')
        Domain.objects.create(
            domain=f"{slug}.{settings.TENANT_BASE_DOMAIN}",
            tenant=workspace,
            is_primary=True,
        )

    owner = owner or workspace.owner
    if owner is not None:
        WorkspaceMembership.objects.get_or_create(
            workspace=workspace,
            user=owner,
            defaults={'role': owner_role},
        )

    return owner_role
