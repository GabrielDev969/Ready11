import os

from django.core.management.base import BaseCommand

from apps.tenants.models import Domain, Workspace

# Extra hostnames that must resolve to the public tenant in development:
# the Prometheus container scrapes the host's runserver through Docker's
# gateway alias.
EXTRA_PUBLIC_DOMAINS = ('host.docker.internal',)


class Command(BaseCommand):
    help = 'Create the base public tenant and domain if they do not exist.'

    def handle(self, *args, **kwargs):
        public_tenant = Workspace.objects.filter(schema_name='public').first()

        if public_tenant is None:
            self.stdout.write('Creating public tenant...')
            public_tenant = Workspace(schema_name='public', name='Ready11')
            public_tenant.save()

            # Read the domain from the environment, defaulting to localhost in development.
            domain_name = os.environ.get('PUBLIC_DOMAIN', 'localhost')
            Domain.objects.create(
                domain=domain_name,
                tenant=public_tenant,
                is_primary=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Public tenant created on domain: {domain_name}'))
        else:
            self.stdout.write(self.style.WARNING('Public tenant already exists.'))

        # Idempotent: make sure the auxiliary domains always exist (safe to
        # re-run after the tenant was first created).
        for domain_name in EXTRA_PUBLIC_DOMAINS:
            _, created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={'tenant': public_tenant, 'is_primary': False},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Added auxiliary public domain: {domain_name}'))
