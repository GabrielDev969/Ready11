from django.contrib import admin
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .models import Workspace, WorkspaceInvite, WorkspaceRole

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'created_on')
    search_fields = ('name', 'schema_name')

@admin.register(WorkspaceRole)
class WorkspaceRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace')

@admin.register(WorkspaceInvite)
class WorkspaceInviteAdmin(admin.ModelAdmin):
    # O que aparece na listagem
    list_display = ('email', 'workspace', 'is_tenant_admin', 'status', 'created_at')
    list_filter = ('status', 'is_tenant_admin')
    search_fields = ('email',)
    
    # Campos que o Django preenche sozinho (não deixamos editar na tela)
    readonly_fields = ('token', 'invited_by', 'status')

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        
        if is_new:
            # Registra que foi você (o admin logado) quem enviou o convite
            obj.invited_by = request.user
        
        # Salva o convite no banco de dados primeiro
        super().save_model(request, obj, form, change)

        # Se for um convite NOVO e for GÊNESIS (sem workspace vinculado)
        if is_new and not obj.workspace:
            domain = request.get_host()
            
            # ATENÇÃO: Essa rota 'genesis_setup' ainda vamos criar na view, 
            # mas já deixamos o link preparado aqui.
            link = f"http://{domain}/convite/{obj.token}/"
            
            assunto = 'Convite Exclusivo - Configure seu Workspace'
            mensagem = f'Olá!\n\nVocê foi selecionado para ter acesso ao nosso sistema.\n\nClique no link abaixo para criar o seu Workspace e definir o nome da sua empresa:\n\n{link}'
            
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [obj.email],
                fail_silently=False,
            )