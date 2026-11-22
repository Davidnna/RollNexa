import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG_VALUE = os.environ.get("DEBUG")
if DEBUG_VALUE is None:
    DEBUG = not bool(os.environ.get("RENDER"))
else:
    DEBUG = DEBUG_VALUE.strip().lower() in {"1", "true", "yes", "on"}

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("The SECRET_KEY environment variable must be configured.")
    SECRET_KEY = "django-insecure-rollnexa-development-only-not-for-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
configured_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS.extend(host.strip() for host in configured_hosts.split(",") if host.strip())

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend(["http://localhost:5173", "http://127.0.0.1:5173"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "academics.apps.AcademicsConfig",
    "accounts.apps.AccountsConfig",
    "attendance.apps.AttendanceConfig",
    "biometrics.apps.BiometricsConfig",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.BiometricRequestSizeLimitMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.ForcePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RollNexaSecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ImproperlyConfigured("The DATABASE_URL environment variable must be configured.")

DATABASES = {
    "default": dj_database_url.parse(
        database_url,
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=not DEBUG,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/minute",
        "qr_issue": "5/minute",
        "qr_verify": "10/minute",
        "biometric_consent": "5/hour",
        "biometric_enrolment": "3/hour",
        "biometric_preview": "90/minute",
        "biometric_challenge": "5/minute",
        "biometric_verify": "5/minute",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
# Trust Render's forwarded scheme and enforce HTTPS for application routes.
# Liveness/readiness endpoints are exempt for platform health checks.
SECURE_SSL_REDIRECT = (
    os.environ.get("SECURE_SSL_REDIRECT", "false" if DEBUG else "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").strip().lower() in {"1", "true", "yes", "on"}
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "false").strip().lower() in {"1", "true", "yes", "on"}

# Keep error details out of public production responses.
ADMINS = []

# One-time first-administrator setup token; configure only in Render environment settings.
BOOTSTRAP_ADMIN_TOKEN = os.environ.get("BOOTSTRAP_ADMIN_TOKEN", "")


# Biometric processing is fail-closed when the encryption key or model assets are unavailable.
BIOMETRIC_ENCRYPTION_KEY = os.environ.get("BIOMETRIC_ENCRYPTION_KEY", "").strip()
BIOMETRIC_ENCRYPTION_KEY_VERSION = os.environ.get("BIOMETRIC_ENCRYPTION_KEY_VERSION", "v1")
BIOMETRIC_CONSENT_POLICY_VERSION = os.environ.get("BIOMETRIC_CONSENT_POLICY_VERSION", "1.1")
BIOMETRIC_FACE_MATCH_THRESHOLD = float(os.environ.get("BIOMETRIC_FACE_MATCH_THRESHOLD", "0.363"))
BIOMETRIC_FACE_DETECTION_THRESHOLD = float(os.environ.get("BIOMETRIC_FACE_DETECTION_THRESHOLD", "0.75"))
BIOMETRIC_MODEL_DIR = Path(
    os.environ.get(
        "BIOMETRIC_MODEL_DIR",
        str(BASE_DIR / "biometrics" / "model_assets"),
    )
)

# Biometric uploads are small and are processed in memory; do not spool camera frames to disk.
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 3
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
