import uuid
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Workspace(TenantMixin):
    # Campos exigidos pela sua regra de negócio
    name = models.CharField(max_length=100, verbose_name="Nome da Companhia")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    created_on = models.DateField(auto_now_add=True)
    
    # Aqui entrariam campos como 'plano', 'limite_usuarios', etc.

    # OBRIGATÓRIO: Diz ao django-tenants para rodar CREATE SCHEMA ao salvar
    auto_create_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    # DomainMixin já traz os campos 'domain' e 'tenant' (ForeignKey)
    pass
    
# Lista de Permissões Base
AVAILABLE_PERMISSIONS = [
    'tenant.update',
    'tenant.delete',
    'users.invite',
    'users.remove',
]

class WorkspaceRole(models.Model):
    """
    Cargos customizados que o Dono do workspace pode criar.
    Ex: Nome: "Financeiro", Permissões: ["billing.view", "billing.update"]
    """
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50, verbose_name="Nome do Cargo")
    
    # O JSONField vai guardar uma lista simples de strings: ["tenant.update", "users.invite"]
    permissions = models.JSONField(default=list, verbose_name="Permissões")

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"

class InviteStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    ACCEPTED = 'accepted', 'Aceito'
    EXPIRED = 'expired', 'Expirado'

def default_expiration():
    return timezone.now() + timedelta(days=3)

class WorkspaceInvite(models.Model):
    email = models.EmailField(verbose_name="E-mail Convidado")
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='invites', null=True, blank=True)
    
    # Em vez de um cargo fixo, passamos se ele será o dono ou qual cargo customizado ele terá
    is_tenant_admin = models.BooleanField(default=False, verbose_name="Será Dono/Admin?")
    role = models.ForeignKey(WorkspaceRole, on_delete=models.SET_NULL, null=True, blank=True)
    
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=InviteStatus.choices, default=InviteStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiration)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Convite para {self.email} ({self.status})"

class WorkspaceMembership(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    
    # A única regra fixa do sistema: O Dono tem passe livre
    is_tenant_admin = models.BooleanField(default=False, verbose_name="É Dono/Admin?")
    
    # Se não for dono, precisa ter um cargo customizado com as permissões atreladas
    role = models.ForeignKey(WorkspaceRole, on_delete=models.SET_NULL, null=True, blank=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')

    def __str__(self):
        tipo = "ADMIN" if self.is_tenant_admin else getattr(self.role, 'name', 'Sem Cargo')
        return f"{self.user.email} - {tipo} em {self.workspace.name}"