from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("records", "0002_recordobjecttypelock"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(blank=True, default="", upload_to="import-jobs/")),
                ("target_object_type", models.CharField(max_length=120)),
                ("mapping", models.JSONField(blank=True, default=dict)),
                ("dry_run_results", models.JSONField(blank=True, default=dict)),
                ("created_records_count", models.PositiveIntegerField(default=0)),
                ("updated_records_count", models.PositiveIntegerField(default=0)),
                ("error_rows", models.JSONField(blank=True, default=list)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("dry_run_ready", "Dry-run ready"),
                            ("dry_run_failed", "Dry-run failed"),
                            ("applied", "Applied"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_jobs_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_jobs_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ImportAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[("created", "Created"), ("updated", "Updated")],
                        max_length=32,
                    ),
                ),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to="imports.importjob",
                    ),
                ),
                (
                    "record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_audit_events",
                        to="records.record",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="importjob",
            index=models.Index(fields=["target_object_type", "state"], name="imports_imp_target__6df508_idx"),
        ),
        migrations.AddIndex(
            model_name="importjob",
            index=models.Index(fields=["created_at"], name="imports_imp_created_2e10b1_idx"),
        ),
        migrations.AddIndex(
            model_name="importauditevent",
            index=models.Index(fields=["record", "action"], name="imports_imp_record__fbf999_idx"),
        ),
        migrations.AddIndex(
            model_name="importauditevent",
            index=models.Index(fields=["created_at"], name="imports_imp_created_d25070_idx"),
        ),
    ]
