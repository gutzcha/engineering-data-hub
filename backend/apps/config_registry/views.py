# ===
# File Summary
# Path: backend\apps\config_registry\views.py
# Type: python
# Purpose: Configuration registry service for dynamic schemas, publishing, and config governance.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: IsConfigurationAdmin, has_permission, active_config, create_draft, update_config_draft
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import is_configuration_admin, is_system_admin
from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.models import ConfigurationDraft, ConfigurationVersion
from apps.config_registry.schemas import ConfigurationDraftSerializer, ConfigurationVersionSerializer
from apps.config_registry.services import (
    ConfigurationValidationError,
    breaking_changes_for_draft,
    create_draft_from_current,
    get_active_config,
    publish_draft,
    validate_draft,
)


class IsConfigurationAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_configuration_admin(request.user)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def active_config(request):
    configuration = get_active_config()
    if configuration is None:
        payload = {
            "id": 0,
            "version": 0,
            "published_at": None,
            "published_by": None,
            "data": starter_configuration_data(),
        }
        configuration_data = payload["data"]
    else:
        payload = dict(ConfigurationVersionSerializer(configuration).data)
        configuration_data = _dict_config(configuration.data)
    payload["document_types"] = _collect_document_types(configuration_data)
    payload["choices"] = _collect_choice_fields(configuration_data)
    return Response(payload)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def active_field_options(request):
    object_type_key = (request.query_params.get("object_type_key") or "").strip()
    field_key = (request.query_params.get("field_key") or "").strip()
    if not object_type_key or not field_key:
        return Response(
            {"detail": "object_type_key and field_key are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    configuration = get_active_config()
    if configuration is None:
        configuration_data = starter_configuration_data()
    else:
        configuration_data = _dict_config(configuration.data)

    choices = _field_options_for_active(
        configuration_data,
        object_type_key=object_type_key,
        field_key=field_key,
    )
    return Response(
        {
            "object_type_key": object_type_key,
            "field_key": field_key,
            "options": choices,
        }
    )


@api_view(["POST"])
@permission_classes([IsConfigurationAdmin])
def create_draft(request):
    draft = create_draft_from_current(request.user)
    return Response(ConfigurationDraftSerializer(draft).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsConfigurationAdmin])
def update_config_draft(request, draft_id):
    draft = get_object_or_404(ConfigurationDraft, pk=draft_id)
    if draft.status != ConfigurationDraft.Status.DRAFT:
        return Response(
            {"detail": "Only draft configurations can be updated."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = request.data.get("data", request.data) if isinstance(request.data, dict) else request.data
    draft.data = data
    draft.updated_by = request.user
    draft.save(update_fields=["data", "updated_by", "updated_at"])
    return Response(ConfigurationDraftSerializer(draft).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def config_history(request):
    versions = list(ConfigurationVersion.objects.order_by("-version"))
    if versions:
        return Response(ConfigurationVersionSerializer(versions, many=True).data)

    return Response(
        [
            {
                "id": 0,
                "version": 0,
                "data": _dict_config(starter_configuration_data()),
                "published_by": None,
                "published_at": None,
            }
        ]
    )


@api_view(["POST"])
@permission_classes([IsConfigurationAdmin])
def validate_config_draft(request, draft_id):
    draft = get_object_or_404(ConfigurationDraft, pk=draft_id)
    return Response(
        {
            "errors": validate_draft(draft),
            "breaking_changes": breaking_changes_for_draft(draft),
        }
    )


@api_view(["POST"])
@permission_classes([IsConfigurationAdmin])
def publish_config_draft(request, draft_id):
    draft = get_object_or_404(ConfigurationDraft, pk=draft_id)
    breaking_changes = breaking_changes_for_draft(draft)
    if breaking_changes and not is_system_admin(request.user):
        return Response(
            {
                "detail": "Destructive configuration changes require System Admin approval.",
                "breaking_changes": breaking_changes,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    confirm_breaking_changes = _confirm_breaking_changes(request.data)
    try:
        configuration = publish_draft(
            draft,
            request.user,
            request=request,
            confirm_breaking_changes=confirm_breaking_changes,
        )
    except ConfigurationValidationError as error:
        if _requires_breaking_change_confirmation(error.errors):
            return Response(
                {
                    "detail": "Breaking configuration changes require confirmation.",
                    "errors": error.errors,
                    "breaking_changes": _breaking_changes_from_errors(error.errors),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"errors": error.errors}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ConfigurationVersionSerializer(configuration).data, status=status.HTTP_201_CREATED)


def _confirm_breaking_changes(request_data):
    return isinstance(request_data, dict) and request_data.get("confirm_breaking_changes") is True


def _requires_breaking_change_confirmation(errors):
    return any(error.get("code") == "breaking_changes_require_confirmation" for error in errors)


def _breaking_changes_from_errors(errors):
    return [
        error for error in errors if error.get("code") != "breaking_changes_require_confirmation"
    ]


def _collect_document_types(configuration):
    document_types = []
    for object_type in _iter_dict_list(configuration.get("object_types")):
        fields = _iter_dict_list(object_type.get("fields"))
        for field in fields:
            if field.get("key") != "document_type":
                continue
            for value in _string_list(field.get("options")):
                if value not in document_types:
                    document_types.append(value)
    return document_types


def _collect_choice_fields(configuration):
    choices = {}
    for object_type in _iter_dict_list(configuration.get("object_types")):
        for field in _iter_dict_list(object_type.get("fields")):
            field_key = field.get("key")
            if not field_key:
                continue
            options = _string_list(field.get("options"))
            if options and field.get("type") == "choice":
                choices[field_key] = options
    return choices


def _field_options_for_active(configuration, *, object_type_key, field_key):
    for object_type in _iter_dict_list(configuration.get("object_types")):
        if object_type.get("key") != object_type_key:
            continue
        for field in _iter_dict_list(object_type.get("fields")):
            if field.get("key") == field_key:
                if field.get("type") == "choice":
                    return _string_list(field.get("options"))
                return []
    return []


def _iter_dict_list(value):
    if not isinstance(value, list):
        return ()
    return (item for item in value if isinstance(item, dict))


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _dict_config(value):
    return value if isinstance(value, dict) else {}

