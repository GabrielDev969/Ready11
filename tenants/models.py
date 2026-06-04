from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

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