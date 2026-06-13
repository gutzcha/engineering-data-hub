# ===
# File Summary
# Path: backend\apps\reports\views.py
# Type: python
# Purpose: Reports domain for query definitions, payload shaping, and saved reporting views.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: IsAuthenticated, has_permission, SavedViewSerializer, Meta, validate_filters
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
from django.db.models import Q
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from types import SimpleNamespace

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.reports.models import Dashboard, SavedView
from apps.reports.query import (
    ReportFilterValidationError,
    home_overview_payload,
    run_dashboard_widget,
    saved_view_results,
    validate_saved_view_filters,
)
from apps.config_registry.services import get_active_config
from apps.config_registry.seed import starter_configuration_data


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class SavedViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedView
        fields = [
            "id",
            "name",
            "filters",
            "columns",
            "sort",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_filters(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Expected a list of filters.")
        try:
            validate_saved_view_filters(value)
        except ReportFilterValidationError as error:
            raise serializers.ValidationError(error.errors) from error
        return value

    def validate_columns(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Expected a list of columns.")
        return value

    def validate_sort(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Expected a list of sort fields.")
        return value


class SavedViewListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request):
        views = SavedView.objects.filter(owner=request.user)
        return Response({"results": SavedViewSerializer(views, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SavedViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved_view = serializer.save(owner=request.user)
        return Response(SavedViewSerializer(saved_view).data, status=status.HTTP_201_CREATED)


class SavedViewResultsView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk):
        saved_view = get_object_or_404(SavedView, pk=pk, owner=request.user)
        try:
            results = saved_view_results(saved_view, request.user, limit=_result_limit(request))
        except ReportFilterValidationError as error:
            return Response({"filters": error.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            results,
            status=status.HTTP_200_OK,
        )


class DashboardDetailView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, identifier):
        dashboards = _visible_dashboards(request.user).prefetch_related("widgets")
        dashboard = _dashboard_by_identifier(dashboards, identifier)
        if dashboard is None:
            payload = _fallback_config_dashboard(identifier, request.user)
            if payload is None:
                return Response({"detail": "Dashboard not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(payload, status=status.HTTP_200_OK)

        return Response(
            {
                "id": dashboard.pk,
                "name": dashboard.name,
                "description": dashboard.description,
                "config": _dict_config(dashboard.config),
                "widgets": [
                    {
                        "id": widget.pk,
                        "title": widget.title,
                        "widget_type": widget.widget_type,
                        "config": _dict_config(widget.config),
                        "sort_order": widget.sort_order,
                        "data": run_dashboard_widget(widget, request.user),
                    }
                    for widget in dashboard.widgets.all()
                ],
            },
            status=status.HTTP_200_OK,
        )


class HomeOverviewView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response(home_overview_payload(request.user, limit=_home_overview_limit(request)))


def _home_overview_limit(request):
    try:
        limit = int(request.query_params.get("limit", 10))
    except (TypeError, ValueError):
        limit = 10
    return max(1, min(limit, 50))


def _result_limit(request):
    try:
        requested_limit = int(request.query_params.get("limit", 100))
    except (TypeError, ValueError):
        return 100
    return max(1, min(requested_limit, 500))


def _visible_dashboards(user):
    dashboards = Dashboard.objects.all()
    if _is_system_admin(user):
        return dashboards
    return dashboards.filter(Q(owner__isnull=True) | Q(owner=user))


def _dashboard_by_identifier(queryset, identifier):
    identifier = str(identifier)
    if identifier.isdigit():
        dashboard = queryset.filter(pk=int(identifier)).first()
        if dashboard is not None:
            return dashboard
    return queryset.filter(config__key=identifier).first()


def _fallback_config_dashboard(identifier, user):
    configuration = get_active_config()
    configuration_data = (
        starter_configuration_data() if configuration is None else _dict_config(configuration.data)
    )

    for dashboard_definition in configuration_data.get("dashboards", []):
        if not isinstance(dashboard_definition, dict):
            continue

        if str(dashboard_definition.get("key")) != str(identifier):
            continue

        dashboard_key = dashboard_definition.get("key")
        widgets = []

        for sort_order, widget_definition in enumerate(dashboard_definition.get("widgets", [])):
            if not isinstance(widget_definition, dict):
                continue

            widget_type = widget_definition.get("widget_type") or widget_definition.get("type")
            if not widget_type:
                continue

            widget = SimpleNamespace(
                widget_type=widget_type,
                config=_dict_config(widget_definition.get("config")),
            )
            if widget_type in _runtime_widget_types():
                widget_data = run_dashboard_widget(widget, user)
            else:
                widget_data = {"items": []}

            widgets.append(
                {
                    "id": f"{dashboard_key}:{sort_order}",
                    "title": _widget_title(widget_definition, widget_type),
                    "widget_type": widget_type,
                    "config": _dict_config(widget_definition.get("config")),
                    "sort_order": sort_order,
                    "data": widget_data,
                }
            )

        return {
            "id": str(dashboard_key),
            "name": dashboard_definition.get("name")
            or dashboard_definition.get("label")
            or str(dashboard_key),
            "description": dashboard_definition.get("description", ""),
            "config": {"key": dashboard_key},
            "widgets": widgets,
        }

    return None


def _runtime_widget_types():
    return {
        "count_by_status",
        "count_by_object_type",
        "overdue_project_tasks",
        "missing_required_documents",
        "recent_changes",
        "workflow_bottlenecks",
    }


def _widget_title(widget_definition, widget_type):
    return widget_definition.get("title") or widget_definition.get("label") or widget_type


def _is_system_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


def _dict_config(value):
    return value if isinstance(value, dict) else {}

