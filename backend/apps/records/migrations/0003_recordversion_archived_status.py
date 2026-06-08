from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("records", "0002_recordobjecttypelock"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("released", "Released"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="RecordVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_number", models.PositiveIntegerField()),
                ("snapshot", models.JSONField(default=dict)),
                ("change_note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="record_versions_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="records.record",
                    ),
                ),
            ],
            options={
                "ordering": ["-version_number", "-created_at"],
                "indexes": [
                    models.Index(fields=["record", "version_number"], name="records_rec_record__d36bd7_idx"),
                    models.Index(fields=["created_at"], name="records_rec_created_e141a1_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="recordversion",
            constraint=models.UniqueConstraint(
                fields=("record", "version_number"),
                name="unique_record_version_number",
            ),
        ),
    ]
