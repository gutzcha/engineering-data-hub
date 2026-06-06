from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import ObjectPermission
from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.accounts.serializers import CurrentUserSerializer, ObjectPermissionSerializer


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


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    return Response(CurrentUserSerializer(request.user).data)
