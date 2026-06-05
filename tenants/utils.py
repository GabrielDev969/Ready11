from .models import WorkspaceMembership


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


def workspace_home_url(request, workspace, path='/inicio/'):
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
