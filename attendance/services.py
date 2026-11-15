from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import UserProfile
from academics.models import CourseLecturerAssignment, CourseRegistration

from .models import AttendanceRecord, AttendanceSession


def _get_manageable_session(session_id, lecturer_profile):
    session = AttendanceSession.objects.select_for_update().select_related(
        "offering"
    ).get(pk=session_id, offering__is_active=True)
    assignment = CourseLecturerAssignment.objects.select_for_update().filter(
        offering=session.offering,
        lecturer=lecturer_profile,
        is_active=True,
    ).first()
    if not assignment:
        raise AttendanceSession.DoesNotExist
    return session


@transaction.atomic
def create_attendance_session(*, offering_id, created_by, title, starts_at, ends_at, notes=""):
    """Create a scheduled session while serialising creation for its offering."""
    from academics.models import CourseOffering

    offering = CourseOffering.objects.select_for_update().get(pk=offering_id)
    lecturer_profile = UserProfile.objects.filter(
        user=created_by, role=UserProfile.ROLE_LECTURER, user__is_active=True
    ).first()
    if not lecturer_profile:
        raise ValidationError("An active lecturer account must create the attendance session.")
    assignment = CourseLecturerAssignment.objects.select_for_update().filter(
        offering=offering, lecturer=lecturer_profile, is_active=True
    ).first()
    if not assignment:
        raise ValidationError("You must have an active teaching assignment for this course offering.")
    session = AttendanceSession(
        offering=offering,
        created_by=created_by,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        notes=notes,
    )
    session.full_clean()
    session.save()
    return session


@transaction.atomic
def activate_attendance_session(*, session_id, lecturer_profile, at=None):
    session = _get_manageable_session(session_id, lecturer_profile)
    moment = at or timezone.now()

    if session.status != AttendanceSession.STATUS_SCHEDULED:
        raise ValidationError("Only scheduled attendance sessions can be activated.")
    if moment < session.starts_at:
        raise ValidationError("This attendance session is scheduled to start later.")
    if moment >= session.ends_at:
        raise ValidationError("This attendance session has already passed its end time and cannot be activated.")

    session.status = AttendanceSession.STATUS_ACTIVE
    session.activated_at = moment
    session.activated_by = lecturer_profile.user
    session.save(update_fields=["status", "activated_at", "activated_by", "updated_at"])
    return session


@transaction.atomic
def close_attendance_session(*, session_id, lecturer_profile, at=None):
    session = _get_manageable_session(session_id, lecturer_profile)
    if session.status != AttendanceSession.STATUS_ACTIVE:
        raise ValidationError("Only active attendance sessions can be closed.")

    closed_at = at or timezone.now()
    if session.activated_at and closed_at < session.activated_at:
        raise ValidationError("A session cannot be closed before it was activated.")
    session.status = AttendanceSession.STATUS_CLOSED
    session.closed_at = closed_at
    session.closed_by = lecturer_profile.user
    session.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
    return session


@transaction.atomic
def cancel_attendance_session(*, session_id, lecturer_profile, at=None):
    session = _get_manageable_session(session_id, lecturer_profile)
    if session.status != AttendanceSession.STATUS_SCHEDULED:
        raise ValidationError("Only scheduled attendance sessions can be cancelled. Close an active session instead.")

    session.status = AttendanceSession.STATUS_CANCELLED
    session.cancelled_at = at or timezone.now()
    session.cancelled_by = lecturer_profile.user
    session.save(update_fields=["status", "cancelled_at", "cancelled_by", "updated_at"])
    return session


def record_verified_attendance(
    *, session_id, student_profile, qr_verified_at, face_verified_at,
    qr_verified=False, face_verified=False, recorded_at=None
):
    """Record presence only after the QR and face verifiers both report success."""
    if qr_verified is not True or face_verified is not True:
        raise ValidationError("Both QR Code verification and facial recognition must succeed before attendance can be recorded.")
    if qr_verified_at is None or face_verified_at is None:
        raise ValidationError("Both successful verification timestamps are required to record attendance.")

    moment = recorded_at or timezone.now()
    try:
        with transaction.atomic():
            session = AttendanceSession.objects.select_for_update().select_related(
                "offering", "offering__course", "offering__programme", "offering__semester"
            ).get(pk=session_id)

            if session.status != AttendanceSession.STATUS_ACTIVE or not session.is_open_at(moment):
                raise ValidationError("This attendance session is not currently open.")
            if not session.offering.is_active:
                raise ValidationError("The course offering is inactive.")
            active_assignment = CourseLecturerAssignment.objects.select_for_update().filter(
                offering=session.offering,
                is_active=True,
                lecturer__role=UserProfile.ROLE_LECTURER,
                lecturer__user__is_active=True,
            ).first()
            if not active_assignment:
                raise ValidationError("The course offering has no active lecturer assignment; attendance verification is unavailable.")

            if not isinstance(student_profile, UserProfile):
                student_profile = UserProfile.objects.select_related("user").get(pk=student_profile)
            if student_profile.role != UserProfile.ROLE_STUDENT or not student_profile.user.is_active:
                raise ValidationError("An active student account is required to record attendance.")
            if (
                student_profile.programme_id != session.offering.programme_id
                or student_profile.current_level != session.offering.level
            ):
                raise ValidationError("The student's current programme and level must match the course offering.")

            registration = CourseRegistration.objects.select_for_update().filter(
                offering=session.offering,
                student=student_profile,
                status=CourseRegistration.STATUS_REGISTERED,
            ).first()
            if not registration:
                raise ValidationError("The student is not currently registered for this course offering.")

            if not (session.starts_at <= qr_verified_at < session.ends_at):
                raise ValidationError("QR Code verification must occur within the attendance session window.")
            if not (session.starts_at <= face_verified_at < session.ends_at):
                raise ValidationError("Facial verification must occur within the attendance session window.")
            if qr_verified_at > moment or face_verified_at > moment:
                raise ValidationError("Verification timestamps cannot be later than the attendance record.")
            if face_verified_at < qr_verified_at:
                raise ValidationError("Facial verification must occur after QR Code verification.")

            record = AttendanceRecord(
                session=session,
                student=student_profile,
                qr_verified_at=qr_verified_at,
                face_verified_at=face_verified_at,
                recorded_at=moment,
            )
            record.full_clean()
            record.save()
            return record
    except IntegrityError as exc:
        raise ValidationError("Attendance has already been recorded for this student and session.") from exc
