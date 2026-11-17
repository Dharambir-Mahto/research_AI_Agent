import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure local pkgs is on sys.path
pkgs_dir = BASE_DIR / "pkgs"
if pkgs_dir.is_dir() and str(pkgs_dir) not in sys.path:
    sys.path.insert(0, str(pkgs_dir))

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "django-insecure-research-agent-pro-ui-2026-key"
)

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "research_ui.apps.ResearchUiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "web_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "research_ui" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
            ],
        },
    },
]

WSGI_APPLICATION = "web_config.wsgi.application"
ASGI_APPLICATION = "web_config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "research_ui" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
