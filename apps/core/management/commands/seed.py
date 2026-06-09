"""
Creates a development superuser so you can access /admin/ without going through
the full genesis setup flow.

Usage:
    python manage.py seed
    python manage.py seed --email admin@example.com --password mypassword
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

DEFAULT_EMAIL = 'admin@example.com'
DEFAULT_PASSWORD = 'Admin1234!'


class Command(BaseCommand):
    help = 'Create a development superuser for local testing'

    def add_arguments(self, parser):
        parser.add_argument('--email', default=DEFAULT_EMAIL)
        parser.add_argument('--password', default=DEFAULT_PASSWORD)

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User {email} already exists — skipping.'))
        else:
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Admin',
                last_name='Dev',
                email_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser created: {email}'))

        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. python manage.py runserver')
        self.stdout.write('  2. Open http://localhost:8000/ and click "Create your workspace"')
        self.stdout.write('  3. Or go to http://localhost:8000/admin/ to manage data directly')
        self.stdout.write(f'     Email: {email}  Password: {password}')
