from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import InviteStatus, Role, WorkspaceInvite, WorkspaceMembership
from .services import create_workspace, expire_stale_invites

User = get_user_model()


class CreateWorkspaceServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email='owner@example.com', password='Str0ng!Pass',
            first_name='Olive', last_name='Owner', email_verified=True,
        )
        cls.workspace = create_workspace('Acme Co', cls.owner)

    def test_creates_fully_provisioned_workspace(self):
        workspace = self.workspace
        self.assertEqual(workspace.schema_name, 'acme_co')
        self.assertEqual(workspace.owner, self.owner)

        domain = workspace.domains.get(is_primary=True)
        self.assertEqual(domain.domain, f'acme-co.{settings.TENANT_BASE_DOMAIN}')

        role_names = set(Role.objects.filter(workspace=workspace).values_list('name', flat=True))
        self.assertEqual(role_names, {'Owner', 'Team Member'})

        membership = WorkspaceMembership.objects.get(workspace=workspace, user=self.owner)
        self.assertTrue(membership.role.is_system_owner)

        self.owner.refresh_from_db()
        self.assertEqual(self.owner.default_workspace, workspace)

    def test_schema_collision_gets_counter_suffix(self):
        other = User.objects.create_user(
            email='other@example.com', password='Str0ng!Pass',
            first_name='Oscar', last_name='Other', email_verified=True,
        )
        second = create_workspace('Acme Co', other)
        self.assertEqual(second.schema_name, 'acme_co_1')

        domain = second.domains.get(is_primary=True)
        self.assertEqual(domain.domain, f'acme-co-1.{settings.TENANT_BASE_DOMAIN}')


class ExpireStaleInvitesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        # Genesis invites (workspace=None) avoid creating a tenant schema.
        cls.stale = WorkspaceInvite.objects.create(
            email='stale@example.com', expires_at=now - timedelta(hours=1),
        )
        cls.valid = WorkspaceInvite.objects.create(
            email='valid@example.com', expires_at=now + timedelta(hours=1),
        )

    def test_only_stale_pending_invites_are_expired(self):
        self.assertEqual(expire_stale_invites(), 1)

        self.stale.refresh_from_db()
        self.valid.refresh_from_db()
        self.assertEqual(self.stale.status, InviteStatus.EXPIRED)
        self.assertEqual(self.valid.status, InviteStatus.PENDING)

        # Idempotent: a second run finds nothing left to expire.
        self.assertEqual(expire_stale_invites(), 0)


class HealthCheckTest(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get(reverse('healthz'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')


class RobotsTxtTest(TestCase):
    def test_robots_txt_accessible(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn(b'User-agent', response.content)
        self.assertIn(b'/admin/', response.content)
