import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import Client
from importlib import import_module

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.accounts.permissions import user_can
from apps.records.models import Record


@pytest.fixture
def user_factory(db):
    User = get_user_model()

    def create_user(username, role_name=None, *, is_active=True, is_superuser=False):
        user = User.objects.create_user(
            username=username,
            password="test-pass",
            is_active=is_active,
            is_superuser=is_superuser,
        )
        if role_name:
            group, _created = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
        return user

    return create_user


@pytest.fixture
def product_permissions(db):
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="product")
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_create=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_release=True,
    )


@pytest.mark.django_db
def test_viewer_can_view_products_but_cannot_edit_them(user_factory, product_permissions):
    viewer = user_factory("viewer", "Viewer")

    assert user_can(viewer, "view", "product") is True
    assert user_can(viewer, "edit", "product") is False


@pytest.mark.django_db
def test_engineer_can_create_and_edit_draft_products(user_factory, product_permissions):
    engineer = user_factory("engineer", "Engineer")

    assert user_can(engineer, "create", "product") is True
    assert user_can(engineer, "edit", "product", record_id="draft-product-1") is True


@pytest.mark.django_db
def test_record_permission_allows_one_record_without_object_permission(user_factory):
    engineer = user_factory("record-scoped-engineer", "Scoped Engineer")
    allowed = Record.objects.create(
        object_type_key="product",
        code="PROD-000101",
        title="Allowed Product",
        schema_version=1,
        data={},
    )
    denied = Record.objects.create(
        object_type_key="product",
        code="PROD-000102",
        title="Denied Product",
        schema_version=1,
        data={},
    )
    RecordPermission.objects.create(
        role_name="Scoped Engineer",
        object_type_key="product",
        record=allowed,
        can_view=True,
        can_edit=True,
    )

    assert user_can(engineer, "view", "product") is False
    assert user_can(engineer, "view", "product", record_id=str(allowed.pk)) is True
    assert user_can(engineer, "edit", "product", record_id=str(allowed.pk)) is True
    assert user_can(engineer, "view", "product", record_id=str(denied.pk)) is False


@pytest.mark.django_db
def test_record_permission_overrides_object_permission_for_that_record(user_factory):
    viewer = user_factory("record-denied-viewer", "Viewer")
    blocked = Record.objects.create(
        object_type_key="product",
        code="PROD-000201",
        title="Blocked Product",
        schema_version=1,
        data={},
    )
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="product")
    RecordPermission.objects.create(
        role_name="Viewer",
        object_type_key="product",
        record=blocked,
        can_view=False,
    )

    assert user_can(viewer, "view", "product") is True
    assert user_can(viewer, "view", "product", record_id=str(blocked.pk)) is False


@pytest.mark.django_db
def test_record_permission_object_type_is_synced_from_record():
    record = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-000201",
        title="Permission Material",
        schema_version=1,
        data={},
    )
    permission = RecordPermission.objects.create(
        role_name="Material Viewer",
        object_type_key="product",
        record=record,
        can_view=True,
    )

    assert permission.object_type_key == "raw_material"


@pytest.mark.django_db
def test_only_approvers_and_admins_can_release_products(user_factory, product_permissions):
    engineer = user_factory("release-engineer", "Engineer")
    approver = user_factory("approver", "Approver")
    system_admin = user_factory("system-admin", "System Admin")

    assert user_can(engineer, "release", "product") is False
    assert user_can(approver, "release", "product") is True
    assert user_can(system_admin, "release", "product") is True


@pytest.mark.django_db
def test_system_admin_always_passes_valid_permission_checks(user_factory):
    system_admin = user_factory("valid-action-admin", "System Admin")
    superuser = user_factory("superuser", is_superuser=True)

    assert user_can(system_admin, "view", "product") is True
    assert user_can(system_admin, "release", "product") is True
    assert user_can(superuser, "view", "product") is True
    assert user_can(superuser, "release", "product") is True


@pytest.mark.django_db
def test_unknown_actions_and_inactive_or_anonymous_users_are_denied(user_factory, product_permissions):
    viewer = user_factory("unknown-action-viewer", "Viewer")
    system_admin = user_factory("unknown-action-admin", "System Admin")
    superuser = user_factory("unknown-action-superuser", is_superuser=True)
    inactive_viewer = user_factory("inactive-viewer", "Viewer", is_active=False)

    assert user_can(viewer, "archive", "product") is False
    assert user_can(system_admin, "archive", "product") is False
    assert user_can(superuser, "archive", "product") is False
    assert user_can(inactive_viewer, "view", "product") is False
    assert user_can(AnonymousUser(), "view", "product") is False


@pytest.mark.django_db
def test_role_group_seed_reverse_migration_does_not_delete_groups_or_memberships(user_factory):
    migration = import_module("apps.accounts.migrations.0002_seed_role_groups")
    user = user_factory("rollback-admin", "System Admin")

    migration.remove_role_groups(import_module("django.apps").apps, None)

    user.refresh_from_db()
    assert Group.objects.filter(name="System Admin").exists() is True
    assert user.groups.filter(name="System Admin").exists() is True


@pytest.mark.django_db
def test_current_user_endpoint_requires_authentication_and_returns_roles(client, user_factory):
    response = client.get("/api/accounts/me/")
    assert response.status_code in {401, 403}

    viewer = user_factory("api-viewer", "Viewer")
    client.force_login(viewer)

    response = client.get("/api/accounts/me/")

    assert response.status_code == 200
    assert response.json()["username"] == "api-viewer"
    assert response.json()["roles"] == ["Viewer"]


@pytest.mark.django_db
def test_csrf_login_current_user_and_logout_session_flow(user_factory):
    user_factory("session-engineer", "Engineer")
    strict_client = Client(enforce_csrf_checks=True)

    csrf_response = strict_client.get("/api/accounts/csrf/")
    assert csrf_response.status_code == 200
    csrf_token = csrf_response.json()["csrfToken"]
    assert "csrftoken" in strict_client.cookies

    response = strict_client.post(
        "/api/accounts/login/",
        data=json.dumps({"username": "session-engineer", "password": "test-pass"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["username"] == "session-engineer"
    assert response.json()["roles"] == ["Engineer"]
    assert strict_client.get("/api/accounts/me/").status_code == 200

    csrf_token = strict_client.get("/api/accounts/csrf/").json()["csrfToken"]
    response = strict_client.post("/api/accounts/logout/", HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 204
    assert strict_client.get("/api/accounts/me/").status_code in {401, 403}


@pytest.mark.django_db
def test_login_rejects_bad_credentials(user_factory):
    user_factory("bad-login-engineer", "Engineer")
    client = Client(enforce_csrf_checks=True)
    csrf_token = client.get("/api/accounts/csrf/").json()["csrfToken"]

    response = client.post(
        "/api/accounts/login/",
        data=json.dumps({"username": "bad-login-engineer", "password": "wrong"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_only_admins_can_manage_object_permissions(client, user_factory):
    normal_user = user_factory("api-normal", "Viewer")
    client.force_login(normal_user)

    response = client.post(
        "/api/accounts/object-permissions/",
        {
            "role_name": "Viewer",
            "object_type_key": "document",
            "can_view": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 403

    client.force_login(user_factory("api-system-admin", "System Admin"))
    response = client.post(
        "/api/accounts/object-permissions/",
        {
            "role_name": "Viewer",
            "object_type_key": "document",
            "can_view": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_superusers_can_manage_object_permissions(client, user_factory):
    client.force_login(user_factory("api-superuser", is_superuser=True))

    response = client.get("/api/accounts/object-permissions/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_only_admins_can_manage_record_permissions(client, user_factory):
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-000301",
        title="Record Permission Managed",
        schema_version=1,
        data={},
    )
    client.force_login(user_factory("api-record-normal", "Viewer"))

    response = client.post(
        "/api/accounts/record-permissions/",
        {
            "role_name": "Viewer",
            "object_type_key": "product",
            "record": str(record.pk),
            "can_view": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 403

    client.force_login(user_factory("api-record-admin", "System Admin"))
    response = client.post(
        "/api/accounts/record-permissions/",
        {
            "role_name": "Viewer",
            "object_type_key": "product",
            "record": str(record.pk),
            "can_view": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
