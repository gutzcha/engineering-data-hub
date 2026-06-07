import copy

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import create_draft_from_current, publish_draft


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def system_admin(db):
    User = get_user_model()
    user = User.objects.create_user(username="config-api-admin", password="test-pass")
    group, _created = Group.objects.get_or_create(name=SYSTEM_ADMIN_ROLE)
    user.groups.add(group)
    return user


@pytest.fixture
def plain_user(db):
    User = get_user_model()
    return User.objects.create_user(username="config-api-user", password="test-pass")


@pytest.mark.django_db
def test_admin_can_update_draft_data(api_client, system_admin):
    draft = create_draft_from_current(system_admin)
    updated_data = copy.deepcopy(draft.data)
    updated_data["object_types"][0]["key"] = "finished_product"

    api_client.force_authenticate(system_admin)
    response = api_client.patch(
        f"/api/config/drafts/{draft.id}/",
        {"data": updated_data},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["data"]["object_types"][0]["key"] == "finished_product"
    draft.refresh_from_db()
    assert draft.data == updated_data
    assert draft.updated_by == system_admin


@pytest.mark.django_db
def test_published_draft_cannot_be_updated(api_client, system_admin):
    draft = create_draft_from_current(system_admin)
    published_version = publish_draft(draft, system_admin)
    updated_data = copy.deepcopy(published_version.data)
    updated_data["object_types"][0]["key"] = "finished_product"

    api_client.force_authenticate(system_admin)
    response = api_client.patch(
        f"/api/config/drafts/{draft.id}/",
        {"data": updated_data},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only draft configurations can be updated."
    draft.refresh_from_db()
    assert draft.data == published_version.data


@pytest.mark.django_db
def test_config_history_returns_versions_newest_first(api_client, system_admin):
    first_data = starter_configuration_data()
    first_draft = create_draft_from_current(system_admin)
    first_draft.data = first_data
    first_draft.save()
    first_version = publish_draft(first_draft, system_admin)

    second_draft = create_draft_from_current(system_admin)
    second_draft.data["object_types"][0]["label"] = "Finished Product"
    second_draft.save()
    second_version = publish_draft(second_draft, system_admin)

    api_client.force_authenticate(system_admin)
    response = api_client.get("/api/config/history/")

    assert response.status_code == 200
    assert [item["version"] for item in response.json()] == [
        second_version.version,
        first_version.version,
    ]


@pytest.mark.django_db
def test_config_history_requires_system_admin(api_client, system_admin, plain_user):
    draft = create_draft_from_current(system_admin)
    publish_draft(draft, system_admin)

    api_client.force_authenticate(plain_user)
    response = api_client.get("/api/config/history/")

    assert response.status_code == 403
