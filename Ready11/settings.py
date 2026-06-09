"""
Django settings for Ready11 project.

Base project for B2B SaaS systems (multi-tenant via django-tenants).

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# SECURITY WARNING: don't run with debug turned on in production!
# Defaults to False: production is the safe default; enable DEBUG explicitly in dev.
DEBUG = env_bool('DEBUG', False)

# SECURITY WARNING: keep the secret key used in production secret!
# In production (DEBUG=False) a real SECRET_KEY is mandatory; we never ship an insecure default.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured(
            "The SECRET_KEY environment variable is required when DEBUG=False."
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()
]

# Base domain used to build tenant subdomains (e.g. acme.yourcompany.com).
# In production set PUBLIC_DOMAIN to your real domain.
TENANT_BASE_DOMAIN = os.environ.get('PUBLIC_DOMAIN', 'localhost')

if TENANT_BASE_DOMAIN != 'localhost':
    # Share the session cookie across all tenant subdomains.
    SESSION_COOKIE_DOMAIN = f".{TENANT_BASE_DOMAIN}"

# CSRF trusted origins: required for HTTPS + tenant subdomains.
# Build from PUBLIC_DOMAIN (wildcard subdomain) and allow an explicit env override.
_csrf_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(',') if o.strip()]
elif TENANT_BASE_DOMAIN != 'localhost':
    CSRF_TRUSTED_ORIGINS = [
        f"https://{TENANT_BASE_DOMAIN}",
        f"https://*.{TENANT_BASE_DOMAIN}",
    ]
else:
    CSRF_TRUSTED_ORIGINS = []


# ==========================================
# Applications (django-tenants split)
# ==========================================
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

SHARED_APPS = (
    'daphne',          # ASGI server + enables Channels' runserver (must precede staticfiles)
    'django_tenants',  # tenant routing
    'widget_tweaks',
    'axes',            # brute-force protection (global access-attempt log)
    'core',            # landing page + healthcheck (public)
    'notifications',   # in-app notifications (global)
    'audit',           # workspace audit log
    'tenants',
    'users',
    'django_otp',                            # TOTP / backup-code models (global — users are global)
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',

    # Native Django apps that must be global
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

TENANT_APPS = (
    # Native Django apps available inside each tenant
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',

    # Your business apps go here (e.g. 'sales', 'reports')
)

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

AUTH_USER_MODEL = 'users.CustomUser'

TENANT_MODEL = "tenants.Workspace"          # app.Model
TENANT_DOMAIN_MODEL = "tenants.Domain"

# Authentication backends: AxesStandaloneBackend must come first.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# ==========================================
# Email
# ==========================================
# Console backend in development; SMTP in production (configured via env).
# Use `or` (not a get default) so an empty value in .env doesn't override the default.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND') or (
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT') or 587)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')


# ==========================================
# Middleware
# ==========================================
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # MUST be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.RequestLoggingMiddleware',
    'core.middleware.PublicOnlyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',            # i18n: detects language
    'core.middleware.WorkspaceTimezoneMiddleware',          # activates workspace timezone for tenant requests
    'core.middleware.UserLanguageMiddleware',               # overrides with user's saved preference
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',                    # must follow AuthenticationMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',                       # MUST be last
]

ROOT_URLCONF = 'Ready11.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.workspaces',
                'core.context_processors.tenant_permissions',
                'notifications.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'Ready11.wsgi.application'
ASGI_APPLICATION = 'Ready11.asgi.application'

# Channels channel layer: Redis in production, in-memory for local dev.
# In-memory works for a single process only (fine for `runserver`); production
# behind multiple workers needs REDIS_URL.
# In-process notification cleanup scheduler (runs the retention purge periodically).
# Disable it (NOTIFICATION_CLEANUP_ENABLED=False) if you schedule
# `manage.py cleanup_notifications` externally (cron / Celery beat).
NOTIFICATION_CLEANUP_ENABLED = env_bool('NOTIFICATION_CLEANUP_ENABLED', True)
NOTIFICATION_CLEANUP_INTERVAL_HOURS = int(os.environ.get('NOTIFICATION_CLEANUP_INTERVAL_HOURS', '24'))

AUDIT_CLEANUP_ENABLED = env_bool('AUDIT_CLEANUP_ENABLED', True)
AUDIT_CLEANUP_INTERVAL_HOURS = int(os.environ.get('AUDIT_CLEANUP_INTERVAL_HOURS', '24'))

REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }


# ==========================================
# Database
# ==========================================
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            engine='django_tenants.postgresql_backend',
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif DEBUG:
    # Local development fallback (matches docker-compose.yml).
    DATABASES = {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': 'ready_db',
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': '127.0.0.1',
            'PORT': '5432',
        }
    }
else:
    raise ImproperlyConfigured(
        "The DATABASE_URL environment variable is required when DEBUG=False."
    )


# ==========================================
# Password validation
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'users.validators.StrictPasswordValidator',
    },
]


# ==========================================
# django-axes (brute-force protection)
# ==========================================
AXES_FAILURE_LIMIT = int(os.environ.get('AXES_FAILURE_LIMIT', '5'))
AXES_COOLOFF_TIME = float(os.environ.get('AXES_COOLOFF_HOURS', '1'))  # hours
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_USERNAME_FORM_FIELD = 'email'
AXES_ENABLED = env_bool('AXES_ENABLED', True)


# ==========================================
# Internationalization
# ==========================================
# Source language is English; LocaleMiddleware auto-detects the visitor's language.
LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', _('English')),
    ('pt-br', _('Portuguese (Brazil)')),
]

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# ==========================================
# Static files
# ==========================================
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    d for d in [os.path.join(BASE_DIR, 'static')] if os.path.isdir(d)
]

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # CompressedManifestStaticFilesStorage needs a manifest generated by
        # collectstatic (used in production). In dev/test (DEBUG=True) use the
        # plain storage so tests and runserver work without running collectstatic.
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Use a custom test runner that bootstraps the public tenant + 'testserver'
# domain after the test DB is created, so TenantMainMiddleware resolves
# requests correctly in all test cases.
TEST_RUNNER = 'Ready11.test_runner.TenantAwareTestRunner'


# ==========================================
# Production security hardening
# ==========================================
# ==========================================
# Error monitoring (Sentry)
# ==========================================
# Set SENTRY_DSN in production to enable automatic error capture and performance tracing.
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        send_default_pii=False,
    )


if not DEBUG:
    # We sit behind a reverse proxy (Easypanel/Nginx) that terminates TLS.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # The container HEALTHCHECK hits http://localhost:8000/healthz/ without the
    # X-Forwarded-Proto header, so exempt it from the HTTPS redirect (otherwise it
    # gets a 301 and never actually checks the DB).
    SECURE_REDIRECT_EXEMPT = [r'^healthz/?$']
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', str(60 * 60 * 24 * 14)))  # 2 weeks
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', str(60 * 60 * 24 * 365)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ==========================================
# Logging
# ==========================================
# In production set LOG_FORMAT=json to emit structured JSON logs for easy
# ingestion by CloudWatch, Grafana Loki, Datadog, etc.
_LOG_FORMAT = os.environ.get('LOG_FORMAT', 'text')

_formatters: dict = {
    'verbose': {
        'format': '{asctime} [{levelname}] {name}: {message}',
        'style': '{',
    },
}
if _LOG_FORMAT == 'json':
    _formatters['json'] = {
        '()': 'pythonjsonlogger.json.JsonFormatter',
        'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': _formatters,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if _LOG_FORMAT == 'json' else 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
