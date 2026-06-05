from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import WorkspaceMembership, expand_permissions

def tenant_permission_required(required_permission=None):
    """
    Protect tenant views.
    If 'required_permission' is given, check that the user's role has the permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Must be authenticated.
            if not request.user.is_authenticated:
                return redirect('login')

            # 2. Must be accessing a valid tenant (not the public schema).
            if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
                return redirect('login')

            # 3. Load the user's membership (with the role, to avoid extra queries).
            try:
                membership = WorkspaceMembership.objects.select_related('role').get(
                    workspace=request.tenant,
                    user=request.user
                )
            except WorkspaceMembership.DoesNotExist:
                messages.error(request, _("You don't have access to this environment."))
                return redirect('login')

            # 4. Specific permission check (RBAC).
            if required_permission:
                # The absolute owner bypasses checks; others need the permission in
                # their (umbrella-expanded) permission set.
                effective = expand_permissions(membership.role.permissions)
                if not (membership.role.is_system_owner or required_permission in effective):
                    messages.error(request, _("You don't have permission to perform this action."))
                    return redirect('tenant_dashboard')

            # 5. Attach the membership to the request for convenience in views.
            request.tenant_membership = membership

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
