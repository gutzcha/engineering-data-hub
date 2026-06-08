from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import is_configuration_admin, is_system_admin
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
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(ConfigurationVersionSerializer(configuration).data)


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
@permission_classes([IsConfigurationAdmin])
def config_history(request):
    versions = ConfigurationVersion.objects.order_by("-version")
    return Response(ConfigurationVersionSerializer(versions, many=True).data)


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
