import copy

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.config_registry.models import ConfigurationVersion
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
def configuration_admin(db):
    User = get_user_model()
    user = User.objects.create_user(username="config-api-config-admin", password="test-pass")
    group, _created = Group.objects.get_or_create(name="Configuration Admin")
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


@pytest.mark.django_db
def test_configuration_admin_can_manage_non_destructive_config_drafts(
    api_client,
    configuration_admin,
):
    api_client.force_authenticate(configuration_admin)
    create_response = api_client.post("/api/config/drafts/", {}, format="json")

    assert create_response.status_code == 201
    draft_id = create_response.json()["id"]
    draft_data = create_response.json()["data"]
    draft_data["object_types"][0]["label"] = "Finished Product"

    update_response = api_client.patch(
        f"/api/config/drafts/{draft_id}/",
        {"data": draft_data},
        format="json",
    )
    validate_response = api_client.post(
        f"/api/config/drafts/{draft_id}/validate/",
        {},
        format="json",
    )
    publish_response = api_client.post(
        f"/api/config/drafts/{draft_id}/publish/",
        {},
        format="json",
    )

    assert update_response.status_code == 200
    assert validate_response.status_code == 200
    assert validate_response.json() == {"errors": [], "breaking_changes": []}
    assert publish_response.status_code == 201
    assert publish_response.json()["data"]["object_types"][0]["label"] == "Finished Product"


@pytest.mark.django_db
def test_validate_reports_breaking_schema_changes(api_client, system_admin):
    published_draft = create_draft_from_current(system_admin)
    publish_draft(published_draft, system_admin)
    draft = create_draft_from_current(system_admin)
    _remove_field(draft.data, "raw_material", "material_family")
    draft.save()

    api_client.force_authenticate(system_admin)
    response = api_client.post(f"/api/config/drafts/{draft.id}/validate/", {}, format="json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["errors"] == []
    assert {
        "path": "object_types.raw_material.fields.material_family",
        "code": "field_removed",
        "message": (
            "Field 'Material Family' (material_family) was removed from Raw Material. "
            "Existing values stay in record data but will no longer appear in normal forms."
        ),
    } in payload["breaking_changes"]


@pytest.mark.django_db
def test_configuration_admin_cannot_publish_destructive_schema_changes(
    api_client,
    system_admin,
    configuration_admin,
):
    published_draft = create_draft_from_current(system_admin)
    publish_draft(published_draft, system_admin)
    draft = create_draft_from_current(configuration_admin)
    _remove_field(draft.data, "raw_material", "material_family")
    draft.save()

    api_client.force_authenticate(configuration_admin)
    response = api_client.post(
        f"/api/config/drafts/{draft.id}/publish/",
        {"confirm_breaking_changes": True},
        format="json",
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"] == "Destructive configuration changes require System Admin approval."
    assert any(change["code"] == "field_removed" for change in payload["breaking_changes"])
    assert ConfigurationVersion.objects.count() == 1


@pytest.mark.django_db
def test_system_admin_must_confirm_destructive_schema_publish(api_client, system_admin):
    published_draft = create_draft_from_current(system_admin)
    publish_draft(published_draft, system_admin)
    draft = create_draft_from_current(system_admin)
    _remove_field(draft.data, "raw_material", "material_family")
    draft.save()

    api_client.force_authenticate(system_admin)
    response = api_client.post(f"/api/config/drafts/{draft.id}/publish/", {}, format="json")

    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"] == "Breaking configuration changes require confirmation."
    assert any(change["code"] == "field_removed" for change in payload["breaking_changes"])
    assert ConfigurationVersion.objects.count() == 1

    confirmed_response = api_client.post(
        f"/api/config/drafts/{draft.id}/publish/",
        {"confirm_breaking_changes": True},
        format="json",
    )

    assert confirmed_response.status_code == 201
    assert ConfigurationVersion.objects.count() == 2


def _remove_field(config_data, object_type_key, field_key):
    object_type = next(
        object_type
        for object_type in config_data["object_types"]
        if object_type["key"] == object_type_key
    )
    object_type["fields"] = [
        field for field in object_type["fields"] if field["key"] != field_key
    ]
