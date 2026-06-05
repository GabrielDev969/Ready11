from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import WorkspaceMembership

def tenant_permission_required(required_permission=None):
    """
    Protege as views do tenant.
    Se 'required_permission' for passado, checa se o Cargo do usuário tem a permissão.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Garante que está logado
            if not request.user.is_authenticated:
                return redirect('login')
            
            # 2. Garante que está acessando um tenant válido
            if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
                return redirect('login')
            
            # 3. Busca o vínculo do usuário com a empresa (trazendo o Cargo junto para otimizar)
            try:
                membership = WorkspaceMembership.objects.select_related('role').get(
                    workspace=request.tenant,
                    user=request.user
                )
            except WorkspaceMembership.DoesNotExist:
                messages.error(request, "Você não tem acesso a este ambiente.")
                return redirect('login')
            
            # 4. Checagem de Permissão Específica (RBAC)
            if required_permission:
                # O Dono absoluto passa direto. Os outros precisam ter a string na lista JSON.
                if not (membership.role.is_system_owner or required_permission in membership.role.permissions):
                    messages.error(request, "Você não tem permissão para realizar esta ação.")
                    return redirect('tenant_dashboard')
            
            # 5. Se passou em tudo, anexa a membership no request para facilitar nas views
            request.tenant_membership = membership
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator