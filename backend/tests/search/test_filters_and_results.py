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
    user = User.objects.create_user(username="filter-user", password="test-pass")
    viewer_group, _created = Group.objects.get_or_create(name="Viewer")
    user.groups.add(viewer_group)
    return user


@pytest.fixture
def permissions(db):
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="product", can_view=True)


@pytest.mark.django_db
def test_search_shows_only_non_empty_sections(api_client, user_with_perm, permissions):
    api_client.force_authenticate(user_with_perm)
    Record.objects.create(
        object_type_key="product",
        code="PROD-SRCH-0001",
        title="Active Search Product",
        schema_version=1,
        data={"commercial_name": "Active Search Product"},
        status="active",
    )
    response = api_client.get("/api/search/?object_type_key=product&status=active")
    payload = response.json()

    assert response.status_code == 200
    assert payload["count"] > 0
    assert "sections" in payload
    assert all(len(section["items"]) > 0 for section in payload["sections"])
