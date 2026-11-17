import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0003_rename_created_accounts_related_name"),
        ("attendance", "0003_manual_attendance_method"),
    ]

    operations = [
        migrations.CreateModel(
            name="BiometricConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("granted", "Granted"), ("withdrawn", "Withdrawn")], db_index=True, max_length=12)),
                ("policy_version", models.CharField(max_length=32)),
                ("granted_at", models.DateTimeField(blank=True, null=True)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_consent", to="accounts.userprofile")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="BiometricConsentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("granted", "Consent granted"), ("withdrawn", "Consent withdrawn")], max_length=12)),
                ("policy_version", models.CharField(max_length=32)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_consent_events", to="accounts.userprofile")),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.CreateModel(
            name="FaceEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("encrypted_template", models.BinaryField()),
                ("encryption_key_version", models.CharField(default="v1", max_length=16)),
                ("model_version", models.CharField(max_length=64)),
                ("template_version", models.PositiveSmallIntegerField(default=1)),
                ("sample_count", models.PositiveSmallIntegerField(default=3)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("enrolled_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_verified_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="face_enrollment", to="accounts.userprofile")),
            ],
            options={"ordering": ["-enrolled_at"]},
        ),
        migrations.CreateModel(
            name="BiometricChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("direction", models.CharField(choices=[("turn_left", "Turn toward the left side of the screen"), ("turn_right", "Turn toward the right side of the screen")], max_length=12)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_challenges", to="accounts.userprofile")),
                ("verification", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_challenges", to="attendance.attendanceverification")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BiometricVerificationAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("result", models.CharField(choices=[("passed", "Passed"), ("failed", "Failed")], db_index=True, max_length=8)),
                ("failure_code", models.CharField(blank=True, max_length=40)),
                ("liveness_passed", models.BooleanField(default=False)),
                ("model_version", models.CharField(max_length=64)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("challenge", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="verification_attempt", to="biometrics.biometricchallenge")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_verification_attempts", to="accounts.userprofile")),
                ("verification", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="biometric_attempts", to="attendance.attendanceverification")),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
        migrations.AddConstraint(
            model_name="biometricconsent",
            constraint=models.CheckConstraint(
                condition=(
                    Q(status="granted", granted_at__isnull=False, withdrawn_at__isnull=True)
                    | Q(status="withdrawn", withdrawn_at__isnull=False)
                ),
                name="biometric_consent_state_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="biometricchallenge",
            constraint=models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")),
                name="biometric_challenge_expiry_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="biometricconsentevent",
            index=models.Index(fields=["student", "occurred_at"], name="bio_consent_student_idx"),
        ),
        migrations.AddIndex(
            model_name="biometricchallenge",
            index=models.Index(fields=["verification", "student", "created_at"], name="bio_challenge_verify_idx"),
        ),
        migrations.AddIndex(
            model_name="biometricverificationattempt",
            index=models.Index(fields=["student", "occurred_at"], name="bio_attempt_student_idx"),
        ),
        migrations.AddIndex(
            model_name="biometricverificationattempt",
            index=models.Index(fields=["verification", "result"], name="bio_attempt_verify_idx"),
        ),
    ]
