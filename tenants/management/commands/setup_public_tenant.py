import os

from django.core.management.base import BaseCommand

from tenants.models import Domain, Workspace


class Command(BaseCommand):
    help = 'Create the base public tenant and domain if they do not exist.'

    def handle(self, *args, **kwargs):
        # Check whether the public tenant is already in the database.
        if not Workspace.objects.filter(schema_name='public').exists():
            self.stdout.write('Creating public tenant...')

            public_tenant = Workspace(schema_name='public', name='Ready11')
            public_tenant.save()

            # Read the domain from the environment, defaulting to localhost in development.
            domain_name = os.environ.get('PUBLIC_DOMAIN', 'localhost')

            Domain.objects.create(
                domain=domain_name,
                tenant=public_tenant,
                is_primary=True
            )
            self.stdout.write(self.style.SUCCESS(f'Public tenant created on domain: {domain_name}'))
        else:
            self.stdout.write(self.style.WARNING('Public tenant already exists. No action needed.'))
