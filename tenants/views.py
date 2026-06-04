from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login
from django.utils.text import slugify
from django.db import transaction
from django.contrib import messages

from .models import WorkspaceInvite, Workspace, Domain, WorkspaceMembership, InviteStatus
from .forms import GenesisSetupForm

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
                    domain_name = f"{schema_name}.localhost" 
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

# Importe provisório para evitar erro no retorno
from django.http import HttpResponse