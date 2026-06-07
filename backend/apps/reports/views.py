from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.reports.models import Dashboard, SavedView
from apps.reports.query import (
    ReportFilterValidationError,
    run_dashboard_widget,
    saved_view_results,
    validate_saved_view_filters,
)


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
    return get_object_or_404(queryset, config__key=identifier)


def _is_system_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


def _dict_config(value):
    return value if isinstance(value, dict) else {}
