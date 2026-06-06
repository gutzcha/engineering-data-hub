import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission
from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.folders.signals import _generate_folder
from apps.folders.services import ManagedFolderCollisionError, generate_managed_folder
from apps.folders.templates import render_folder_template
from apps.records.models import Record


@pytest.fixture
def user_factory(db):
    User = get_user_model()

    def create_user(username, role_name=None, *, is_superuser=False):
        user = User.objects.create_user(
            username=username,
            password="test-pass",
            is_superuser=is_superuser,
        )
        if role_name:
            group, _created = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
        return user

    return create_user


@pytest.fixture
def product_record(db):
    return Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )


@pytest.fixture
def raw_material_record(db):
    return Record.objects.create(
        object_type_key="raw_material",
        code="MAT-2026-0001",
        title="Resin A",
        schema_version=1,
        data={},
    )


@pytest.mark.django_db
def test_product_template_renders_expected_root_and_children(product_record):
    rendered = render_folder_template(product_record, "product_standard")

    assert rendered.root == "Products/PROD-000001_Clear_Film"
    assert rendered.children == [
        "Products/PROD-000001_Clear_Film/01_Specifications",
        "Products/PROD-000001_Clear_Film/02_Drawings",
        "Products/PROD-000001_Clear_Film/03_Materials",
        "Products/PROD-000001_Clear_Film/04_Testing",
        "Products/PROD-000001_Clear_Film/05_Project_Files",
        "Products/PROD-000001_Clear_Film/99_Working",
    ]


@pytest.mark.django_db
def test_raw_material_template_renders_expected_root_and_children(raw_material_record):
    rendered = render_folder_template(raw_material_record, "raw_material_standard")

    assert rendered.root == "Raw_Materials/MAT-2026-0001_Resin_A"
    assert rendered.children == [
        "Raw_Materials/MAT-2026-0001_Resin_A/01_Supplier_Documents",
        "Raw_Materials/MAT-2026-0001_Resin_A/02_Technical_Data",
        "Raw_Materials/MAT-2026-0001_Resin_A/03_Compliance",
        "Raw_Materials/MAT-2026-0001_Resin_A/99_Working",
    ]


@pytest.mark.django_db
def test_unsafe_title_path_characters_are_slugged(db):
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-000002",
        title='Film/With\\Unsafe:*?"<>| Characters',
        schema_version=1,
        data={},
    )

    rendered = render_folder_template(record)

    assert rendered.root == "Products/PROD-000002_Film_With_Unsafe_Characters"
    assert all("\\" not in path for path in rendered.paths)
    assert all("//" not in path for path in rendered.paths)


@pytest.mark.django_db
def test_collision_appends_record_id_short_and_creates_event(product_record, settings, tmp_path):
    settings.MANAGED_FILE_ROOT = tmp_path
    existing_root = tmp_path / "Products" / "PROD-000001_Clear_Film"
    existing_root.mkdir(parents=True)

    managed_folder = generate_managed_folder(product_record)

    expected_root = f"Products/PROD-000001_Clear_Film-{product_record.id.hex[:8]}"
    assert managed_folder.relative_path == expected_root
    assert (tmp_path / "Products" / f"PROD-000001_Clear_Film-{product_record.id.hex[:8]}").is_dir()
    assert ManagedFolder.objects.get(record=product_record).relative_path == expected_root
    event = FolderChangeEvent.objects.get(event_type="collision")
    assert event.path == "Products/PROD-000001_Clear_Film"
    assert event.matched_record == product_record
    assert event.managed_folder == managed_folder
    assert event.review_status == "pending"


@pytest.mark.django_db
def test_generation_failure_creates_pending_event(product_record, settings, tmp_path):
    managed_root_file = tmp_path / "managed-root"
    managed_root_file.write_text("not a directory", encoding="utf-8")
    settings.MANAGED_FILE_ROOT = managed_root_file

    _generate_folder(product_record.pk)

    event = FolderChangeEvent.objects.get(event_type="generation_failed")
    assert event.path == "Products/PROD-000001_Clear_Film"
    assert event.matched_record == product_record
    assert event.review_status == "pending"


@pytest.mark.django_db
def test_manual_generation_returns_conflict_when_base_and_suffixed_paths_exist(
    client,
    user_factory,
    product_record,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    (tmp_path / "Products" / "PROD-000001_Clear_Film").mkdir(parents=True)
    (tmp_path / "Products" / f"PROD-000001_Clear_Film-{product_record.id.hex[:8]}").mkdir(
        parents=True
    )
    ObjectPermission.objects.create(
        role_name="Product Admin",
        object_type_key="product",
        can_view=True,
        can_admin=True,
    )
    client.force_login(user_factory("folder-generation-admin", "Product Admin"))

    response = client.post(f"/api/records/{product_record.pk}/folders/generate/")

    assert response.status_code == 409
    assert FolderChangeEvent.objects.filter(
        event_type="collision",
        path="Products/PROD-000001_Clear_Film",
        matched_record=product_record,
    ).exists()


@pytest.mark.django_db
def test_manual_generation_returns_bad_request_for_unsupported_object_type(
    client,
    user_factory,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    supplier = Record.objects.create(
        object_type_key="supplier",
        code="SUP-000001",
        title="Supplier A",
        schema_version=1,
        data={},
    )
    ObjectPermission.objects.create(
        role_name="Supplier Admin",
        object_type_key="supplier",
        can_view=True,
        can_admin=True,
    )
    client.force_login(user_factory("supplier-folder-admin", "Supplier Admin"))

    response = client.post(f"/api/records/{supplier.pk}/folders/generate/")

    assert response.status_code == 400
    assert response.json()["detail"] == "No managed folder template for supplier."


@pytest.mark.django_db
def test_folder_generation_converts_mkdir_race_to_collision_event(
    product_record,
    settings,
    tmp_path,
    monkeypatch,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    original_mkdir = type(tmp_path).mkdir
    expected_root = tmp_path / "Products" / "PROD-000001_Clear_Film"

    def race_mkdir(path, *args, **kwargs):
        if path == expected_root:
            raise FileExistsError("created concurrently")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "mkdir", race_mkdir)

    with pytest.raises(ManagedFolderCollisionError):
        generate_managed_folder(product_record)

    assert FolderChangeEvent.objects.filter(
        event_type="collision",
        path="Products/PROD-000001_Clear_Film",
        matched_record=product_record,
    ).exists()
