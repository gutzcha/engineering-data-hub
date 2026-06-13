# ===
# File Summary
# Path: backend\tests\test_health.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: test_health_endpoint_returns_ok, test_health_endpoint_reports_unconfigured_search, test_health_endpoint_returns_503_when_database_unavailable, raise_database_error
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

import pytest
from django.db import OperationalError


@pytest.mark.django_db
def test_health_endpoint_returns_ok(client, settings):
    settings.MEILI_URL = "http://meilisearch:7700"
    settings.MANAGED_FILE_ROOT = "/data/managed"
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["search"] == "configured"
    assert response.json()["managed_file_root"] == "/data/managed"


@pytest.mark.django_db
def test_health_endpoint_reports_unconfigured_search(client, settings):
    settings.MEILI_URL = ""
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["search"] == "unconfigured"


@pytest.mark.django_db
def test_health_endpoint_returns_503_when_database_unavailable(client, monkeypatch, settings):
    settings.MEILI_URL = ""
    settings.MANAGED_FILE_ROOT = "/data/managed"

    def raise_database_error():
        raise OperationalError("database unavailable")

    monkeypatch.setattr("apps.api.views.connection.ensure_connection", raise_database_error)

    response = client.get("/api/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "unavailable",
        "search": "unconfigured",
        "managed_file_root": "/data/managed",
    }

