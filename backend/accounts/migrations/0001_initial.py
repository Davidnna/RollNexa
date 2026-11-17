from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_existing_profiles(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("accounts", "UserProfile")
    batch = []
    for user in User.objects.all().iterator():
        role = "admin" if user.is_superuser else "student"
        batch.append(UserProfile(user_id=user.pk, role=role))
        if len(batch) >= 500:
            UserProfile.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        UserProfile.objects.bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("admin", "System administrator"), ("lecturer", "Lecturer"), ("student", "Student")], db_index=True, default="student", max_length=20)),
                ("institutional_id", models.CharField(blank=True, max_length=60)),
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("must_change_password", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_attendiq_accounts", to=settings.AUTH_USER_MODEL)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "user profile",
                "verbose_name_plural": "user profiles",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(create_existing_profiles, migrations.RunPython.noop),
    ]
