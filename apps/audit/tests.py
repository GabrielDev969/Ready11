from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

import apps.audit.actions as audit_actions
from apps.audit.models import AuditLog
from apps.audit.services import log_action

User = get_user_model()


class AuditLogServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='audit@example.com',
            password='SecurePass1!',
            first_name='Audit',
            last_name='User',
            is_active=True,
            email_verified=True,
        )
        self.factory = RequestFactory()

    def test_log_action_creates_record(self):
        log_action(self.user, audit_actions.WORKSPACE_CREATED, detail={'workspace_name': 'Acme'})
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.first()
        self.assertEqual(log.action, audit_actions.WORKSPACE_CREATED)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.detail, {'workspace_name': 'Acme'})

    def test_log_action_with_resource_captures_type_and_id(self):
        log_action(self.user, audit_actions.MEMBER_REMOVED, resource=self.user)
        log = AuditLog.objects.first()
        self.assertEqual(log.resource_type, 'CustomUser')
        self.assertEqual(log.resource_id, str(self.user.pk))

    def test_log_action_extracts_ip_from_request(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        # django-tenants adds a tenant attribute; simulate public schema
        request.tenant = None
        log_action(self.user, audit_actions.MEMBER_JOINED, request=request)
        log = AuditLog.objects.first()
        self.assertEqual(log.ip_address, '192.168.1.100')

    def test_log_action_extracts_ip_from_x_forwarded_for(self):
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 172.16.0.1'
        request.tenant = None
        log_action(self.user, audit_actions.MEMBER_JOINED, request=request)
        log = AuditLog.objects.first()
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_log_action_with_none_user(self):
        log_action(None, audit_actions.WORKSPACE_CREATED)
        log = AuditLog.objects.first()
        self.assertIsNone(log.user)

    def test_log_action_silently_noop_on_invalid_data(self):
        # Passing a bad IP should not raise — the service swallows errors.
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = 'not-an-ip'
        request.tenant = None
        try:
            log_action(self.user, audit_actions.MEMBER_JOINED, request=request)
        except Exception as exc:
            self.fail(f'log_action raised unexpectedly: {exc}')

    def test_audit_log_str(self):
        log_action(self.user, audit_actions.ROLE_CREATED)
        log = AuditLog.objects.first()
        self.assertIn(audit_actions.ROLE_CREATED, str(log))

    def test_audit_log_ordering_newest_first(self):
        log_action(self.user, audit_actions.ROLE_CREATED)
        log_action(self.user, audit_actions.ROLE_UPDATED)
        logs = list(AuditLog.objects.values_list('action', flat=True))
        self.assertEqual(logs[0], audit_actions.ROLE_UPDATED)
        self.assertEqual(logs[1], audit_actions.ROLE_CREATED)
