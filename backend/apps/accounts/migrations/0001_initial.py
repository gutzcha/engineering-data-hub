# ===
# File Summary
# Path: backend\apps\accounts\migrations\0001_initial.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: Migration
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ObjectPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role_name", models.CharField(max_length=120)),
                ("object_type_key", models.CharField(max_length=120)),
                ("can_view", models.BooleanField(default=True)),
                ("can_create", models.BooleanField(default=False)),
                ("can_edit", models.BooleanField(default=False)),
                ("can_release", models.BooleanField(default=False)),
                ("can_admin", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["object_type_key", "role_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="objectpermission",
            constraint=models.UniqueConstraint(
                fields=("role_name", "object_type_key"),
                name="unique_role_object_permission",
            ),
        ),
    ]

