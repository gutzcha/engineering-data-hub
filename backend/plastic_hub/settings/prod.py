# ===
# File Summary
# Path: backend\plastic_hub\settings\prod.py
# Type: python
# Purpose: Django project runtime configuration, routing, and process bootstrap.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: inferred from domain responsibilities
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from .base import *  # noqa: F403

DEBUG = False

from django.core.exceptions import ImproperlyConfigured

PLACEHOLDER_SECRET_KEYS = {
    "",
    "dev-insecure-change-me",
    "change-me-before-production",
    "change-me",
    "changeme",
    "please-change-me",
}

if SECRET_KEY in PLACEHOLDER_SECRET_KEYS:  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY must be set to a unique production value.")

meili_master_key = os.environ.get("MEILI_MASTER_KEY", "")  # noqa: F405
if meili_master_key.strip().lower() in PLACEHOLDER_SECRET_KEYS:
    raise ImproperlyConfigured("MEILI_MASTER_KEY must be set to a unique production value.")

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)  # noqa: F405
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"

