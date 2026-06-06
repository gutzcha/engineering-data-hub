from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import user_can
from apps.records.models import Record
from apps.relationships.models import Relationship
from apps.relationships.services import validate_relationship_type


class RelationshipSerializer(serializers.ModelSerializer):
    source_record = serializers.PrimaryKeyRelatedField(queryset=Record.objects.all())
    target_record = serializers.PrimaryKeyRelatedField(queryset=Record.objects.all())

    class Meta:
        model = Relationship
        fields = [
            "id",
            "source_record",
            "target_record",
            "relationship_type_key",
            "data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected an object.")
        return value

    def validate(self, attrs):
        source_record = attrs["source_record"]
        target_record = attrs["target_record"]
        self._validate_create_permissions(source_record, target_record)
        validate_relationship_type(
            source_record,
            target_record,
            attrs["relationship_type_key"],
        )
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"non_field_errors": ["Relationship already exists."]}
            ) from error

    def _validate_create_permissions(self, source_record, target_record):
        request = self.context.get("request")
        if not request:
            return

        if not user_can(
            request.user,
            "edit",
            source_record.object_type_key,
            record_id=str(source_record.pk),
        ):
            raise PermissionDenied("You do not have permission to edit the source record.")

        if not user_can(
            request.user,
            "view",
            target_record.object_type_key,
            record_id=str(target_record.pk),
        ):
            raise PermissionDenied("You do not have permission to view the target record.")
