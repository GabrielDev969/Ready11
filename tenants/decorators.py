from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from .models import WorkspaceMembership

def tenant_permission_required(permission_name=None):
    """
    Guardião de rotas internas do Tenant.
    Verifica se o usuário pertence ao tenant atual da URL e se tem a permissão necessária.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Garante que o usuário está logado
            if not request.user.is_authenticated:
                return redirect('login')

            # O django-tenants já resolveu o tenant atual automaticamente com base no subdomínio
            tenant_atual = request.tenant
            
            # Segurança: Impede que rotas internas sejam acessadas no domínio público (localhost)
            if tenant_atual.schema_name == 'public':
                return HttpResponseForbidden("Esta área é exclusiva para uso dentro de um Workspace válido.")
            
            # Busca o vínculo exato do usuário com a empresa atual
            try:
                membership = WorkspaceMembership.objects.get(workspace=tenant_atual, user=request.user)
            except WorkspaceMembership.DoesNotExist:
                return HttpResponseForbidden("Você não possui vínculo ou permissão para acessar este Workspace.")
            
            # REGRA DE OURO 1: Se for Dono/Admin do Tenant, tem passe livre absoluto (ignora checagens)
            if membership.is_tenant_admin:
                return view_func(request, *args, **kwargs)
            
            # REGRA DE OURO 2: Se foi exigida uma permissão específica (ex: 'tenant.delete')
            if permission_name:
                # Verifica se o usuário tem um cargo e se a permissão está na lista JSON
                if membership.role and permission_name in membership.role.permissions:
                    return view_func(request, *args, **kwargs)
                
                return HttpResponseForbidden(f"Acesso negado. Você precisa da permissão '{permission_name}' para executar esta ação.")
            
            # Se nenhuma permissão específica foi exigida (apenas o acesso base ao painel), libera
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator