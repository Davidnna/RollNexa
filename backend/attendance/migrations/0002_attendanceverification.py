import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_rename_created_accounts_related_name"),
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceVerification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("qr_token_fingerprint", models.CharField(max_length=64)),
                ("qr_verified_at", models.DateTimeField()),
                ("face_verified_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("qr_verified", "QR verified; face check pending"),
                            ("face_verified", "Face verified"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="qr_verified",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verifications",
                        to="attendance.attendancesession",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attendance_verifications",
                        to="accounts.userprofile",
                    ),
                ),
            ],
            options={"ordering": ["-qr_verified_at"]},
        ),
        migrations.AddConstraint(
            model_name="attendanceverification",
            constraint=models.CheckConstraint(
                condition=Q(expires_at__gt=F("qr_verified_at")),
                name="att_verify_expiry_after_qr",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendanceverification",
            constraint=models.CheckConstraint(
                condition=(
                    Q(status="qr_verified", face_verified_at__isnull=True)
                    | Q(status__in=["face_verified", "completed"], face_verified_at__isnull=False)
                    | Q(status__in=["failed", "expired"])
                ),
                name="att_verify_face_state_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendanceverification",
            constraint=models.CheckConstraint(
                condition=Q(face_verified_at__isnull=True) | Q(face_verified_at__gte=F("qr_verified_at")),
                name="att_verify_face_after_qr",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendanceverification",
            constraint=models.UniqueConstraint(
                condition=Q(status="qr_verified"),
                fields=("session", "student"),
                name="uniq_pending_att_verify_per_student",
            ),
        ),
        migrations.AddIndex(
            model_name="attendanceverification",
            index=models.Index(
                fields=["session", "student", "status"],
                name="att_verify_session_student_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="attendanceverification",
            index=models.Index(fields=["expires_at"], name="att_verify_expiry_idx"),
        ),
    ]
