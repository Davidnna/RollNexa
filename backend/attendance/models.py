import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


MANUAL_ATTENDANCE_REASON_CONSENT_WITHDRAWN = "consent_withdrawn"
MANUAL_ATTENDANCE_REASON_CAMERA_UNAVAILABLE = "camera_unavailable"
MANUAL_ATTENDANCE_REASON_ACCESSIBILITY = "accessibility"
MANUAL_ATTENDANCE_REASON_RECOGNITION_FAILED = "recognition_failed"
MANUAL_ATTENDANCE_REASON_TECHNICAL_ISSUE = "technical_issue"
MANUAL_ATTENDANCE_REASON_OTHER = "other"
MANUAL_ATTENDANCE_REASON_CHOICES = [
    (MANUAL_ATTENDANCE_REASON_CONSENT_WITHDRAWN, "Biometric consent not given or withdrawn"),
    (MANUAL_ATTENDANCE_REASON_CAMERA_UNAVAILABLE, "Camera unavailable"),
    (MANUAL_ATTENDANCE_REASON_ACCESSIBILITY, "Accessibility accommodation"),
    (MANUAL_ATTENDANCE_REASON_RECOGNITION_FAILED, "Facial verification unsuccessful"),
    (MANUAL_ATTENDANCE_REASON_TECHNICAL_ISSUE, "Technical issue"),
    (MANUAL_ATTENDANCE_REASON_OTHER, "Other approved reason"),
]


class AttendanceSession(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )
    title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional label, such as Lecture 1 or Week 3 tutorial.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_attendance_sessions",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activated_attendance_sessions",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_attendance_sessions",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_attendance_sessions",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="att_session_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="scheduled",
                        activated_at__isnull=True,
                        activated_by__isnull=True,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                        cancelled_at__isnull=True,
                        cancelled_by__isnull=True,
                    )
                    | Q(
                        status="active",
                        activated_at__isnull=False,
                        activated_by__isnull=False,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                        cancelled_at__isnull=True,
                        cancelled_by__isnull=True,
                    )
                    | Q(
                        status="closed",
                        activated_at__isnull=False,
                        activated_by__isnull=False,
                        closed_at__isnull=False,
                        closed_by__isnull=False,
                        closed_at__gte=F("activated_at"),
                        cancelled_at__isnull=True,
                        cancelled_by__isnull=True,
                    )
                    | Q(
                        status="cancelled",
                        activated_at__isnull=True,
                        activated_by__isnull=True,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                        cancelled_at__isnull=False,
                        cancelled_by__isnull=False,
                    )
                ),
                name="att_session_state_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["offering", "status"], name="att_sess_offer_status_idx"),
            models.Index(fields=["offering", "starts_at", "ends_at"], name="att_sess_window_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors["ends_at"] = "The session end time must be later than its start time."

        if self.offering_id:
            offering = self.offering
            if not offering.is_active:
                errors["offering"] = "Only active course offerings can have attendance sessions."
            elif (
                not offering.course.is_active
                or not offering.course.department.is_active
                or not offering.course.department.faculty.is_active
                or not offering.programme.is_active
                or not offering.programme.department.is_active
                or not offering.programme.department.faculty.is_active
                or not offering.semester.is_active
                or not offering.semester.session.is_active
            ):
                errors["offering"] = "The course offering and its academic records must be active."

            if self.created_by_id:
                from accounts.models import UserProfile
                from academics.models import CourseLecturerAssignment

                lecturer_profile = UserProfile.objects.filter(
                    user_id=self.created_by_id,
                    role=UserProfile.ROLE_LECTURER,
                    user__is_active=True,
                ).first()
                if not lecturer_profile:
                    errors["created_by"] = "An active lecturer account must create the attendance session."
                elif not CourseLecturerAssignment.objects.filter(
                    offering_id=self.offering_id,
                    lecturer=lecturer_profile,
                    is_active=True,
                ).exists():
                    errors["created_by"] = "The lecturer must have an active teaching assignment for this course offering."

            if self.starts_at and self.ends_at:
                overlapping = AttendanceSession.objects.filter(
                    offering_id=self.offering_id,
                    starts_at__lt=self.ends_at,
                    ends_at__gt=self.starts_at,
                ).exclude(status=self.STATUS_CANCELLED)
                if self.pk:
                    overlapping = overlapping.exclude(pk=self.pk)
                if overlapping.exists():
                    errors["starts_at"] = "This time window overlaps another non-cancelled attendance session for the same course offering."

        if errors:
            raise ValidationError(errors)

    @property
    def is_expired(self):
        return self.status == self.STATUS_ACTIVE and timezone.now() >= self.ends_at

    @property
    def is_open(self):
        return self.is_open_at(timezone.now())

    def is_open_at(self, moment):
        return (
            self.status == self.STATUS_ACTIVE
            and self.starts_at <= moment < self.ends_at
        )

    def __str__(self):
        label = self.title or "Attendance session"
        return f"{self.offering.course.code} — {label} ({self.starts_at:%d %b %Y %H:%M})"


class AttendanceRecord(models.Model):
    METHOD_DUAL_VERIFIED = "dual_verified"
    METHOD_MANUAL_EXCEPTION = "manual_exception"
    METHOD_CHOICES = [
        (METHOD_DUAL_VERIFIED, "QR and facial verification"),
        (METHOD_MANUAL_EXCEPTION, "Lecturer-approved manual exception"),
    ]

    MANUAL_REASON_CONSENT_WITHDRAWN = MANUAL_ATTENDANCE_REASON_CONSENT_WITHDRAWN
    MANUAL_REASON_CAMERA_UNAVAILABLE = MANUAL_ATTENDANCE_REASON_CAMERA_UNAVAILABLE
    MANUAL_REASON_ACCESSIBILITY = MANUAL_ATTENDANCE_REASON_ACCESSIBILITY
    MANUAL_REASON_RECOGNITION_FAILED = MANUAL_ATTENDANCE_REASON_RECOGNITION_FAILED
    MANUAL_REASON_TECHNICAL_ISSUE = MANUAL_ATTENDANCE_REASON_TECHNICAL_ISSUE
    MANUAL_REASON_OTHER = MANUAL_ATTENDANCE_REASON_OTHER
    MANUAL_REASON_CHOICES = MANUAL_ATTENDANCE_REASON_CHOICES

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.PROTECT,
        related_name="records",
    )
    student = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    recording_method = models.CharField(
        max_length=24,
        choices=METHOD_CHOICES,
        default=METHOD_DUAL_VERIFIED,
        db_index=True,
    )
    qr_verified_at = models.DateTimeField(null=True, blank=True)
    face_verified_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="manual_attendance_records",
    )
    manual_reason = models.CharField(
        max_length=32,
        choices=MANUAL_REASON_CHOICES,
        blank=True,
    )
    manual_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at", "student__user__last_name", "student__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="uniq_attendance_record_per_student_session",
            ),
            models.CheckConstraint(
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
                        manual_reason__in=[choice[0] for choice in MANUAL_ATTENDANCE_REASON_CHOICES],
                    )
                ),
                name="att_record_method_valid",
            ),
            models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(qr_verified_at__lte=F("recorded_at")),
                name="att_qr_before_recorded",
            ),
            models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(face_verified_at__lte=F("recorded_at")),
                name="att_face_before_recorded",
            ),
            models.CheckConstraint(
                condition=Q(recording_method="manual_exception") | Q(face_verified_at__gte=F("qr_verified_at")),
                name="att_face_after_qr",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "recorded_at"], name="att_record_student_time_idx"),
        ]

    def clean(self):
        super().clean()
        from accounts.models import UserProfile

        errors = {}

        if self.student_id:
            if self.student.role != UserProfile.ROLE_STUDENT:
                errors["student"] = "Only student accounts can have attendance records."
            elif not self.student.user.is_active:
                errors["student"] = "An inactive student cannot be marked present."

        if self.session_id:
            if self.session.status != AttendanceSession.STATUS_ACTIVE:
                errors["session"] = "Attendance can only be recorded for an active session."
            if self.recorded_at and not self.session.is_open_at(self.recorded_at):
                errors["recorded_at"] = "The attendance record must fall within the active session window."

            if self.recording_method == self.METHOD_DUAL_VERIFIED:
                if not self.qr_verified_at or not self.face_verified_at:
                    errors["recording_method"] = "Both QR Code and facial verification timestamps are required."
                if self.recorded_by_id or self.manual_reason or self.manual_notes:
                    errors["recording_method"] = "Automated attendance cannot contain manual-exception details."
                for field_name in ("qr_verified_at", "face_verified_at"):
                    verified_at = getattr(self, field_name)
                    if verified_at and not (self.session.starts_at <= verified_at < self.session.ends_at):
                        errors[field_name] = "Verification must occur within the attendance session window."
                    if verified_at and self.recorded_at and verified_at > self.recorded_at:
                        errors[field_name] = "Verification cannot occur after the attendance record is recorded."
                if self.qr_verified_at and self.face_verified_at and self.face_verified_at < self.qr_verified_at:
                    errors["face_verified_at"] = "Facial verification must occur after QR Code verification."
            elif self.recording_method == self.METHOD_MANUAL_EXCEPTION:
                if self.qr_verified_at or self.face_verified_at:
                    errors["recording_method"] = "Manual attendance exceptions must not claim automated verification timestamps."
                if not self.recorded_by_id:
                    errors["recorded_by"] = "A lecturer must approve a manual attendance exception."
                if self.manual_reason not in dict(self.MANUAL_REASON_CHOICES):
                    errors["manual_reason"] = "Select a valid reason for the manual attendance exception."
                if self.manual_reason == self.MANUAL_REASON_OTHER and not self.manual_notes.strip():
                    errors["manual_notes"] = "Provide a reason when selecting Other."
                if self.recorded_by_id:
                    from academics.models import CourseLecturerAssignment

                    lecturer_profile = UserProfile.objects.filter(
                        user_id=self.recorded_by_id,
                        role=UserProfile.ROLE_LECTURER,
                        user__is_active=True,
                    ).first()
                    if not lecturer_profile or not CourseLecturerAssignment.objects.filter(
                        offering_id=self.session.offering_id,
                        lecturer=lecturer_profile,
                        is_active=True,
                    ).exists():
                        errors["recorded_by"] = "Only an active lecturer assigned to this course can approve the exception."
            else:
                errors["recording_method"] = "Select a valid attendance recording method."

            if self.student_id and not errors.get("student"):
                from academics.models import CourseRegistration

                if (
                    self.student.programme_id != self.session.offering.programme_id
                    or self.student.current_level != self.session.offering.level
                ):
                    errors["student"] = "The student's current programme and level must match the course offering."
                elif not CourseRegistration.objects.filter(
                    offering_id=self.session.offering_id,
                    student_id=self.student_id,
                    status=CourseRegistration.STATUS_REGISTERED,
                ).exists():
                    errors["student"] = "The student must be currently registered for this course offering."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        method = "manual exception" if self.recording_method == self.METHOD_MANUAL_EXCEPTION else "dual verified"
        return f"{self.student.user.get_username()} — {self.session} ({method})"


class AttendanceVerification(models.Model):
    """Tracks the QR stage while the required facial check is pending."""

    STATUS_QR_VERIFIED = "qr_verified"
    STATUS_FACE_VERIFIED = "face_verified"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_QR_VERIFIED, "QR verified; face check pending"),
        (STATUS_FACE_VERIFIED, "Face verified"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_EXPIRED, "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.PROTECT,
        related_name="verifications",
    )
    student = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.PROTECT,
        related_name="attendance_verifications",
    )
    qr_token_fingerprint = models.CharField(max_length=64)
    qr_verified_at = models.DateTimeField()
    face_verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_QR_VERIFIED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-qr_verified_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("qr_verified_at")),
                name="att_verify_expiry_after_qr",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="qr_verified", face_verified_at__isnull=True)
                    | Q(status__in=["face_verified", "completed"], face_verified_at__isnull=False)
                    | Q(status__in=["failed", "expired"])
                ),
                name="att_verify_face_state_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(face_verified_at__isnull=True)
                    | Q(face_verified_at__gte=F("qr_verified_at"))
                ),
                name="att_verify_face_after_qr",
            ),
            models.UniqueConstraint(
                fields=["session", "student"],
                condition=Q(status="qr_verified"),
                name="uniq_pending_att_verify_per_student",
            ),
        ]
        indexes = [
            models.Index(
                fields=["session", "student", "status"],
                name="att_verify_session_student_idx",
            ),
            models.Index(fields=["expires_at"], name="att_verify_expiry_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if len(self.qr_token_fingerprint) != 64:
            errors["qr_token_fingerprint"] = "The QR token fingerprint is invalid."

        if self.student_id:
            from accounts.models import UserProfile
            from academics.models import CourseRegistration

            if self.student.role != UserProfile.ROLE_STUDENT or not self.student.user.is_active:
                errors["student"] = "An active student account is required for attendance verification."
            elif self.session_id:
                offering = self.session.offering
                if (
                    self.student.programme_id != offering.programme_id
                    or self.student.current_level != offering.level
                ):
                    errors["student"] = "The student's current programme and level must match the course offering."
                elif not CourseRegistration.objects.filter(
                    offering=offering,
                    student=self.student,
                    status=CourseRegistration.STATUS_REGISTERED,
                ).exists():
                    errors["student"] = "The student must be currently registered for this course offering."

        if self.session_id and self.qr_verified_at:
            if not (self.session.starts_at <= self.qr_verified_at < self.session.ends_at):
                errors["qr_verified_at"] = "QR verification must occur within the attendance session window."

        if self.expires_at and self.session_id and self.expires_at > self.session.ends_at:
            errors["expires_at"] = "The verification cannot remain valid beyond the attendance session."

        if self.face_verified_at and self.expires_at and self.face_verified_at > self.expires_at:
            errors["face_verified_at"] = "Facial verification must occur before the verification expires."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student.user.get_username()} — {self.session} ({self.get_status_display()})"
