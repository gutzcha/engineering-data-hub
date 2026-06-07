import copy

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.config_registry.models import (
    ConfigurationSequence,
    ConfigurationVersion,
    ObjectTypeDefinition,
)
from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import (
    ConfigurationValidationError,
    create_draft_from_current,
    get_active_config,
    publish_draft,
    validate_draft,
)


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(username="config-admin", password="test-pass")


@pytest.fixture
def valid_data():
    return starter_configuration_data()


@pytest.mark.django_db
def test_invalid_field_type_blocks_publish(user, valid_data):
    draft = create_draft_from_current(user)
    draft.data = valid_data
    draft.data["object_types"][0]["fields"][0]["type"] = "currency"
    draft.save()

    errors = validate_draft(draft)

    assert errors == [
        {
            "path": "object_types[0].fields[0].type",
            "code": "invalid_field_type",
            "message": "Field type must be one of the v1 allowed field types.",
        }
    ]
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)


@pytest.mark.django_db
def test_duplicate_field_keys_block_publish(user, valid_data):
    draft = create_draft_from_current(user)
    product = valid_data["object_types"][0]
    product["fields"].append(copy.deepcopy(product["fields"][0]))
    duplicate_index = len(product["fields"]) - 1
    draft.data = valid_data
    draft.save()

    errors = validate_draft(draft)

    assert {
        "path": f"object_types[0].fields[{duplicate_index}].key",
        "code": "duplicate_field_key",
        "message": "Field keys must be unique within an object type.",
    } in errors
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)


@pytest.mark.django_db
def test_duplicate_object_type_keys_block_publish(user, valid_data):
    draft = create_draft_from_current(user)
    valid_data["object_types"].append(copy.deepcopy(valid_data["object_types"][0]))
    draft.data = valid_data
    draft.save()

    errors = validate_draft(draft)

    assert {
        "path": "object_types[8].key",
        "code": "duplicate_object_type_key",
        "message": "Object type keys must be unique.",
    } in errors
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)
    assert ConfigurationVersion.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_optional_keyed_section_keys_block_publish(user, valid_data):
    draft = create_draft_from_current(user)
    valid_data["form_layouts"] = [
        {"key": "product_default", "label": "Product Default"},
        {"key": "product_default", "label": "Product Default Copy"},
    ]
    valid_data["folder_templates"] = [
        {"key": "product_standard", "label": "Product Standard"},
        {"key": "product_standard", "label": "Product Standard Copy"},
    ]
    valid_data["dashboards"] = [
        {"key": "engineering_overview", "label": "Engineering Overview"},
        {"key": "engineering_overview", "label": "Engineering Overview Copy"},
    ]
    draft.data = valid_data
    draft.save()

    errors = validate_draft(draft)

    assert {
        "path": "form_layouts[1].key",
        "code": "duplicate_form_layout_key",
        "message": "Form layout keys must be unique.",
    } in errors
    assert {
        "path": "folder_templates[1].key",
        "code": "duplicate_folder_template_key",
        "message": "Folder template keys must be unique.",
    } in errors
    assert {
        "path": "dashboards[1].key",
        "code": "duplicate_dashboard_key",
        "message": "Dashboard keys must be unique.",
    } in errors
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)
    assert ConfigurationVersion.objects.count() == 0


@pytest.mark.django_db
def test_publish_creates_new_immutable_integer_version(user, valid_data):
    first_draft = create_draft_from_current(user)
    first_draft.data = valid_data
    first_draft.save()

    first_version = publish_draft(first_draft, user)

    assert first_version.version == 1
    assert first_version.data == valid_data
    assert first_version.published_by == user
    assert first_version.published_at is not None

    first_version.data["object_types"][0]["label"] = "Changed Product"
    with pytest.raises(ValidationError):
        first_version.save()

    second_draft = create_draft_from_current(user)
    second_draft.data["object_types"][0]["label"] = "Updated Product"
    second_draft.save()

    second_version = publish_draft(second_draft, user)

    assert second_version.version == 2
    assert ConfigurationVersion.objects.get(version=1).data == valid_data
    assert ConfigurationSequence.objects.get(pk=1).next_version == 3


@pytest.mark.django_db
def test_published_draft_cannot_be_published_again(user, valid_data):
    draft = create_draft_from_current(user)
    draft.data = valid_data
    draft.save()

    first_version = publish_draft(draft, user)

    with pytest.raises(ConfigurationValidationError) as error:
        publish_draft(draft, user)

    assert error.value.errors == [
        {
            "path": "status",
            "code": "draft_not_publishable",
            "message": "Only draft configurations can be published.",
        }
    ]
    assert ConfigurationVersion.objects.count() == 1
    assert ConfigurationVersion.objects.get() == first_version


@pytest.mark.django_db
def test_active_config_returns_latest_published_version(user, valid_data):
    first_draft = create_draft_from_current(user)
    first_draft.data = valid_data
    first_draft.save()
    publish_draft(first_draft, user)

    second_draft = create_draft_from_current(user)
    second_draft.data["object_types"][0]["label"] = "Newest Product"
    second_draft.save()
    latest = publish_draft(second_draft, user)

    assert get_active_config() == latest


@pytest.mark.django_db
def test_malformed_root_data_blocks_publish_without_creating_version(user):
    draft = create_draft_from_current(user)
    draft.data = ["not", "a", "configuration"]
    draft.save()

    errors = validate_draft(draft)

    assert errors == [
        {
            "path": "",
            "code": "invalid_configuration",
            "message": "Configuration data must be an object.",
        }
    ]
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)
    assert ConfigurationVersion.objects.count() == 0


@pytest.mark.django_db
def test_malformed_optional_definition_sections_block_publish(user, valid_data):
    draft = create_draft_from_current(user)
    draft.data = valid_data
    draft.data["form_layouts"] = [{"label": "Missing Key"}]
    draft.data["folder_templates"] = "bad templates"
    draft.data["dashboards"] = ["bad dashboard"]
    draft.save()

    errors = validate_draft(draft)

    assert {
        "path": "form_layouts[0].key",
        "code": "invalid_form_layout_key",
        "message": "Form layout keys must use lowercase snake case.",
    } in errors
    assert {
        "path": "folder_templates",
        "code": "invalid_folder_templates",
        "message": "Folder templates must be a list.",
    } in errors
    assert {
        "path": "dashboards[0]",
        "code": "invalid_dashboard",
        "message": "Dashboard definitions must be objects.",
    } in errors
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)


@pytest.mark.django_db
def test_relationship_type_keys_and_object_type_references_are_validated(user, valid_data):
    draft = create_draft_from_current(user)
    draft.data = valid_data
    draft.data["relationship_types"] = [
        {
            "key": "Product Uses Material",
            "label": "Product uses material",
            "source_object_type": "product",
            "target_object_type": "raw_material",
        },
        {
            "key": "product_uses_material",
            "label": "Product uses material copy",
            "source_object_type": "product",
            "target_object_type": "missing_type",
        },
        {
            "key": "product_uses_material",
            "label": "Product uses material duplicate",
            "source_object_type": "missing_type",
            "target_object_type": "raw_material",
        },
    ]
    draft.save()

    errors = validate_draft(draft)

    assert {
        "path": "relationship_types[0].key",
        "code": "invalid_relationship_type_key",
        "message": "Relationship type keys must use lowercase snake case.",
    } in errors
    assert {
        "path": "relationship_types[1].target_object_type",
        "code": "unknown_relationship_target_object_type",
        "message": "Relationship target object type must reference an object type.",
    } in errors
    assert {
        "path": "relationship_types[2].key",
        "code": "duplicate_relationship_type_key",
        "message": "Relationship type keys must be unique.",
    } in errors
    assert {
        "path": "relationship_types[2].source_object_type",
        "code": "unknown_relationship_source_object_type",
        "message": "Relationship source object type must reference an object type.",
    } in errors
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)


@pytest.mark.django_db
def test_malformed_object_entry_blocks_publish(user):
    draft = create_draft_from_current(user)
    draft.data = {"object_types": ["bad object"], "form_layouts": [], "folder_templates": [], "dashboards": []}
    draft.save()

    assert validate_draft(draft) == [
        {
            "path": "object_types[0]",
            "code": "invalid_object_type",
            "message": "Object type definitions must be objects.",
        }
    ]
    with pytest.raises(ConfigurationValidationError):
        publish_draft(draft, user)


@pytest.mark.django_db
def test_derived_definition_rows_are_immutable_after_publish(user, valid_data):
    draft = create_draft_from_current(user)
    draft.data = valid_data
    draft.save()
    version = publish_draft(draft, user)
    object_type = ObjectTypeDefinition.objects.get(configuration_version=version, key="product")

    object_type.label = "Mutated Product"
    with pytest.raises(ValidationError):
        object_type.save()

    with pytest.raises(ValidationError):
        object_type.delete()


def test_starter_configuration_contains_required_object_types(valid_data):
    object_type_keys = {object_type["key"] for object_type in valid_data["object_types"]}
    relationship_type_keys = {
        relationship_type["key"] for relationship_type in valid_data["relationship_types"]
    }

    assert object_type_keys == {
        "product",
        "raw_material",
        "product_spec",
        "supplier",
        "customer",
        "project",
        "test_method",
        "document",
    }
    assert relationship_type_keys == {
        "product_uses_material",
        "product_has_spec",
        "project_affects_product",
        "supplier_provides_material",
        "customer_uses_product",
        "document_attached_to_record",
    }
    assert all(object_type["fields"] for object_type in valid_data["object_types"])
