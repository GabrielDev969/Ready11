from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core.views import error_403, error_404, error_500


class ErrorPageTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_404_view_returns_404_status(self):
        request = self.factory.get('/nonexistent/')
        response = error_404(request, exception=Exception('Not found'))
        self.assertEqual(response.status_code, 404)

    def test_403_view_returns_403_status(self):
        request = self.factory.get('/')
        response = error_403(request, exception=Exception('Forbidden'))
        self.assertEqual(response.status_code, 403)

    def test_500_view_returns_500_status(self):
        request = self.factory.get('/')
        response = error_500(request)
        self.assertEqual(response.status_code, 500)


class HealthCheckTest(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get(reverse('healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')


class RobotsTxtTest(TestCase):
    def test_robots_txt_accessible(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn(b'User-agent', response.content)
        self.assertIn(b'/admin/', response.content)
