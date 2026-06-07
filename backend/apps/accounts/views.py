from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.accounts.serializers import (
    CurrentUserSerializer,
    ObjectPermissionSerializer,
    RecordPermissionSerializer,
)


class IsSystemAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


class ObjectPermissionViewSet(viewsets.ModelViewSet):
    queryset = ObjectPermission.objects.all()
    serializer_class = ObjectPermissionSerializer
    permission_classes = [IsSystemAdmin]
    filterset_fields = ["role_name", "object_type_key"]


class RecordPermissionViewSet(viewsets.ModelViewSet):
    queryset = RecordPermission.objects.select_related("record").all()
    serializer_class = RecordPermissionSerializer
    permission_classes = [IsSystemAdmin]
    filterset_fields = ["role_name", "object_type_key", "record"]


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf_token(request):
    return Response({"csrfToken": get_token(request)})


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def session_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response(CurrentUserSerializer(user).data, status=status.HTTP_200_OK)


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def session_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    return Response(CurrentUserSerializer(request.user).data)
