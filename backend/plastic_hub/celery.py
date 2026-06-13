# ===
# File Summary
# Path: backend\plastic_hub\celery.py
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

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plastic_hub.settings.dev")

app = Celery("plastic_hub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

