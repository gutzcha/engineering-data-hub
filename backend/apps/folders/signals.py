import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.folders.models import FolderChangeEvent
from apps.folders.services import generate_managed_folder
from apps.folders.templates import default_template_key, render_folder_template
from apps.records.models import Record

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Record)
def generate_default_managed_folder(sender, instance, created, **kwargs):
    if not created or not getattr(settings, "MANAGED_FOLDERS_AUTO_GENERATE", True):
        return
    if not default_template_key(instance.object_type_key):
        return

    transaction.on_commit(lambda: _generate_folder(instance.pk))


def _generate_folder(record_id):
    record = Record.objects.get(pk=record_id)
    try:
        generate_managed_folder(record)
    except Exception:
        _record_generation_failed(record)
        logger.exception("Unable to generate managed folder for record %s", record_id)


def _record_generation_failed(record):
    try:
        path = render_folder_template(record).root
    except ValueError:
        path = ""
    FolderChangeEvent.objects.get_or_create(
        event_type=FolderChangeEvent.EventType.GENERATION_FAILED,
        path=path,
        matched_record=record,
        review_status=FolderChangeEvent.ReviewStatus.PENDING,
    )
