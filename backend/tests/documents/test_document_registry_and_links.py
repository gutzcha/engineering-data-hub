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
    user = User.objects.create_user(username="config-admin", password="test-pass")
    config_group, _created = Group.objects.get_or_create(name="Configuration Admin")
    user.groups.add(config_group)
    return user


@pytest.mark.django_db
def test_lookup_options_are_live_and_config_managed(api_client, config_admin):
    api_client.force_authenticate(config_admin)
    response = api_client.get("/api/config/active/field-options/?object_type_key=product&field_key=resin_family")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_type_key"] == "product"
    assert payload["field_key"] == "resin_family"
    assert isinstance(payload["options"], list)
