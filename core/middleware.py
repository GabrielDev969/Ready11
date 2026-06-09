import logging
import time

logger = logging.getLogger('request')

_SKIP_PREFIXES = ('/static/', '/ws/')
_SKIP_EXACT = frozenset(['/healthz/', '/healthz', '/robots.txt', '/favicon.ico'])


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
