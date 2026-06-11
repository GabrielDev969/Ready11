from types import SimpleNamespace

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.middleware import CanonicalHostMiddleware
from apps.core.views import error_403, error_404, error_500


@override_settings(TENANT_BASE_DOMAIN='example.com', ALLOWED_HOSTS=['*'])
class CanonicalHostMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CanonicalHostMiddleware(lambda request: 'reached-view')

    def _request(self, method='get', host='other.host:8000', path='/', schema='public'):
        request = getattr(self.factory, method)(path, HTTP_HOST=host)
        request.tenant = SimpleNamespace(schema_name=schema)
        return request

    def test_get_on_non_canonical_host_redirects_to_public_domain(self):
        response = self.middleware(self._request())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://example.com:8000/')

    def test_canonical_host_passes_through(self):
        response = self.middleware(self._request(host='example.com:8000'))
        self.assertEqual(response, 'reached-view')

    def test_tenant_schema_is_not_redirected(self):
        response = self.middleware(self._request(host='acme.other.host', schema='acme'))
        self.assertEqual(response, 'reached-view')

    def test_post_is_not_redirected(self):
        response = self.middleware(self._request(method='post'))
        self.assertEqual(response, 'reached-view')

    def test_healthz_is_exempt(self):
        response = self.middleware(self._request(path='/healthz/'))
        self.assertEqual(response, 'reached-view')


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


class MetricsEndpointTest(TestCase):
    def test_metrics_open_without_token(self):
        response = self.client.get(reverse('metrics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'django_http_requests_total_by_method_total', response.content)

    def test_metrics_includes_db_instrumentation(self):
        response = self.client.get(reverse('metrics'))
        self.assertIn(b'django_db_query_duration_seconds', response.content)

    @override_settings(METRICS_TOKEN='sekret')
    def test_metrics_rejects_missing_or_wrong_token(self):
        self.assertEqual(self.client.get(reverse('metrics')).status_code, 401)
        response = self.client.get(reverse('metrics'), headers={'Authorization': 'Bearer wrong'})
        self.assertEqual(response.status_code, 401)

    @override_settings(METRICS_TOKEN='sekret')
    def test_metrics_accepts_valid_token(self):
        response = self.client.get(reverse('metrics'), headers={'Authorization': 'Bearer sekret'})
        self.assertEqual(response.status_code, 200)


class RobotsTxtTest(TestCase):
    def test_robots_txt_accessible(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn(b'User-agent', response.content)
        self.assertIn(b'/admin/', response.content)
