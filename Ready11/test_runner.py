from django.test.runner import DiscoverRunner


class TenantAwareTestRunner(DiscoverRunner):
    """
    Test runner that bootstraps the public tenant after the test database is
    created, so TenantMainMiddleware can resolve 'testserver' (the default
    SERVER_NAME used by Django's test client).

    Without this, every HTTP request in tests returns 404 because there is no
    Domain record for 'testserver' in the fresh test database.
    """

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        self._bootstrap_public_tenant()
        return result

    @staticmethod
    def _bootstrap_public_tenant():
        from django.core.management import call_command

        from apps.tenants.models import Domain, Workspace

        # Create the public workspace (schema already exists from migrations).
        call_command('setup_public_tenant', verbosity=0)

        # Add 'testserver' domain so Django's test client resolves correctly.
        public = Workspace.objects.get(schema_name='public')
        Domain.objects.get_or_create(
            tenant=public,
            domain='testserver',
            defaults={'is_primary': False},
        )
