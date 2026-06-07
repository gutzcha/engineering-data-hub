from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are append-only.")

    def delete(self):
        raise ValidationError("Audit events are append-only.")


class AuditEvent(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120)
    object_type = models.CharField(max_length=120)
    object_id = models.CharField(max_length=120)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    request_id = models.CharField(max_length=120, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(
                fields=["object_type", "object_id", "created_at"],
                name="audit_audit_object__551ade_idx",
            ),
            models.Index(fields=["action", "created_at"], name="audit_audit_action_235b5a_idx"),
            models.Index(fields=["actor", "created_at"], name="audit_audit_actor_i_ed8fd7_idx"),
            models.Index(fields=["request_id"], name="audit_audit_request_6500e3_idx"),
        ]
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")

    def __str__(self):
        return f"{self.action}: {self.object_type}:{self.object_id}"
