import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0003_rename_created_accounts_related_name"),
        ("academics", "0007_lecturer_assignment_audit_history"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_sessions", to="academics.courseoffering")),
                ("title", models.CharField(blank=True, help_text="Optional label, such as Lecture 1 or Week 3 tutorial.", max_length=120)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("active", "Active"), ("closed", "Closed"), ("cancelled", "Cancelled")], db_index=True, default="scheduled", max_length=12)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_attendance_sessions", to=settings.AUTH_USER_MODEL)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("activated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="activated_attendance_sessions", to=settings.AUTH_USER_MODEL)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="closed_attendance_sessions", to=settings.AUTH_USER_MODEL)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cancelled_attendance_sessions", to=settings.AUTH_USER_MODEL)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-starts_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AttendanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="records", to="attendance.attendancesession")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_records", to="accounts.userprofile")),
                ("qr_verified_at", models.DateTimeField()),
                ("face_verified_at", models.DateTimeField()),
                ("recorded_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={"ordering": ["-recorded_at", "student__user__last_name", "student__user__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="attendancesession",
            constraint=models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="att_session_end_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancesession",
            constraint=models.CheckConstraint(
                condition=(
                    Q(status="scheduled", activated_at__isnull=True, activated_by__isnull=True, closed_at__isnull=True, closed_by__isnull=True, cancelled_at__isnull=True, cancelled_by__isnull=True)
                    | Q(status="active", activated_at__isnull=False, activated_by__isnull=False, closed_at__isnull=True, closed_by__isnull=True, cancelled_at__isnull=True, cancelled_by__isnull=True)
                    | Q(status="closed", activated_at__isnull=False, activated_by__isnull=False, closed_at__isnull=False, closed_by__isnull=False, closed_at__gte=F("activated_at"), cancelled_at__isnull=True, cancelled_by__isnull=True)
                    | Q(status="cancelled", activated_at__isnull=True, activated_by__isnull=True, closed_at__isnull=True, closed_by__isnull=True, cancelled_at__isnull=False, cancelled_by__isnull=False)
                ),
                name="att_session_state_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.UniqueConstraint(fields=("session", "student"), name="uniq_attendance_record_per_student_session"),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(condition=Q(qr_verified_at__lte=F("recorded_at")), name="att_qr_before_recorded"),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(condition=Q(face_verified_at__lte=F("recorded_at")), name="att_face_before_recorded"),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(condition=Q(face_verified_at__gte=F("qr_verified_at")), name="att_face_after_qr"),
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["offering", "status"], name="att_sess_offer_status_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(fields=["offering", "starts_at", "ends_at"], name="att_sess_window_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancerecord",
            index=models.Index(fields=["student", "recorded_at"], name="att_record_student_time_idx"),
        ),
    ]
