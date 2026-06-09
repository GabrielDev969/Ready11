"""
Best-effort distributed lock backed by Redis.

Used so the in-process cleanup scheduler runs the purge once across replicas. When
``REDIS_URL`` isn't set (single-process dev), there's nothing to coordinate, so the
lock is a no-op that always "acquires" — the purge just runs locally.
"""
import logging
from contextlib import contextmanager

from django.conf import settings

logger = logging.getLogger(__name__)


@contextmanager
def distributed_lock(name, timeout=300, release=True):
    """
    Yield True if this process holds the lock (and should do the work), False if
    another replica already holds it. Safe when Redis is absent or unreachable.

    ``release=True`` frees the lock on exit (use for short critical sections).
    ``release=False`` keeps it until the ``timeout`` (TTL) expires — use for
    "run once per period" tasks so other replicas skip that window.
    """
    redis_url = getattr(settings, 'REDIS_URL', None)
    if not redis_url:
        # No shared backend → single process; just run.
        yield True
        return

    client = None
    acquired = False
    try:
        import redis  # provided by channels-redis
        client = redis.Redis.from_url(redis_url)
        # SET key value NX EX timeout → atomic acquire with auto-expiry.
        acquired = bool(client.set(f'lock:{name}', '1', nx=True, ex=timeout))
        yield acquired
    except Exception:
        # If Redis is misbehaving, don't block the work — fall back to running.
        logger.warning("Distributed lock unavailable (%s); proceeding without it.", name, exc_info=True)
        yield True
        return
    finally:
        if client is not None and acquired and release:
            try:
                client.delete(f'lock:{name}')
            except Exception:
                pass  # the EX timeout will release it anyway
