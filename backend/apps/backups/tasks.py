from celery import shared_task

from apps.backups.services import create_backup


@shared_task
def create_scheduled_backup():
    manifest = create_backup()
    return {"backup_id": manifest.backup_id, "state": manifest.state}
