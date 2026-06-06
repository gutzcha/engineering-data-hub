from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ConfigurationDraft(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    data = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="configuration_drafts_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="configuration_drafts_updated",
    )
    published_version = models.ForeignKey(
        "ConfigurationVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_drafts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"Configuration draft {self.pk or 'unsaved'} ({self.status})"


class ConfigurationVersion(models.Model):
    version = models.PositiveIntegerField(unique=True)
    data = models.JSONField(default=dict)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="configuration_versions_published",
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.only("data", "version").get(pk=self.pk)
            if original.data != self.data:
                raise ValidationError("Published configuration data is immutable.")
            if original.version != self.version:
                raise ValidationError("Published configuration version is immutable.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Configuration v{self.version}"


class ConfigurationSequence(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    next_version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "configuration sequence"
        verbose_name_plural = "configuration sequence"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Next configuration version: {self.next_version}"


class PublishedDefinitionImmutableMixin(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Published definition rows are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Published definition rows are immutable.")


class ObjectTypeDefinition(PublishedDefinitionImmutableMixin, models.Model):
    configuration_version = models.ForeignKey(
        ConfigurationVersion,
        on_delete=models.CASCADE,
        related_name="object_type_definitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=200)
    plural_label = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuration_version", "key"],
                name="unique_object_type_per_config_version",
            )
        ]
        ordering = ["configuration_version", "key"]

    def __str__(self):
        return f"{self.key} ({self.configuration_version})"


class FieldDefinition(PublishedDefinitionImmutableMixin, models.Model):
    object_type = models.ForeignKey(
        ObjectTypeDefinition,
        on_delete=models.CASCADE,
        related_name="field_definitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=40)
    required = models.BooleanField(default=False)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["object_type", "key"],
                name="unique_field_per_object_type_definition",
            )
        ]
        ordering = ["object_type", "key"]

    def __str__(self):
        return f"{self.object_type.key}.{self.key}"


class FormLayoutDefinition(PublishedDefinitionImmutableMixin, models.Model):
    configuration_version = models.ForeignKey(
        ConfigurationVersion,
        on_delete=models.CASCADE,
        related_name="form_layout_definitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuration_version", "key"],
                name="unique_form_layout_per_config_version",
            )
        ]
        ordering = ["configuration_version", "key"]

    def __str__(self):
        return f"{self.key} ({self.configuration_version})"


class FolderTemplateDefinition(PublishedDefinitionImmutableMixin, models.Model):
    configuration_version = models.ForeignKey(
        ConfigurationVersion,
        on_delete=models.CASCADE,
        related_name="folder_template_definitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuration_version", "key"],
                name="unique_folder_template_per_config_version",
            )
        ]
        ordering = ["configuration_version", "key"]

    def __str__(self):
        return f"{self.key} ({self.configuration_version})"


class DashboardDefinition(PublishedDefinitionImmutableMixin, models.Model):
    configuration_version = models.ForeignKey(
        ConfigurationVersion,
        on_delete=models.CASCADE,
        related_name="dashboard_definitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuration_version", "key"],
                name="unique_dashboard_per_config_version",
            )
        ]
        ordering = ["configuration_version", "key"]

    def __str__(self):
        return f"{self.key} ({self.configuration_version})"
