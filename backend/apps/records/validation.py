from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.config_registry.services import ALLOWED_FIELD_TYPES, get_active_config


def get_object_type_definition(object_type_key):
    active_config = get_active_config()
    object_types = (active_config.data or {}).get("object_types", []) if active_config else []
    for object_type in object_types:
        if object_type.get("key") == object_type_key:
            return object_type, active_config
    raise serializers.ValidationError({"object_type_key": ["Unknown object type."]})


def validate_record_data(object_type_key, data, *, current_record=None):
    if not isinstance(data, dict):
        raise serializers.ValidationError({"data": ["Expected an object."]})

    object_type, _active_config = get_object_type_definition(object_type_key)
    errors = {}
    for field in object_type.get("fields", []):
        field_key = field.get("key")
        field_type = field.get("type")
        value = data.get(field_key)

        if field.get("required") and _is_blank(value):
            errors.setdefault(field_key, []).append("This field is required.")
            continue

        if _is_blank(value):
            continue

        if field_type not in ALLOWED_FIELD_TYPES:
            continue

        field_errors = _validate_field_value(field, value)
        if field_errors:
            errors.setdefault(field_key, []).extend(field_errors)
            continue

        if field.get("unique"):
            duplicate = _duplicate_unique_value(
                object_type_key,
                field_key,
                value,
                current_record=current_record,
            )
            if duplicate:
                errors.setdefault(field_key, []).append(
                    f"Value must be unique within {object_type_key}."
                )

    if errors:
        raise serializers.ValidationError({"data": errors})


def _validate_field_value(field, value):
    field_type = field.get("type")
    if field_type in {"text", "long_text", "url", "file_ref"}:
        return [] if isinstance(value, str) else ["Expected a string."]
    if field_type == "number":
        if isinstance(value, int | float) and not isinstance(value, bool):
            return []
        return ["Expected a number."]
    if field_type == "date":
        return _validate_date(value)
    if field_type == "boolean":
        return [] if isinstance(value, bool) else ["Expected a boolean."]
    if field_type == "choice":
        options = _choice_values(field.get("options", []))
        return [] if value in options else [f"Value must be one of: {', '.join(options)}."]
    if field_type == "multi_choice":
        return _validate_multi_choice(field, value)
    if field_type == "record_ref":
        return _validate_record_ref(field, value)
    if field_type == "user_ref":
        return _validate_user_ref(value)
    return []


def _validate_date(value):
    if not isinstance(value, str):
        return ["Expected an ISO date string."]
    try:
        date.fromisoformat(value)
    except ValueError:
        return ["Expected an ISO date string."]
    return [] if len(value) == 10 else ["Expected an ISO date string."]


def _validate_multi_choice(field, value):
    if not isinstance(value, list):
        return ["Expected a list."]
    options = _choice_values(field.get("options", []))
    invalid = [item for item in value if item not in options]
    if invalid:
        return [f"Values must be one of: {', '.join(options)}."]
    return []


def _validate_record_ref(field, value):
    from apps.records.models import Record

    try:
        record = Record.objects.get(pk=value)
    except (Record.DoesNotExist, ValueError, TypeError):
        return ["Referenced record does not exist."]

    target_object_type = field.get("target_object_type")
    if target_object_type and record.object_type_key != target_object_type:
        return [f"Referenced record must be a {target_object_type}."]
    return []


def _validate_user_ref(value):
    User = get_user_model()
    return [] if User.objects.filter(pk=value).exists() else ["Referenced user does not exist."]


def _choice_values(options):
    values = []
    for option in options:
        if isinstance(option, dict) and "value" in option:
            values.append(str(option["value"]))
        elif isinstance(option, str):
            values.append(option)
    return values


def _duplicate_unique_value(object_type_key, field_key, value, *, current_record=None):
    from apps.records.models import Record

    queryset = Record.objects.filter(
        object_type_key=object_type_key,
        **{f"data__{field_key}": value},
    )
    if current_record is not None:
        queryset = queryset.exclude(pk=current_record.pk)
    return queryset.exists()


def _is_blank(value):
    return value is None or value == "" or value == []
