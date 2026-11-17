import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class BiometricConsent(models.Model):
    STATUS_GRANTED = "granted"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = [
        (STATUS_GRANTED, "Granted"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    ]

    student = models.OneToOneField(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="biometric_consent",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, db_index=True)
    policy_version = models.CharField(max_length=32)
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status="granted", granted_at__isnull=False, withdrawn_at__isnull=True)
                    | Q(status="withdrawn", withdrawn_at__isnull=False)
                ),
                name="biometric_consent_state_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != "student":
            raise ValidationError({"student": "Biometric consent can only be recorded for a student account."})

    @property
    def is_granted(self):
        return self.status == self.STATUS_GRANTED

    def __str__(self):
        return f"Biometric consent for profile {self.student_id}: {self.status}"


class BiometricConsentEvent(models.Model):
    ACTION_GRANTED = "granted"
    ACTION_WITHDRAWN = "withdrawn"
    ACTION_CHOICES = [
        (ACTION_GRANTED, "Consent granted"),
        (ACTION_WITHDRAWN, "Consent withdrawn"),
    ]

    student = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="biometric_consent_events",
    )
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    policy_version = models.CharField(max_length=32)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["student", "occurred_at"], name="bio_consent_student_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} — profile {self.student_id}"


class FaceEnrollment(models.Model):
    student = models.OneToOneField(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="face_enrollment",
    )
    encrypted_template = models.BinaryField()
    encryption_key_version = models.CharField(max_length=16, default="v1")
    model_version = models.CharField(max_length=64)
    template_version = models.PositiveSmallIntegerField(default=1)
    sample_count = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True, db_index=True)
    enrolled_at = models.DateTimeField(default=timezone.now)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrolled_at"]

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != "student":
            raise ValidationError({"student": "Only a student account can have a facial template."})
        consent = None
        if self.student_id:
            try:
                consent = self.student.biometric_consent
            except BiometricConsent.DoesNotExist:
                consent = None
        current_policy = getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0")
        if self.is_active and (
            not consent
            or not consent.is_granted
            or consent.policy_version != current_policy
        ):
            raise ValidationError("An active facial template requires current biometric consent.")

    def __str__(self):
        return f"Face template for profile {self.student_id}"


class BiometricChallenge(models.Model):
    DIRECTION_LEFT = "turn_left"
    DIRECTION_RIGHT = "turn_right"
    DIRECTION_CHOICES = [
        (DIRECTION_LEFT, "Turn toward the left side of the screen"),
        (DIRECTION_RIGHT, "Turn toward the right side of the screen"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verification = models.ForeignKey(
        "attendance.AttendanceVerification",
        on_delete=models.PROTECT,
        related_name="biometric_challenges",
    )
    student = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="biometric_challenges",
    )
    direction = models.CharField(max_length=12, choices=DIRECTION_CHOICES)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")),
                name="biometric_challenge_expiry_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["verification", "student", "created_at"], name="bio_challenge_verify_idx"),
        ]

    def __str__(self):
        return f"Face challenge {self.direction} for verification {self.verification_id}"


class BiometricVerificationAttempt(models.Model):
    RESULT_PASSED = "passed"
    RESULT_FAILED = "failed"
    RESULT_CHOICES = [
        (RESULT_PASSED, "Passed"),
        (RESULT_FAILED, "Failed"),
    ]

    verification = models.ForeignKey(
        "attendance.AttendanceVerification",
        on_delete=models.PROTECT,
        related_name="biometric_attempts",
    )
    student = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="biometric_verification_attempts",
    )
    challenge = models.OneToOneField(
        BiometricChallenge,
        on_delete=models.PROTECT,
        related_name="verification_attempt",
    )
    result = models.CharField(max_length=8, choices=RESULT_CHOICES, db_index=True)
    failure_code = models.CharField(max_length=40, blank=True)
    liveness_passed = models.BooleanField(default=False)
    model_version = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["student", "occurred_at"], name="bio_attempt_student_idx"),
            models.Index(fields=["verification", "result"], name="bio_attempt_verify_idx"),
        ]

    def __str__(self):
        return f"Biometric {self.result} — verification {self.verification_id}"
