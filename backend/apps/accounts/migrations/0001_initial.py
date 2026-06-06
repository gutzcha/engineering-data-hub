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
