from .models import WorkspaceMembership, AVAILABLE_PERMISSIONS, expand_permissions


def tenant_permission_set(request):
    """
    Return ``(permissions, is_owner)`` for the current user in the current tenant.

    ``permissions`` is a set of permission strings; the system owner gets every
    available permission (so template checks like ``'users.invite' in perms`` just
    work). Returns ``(set(), False)`` on the public schema or for non-members.

    Reuses ``request.tenant_membership`` (set by ``tenant_permission_required``)
    when available, to avoid an extra query.
    """
    user = getattr(request, 'user', None)
    tenant = getattr(request, 'tenant', None)
    if (not user or not user.is_authenticated
            or tenant is None or getattr(tenant, 'schema_name', 'public') == 'public'):
        return set(), False

    membership = getattr(request, 'tenant_membership', None)
    if membership is None:
        membership = (
            WorkspaceMembership.objects
            .select_related('role')
            .filter(workspace=tenant, user=user)
            .first()
        )
    if membership is None:
        return set(), False

    if membership.role.is_system_owner:
        return set(AVAILABLE_PERMISSIONS), True
    return expand_permissions(membership.role.permissions), False


def effective_workspace(user):
    """
    Resolve which workspace an authenticated user should land on.

    Prefers their ``default_workspace`` (but only if they still hold a membership
    there), otherwise falls back to any workspace they belong to. Returns ``None``
    when the user is anonymous or has no workspace membership at all.

    Validating the membership avoids redirect loops when a ``default_workspace``
    becomes stale (e.g. the user was removed from it).
    """
    if not getattr(user, 'is_authenticated', False):
        return None

    if user.default_workspace_id and WorkspaceMembership.objects.filter(
        user=user, workspace_id=user.default_workspace_id
    ).exists():
        return user.default_workspace

    membership = (
        WorkspaceMembership.objects
        .filter(user=user)
        .select_related('workspace')
        .first()
    )
    return membership.workspace if membership else None


def workspace_home_url(request, workspace, path='/home/'):
    """
    Build an absolute, scheme-aware URL to a page inside a workspace's subdomain,
    preserving the current port (so local development on :8000 keeps working).

    Returns ``None`` if the workspace has no primary domain.
    """
    domain = workspace.domains.filter(is_primary=True).first()
    if not domain:
        return None

    host = request.get_host()
    port = f":{host.split(':')[1]}" if ':' in host else ''
    return f"{request.scheme}://{domain.domain}{port}{path}"


def user_workspaces(request):
    """
    List every workspace the current user belongs to, for the header switcher.

    Each item carries the workspace, its home URL, and flags for the workspace the
    user is currently viewing and the one set as their default. Returns ``[]`` for
    anonymous users.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return []

    current_schema = getattr(getattr(request, 'tenant', None), 'schema_name', 'public')

    memberships = (
        WorkspaceMembership.objects
        .filter(user=user)
        .select_related('workspace', 'role')
        .order_by('workspace__name')
    )

    items = []
    for membership in memberships:
        workspace = membership.workspace
        items.append({
            'workspace': workspace,
            'url': workspace_home_url(request, workspace),
            'is_current': workspace.schema_name == current_schema,
            'is_default': user.default_workspace_id == workspace.id,
            'role': membership.role.name,
        })
    return items
