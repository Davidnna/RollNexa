import hashlib
import secrets
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import UserProfile
from academics.models import CourseLecturerAssignment, CourseRegistration

from .models import AttendanceRecord, AttendanceSession, AttendanceVerification


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
    AttendanceVerification.objects.filter(
        session=session, status=AttendanceVerification.STATUS_QR_VERIFIED
    ).update(status=AttendanceVerification.STATUS_EXPIRED, updated_at=closed_at)
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
    AttendanceVerification.objects.filter(
        session=session, status=AttendanceVerification.STATUS_QR_VERIFIED
    ).update(status=AttendanceVerification.STATUS_EXPIRED, updated_at=session.cancelled_at)
    return session


@transaction.atomic
def record_verified_attendance(*, verification_id, recorded_at=None):
    """Create a present record only from a persisted, face-verified attempt."""
    moment = recorded_at or timezone.now()
    try:
        verification_reference = AttendanceVerification.objects.only("session_id").get(pk=verification_id)
    except AttendanceVerification.DoesNotExist:
        raise ValidationError("The attendance verification attempt does not exist.")

    try:
        with transaction.atomic():
            session = AttendanceSession.objects.select_for_update().select_related(
                "offering", "offering__course", "offering__programme", "offering__semester"
            ).get(pk=verification_reference.session_id)
            verification = AttendanceVerification.objects.select_for_update().select_related(
                "student__user"
            ).get(pk=verification_id)

            if (
                verification.status != AttendanceVerification.STATUS_FACE_VERIFIED
                or verification.face_verified_at is None
            ):
                raise ValidationError("Both QR Code and facial verification must succeed before attendance can be recorded.")
            if verification.expires_at <= moment:
                raise ValidationError("The attendance verification attempt has expired. Scan the current session QR Code again.")
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

            student_profile = verification.student
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

            qr_verified_at = verification.qr_verified_at
            face_verified_at = verification.face_verified_at
            if not (session.starts_at <= qr_verified_at < session.ends_at):
                raise ValidationError("QR Code verification must occur within the attendance session window.")
            if not (session.starts_at <= face_verified_at < session.ends_at):
                raise ValidationError("Facial verification must occur within the attendance session window.")
            if qr_verified_at > moment or face_verified_at > moment:
                raise ValidationError("Verification timestamps cannot be later than the attendance record.")
            if face_verified_at <= qr_verified_at:
                raise ValidationError("Facial verification must occur after QR Code verification.")

            record = AttendanceRecord(
                session=session,
                student=student_profile,
                recording_method=AttendanceRecord.METHOD_DUAL_VERIFIED,
                qr_verified_at=qr_verified_at,
                face_verified_at=face_verified_at,
                recorded_at=moment,
            )
            record.full_clean()
            record.save()

            verification.status = AttendanceVerification.STATUS_COMPLETED
            verification.save(update_fields=["status", "updated_at"])
            return record
    except IntegrityError as exc:
        raise ValidationError("Attendance has already been recorded for this student and session.") from exc


@transaction.atomic
def complete_attendance_verification(*, verification_id, verified_at=None):
    """Complete a pending attempt after the trusted server-side face verifier succeeds.

    This function is an internal service boundary. It must not be exposed as an API
    that accepts a client-supplied face-success flag or timestamp.
    """
    try:
        verification_reference = AttendanceVerification.objects.only("session_id").get(pk=verification_id)
    except AttendanceVerification.DoesNotExist:
        raise ValidationError("The attendance verification attempt does not exist.")

    session = AttendanceSession.objects.select_for_update().get(pk=verification_reference.session_id)
    verification = AttendanceVerification.objects.select_for_update().select_related(
        "student__user"
    ).get(pk=verification_id)

    if verification.status != AttendanceVerification.STATUS_QR_VERIFIED:
        raise ValidationError("This verification attempt is not awaiting facial verification.")

    moment = verified_at or timezone.now()
    if verification.expires_at <= moment:
        raise ValidationError("The attendance verification attempt has expired. Scan the current session QR Code again.")
    if moment <= verification.qr_verified_at:
        raise ValidationError("Facial verification must occur after QR Code verification.")
    if session.status != AttendanceSession.STATUS_ACTIVE or not session.is_open_at(moment):
        raise ValidationError("This attendance session is no longer open.")

    verification.face_verified_at = moment
    verification.status = AttendanceVerification.STATUS_FACE_VERIFIED
    verification.full_clean()
    verification.save(update_fields=["face_verified_at", "status", "updated_at"])
    return record_verified_attendance(verification_id=verification.pk, recorded_at=moment)


@transaction.atomic
def record_manual_attendance_exception(
    *,
    session_id,
    student_id,
    lecturer_profile,
    reason,
    notes="",
    recorded_at=None,
):
    """Record a lecturer-approved alternative when automated biometrics cannot be used."""
    moment = recorded_at or timezone.now()
    session = AttendanceSession.objects.select_for_update().select_related(
        "offering__programme",
        "offering__course",
    ).get(pk=session_id)

    if session.status != AttendanceSession.STATUS_ACTIVE or not session.is_open_at(moment):
        raise ValidationError("Manual attendance exceptions can only be approved during an active attendance session.")
    if not session.offering.is_active:
        raise ValidationError("The course offering is inactive.")

    if not isinstance(lecturer_profile, UserProfile):
        lecturer_profile = UserProfile.objects.select_related("user").get(pk=lecturer_profile)
    if lecturer_profile.role != UserProfile.ROLE_LECTURER or not lecturer_profile.user.is_active:
        raise ValidationError("An active lecturer account is required to approve a manual attendance exception.")
    assignment = CourseLecturerAssignment.objects.select_for_update().filter(
        offering=session.offering,
        lecturer=lecturer_profile,
        is_active=True,
    ).first()
    if not assignment:
        raise ValidationError("You must have an active teaching assignment for this course offering.")

    if student_id in (None, ""):
        raise ValidationError("Select a registered student.")
    if not isinstance(student_id, UserProfile):
        try:
            student_profile = UserProfile.objects.select_related("user").get(pk=student_id)
        except (UserProfile.DoesNotExist, TypeError, ValueError) as exc:
            raise ValidationError("The selected student account does not exist.") from exc
    else:
        student_profile = student_id

    if student_profile.role != UserProfile.ROLE_STUDENT or not student_profile.user.is_active:
        raise ValidationError("An active student account is required.")
    if (
        student_profile.programme_id != session.offering.programme_id
        or student_profile.current_level != session.offering.level
    ):
        raise ValidationError("The student's programme and level do not match this course offering.")
    if not CourseRegistration.objects.filter(
        offering=session.offering,
        student=student_profile,
        status=CourseRegistration.STATUS_REGISTERED,
    ).exists():
        raise ValidationError("The student must be currently registered for this course offering.")
    if AttendanceRecord.objects.filter(session=session, student=student_profile).exists():
        raise ValidationError("Attendance has already been recorded for this student and session.")

    record = AttendanceRecord(
        session=session,
        student=student_profile,
        recording_method=AttendanceRecord.METHOD_MANUAL_EXCEPTION,
        recorded_by=lecturer_profile.user,
        manual_reason=reason,
        manual_notes=(notes or "").strip(),
        recorded_at=moment,
    )
    record.full_clean()
    try:
        with transaction.atomic():
            record.save()
    except IntegrityError as exc:
        raise ValidationError("Attendance has already been recorded for this student and session.") from exc
    return record


QR_TOKEN_TTL_SECONDS = 60
QR_TOKEN_SIGNING_SALT = "rollnexa.attendance.qr.v1"
QR_VERIFICATION_TTL = timedelta(minutes=5)


@transaction.atomic
def issue_attendance_qr_token(*, session_id, lecturer_profile):
    """Issue a short-lived signed QR token for an assigned lecturer's active session."""
    session = _get_manageable_session(session_id, lecturer_profile)
    moment = timezone.now()

    if session.status != AttendanceSession.STATUS_ACTIVE or not session.is_open_at(moment):
        raise ValidationError("A QR Code can only be issued for an active attendance session within its scheduled window.")
    if not session.offering.is_active:
        raise ValidationError("The course offering is inactive.")

    issued_at = int(moment.timestamp())
    payload = {
        "session_id": session.pk,
        "issued_by": lecturer_profile.user_id,
        "issued_at": issued_at,
        "nonce": secrets.token_urlsafe(12),
    }
    token = signing.dumps(payload, salt=QR_TOKEN_SIGNING_SALT, compress=True)
    expires_at = datetime.fromtimestamp(
        issued_at + QR_TOKEN_TTL_SECONDS,
        tz=datetime_timezone.utc,
    )
    return {
        "token": token,
        "issued_at": datetime.fromtimestamp(issued_at, tz=datetime_timezone.utc),
        "expires_at": min(expires_at, session.ends_at),
        "ttl_seconds": max(0, int((min(expires_at, session.ends_at) - moment).total_seconds())),
        "session": session,
    }


@transaction.atomic
def verify_attendance_qr(*, token, student_profile, at=None):
    """Validate a signed session QR token and create a pending face-verification attempt."""
    if not isinstance(token, str) or not token or len(token) > 512:
        raise ValidationError("The QR Code is invalid or has expired. Scan the current code displayed by your lecturer.")

    try:
        payload = signing.loads(token, salt=QR_TOKEN_SIGNING_SALT, max_age=QR_TOKEN_TTL_SECONDS)
    except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
        raise ValidationError("The QR Code is invalid or has expired. Scan the current code displayed by your lecturer.")

    if not isinstance(payload, dict):
        raise ValidationError("The QR Code payload is invalid.")

    session_id = payload.get("session_id")
    issuer_id = payload.get("issued_by")
    issued_at = payload.get("issued_at")
    nonce = payload.get("nonce")
    if (
        not isinstance(session_id, int)
        or not isinstance(issuer_id, int)
        or not isinstance(issued_at, int)
        or not isinstance(nonce, str)
        or not nonce
    ):
        raise ValidationError("The QR Code payload is invalid.")

    moment = at or timezone.now()
    if moment.timestamp() < issued_at or moment.timestamp() >= issued_at + QR_TOKEN_TTL_SECONDS:
        raise ValidationError("The QR Code is invalid or has expired. Scan the current code displayed by your lecturer.")

    try:
        session = AttendanceSession.objects.select_for_update().select_related(
            "offering", "offering__course", "offering__programme", "offering__semester__session"
        ).get(pk=session_id)
    except AttendanceSession.DoesNotExist:
        raise ValidationError("The QR Code does not identify a valid attendance session.")

    if session.status != AttendanceSession.STATUS_ACTIVE or not session.is_open_at(moment):
        raise ValidationError("This attendance session is not currently open.")
    if not session.offering.is_active:
        raise ValidationError("The course offering is inactive.")
    issuer_assignment = CourseLecturerAssignment.objects.select_for_update().filter(
        offering=session.offering,
        lecturer__user_id=issuer_id,
        lecturer__role=UserProfile.ROLE_LECTURER,
        lecturer__user__is_active=True,
        is_active=True,
    ).first()
    if not issuer_assignment:
        raise ValidationError("The lecturer who issued this QR Code is no longer authorised for this course offering.")

    if not isinstance(student_profile, UserProfile):
        student_profile = UserProfile.objects.select_related("user").get(pk=student_profile)
    if student_profile.role != UserProfile.ROLE_STUDENT or not student_profile.user.is_active:
        raise ValidationError("An active student account is required to verify attendance.")
    if (
        student_profile.programme_id != session.offering.programme_id
        or student_profile.current_level != session.offering.level
    ):
        raise ValidationError("Your current programme and level do not match this course offering.")
    registration = CourseRegistration.objects.select_for_update().filter(
        offering=session.offering,
        student=student_profile,
        status=CourseRegistration.STATUS_REGISTERED,
    ).first()
    if not registration:
        raise ValidationError("You are not currently registered for this course offering.")
    if AttendanceRecord.objects.filter(session=session, student=student_profile).exists():
        raise ValidationError("Attendance has already been recorded for this session.")

    pending = AttendanceVerification.objects.select_for_update().filter(
        session=session,
        student=student_profile,
        status=AttendanceVerification.STATUS_QR_VERIFIED,
    ).first()
    if pending and pending.expires_at > moment:
        return pending, True
    if pending:
        pending.status = AttendanceVerification.STATUS_EXPIRED
        pending.save(update_fields=["status", "updated_at"])

    expires_at = min(moment + QR_VERIFICATION_TTL, session.ends_at)
    verification = AttendanceVerification(
        session=session,
        student=student_profile,
        qr_token_fingerprint=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        qr_verified_at=moment,
        expires_at=expires_at,
        status=AttendanceVerification.STATUS_QR_VERIFIED,
    )
    verification.full_clean()
    verification.save()
    return verification, False
