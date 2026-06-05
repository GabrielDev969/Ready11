"""
Django settings for Ready11 project.

Base project for B2B SaaS systems (multi-tenant via django-tenants).

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""
import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

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
    'django_tenants',  # MUST be first
    'widget_tweaks',
    'axes',            # brute-force protection (global access-attempt log)
    'core',            # landing page + healthcheck (public)
    'tenants',
    'users',

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
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',            # i18n: detects language
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'Ready11.wsgi.application'


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
    os.path.join(BASE_DIR, 'static'),
]

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==========================================
# Production security hardening
# ==========================================
if not DEBUG:
    # We sit behind a reverse proxy (Easypanel/Nginx) that terminates TLS.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', str(60 * 60 * 24 * 365)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ==========================================
# Logging
# ==========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
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
    },
}
