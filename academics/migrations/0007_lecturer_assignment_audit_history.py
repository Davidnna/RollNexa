import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.utils import timezone


def revoke_assignments_for_inactive_lecturers(apps, schema_editor):
    Assignment = apps.get_model("academics", "CourseLecturerAssignment")
    UserProfile = apps.get_model("accounts", "UserProfile")
    inactive_lecturer_ids = UserProfile.objects.filter(
        role="lecturer", user__is_active=False
    ).values_list("pk", flat=True)
    Assignment.objects.filter(
        lecturer_id__in=inactive_lecturer_ids, is_active=True
    ).update(
        is_active=False,
        removed_at=timezone.now(),
        removal_note="Lecturer account was inactive during the RollNexa 0.5.0 upgrade",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0006_course_offering_provenance"),
        ("accounts", "0003_rename_created_accounts_related_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="courselecturerassignment",
            name="uniq_lecturer_per_course_offering",
        ),
        migrations.AddField(
            model_name="courselecturerassignment",
            name="assigned_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_course_lecturer_assignments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="courselecturerassignment",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="courselecturerassignment",
            name="removed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="courselecturerassignment",
            name="removed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="revoked_course_lecturer_assignments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="courselecturerassignment",
            name="removal_note",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.RunPython(
            revoke_assignments_for_inactive_lecturers,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="courselecturerassignment",
            constraint=models.UniqueConstraint(
                condition=Q(is_active=True),
                fields=("offering", "lecturer"),
                name="uniq_active_lecturer_per_offering",
            ),
        ),
        migrations.AddIndex(
            model_name="courselecturerassignment",
            index=models.Index(
                fields=["lecturer", "is_active"],
                name="lecturer_assign_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="courselecturerassignment",
            index=models.Index(
                fields=["offering", "is_active"],
                name="offering_assign_active_idx",
            ),
        ),
    ]
