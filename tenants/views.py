import logging
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login
from django.urls import reverse
from django.utils.text import slugify
from django.db import transaction
from django.contrib import messages
from .decorators import tenant_permission_required
from django.conf import settings
from django.core.mail import send_mail

from django.http import HttpResponse

# Adicionei o Role aqui nos imports
from .models import WorkspaceInvite, Workspace, Domain, WorkspaceMembership, InviteStatus, Role, default_expiration
from .forms import GenesisSetupForm, TeamInviteForm, EmployeeSetupForm, RoleForm

User = get_user_model()
logger = logging.getLogger(__name__)

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


def _send_invite_email(request, invite):
    """Send (or resend) the team invitation email with an absolute, scheme-aware link."""
    link = request.build_absolute_uri(f"/aceitar-convite/{invite.token}/")
    assunto = f'Convite para juntar-se à {invite.workspace.name}'
    mensagem = (
        f'Olá!\n\nVocê foi convidado por {request.user.first_name} para participar '
        f'do workspace {invite.workspace.name} como {invite.role.name}.\n\n'
        f'Clique no link para acessar (válido por 24 horas):\n\n{link}'
    )
    send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [invite.email], fail_silently=False)

def genesis_setup_view(request, token):
    invite = get_object_or_404(WorkspaceInvite, token=token)

    # Lazily mark expired invites, then block any link that is no longer usable
    # (expired, cancelled or already accepted).
    if invite.status == InviteStatus.PENDING and invite.is_expired:
        invite.expire()
    if not invite.is_usable:
        return render(request, 'tenants/invite_unavailable.html', status=410)

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

                    schema_name = build_schema_name(company_name)

                    base_schema_name = schema_name
                    base_domain_slug = schema_name.replace('_', '-')
                    counter = 1
                    # Ajuste fino: Se o schema tiver contador, o domínio também deve ter
                    domain_slug = base_domain_slug

                    while Workspace.objects.filter(schema_name=schema_name).exists():
                        suffix = f"_{counter}"
                        schema_name = f"{base_schema_name[:MAX_SCHEMA_LENGTH - len(suffix)]}{suffix}"
                        domain_slug = f"{base_domain_slug}-{counter}"
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

            except Exception:
                logger.exception("Failed to provision workspace from genesis invite %s", invite.pk)
                messages.error(request, "Something went wrong while provisioning your workspace. Please try again.")
    else:
        form = GenesisSetupForm()

    return render(request, 'tenants/genesis_setup.html', {'form': form, 'invite': invite})

@tenant_permission_required()
def tenant_home_view(request):
    """
    Workspace home ("Início"). Accessible to ANY member, regardless of role —
    this is the safe landing so a user with no permissions still has somewhere
    to go. Shows system-wide update notifications.
    """
    workspace = request.tenant
    return render(request, 'tenants/home.html', {'workspace': workspace})


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

            _send_invite_email(request, invite)
            messages.success(request, f"Convite enviado com sucesso para {invite.email}!")
        else:
            messages.error(request, "Erro ao enviar o convite. Verifique os dados.")

    return redirect('team_list')


@tenant_permission_required('users.invite')
def invite_cancel_view(request, invite_id):
    """Cancel a pending invite (revokes its link)."""
    if request.method != 'POST':
        return redirect('team_list')

    invite = get_object_or_404(WorkspaceInvite, id=invite_id, workspace=request.tenant)
    if invite.status == InviteStatus.PENDING:
        invite.cancel()
        messages.success(request, f"Convite para {invite.email} cancelado.")
    else:
        messages.error(request, "Este convite não pode ser cancelado.")

    return redirect('team_list')


@tenant_permission_required('users.invite')
def invite_resend_view(request, invite_id):
    """Resend an invite, generating a brand-new token and a fresh 24h window."""
    if request.method != 'POST':
        return redirect('team_list')

    invite = get_object_or_404(WorkspaceInvite, id=invite_id, workspace=request.tenant)
    if invite.status in (InviteStatus.ACCEPTED, InviteStatus.CANCELLED):
        messages.error(request, "Este convite não pode ser reenviado.")
        return redirect('team_list')

    # New token invalidates the previous link; reset status and expiration window.
    invite.token = uuid.uuid4()
    invite.status = InviteStatus.PENDING
    invite.expires_at = default_expiration()
    invite.save(update_fields=['token', 'status', 'expires_at'])

    _send_invite_email(request, invite)
    messages.success(request, f"Convite reenviado para {invite.email}.")
    return redirect('team_list')

def accept_invite_view(request, token):
    workspace = request.tenant
    invite = get_object_or_404(WorkspaceInvite, token=token, workspace=workspace)

    # Lazily mark expired invites, then block any link that is no longer usable
    # (expired, cancelled or already accepted).
    if invite.status == InviteStatus.PENDING and invite.is_expired:
        invite.expire()
    if not invite.is_usable:
        return render(request, 'tenants/invite_unavailable.html', status=410)

    user_exists = User.objects.filter(email=invite.email).exists()

    if request.method == 'POST':
        if user_exists:
            # Existing accounts must be authenticated as the invited e-mail before
            # being added to the workspace. Possession of the link is not enough.
            if not request.user.is_authenticated:
                messages.info(request, "Please log in to accept this invitation.")
                return redirect(f"{reverse('login')}?next={request.get_full_path()}")

            if request.user.email.lower() != invite.email.lower():
                messages.error(request, "This invitation was sent to a different account.")
                return redirect('login')

            user = request.user
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=user,
                # Usa o cargo que foi definido no convite
                defaults={'role': invite.role}
            )
            # First workspace a user joins becomes their default.
            if user.default_workspace is None:
                user.default_workspace = workspace
                user.save(update_fields=['default_workspace'])

            invite.status = InviteStatus.ACCEPTED
            invite.save()

            messages.success(request, f"Você entrou no workspace {workspace.name} com sucesso!")
            return redirect('tenant_dashboard')

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

                except Exception:
                    logger.exception("Failed to accept invite %s for new user", invite.pk)
                    messages.error(request, "Something went wrong while processing your invitation. Please try again.")
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