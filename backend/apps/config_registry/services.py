import copy
import re

from django.db import transaction

from apps.audit.services import record_audit_event
from apps.config_registry.models import (
    ConfigurationDraft,
    ConfigurationSequence,
    ConfigurationVersion,
    DashboardDefinition,
    FieldDefinition,
    FolderTemplateDefinition,
    FormLayoutDefinition,
    ObjectTypeDefinition,
)
from apps.config_registry.seed import starter_configuration_data


ALLOWED_FIELD_TYPES = {
    "text",
    "long_text",
    "number",
    "date",
    "boolean",
    "choice",
    "multi_choice",
    "record_ref",
    "file_ref",
    "url",
    "user_ref",
}
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class ConfigurationValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Configuration draft is invalid.")


def create_draft_from_current(user) -> ConfigurationDraft:
    active_config = ConfigurationVersion.objects.order_by("-version").first()
    data = copy.deepcopy(active_config.data if active_config else starter_configuration_data())
    return ConfigurationDraft.objects.create(data=data, created_by=user, updated_by=user)


def validate_draft(draft: ConfigurationDraft) -> list[dict]:
    errors = []
    data = draft.data
    if not isinstance(data, dict):
        return [
            {
                "path": "",
                "code": "invalid_configuration",
                "message": "Configuration data must be an object.",
            }
        ]

    object_types = data.get("object_types")

    if not isinstance(object_types, list):
        errors.append(
            {
                "path": "object_types",
                "code": "invalid_object_types",
                "message": "Object types must be a list.",
            }
        )
    else:
        _validate_object_types(object_types, errors)

    object_type_keys = _valid_object_type_keys(object_types)
    _validate_relationship_types(data, object_type_keys, errors)

    _validate_keyed_definition_section(
        data,
        "form_layouts",
        "form layout",
        "form_layout",
        errors,
    )
    _validate_keyed_definition_section(
        data,
        "folder_templates",
        "folder template",
        "folder_template",
        errors,
    )
    _validate_keyed_definition_section(data, "dashboards", "dashboard", "dashboard", errors)

    return errors


def _valid_object_type_keys(object_types):
    if not isinstance(object_types, list):
        return set()
    return {
        object_type.get("key")
        for object_type in object_types
        if isinstance(object_type, dict) and _is_snake_case_key(object_type.get("key"))
    }


def _validate_object_types(object_types, errors):
    seen_object_type_keys = set()
    for object_index, object_type in enumerate(object_types):
        object_path = f"object_types[{object_index}]"
        if not _validate_mapping(object_type, object_path, "object type", "object_type", errors):
            continue

        object_key = object_type.get("key")
        if not _is_snake_case_key(object_key):
            errors.append(
                {
                    "path": f"{object_path}.key",
                    "code": "invalid_object_type_key",
                    "message": "Object type keys must use lowercase snake case.",
                }
            )
        elif object_key in seen_object_type_keys:
            errors.append(
                {
                    "path": f"{object_path}.key",
                    "code": "duplicate_object_type_key",
                    "message": "Object type keys must be unique.",
                }
            )
        else:
            seen_object_type_keys.add(object_key)

        fields = object_type.get("fields")
        if not isinstance(fields, list):
            errors.append(
                {
                    "path": f"{object_path}.fields",
                    "code": "invalid_fields",
                    "message": "Fields must be a list.",
                }
            )
            continue

        _validate_fields(fields, object_path, errors)


def _validate_relationship_types(data, object_type_keys, errors):
    if "relationship_types" not in data:
        return

    relationship_types = data["relationship_types"]
    if not isinstance(relationship_types, list):
        errors.append(
            {
                "path": "relationship_types",
                "code": "invalid_relationship_types",
                "message": "Relationship types must be a list.",
            }
        )
        return

    seen_keys = set()
    for relationship_index, relationship_type in enumerate(relationship_types):
        path = f"relationship_types[{relationship_index}]"
        if not _validate_mapping(
            relationship_type,
            path,
            "relationship type",
            "relationship_type",
            errors,
        ):
            continue

        key = relationship_type.get("key")
        if not _is_snake_case_key(key):
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": "invalid_relationship_type_key",
                    "message": "Relationship type keys must use lowercase snake case.",
                }
            )
        elif key in seen_keys:
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": "duplicate_relationship_type_key",
                    "message": "Relationship type keys must be unique.",
                }
            )
        else:
            seen_keys.add(key)

        _validate_relationship_object_type_reference(
            relationship_type,
            "source_object_type",
            "source",
            object_type_keys,
            path,
            errors,
        )
        _validate_relationship_object_type_reference(
            relationship_type,
            "target_object_type",
            "target",
            object_type_keys,
            path,
            errors,
        )


def _validate_relationship_object_type_reference(
    relationship_type,
    field,
    direction,
    object_type_keys,
    path,
    errors,
):
    if field not in relationship_type:
        return

    object_type_key = relationship_type.get(field)
    if object_type_key not in object_type_keys:
        errors.append(
            {
                "path": f"{path}.{field}",
                "code": f"unknown_relationship_{direction}_object_type",
                "message": f"Relationship {direction} object type must reference an object type.",
            }
        )


def _validate_fields(fields, object_path, errors):
    seen_field_keys = set()
    for field_index, field in enumerate(fields):
        field_path = f"{object_path}.fields[{field_index}]"
        if not _validate_mapping(field, field_path, "field", "field", errors):
            continue

        field_key = field.get("key")
        if not _is_snake_case_key(field_key):
            errors.append(
                {
                    "path": f"{field_path}.key",
                    "code": "invalid_field_key",
                    "message": "Field keys must use lowercase snake case.",
                }
            )
        elif field_key in seen_field_keys:
            errors.append(
                {
                    "path": f"{field_path}.key",
                    "code": "duplicate_field_key",
                    "message": "Field keys must be unique within an object type.",
                }
            )
        else:
            seen_field_keys.add(field_key)

        if field.get("type") not in ALLOWED_FIELD_TYPES:
            errors.append(
                {
                    "path": f"{field_path}.type",
                    "code": "invalid_field_type",
                    "message": "Field type must be one of the v1 allowed field types.",
                }
            )


def _validate_keyed_definition_section(data, section, singular_label, code_label, errors):
    if section not in data:
        return

    definitions = data[section]
    if not isinstance(definitions, list):
        errors.append(
            {
                "path": section,
                "code": f"invalid_{section}",
                "message": f"{section.replace('_', ' ').capitalize()} must be a list.",
            }
        )
        return

    seen_keys = set()
    for index, definition in enumerate(definitions):
        path = f"{section}[{index}]"
        if not _validate_mapping(definition, path, singular_label, code_label, errors):
            continue

        key = definition.get("key")
        if not _is_snake_case_key(key):
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": f"invalid_{code_label}_key",
                    "message": f"{singular_label.capitalize()} keys must use lowercase snake case.",
                }
            )
        elif key in seen_keys:
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": f"duplicate_{code_label}_key",
                    "message": f"{singular_label.capitalize()} keys must be unique.",
                }
            )
        else:
            seen_keys.add(key)


def _validate_mapping(value, path, label, code_label, errors):
    if isinstance(value, dict):
        return True

    errors.append(
        {
            "path": path,
            "code": f"invalid_{code_label}",
            "message": f"{label.capitalize()} definitions must be objects.",
        }
    )
    return False


@transaction.atomic
def publish_draft(draft: ConfigurationDraft, user, request=None) -> ConfigurationVersion:
    if draft.pk:
        draft = ConfigurationDraft.objects.select_for_update().get(pk=draft.pk)

    if draft.status != ConfigurationDraft.Status.DRAFT:
        raise ConfigurationValidationError(
            [
                {
                    "path": "status",
                    "code": "draft_not_publishable",
                    "message": "Only draft configurations can be published.",
                }
            ]
        )

    errors = validate_draft(draft)
    if errors:
        raise ConfigurationValidationError(errors)

    configuration_version = ConfigurationVersion.objects.create(
        version=_allocate_next_version(),
        data=copy.deepcopy(draft.data),
        published_by=user,
    )
    _sync_definition_models(configuration_version)

    draft.status = ConfigurationDraft.Status.PUBLISHED
    draft.published_version = configuration_version
    draft.updated_by = user
    draft.save(update_fields=["status", "published_version", "updated_by", "updated_at"])
    record_audit_event(
        user,
        "configuration.published",
        configuration_version,
        before=None,
        after={
            "id": configuration_version.pk,
            "version": configuration_version.version,
            "data": copy.deepcopy(configuration_version.data),
        },
        request=request,
    )
    return configuration_version


def get_active_config() -> ConfigurationVersion:
    return ConfigurationVersion.objects.order_by("-version").first()


def _is_snake_case_key(value):
    return isinstance(value, str) and SNAKE_CASE_RE.fullmatch(value) is not None


def _allocate_next_version():
    sequence, _created = ConfigurationSequence.objects.select_for_update().get_or_create(
        pk=1,
        defaults={"next_version": 1},
    )
    version = sequence.next_version
    sequence.next_version += 1
    sequence.save(update_fields=["next_version"])
    return version


def _sync_definition_models(configuration_version):
    data = configuration_version.data
    object_type_models = {}

    for object_type in data.get("object_types", []):
        object_model = ObjectTypeDefinition.objects.create(
            configuration_version=configuration_version,
            key=object_type["key"],
            label=object_type.get("label", object_type["key"]),
            plural_label=object_type.get("plural_label", ""),
            payload=copy.deepcopy(object_type),
        )
        object_type_models[object_type["key"]] = object_model
        for field in object_type.get("fields", []):
            FieldDefinition.objects.create(
                object_type=object_model,
                key=field["key"],
                label=field.get("label", field["key"]),
                field_type=field["type"],
                required=field.get("required", False),
                payload=copy.deepcopy(field),
            )

    for layout in data.get("form_layouts", []):
        FormLayoutDefinition.objects.create(
            configuration_version=configuration_version,
            key=layout["key"],
            label=layout.get("label", ""),
            payload=copy.deepcopy(layout),
        )

    for template in data.get("folder_templates", []):
        FolderTemplateDefinition.objects.create(
            configuration_version=configuration_version,
            key=template["key"],
            label=template.get("label", ""),
            payload=copy.deepcopy(template),
        )

    for dashboard in data.get("dashboards", []):
        DashboardDefinition.objects.create(
            configuration_version=configuration_version,
            key=dashboard["key"],
            label=dashboard.get("label", ""),
            payload=copy.deepcopy(dashboard),
        )
