from django.test import TestCase
from django.urls import reverse


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
