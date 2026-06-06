import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission
from apps.records.models import Record


@pytest.fixture
def user_factory(db):
    User = get_user_model()

    def create_user(username, role_name=None):
        user = User.objects.create_user(username=username, password="test-pass")
        if role_name:
            group, _created = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
        return user

    return create_user


@pytest.fixture
def folder_link_permissions(db):
    ObjectPermission.objects.create(
        role_name="Folder Admin",
        object_type_key="product",
        can_view=True,
        can_edit=True,
        can_admin=True,
    )
    ObjectPermission.objects.create(
        role_name="Folder Editor",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )


@pytest.fixture
def product_records(db):
    first = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )
    second = Record.objects.create(
        object_type_key="product",
        code="PROD-000002",
        title="Resin Film",
        schema_version=1,
        data={},
    )
    return first, second


@pytest.mark.django_db
def test_folder_scan_suggests_links_unmatched_folders_and_conflicts(
    tmp_path,
    settings,
    product_records,
):
    from apps.imports.services import scan_legacy_folders

    settings.MANAGED_FILE_ROOT = tmp_path
    first, second = product_records
    legacy_root = tmp_path / "Legacy"
    (legacy_root / "PROD-000001_Clear_Film").mkdir(parents=True)
    (legacy_root / "Archive" / "PROD-000002_Resin_Film").mkdir(parents=True)
    (legacy_root / "NO_MATCH").mkdir(parents=True)
    (legacy_root / "Mixed_PROD-000001_PROD-000002").mkdir(parents=True)

    result = scan_legacy_folders(
        legacy_root_path=legacy_root,
        object_type_key="product",
        matching_rule={"type": "code_in_path"},
    )

    assert {
        (link["record_id"], link["relative_path"], link["managed_relative_path"])
        for link in result["suggested_record_links"]
    } == {
        (str(first.pk), "PROD-000001_Clear_Film", "Legacy/PROD-000001_Clear_Film"),
        (
            str(second.pk),
            "Archive/PROD-000002_Resin_Film",
            "Legacy/Archive/PROD-000002_Resin_Film",
        ),
    }
    assert result["unmatched_folders"] == [
        {"relative_path": "NO_MATCH", "managed_relative_path": "Legacy/NO_MATCH"}
    ]
    assert result["conflicts"] == [
        {
            "relative_path": "Mixed_PROD-000001_PROD-000002",
            "managed_relative_path": "Legacy/Mixed_PROD-000001_PROD-000002",
            "matched_codes": ["PROD-000001", "PROD-000002"],
        }
    ]
    assert result["accepted_links"] == []
    assert "path" not in result["suggested_record_links"][0]
    assert "path" not in result["unmatched_folders"][0]
    assert "path" not in result["conflicts"][0]


@pytest.mark.django_db
def test_folder_scan_rejects_roots_outside_managed_root(tmp_path, settings, product_records):
    from apps.imports.services import scan_legacy_folders

    settings.MANAGED_FILE_ROOT = tmp_path / "managed"
    settings.MANAGED_FILE_ROOT.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    with pytest.raises(ValueError, match="inside MANAGED_FILE_ROOT"):
        scan_legacy_folders(
            legacy_root_path=outside_root,
            object_type_key="product",
            matching_rule={"type": "code_in_path"},
        )


@pytest.mark.django_db
def test_folder_scan_view_requires_admin_permission(
    client,
    tmp_path,
    settings,
    user_factory,
    folder_link_permissions,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    legacy_root = tmp_path / "Legacy"
    legacy_root.mkdir()
    client.force_login(user_factory("folder-editor", "Folder Editor"))

    response = client.post(
        "/api/imports/folder-scan/",
        {
            "legacy_root_path": str(legacy_root),
            "object_type_key": "product",
            "matching_rule": {"type": "code_in_path"},
        },
        content_type="application/json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_accept_folder_links_creates_managed_folder_without_moving_files(
    tmp_path,
    settings,
    product_records,
    user_factory,
    folder_link_permissions,
):
    from apps.folders.models import FolderChangeEvent, ManagedFolder
    from apps.imports.services import accept_folder_links

    settings.MANAGED_FILE_ROOT = tmp_path
    first, _second = product_records
    actor = user_factory("folder-link-admin", "Folder Admin")
    legacy_root = tmp_path / "Legacy"
    linked_folder = legacy_root / "PROD-000001_Clear_Film"
    linked_folder.mkdir(parents=True)

    result = accept_folder_links(
        legacy_root_path=legacy_root,
        object_type_key="product",
        links=[{"record_id": str(first.pk), "relative_path": "PROD-000001_Clear_Film"}],
        actor=actor,
    )

    managed_folder = ManagedFolder.objects.get(record=first, folder_role="legacy")
    assert result["accepted_links"] == [
        {
            "record_id": str(first.pk),
            "code": "PROD-000001",
            "relative_path": "Legacy/PROD-000001_Clear_Film",
        }
    ]
    assert managed_folder.absolute_path == str(linked_folder.resolve())
    assert managed_folder.relative_path == "Legacy/PROD-000001_Clear_Film"
    assert linked_folder.is_dir()
    assert FolderChangeEvent.objects.filter(
        event_type=FolderChangeEvent.EventType.LINK_REQUESTED,
        matched_record=first,
        managed_folder=managed_folder,
        review_status=FolderChangeEvent.ReviewStatus.LINKED,
        reviewer=actor,
    ).exists()


@pytest.mark.django_db
def test_accept_folder_links_rejects_path_traversal(
    tmp_path,
    settings,
    product_records,
    user_factory,
    folder_link_permissions,
):
    from apps.imports.services import accept_folder_links

    settings.MANAGED_FILE_ROOT = tmp_path
    first, _second = product_records
    actor = user_factory("folder-link-traversal-admin", "Folder Admin")
    legacy_root = tmp_path / "Legacy"
    legacy_root.mkdir()

    with pytest.raises(ValueError, match="relative"):
        accept_folder_links(
            legacy_root_path=legacy_root,
            object_type_key="product",
            links=[{"record_id": str(first.pk), "relative_path": "../escape"}],
            actor=actor,
        )
