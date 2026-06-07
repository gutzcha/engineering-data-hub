import os
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env.example")
load_dotenv(REPO_ROOT / ".env", override=True)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def unique_list(items):
    return list(dict.fromkeys(items))


def database_from_url(url):
    parsed = urlparse(url)
    query_options = dict(parse_qsl(parsed.query))

    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "OPTIONS": query_options,
        }

    if parsed.scheme == "sqlite":
        path = parsed.path or ":memory:"
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": path,
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DEBUG", os.environ.get("APP_ENV", "dev") != "prod")
APP_HOST = os.environ.get("APP_HOST", "plastic-hub.local")
ALLOWED_HOSTS = unique_list(env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,backend") + [APP_HOST])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "apps.accounts",
    "apps.audit",
    "apps.config_registry",
    "apps.documents",
    "apps.folders",
    "apps.imports",
    "apps.projects",
    "apps.records",
    "apps.relationships",
    "apps.search",
    "apps.workflows",
    "apps.api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.AuditRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "plastic_hub.urls"
WSGI_APPLICATION = "plastic_hub.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": database_from_url(DATABASE_URL)}
else:
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

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

MEILI_URL = os.environ.get("MEILI_URL", "")
MEILI_MASTER_KEY = os.environ.get("MEILI_MASTER_KEY", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
MANAGED_FILE_ROOT = os.environ.get("MANAGED_FILE_ROOT", "/data/managed")
MANAGED_FOLDERS_AUTO_GENERATE = env_bool("MANAGED_FOLDERS_AUTO_GENERATE", True)
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/data/media")
BACKUP_ROOT = os.environ.get("BACKUP_ROOT", "/data/backups")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_DEFAULT_QUEUE = "plastic_hub"
