from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.config_registry.models import ConfigurationDraft, ConfigurationVersion
from apps.config_registry.schemas import ConfigurationDraftSerializer, ConfigurationVersionSerializer
from apps.config_registry.services import (
    ConfigurationValidationError,
    create_draft_from_current,
    get_active_config,
    publish_draft,
    validate_draft,
)


class IsSystemAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def active_config(request):
    configuration = get_active_config()
    if configuration is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(ConfigurationVersionSerializer(configuration).data)


@api_view(["POST"])
@permission_classes([IsSystemAdmin])
def create_draft(request):
    draft = create_draft_from_current(request.user)
    return Response(ConfigurationDraftSerializer(draft).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsSystemAdmin])
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
@permission_classes([IsSystemAdmin])
def config_history(request):
    versions = ConfigurationVersion.objects.order_by("-version")
    return Response(ConfigurationVersionSerializer(versions, many=True).data)


@api_view(["POST"])
@permission_classes([IsSystemAdmin])
def validate_config_draft(request, draft_id):
    draft = get_object_or_404(ConfigurationDraft, pk=draft_id)
    return Response({"errors": validate_draft(draft)})


@api_view(["POST"])
@permission_classes([IsSystemAdmin])
def publish_config_draft(request, draft_id):
    draft = get_object_or_404(ConfigurationDraft, pk=draft_id)
    try:
        configuration = publish_draft(draft, request.user, request=request)
    except ConfigurationValidationError as error:
        return Response({"errors": error.errors}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ConfigurationVersionSerializer(configuration).data, status=status.HTTP_201_CREATED)
