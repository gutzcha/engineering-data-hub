from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.audit.services import record_audit_event
from apps.records.codes import generate_record_code, validate_code_pattern
from apps.records.models import Record, RecordObjectTypeLock
from apps.records.validation import get_object_type_definition, validate_record_data


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = [
            "id",
            "object_type_key",
            "code",
            "title",
            "status",
            "schema_version",
            "data",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "title",
            "schema_version",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"code": {"required": False}}

    def validate(self, attrs):
        if self.instance is None:
            object_type_key = attrs.get("object_type_key")
            data = attrs.get("data", {})
            object_type, active_config = get_object_type_definition(object_type_key)
            if attrs.get("status", Record.Status.DRAFT) != Record.Status.DRAFT:
                raise serializers.ValidationError(
                    {"status": ["New records must be created as draft."]}
                )
            if "code" not in attrs:
                validate_code_pattern(object_type.get("code_pattern", "{seq:000000}"))
            validate_record_data(object_type_key, data)
            attrs["data"] = data
            attrs["_object_type"] = object_type
            attrs["_active_config"] = active_config
            return attrs

        object_type_key = self.instance.object_type_key
        if "object_type_key" in attrs and attrs["object_type_key"] != self.instance.object_type_key:
            raise serializers.ValidationError(
                {"object_type_key": ["Object type cannot be changed."]}
            )
        if "code" in attrs and attrs["code"] != self.instance.code:
            raise serializers.ValidationError({"code": ["Code cannot be changed."]})
        if "status" in attrs and attrs["status"] != self.instance.status:
            raise serializers.ValidationError(
                {"status": ["Use the release endpoint to release records."]}
            )
        data = self.instance.data.copy()
        if "data" in attrs:
            if not isinstance(attrs["data"], dict):
                raise serializers.ValidationError({"data": ["Expected an object."]})
            data.update(attrs["data"])
        object_type, active_config = get_object_type_definition(object_type_key)
        validate_record_data(object_type_key, data, current_record=self.instance)
        attrs["data"] = data
        attrs["_object_type"] = object_type
        attrs["_active_config"] = active_config
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        object_type = validated_data.pop("_object_type")
        active_config = validated_data.pop("_active_config")
        request = self.context.get("request")
        object_type_key = validated_data["object_type_key"]
        _lock_records_for_dynamic_unique_fields(object_type_key)
        data = validated_data.setdefault("data", {})
        validate_record_data(object_type_key, data)
        code = validated_data.get("code")
        if not code:
            code = generate_record_code(
                object_type_key,
                object_type.get("code_pattern", "{seq:000000}"),
            )
        validated_data["code"] = code
        validated_data["title"] = _title_from_data(object_type, validated_data["data"], code)
        validated_data["schema_version"] = active_config.version
        validated_data["created_by"] = request.user if request else None
        validated_data["updated_by"] = request.user if request else None
        try:
            record = super().create(validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError({"code": ["Record code must be unique."]}) from error
        record_audit_event(
            request.user if request else None,
            "record.created",
            record,
            before=None,
            after=_record_snapshot(record),
            request=request,
        )
        return record

    @transaction.atomic
    def update(self, instance, validated_data):
        object_type = validated_data.pop("_object_type")
        active_config = validated_data.pop("_active_config")
        request = self.context.get("request")
        _lock_records_for_dynamic_unique_fields(instance.object_type_key)
        data = validated_data.get("data", instance.data)
        validate_record_data(instance.object_type_key, data, current_record=instance)
        if "data" in validated_data:
            validated_data["title"] = _title_from_data(object_type, validated_data["data"], instance.code)
        validated_data["schema_version"] = active_config.version
        if request:
            validated_data["updated_by"] = request.user
        before = _record_snapshot(instance)
        try:
            record = super().update(instance, validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError({"code": ["Record code must be unique."]}) from error
        record_audit_event(
            request.user if request else None,
            "record.updated",
            record,
            before=before,
            after=_record_snapshot(record),
            request=request,
        )
        return record


def _title_from_data(object_type, data, code):
    title_field = object_type.get("title_field")
    title = data.get(title_field) if title_field else None
    if title is None or title == "":
        return code
    return str(title)


def _record_snapshot(record):
    return {
        "id": str(record.pk),
        "object_type_key": record.object_type_key,
        "code": record.code,
        "title": record.title,
        "status": record.status,
        "schema_version": record.schema_version,
        "data": record.data.copy(),
    }


def _lock_records_for_dynamic_unique_fields(object_type_key):
    # Dynamic unique fields live inside JSON data, so v1 enforces them at the
    # application layer by serializing writes through one lock row per object type.
    RecordObjectTypeLock.objects.get_or_create(object_type_key=object_type_key)
    RecordObjectTypeLock.objects.select_for_update().get(object_type_key=object_type_key)
