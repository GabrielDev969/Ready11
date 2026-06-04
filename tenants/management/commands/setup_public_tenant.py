import os
from django.core.management.base import BaseCommand
from tenants.models import Workspace, Domain

class Command(BaseCommand):
    help = 'Cria o tenant e dominio publico base, se nao existirem.'

    def handle(self, *args, **kwargs):
        # Verifica se o tenant publico ja esta no banco
        if not Workspace.objects.filter(schema_name='public').exists():
            self.stdout.write('Criando tenant publico...')
            
            tenant_publico = Workspace(schema_name='public', name='Ready11')
            tenant_publico.save()

            # Aqui mora um detalhe vital: o dominio.
            # Lemos da variavel de ambiente, com fallback para localhost no desenvolvimento
            domain_name = os.environ.get('PUBLIC_DOMAIN', 'localhost')
            
            Domain.objects.create(
                domain=domain_name,
                tenant=tenant_publico,
                is_primary=True
            )
            self.stdout.write(self.style.SUCCESS(f'Tenant publico criado com sucesso no dominio: {domain_name}'))
        else:
            self.stdout.write(self.style.WARNING('Tenant publico ja existe. Nenhuma acao necessaria.'))