from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login
from django.utils.text import slugify
from django.db import transaction
from django.contrib import messages
from .decorators import tenant_permission_required
from django.conf import settings
from django.core.mail import send_mail

# Importe provisório para evitar erro no retorno
from django.http import HttpResponse

from .models import WorkspaceInvite, Workspace, Domain, WorkspaceMembership, InviteStatus
from .forms import GenesisSetupForm, TeamInviteForm, EmployeeSetupForm

User = get_user_model()

def genesis_setup_view(request, token):
    # 1. Valida o Token
    invite = get_object_or_404(WorkspaceInvite, token=token, status=InviteStatus.PENDING)

    if request.method == 'POST':
        form = GenesisSetupForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            # Usamos o transaction.atomic() para garantir que, se algo der erro no meio 
            # (ex: falha ao criar o schema), o Django desfaz tudo e não deixa lixo no banco.
            try:
                with transaction.atomic():
                    # 2. Cria o Usuário Global (já com e-mail verificado, pois ele clicou no link)
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

                    # 3. Cria o Schema físico da Empresa no PostgreSQL
                    # Substitui hifens por underlines para evitar problemas de sintaxe no Postgres
                    schema_name = slugify(company_name).replace('-', '_')

                    # Garante que o schema seja único (adiciona um sufixo se necessário)
                    base_schema_name = schema_name
                    counter = 1
                    while Workspace.objects.filter(schema_name=schema_name).exists():
                        schema_name = f"{base_schema_name}_{counter}"
                        counter += 1

                    workspace = Workspace.objects.create(
                        name=company_name,
                        schema_name=schema_name
                    )

                    # 4. Cria o Domínio Virtual
                    # No futuro, 'localhost' será substituído pela variável do seu domínio de produção
                    domain_name = f"{slugify(company_name)}.{settings.TENANT_BASE_DOMAIN}"
                    Domain.objects.create(
                        domain=domain_name,
                        tenant=workspace,
                        is_primary=True
                    )

                    # 5. Dá o poder de Dono para o usuário
                    WorkspaceMembership.objects.create(
                        workspace=workspace,
                        user=user,
                        is_tenant_admin=True
                    )

                    # 6. Atualiza o perfil e "queima" o convite
                    user.default_workspace = workspace
                    user.save()
                    
                    invite.status = InviteStatus.ACCEPTED
                    invite.save()

                    # 7. Loga o usuário e manda para o sistema
                    login(request, user)
                    return HttpResponse(f"<h1>Workspace {workspace.name} criado com sucesso!</h1><p>Seu banco isolado está pronto.</p>")

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao provisionar o sistema: {str(e)}")
    else:
        # Pré-preenche o e-mail (que já sabemos qual é) apenas visualmente, se quisermos
        form = GenesisSetupForm()

    return render(request, 'tenants/genesis_setup.html', {'form': form, 'invite': invite})

@tenant_permission_required() # Usa as regras de segurança padrão (pertencer ao tenant)
def tenant_dashboard_view(request):
    # O django-tenants já sabe qual é a empresa pela URL e injeta o objeto aqui!
    workspace = request.tenant
    
    context = {
        'workspace_name': workspace.name,
    }
    
    return render(request, 'tenants/dashboard.html', context)

@tenant_permission_required()
def team_list_view(request):
    workspace = request.tenant
    
    # 1. Pega quem já está dentro da empresa
    members = WorkspaceMembership.objects.filter(workspace=workspace).select_related('user')
    
    # 2. Pega os convites que o dono enviou mas ainda não foram aceitos
    pending_invites = WorkspaceInvite.objects.filter(
        workspace=workspace, 
        status=InviteStatus.PENDING
    ).order_by('-created_at')

    form = TeamInviteForm()

    context = {
        'members': members,
        'pending_invites': pending_invites,
        'form': form
    }
    return render(request, 'tenants/team_list.html', context)


@tenant_permission_required() # No futuro, você pode exigir a permissão 'users.invite' aqui
def team_invite_view(request):
    workspace = request.tenant
    
    # Por segurança, garante que apenas admins do tenant possam convidar
    membership = WorkspaceMembership.objects.get(workspace=workspace, user=request.user)
    if not membership.is_tenant_admin:
        messages.error(request, "Apenas administradores podem convidar novos membros.")
        return redirect('team_list')

    if request.method == 'POST':
        form = TeamInviteForm(request.POST)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.workspace = workspace
            invite.invited_by = request.user
            invite.save()

            # Dispara o e-mail
            # Como estamos dentro do tenant, a URL será do próprio subdomínio
            domain = request.get_host()
            link = f"http://{domain}/aceitar-convite/{invite.token}/"
            
            assunto = f'Convite para juntar-se à {workspace.name}'
            mensagem = f'Olá!\n\nVocê foi convidado por {request.user.first_name} para participar do workspace {workspace.name}.\n\nClique no link para acessar:\n\n{link}'
            
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
    
    # Verifica se o usuário já tem conta no sistema global
    user_exists = User.objects.filter(email=invite.email).exists()

    if request.method == 'POST':
        if user_exists:
            user = User.objects.get(email=invite.email)
            # Apenas cria o vínculo
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=user,
                defaults={'is_tenant_admin': invite.is_tenant_admin}
            )
            invite.status = InviteStatus.ACCEPTED
            invite.save()
            
            messages.success(request, f"Você entrou no workspace {workspace.name} com sucesso!")
            return redirect('login') # Manda para o login normal
            
        else:
            form = EmployeeSetupForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Cria o novo usuário
                        user = User.objects.create(
                            email=invite.email,
                            first_name=form.cleaned_data['first_name'],
                            last_name=form.cleaned_data['last_name'],
                            is_active=True,
                            email_verified=True # Já clicou no link
                        )
                        user.set_password(form.cleaned_data['password'])
                        
                        # Se for o primeiro workspace dele, define como padrão
                        user.default_workspace = workspace
                        user.save()

                        # Cria o vínculo com o workspace
                        WorkspaceMembership.objects.create(
                            workspace=workspace,
                            user=user,
                            is_tenant_admin=invite.is_tenant_admin
                        )
                        
                        invite.status = InviteStatus.ACCEPTED
                        invite.save()

                        # Loga o funcionário direto
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