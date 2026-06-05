import uuid
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# ==========================================
# CONSTANTES DE PERMISSÕES
# ==========================================
# Esta lista servirá para criarmos os "checkboxes" na tela de criar cargos depois.
AVAILABLE_PERMISSIONS = [
    'tenant.update',          # Pode editar dados da empresa
    'tenant.delete',          # Pode deletar a empresa (Geralmente só o Dono tem)
    'users.view',             # Pode ver a equipe
    'users.invite',           # Pode convidar novas pessoas
    'users.remove',           # Pode remover membros
    'roles.manage',           # Pode criar/editar cargos
]

# ==========================================
# MODELOS CORE (TENANT)
# ==========================================

class Workspace(TenantMixin):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # O ÚNICO Dono absoluto do workspace. Só ele não pode ser deletado.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='owned_workspaces', 
        null=True, 
        blank=True
    )

    auto_create_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    # DomainMixin já traz os campos 'domain' e 'tenant' (ForeignKey)
    pass
    

# ==========================================
# SISTEMA DE CARGOS (RBAC)
# ==========================================

class Role(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50, verbose_name="Nome do Cargo")
    
    # Travas do Sistema
    is_system_owner = models.BooleanField(default=False) # Trava para o cargo "Dono" não ser editado
    is_default = models.BooleanField(default=False) # Cargo padrão para novos convites
    
    # Permissões salvas como uma lista: ["users.invite", "roles.manage"]
    permissions = models.JSONField(default=list, verbose_name="Permissões") 

    class Meta:
        unique_together = ('workspace', 'name') # Impede dois cargos com mesmo nome na empresa

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"


# ==========================================
# MEMBROS E CONVITES
# ==========================================

class WorkspaceMembership(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    
    # Adeus is_tenant_admin! Todo membro obrigatoriamente tem um Cargo (Role).
    # Usamos PROTECT para impedir que deletem um cargo se houver gente usando ele.
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='members')
    
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.role.name} em {self.workspace.name}"


class InviteStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    ACCEPTED = 'accepted', 'Aceito'
    EXPIRED = 'expired', 'Expirado'
    CANCELLED = 'cancelled', 'Cancelado'

def default_expiration():
    # Convites valem por 24 horas a partir da criação/reenvio.
    return timezone.now() + timedelta(hours=24)

class WorkspaceInvite(models.Model):
    email = models.EmailField(verbose_name="E-mail Convidado")
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invites', null=True, blank=True)
    
    # Quando o convite for aceito, a pessoa receberá este cargo.
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=InviteStatus.choices, default=InviteStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiration)
    
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Convite para {self.email} ({self.status})"

    @property
    def is_expired(self):
        """True if the invite passed its expiration date."""
        return timezone.now() > self.expires_at

    @property
    def is_usable(self):
        """True only if the invite can still be accepted (pending and not expired)."""
        return self.status == InviteStatus.PENDING and not self.is_expired

    def expire(self):
        """Mark this invite as expired and persist the change."""
        if self.status == InviteStatus.PENDING:
            self.status = InviteStatus.EXPIRED
            self.save(update_fields=['status'])

    def cancel(self):
        """Cancel a pending invite (revokes the link)."""
        if self.status == InviteStatus.PENDING:
            self.status = InviteStatus.CANCELLED
            self.save(update_fields=['status'])