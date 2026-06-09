from apps.tenants.utils import tenant_permission_set
from apps.tenants.utils import user_workspaces as _user_workspaces


def workspaces(request):
    """Expose the current user's workspaces to every template (header switcher)."""
    return {'user_workspaces': _user_workspaces(request)}


def tenant_permissions(request):
    """
    Expose the current user's tenant permissions to every template so the UI can
    hide actions the user can't perform.

    - ``tenant_perms``: a set of permission strings (owner gets all).
    - ``is_workspace_owner``: True for the absolute owner role.
    """
    perms, is_owner = tenant_permission_set(request)
    return {'tenant_perms': perms, 'is_workspace_owner': is_owner}
