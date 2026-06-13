# ===
# File Summary
# Path: backend\apps\api\views.py
# Type: python
# Purpose: API facade and health/bootstrapping endpoints.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: search_status, health
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

from django.conf import settings
from django.db import DatabaseError, Error, InterfaceError, OperationalError, connection
from rest_framework.decorators import api_view
from rest_framework.response import Response


def search_status():
    return "configured" if settings.MEILI_URL else "unconfigured"


@api_view(["GET"])
def health(_request):
    response = {
        "status": "ok",
        "database": "ok",
        "search": search_status(),
        "managed_file_root": settings.MANAGED_FILE_ROOT,
    }

    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except (DatabaseError, Error, InterfaceError, OperationalError):
        response["status"] = "degraded"
        response["database"] = "unavailable"
        return Response(response, status=503)

    return Response(response)

