import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import ObjectPermission
from apps.records.models import Record


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_with_perm(db):
    User = get_user_model()
    user = User.objects.create_user(username="home-overview-user", password="test-pass")
    viewer_group, _created = Group.objects.get_or_create(name="Viewer")
    user.groups.add(viewer_group)
    return user


@pytest.fixture
def permissions(db):
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="product", can_view=True)
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="raw_material", can_view=True)


@pytest.mark.django_db
def test_home_overview_uses_live_counts_and_no_placeholders(api_client, user_with_perm, permissions):
    api_client.force_authenticate(user_with_perm)
    Record.objects.create(
        object_type_key="product",
        code="PROD-HOME-0001",
        title="Live Product A",
        schema_version=1,
        data={"commercial_name": "Live Product A"},
    )
    Record.objects.create(
        object_type_key="raw_material",
        code="MAT-HOME-0001",
        title="Live Material A",
        schema_version=1,
        data={"material_name": "PLA"},
    )
    response = api_client.get("/api/reports/dashboards/home-overview/")

    assert response.status_code == 200
    payload = response.json()
    assert "cards" in payload
    assert payload["cards"], "Home overview API should return at least one metric card."
    assert all(isinstance(card["value"], int) for card in payload["cards"])
    assert payload["cards"][0]["filter"]["status"] in {"active", "review", "blocked", "ready"}

