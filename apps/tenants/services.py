from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.utils.text import slugify

import apps.audit.actions as audit_actions
from apps.audit.services import log_action

from .models import Domain, InviteStatus, Role, Workspace, WorkspaceInvite, WorkspaceMembership

# PostgreSQL identifiers (schema names) are limited to 63 bytes.
MAX_SCHEMA_LENGTH = 63
RESERVED_SCHEMA_NAMES = {'public', 'pg_catalog', 'information_schema'}


def build_schema_name(company_name):
    """
    Derive a safe PostgreSQL schema name from a company name.

    Returns a slug (underscores, <=63 chars) or 'workspace' as a safe fallback
    when the name produces an empty/reserved identifier.
    """
    schema = slugify(company_name).replace('-', '_')[:MAX_SCHEMA_LENGTH].strip('_')
    if not schema or schema in RESERVED_SCHEMA_NAMES or schema.startswith('pg_'):
        schema = 'workspace'
    return schema


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


def create_workspace(name, owner, request=None):
    """
    Create a fully provisioned workspace: unique schema name, primary domain,
    default roles, owner membership, the owner's default_workspace and an
    audit log entry. Returns the new Workspace.

    Creating the Workspace row also creates its PostgreSQL schema
    (django-tenants ``auto_create_schema``), so callers should wrap this in
    ``transaction.atomic()`` together with any related writes.
    """
    schema_name = build_schema_name(name)
    base_schema_name = schema_name
    counter = 1

    while Workspace.objects.filter(schema_name=schema_name).exists():
        suffix = f"_{counter}"
        schema_name = f"{base_schema_name[:MAX_SCHEMA_LENGTH - len(suffix)]}{suffix}"
        counter += 1

    workspace = Workspace.objects.create(
        name=name,
        schema_name=schema_name,
    )

    workspace.owner = owner
    workspace.save()

    # Creates the default roles, the primary domain (derived from the final
    # schema name) and the owner's membership.
    provision_workspace_defaults(workspace, owner=owner)

    owner.default_workspace = workspace
    owner.save(update_fields=['default_workspace'])

    log_action(owner, audit_actions.WORKSPACE_CREATED, resource=workspace,
               detail={'workspace_name': workspace.name}, request=request)

    # auto_create_schema runs tenant migrations in a schema_context, which may
    # leave the connection pointing at the new tenant schema. Reset to public so
    # callers (and the session middleware) operate on the correct schema.
    connection.set_schema_to_public()

    return workspace


def expire_stale_invites():
    """
    Bulk-mark pending invites past their expiration date as expired.

    Idempotent; complements the lazy per-invite expiration done when an invite
    link is opened. Returns the number of invites updated.
    """
    return WorkspaceInvite.objects.filter(
        status=InviteStatus.PENDING,
        expires_at__lt=timezone.now(),
    ).update(status=InviteStatus.EXPIRED)
