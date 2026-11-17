import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0002_attendanceverification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="attendancerecord",
            name="att_qr_before_recorded",
        ),
        migrations.RemoveConstraint(
            model_name="attendancerecord",
            name="att_face_before_recorded",
        ),
        migrations.RemoveConstraint(
            model_name="attendancerecord",
            name="att_face_after_qr",
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="recording_method",
            field=models.CharField(
                choices=[
                    ("dual_verified", "QR and facial verification"),
                    ("manual_exception", "Lecturer-approved manual exception"),
                ],
                db_index=True,
                default="dual_verified",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="qr_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="face_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="recorded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="manual_attendance_records",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="manual_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("consent_withdrawn", "Biometric consent not given or withdrawn"),
                    ("camera_unavailable", "Camera unavailable"),
                    ("accessibility", "Accessibility accommodation"),
                    ("recognition_failed", "Facial verification unsuccessful"),
                    ("technical_issue", "Technical issue"),
                    ("other", "Other approved reason"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="manual_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        recording_method="dual_verified",
                        qr_verified_at__isnull=False,
                        face_verified_at__isnull=False,
                        recorded_by__isnull=True,
                        manual_reason="",
                        manual_notes="",
                    )
                    | Q(
                        recording_method="manual_exception",
                        qr_verified_at__isnull=True,
                        face_verified_at__isnull=True,
                        recorded_by__isnull=False,
                        manual_reason__in=[
                            "consent_withdrawn",
                            "camera_unavailable",
                            "accessibility",
                            "recognition_failed",
                            "technical_issue",
                            "other",
                        ],
                    )
                ),
                name="att_record_method_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(qr_verified_at__lte=F("recorded_at")),
                name="att_qr_before_recorded",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(face_verified_at__lte=F("recorded_at")),
                name="att_face_before_recorded",
            ),
        ),
        migrations.AddConstraint(
            model_name="attendancerecord",
            constraint=models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(face_verified_at__gte=F("qr_verified_at")),
                name="att_face_after_qr",
            ),
        ),
    ]
