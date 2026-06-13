import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def config_admin(db):
    User = get_user_model()
    user = User.objects.create_user(username="config-contract-admin", password="test-pass")
    config_group, _created = Group.objects.get_or_create(name="Configuration Admin")
    user.groups.add(config_group)
    return user


@pytest.mark.django_db
def test_form_layout_contracts_expose_fields_and_sections(api_client, config_admin):
    api_client.force_authenticate(config_admin)
    response = api_client.get("/api/config/active/")

    assert response.status_code == 200
    payload = response.json()

    assert "data" in payload
    assert isinstance(payload["data"]["object_types"], list)
    assert isinstance(payload["data"]["form_layouts"], list)
    assert payload["data"]["object_types"], "Published config should define object types."
    object_type = payload["data"]["object_types"][0]
    assert isinstance(object_type["fields"], list)

