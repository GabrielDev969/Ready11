from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login
from django.utils.text import slugify
from django.db import transaction
from django.contrib import messages
from .decorators import tenant_permission_required
from django.conf import settings
from django.core.mail import send_mail

from django.http import HttpResponse

# Adicionei o Role aqui nos imports
from .models import WorkspaceInvite, Workspace, Domain, WorkspaceMembership, InviteStatus, Role 
from .forms import GenesisSetupForm, TeamInviteForm, EmployeeSetupForm, RoleForm

User = get_user_model()

def genesis_setup_view(request, token):
    invite = get_object_or_404(WorkspaceInvite, token=token, status=InviteStatus.PENDING)

    if request.method == 'POST':
        form = GenesisSetupForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            try:
                with transaction.atomic():
                    user, created = User.objects.get_or_create(
                        email=invite.email,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'is_active': True,
                            'email_verified': True
                        }
                    )
                    
                    if created:
                        user.set_password(password)
                        user.save()

                    schema_name = slugify(company_name).replace('-', '_')

                    base_schema_name = schema_name
                    counter = 1
                    # Ajuste fino: Se o schema tiver contador, o domínio também deve ter
                    domain_slug = slugify(company_name)
                    
                    while Workspace.objects.filter(schema_name=schema_name).exists():
                        schema_name = f"{base_schema_name}_{counter}"
                        domain_slug = f"{slugify(company_name)}-{counter}"
                        counter += 1

                    workspace = Workspace.objects.create(
                        name=company_name,
                        schema_name=schema_name
                    )

                    workspace.owner = user
                    workspace.save()

                    # JSON alterado para Lista (Array de strings)
                    owner_role = Role.objects.create(
                        workspace=workspace,
                        name="Dono",
                        is_system_owner=True,
                        permissions=["all_access"] 
                    )

                    default_role = Role.objects.create(
                        workspace=workspace,
                        name="Membro da Equipe",
                        is_default=True,
                        permissions=[] # Começa sem permissões especiais
                    )

                    domain_name = f"{domain_slug}.{settings.TENANT_BASE_DOMAIN}"
                    
                    Domain.objects.create(
                        domain=domain_name,
                        tenant=workspace,
                        is_primary=True
                    )

                    WorkspaceMembership.objects.create(
                        workspace=workspace,
                        user=user,
                        role=owner_role 
                    )

                    user.default_workspace = workspace
                    user.save()
                    
                    invite.status = InviteStatus.ACCEPTED
                    invite.save()

                    login(request, user)
                    return HttpResponse(f"<h1>Workspace {workspace.name} criado com sucesso!</h1><p>Seu banco isolado está pronto.</p>")

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao provisionar o sistema: {str(e)}")
    else:
        form = GenesisSetupForm()

    return render(request, 'tenants/genesis_setup.html', {'form': form, 'invite': invite})

@tenant_permission_required()
def tenant_dashboard_view(request):
    workspace = request.tenant
    context = {
        'workspace_name': workspace.name,
    }
    return render(request, 'tenants/dashboard.html', context)

@tenant_permission_required()
def team_list_view(request):
    workspace = request.tenant
    
    # O select_related('role') otimiza a query no banco de dados
    members = WorkspaceMembership.objects.filter(workspace=workspace).select_related('user', 'role')
    
    pending_invites = WorkspaceInvite.objects.filter(
        workspace=workspace, 
        status=InviteStatus.PENDING
    ).select_related('role').order_by('-created_at')

    # Passamos o workspace para o form saber quais cargos listar
    form = TeamInviteForm(workspace=workspace)

    context = {
        'members': members,
        'pending_invites': pending_invites,
        'form': form
    }
    return render(request, 'tenants/team_list.html', context)

@tenant_permission_required()
def team_invite_view(request):
    workspace = request.tenant
    
    # 1. Nova checagem de permissão baseada no Role
    membership = WorkspaceMembership.objects.select_related('role').get(workspace=workspace, user=request.user)
    
    # Se não for dono E não tiver a permissão 'users.invite' na lista, bloqueia!
    if not (membership.role.is_system_owner or 'users.invite' in membership.role.permissions):
        messages.error(request, "Você não tem permissão para convidar novos membros.")
        return redirect('team_list')

    if request.method == 'POST':
        # Passamos o workspace para o form
        form = TeamInviteForm(request.POST, workspace=workspace)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.workspace = workspace
            invite.invited_by = request.user
            invite.save()

            domain = request.get_host()
            link = f"http://{domain}/aceitar-convite/{invite.token}/"
            
            assunto = f'Convite para juntar-se à {workspace.name}'
            mensagem = f'Olá!\n\nVocê foi convidado por {request.user.first_name} para participar do workspace {workspace.name} como {invite.role.name}.\n\nClique no link para acessar:\n\n{link}'
            
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [invite.email],
                fail_silently=False,
            )
            
            messages.success(request, f"Convite enviado com sucesso para {invite.email}!")
        else:
            messages.error(request, "Erro ao enviar o convite. Verifique os dados.")
            
    return redirect('team_list')

def accept_invite_view(request, token):
    workspace = request.tenant
    invite = get_object_or_404(WorkspaceInvite, token=token, workspace=workspace, status=InviteStatus.PENDING)
    
    user_exists = User.objects.filter(email=invite.email).exists()

    if request.method == 'POST':
        if user_exists:
            user = User.objects.get(email=invite.email)
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=user,
                # Usa o cargo que foi definido no convite
                defaults={'role': invite.role} 
            )
            invite.status = InviteStatus.ACCEPTED
            invite.save()
            
            messages.success(request, f"Você entrou no workspace {workspace.name} com sucesso!")
            return redirect('login') 
            
        else:
            form = EmployeeSetupForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        user = User.objects.create(
                            email=invite.email,
                            first_name=form.cleaned_data['first_name'],
                            last_name=form.cleaned_data['last_name'],
                            is_active=True,
                            email_verified=True 
                        )
                        user.set_password(form.cleaned_data['password'])
                        
                        user.default_workspace = workspace
                        user.save()

                        WorkspaceMembership.objects.create(
                            workspace=workspace,
                            user=user,
                            # Usa o cargo que foi definido no convite
                            role=invite.role 
                        )
                        
                        invite.status = InviteStatus.ACCEPTED
                        invite.save()

                        login(request, user)
                        return redirect('tenant_dashboard')

                except Exception as e:
                    messages.error(request, f"Erro ao processar convite: {str(e)}")
    else:
        form = EmployeeSetupForm() if not user_exists else None

    context = {
        'invite': invite,
        'form': form,
        'user_exists': user_exists,
        'workspace': workspace
    }
    return render(request, 'tenants/accept_invite.html', context)

@tenant_permission_required('roles.manage')
def role_list_view(request):
    workspace = request.tenant
    # Traz todos os cargos da empresa atual
    roles = Role.objects.filter(workspace=workspace).order_by('-is_system_owner', 'name')
    
    return render(request, 'tenants/role_list.html', {'roles': roles})

@tenant_permission_required('roles.manage')
def role_create_view(request):
    workspace = request.tenant

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.workspace = workspace
            
            # Se esse cargo foi marcado como padrão, desmarca o anterior
            if role.is_default:
                Role.objects.filter(workspace=workspace, is_default=True).update(is_default=False)
                
            # Salva a lista de permissões no JSON
            role.permissions = form.cleaned_data['permissions']
            role.save()
            
            messages.success(request, f"Cargo '{role.name}' criado com sucesso!")
            return redirect('role_list')
    else:
        form = RoleForm()

    return render(request, 'tenants/role_form.html', {'form': form})