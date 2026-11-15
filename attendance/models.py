from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


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
    """A present record created only after both required checks succeed."""

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
    qr_verified_at = models.DateTimeField()
    face_verified_at = models.DateTimeField()
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at", "student__user__last_name", "student__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="uniq_attendance_record_per_student_session",
            ),
            models.CheckConstraint(
                condition=Q(qr_verified_at__lte=F("recorded_at")),
                name="att_qr_before_recorded",
            ),
            models.CheckConstraint(
                condition=Q(face_verified_at__lte=F("recorded_at")),
                name="att_face_before_recorded",
            ),
            models.CheckConstraint(
                condition=Q(face_verified_at__gte=F("qr_verified_at")),
                name="att_face_after_qr",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "recorded_at"], name="att_record_student_time_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.student_id:
            from accounts.models import UserProfile

            if self.student.role != UserProfile.ROLE_STUDENT:
                errors["student"] = "Only student accounts can have attendance records."
            elif not self.student.user.is_active:
                errors["student"] = "An inactive student cannot be marked present."

        if self.session_id:
            if self.session.status != AttendanceSession.STATUS_ACTIVE:
                errors["session"] = "Attendance can only be recorded for an active session."
            if self.recorded_at and not self.session.is_open_at(self.recorded_at):
                errors["recorded_at"] = "The attendance record must fall within the active session window."
            for field_name in ("qr_verified_at", "face_verified_at"):
                verified_at = getattr(self, field_name)
                if verified_at and not (self.session.starts_at <= verified_at < self.session.ends_at):
                    errors[field_name] = "Verification must occur within the attendance session window."
                if verified_at and self.recorded_at and verified_at > self.recorded_at:
                    errors[field_name] = "Verification cannot occur after the attendance record is recorded."
            if self.qr_verified_at and self.face_verified_at and self.face_verified_at < self.qr_verified_at:
                errors["face_verified_at"] = "Facial verification must occur after QR Code verification."

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
        return f"{self.student.user.get_username()} — {self.session}"
