from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.views import IsSystemAdmin
from apps.backups.models import BackupManifest
from apps.backups.services import BackupError, create_backup


class BackupManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupManifest
        fields = [
            "id",
            "backup_id",
            "started_at",
            "finished_at",
            "database_dump_path",
            "managed_files_archive_path",
            "media_archive_path",
            "config_export_path",
            "audit_export_path",
            "sha256_manifest",
            "state",
            "failure_message",
        ]
        read_only_fields = fields


@api_view(["GET", "POST"])
@permission_classes([IsSystemAdmin])
def backup_collection(request):
    if request.method == "GET":
        manifests = BackupManifest.objects.all()[:100]
        return Response({"results": BackupManifestSerializer(manifests, many=True).data})

    backup_id = request.data.get("backup_id") if isinstance(request.data, dict) else None
    try:
        manifest = create_backup(backup_id=backup_id)
    except BackupError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(BackupManifestSerializer(manifest).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsSystemAdmin])
def backup_detail(request, backup_id):
    manifest = get_object_or_404(BackupManifest, backup_id=backup_id)
    return Response(BackupManifestSerializer(manifest).data)
