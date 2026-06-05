from tenants.utils import user_workspaces as _user_workspaces


def workspaces(request):
    """Expose the current user's workspaces to every template (header switcher)."""
    return {'user_workspaces': _user_workspaces(request)}
