import logging
import time
import zoneinfo

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone, translation

logger = logging.getLogger('request')

# Auth paths that only make sense on the public domain.
# Accessing them on a tenant subdomain redirects to the public domain.
_PUBLIC_ONLY_PREFIXES = (
    '/login/',
    '/register/',
    '/logout/',
    '/forgot-password/',
    '/reset-password/',
    '/verify/',
)

_SKIP_PREFIXES = ('/static/', '/ws/')
_SKIP_EXACT = frozenset(['/healthz/', '/healthz', '/robots.txt', '/favicon.ico'])


class PublicOnlyMiddleware:
    """
    Redirect auth routes (login, register, etc.) to the public domain when
    they are accessed from a tenant subdomain. Those pages have no meaning
    inside a workspace context and confuse users who land on them via a
    direct link or bookmark.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)
        schema = getattr(tenant, 'schema_name', 'public')

        if schema != 'public':
            path = request.path
            if any(path.startswith(p) for p in _PUBLIC_ONLY_PREFIXES):
                base_domain = settings.TENANT_BASE_DOMAIN
                host = request.get_host()
                port = f":{host.split(':')[1]}" if ':' in host else ''
                public_url = f"{request.scheme}://{base_domain}{port}{path}"
                if request.META.get('QUERY_STRING'):
                    public_url += f"?{request.META['QUERY_STRING']}"
                return HttpResponseRedirect(public_url)

        return self.get_response(request)


class WorkspaceTimezoneMiddleware:
    """
    Activate the workspace's configured timezone for every tenant request.
    Falls back to UTC (Django's default) on the public schema or if the stored
    timezone name is invalid.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = None
        tenant = getattr(request, 'tenant', None)
        if tenant and getattr(tenant, 'schema_name', 'public') != 'public':
            tz_name = getattr(tenant, 'timezone', None) or None

        if tz_name:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tz_name))
            except (zoneinfo.ZoneInfoNotFoundError, KeyError):
                timezone.deactivate()
        else:
            timezone.deactivate()

        response = self.get_response(request)
        timezone.deactivate()
        return response


class UserLanguageMiddleware:
    """
    Apply the authenticated user's saved language preference on every request.
    Runs after LocaleMiddleware so it takes priority over Accept-Language headers.
    Unauthenticated users and users without a saved preference keep the default (English).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            lang = getattr(user, 'language', '') or ''
            if lang:
                translation.activate(lang)
                request.LANGUAGE_CODE = lang
        return self.get_response(request)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path in _SKIP_EXACT or any(path.startswith(p) for p in _SKIP_PREFIXES):
            return self.get_response(request)

        t0 = time.monotonic()
        response = self.get_response(request)
        ms = round((time.monotonic() - t0) * 1000)

        logger.info(
            '%s %s %s %dms',
            request.method,
            path,
            response.status_code,
            ms,
            extra={
                'method': request.method,
                'path': path,
                'status': response.status_code,
                'duration_ms': ms,
            },
        )
        return response
