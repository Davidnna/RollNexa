from datetime import timedelta
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import UserProfile
from attendance.models import AttendanceSession, AttendanceVerification
from attendance.services import complete_attendance_verification
from api.views import NoCacheAPIView

from .models import (
    BiometricChallenge,
    BiometricConsent,
    BiometricConsentEvent,
    BiometricVerificationAttempt,
    FaceEnrollment,
)
from .services import (
    BiometricServiceError,
    BiometricServiceUnavailable,
    MODEL_VERSION,
    biometric_models_available,
    verify_face_challenge,
)
from .workflows import create_or_replace_face_enrollment, update_biometric_consent


CHALLENGE_TTL = timedelta(seconds=90)
MAX_FACE_ATTEMPTS = 3


def _student_profile(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None
    if not profile or profile.role != UserProfile.ROLE_STUDENT:
        raise PermissionDenied("Only student accounts can use biometric enrolment and verification.")
    if profile.must_change_password:
        raise PermissionDenied("Change your temporary password before using biometric verification.")
    return profile


def _current_consent(student):
    try:
        return student.biometric_consent
    except BiometricConsent.DoesNotExist:
        return None


def _consent_data(student):
    consent = _current_consent(student)
    enrollment = FaceEnrollment.objects.filter(student=student, is_active=True).first()
    return {
        "consentStatus": (
            "consent_update_required"
            if consent and consent.is_granted and consent.policy_version != getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0")
            else consent.status if consent else "not_given"
        ),
        "consentPolicyVersion": consent.policy_version if consent else None,
        "currentPolicyVersion": getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0"),
        "consentGrantedAt": consent.granted_at.isoformat() if consent and consent.granted_at else None,
        "consentWithdrawnAt": consent.withdrawn_at.isoformat() if consent and consent.withdrawn_at else None,
        "isEnrolled": enrollment is not None,
        "enrolledAt": enrollment.enrolled_at.isoformat() if enrollment else None,
        "modelVersion": enrollment.model_version if enrollment else None,
        "modelsAvailable": biometric_models_available(),
        "encryptionConfigured": bool(getattr(settings, "BIOMETRIC_ENCRYPTION_KEY", "")),
    }


def _verification_for_student(verification_id, student):
    return get_object_or_404(
        AttendanceVerification.objects.select_related(
            "session__offering__course",
            "session__offering__semester__session",
        ),
        pk=verification_id,
        student=student,
    )


class BiometricStatusView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _student_profile(request)
        return Response(_consent_data(student))


class BiometricConsentView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "biometric_consent"

    def post(self, request):
        student = _student_profile(request)
        action = str(request.data.get("action", "")).strip().lower()
        policy_version = str(request.data.get("policyVersion", "")).strip()
        if action == BiometricConsentEvent.ACTION_GRANTED and request.data.get("acknowledged") is not True:
            return Response(
                {"detail": "Confirm that you have read and understood the biometric notice before granting consent."},
                status=400,
            )
        try:
            update_biometric_consent(
                student=student,
                action=action,
                policy_version=policy_version,
            )
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages), "errors": exc.messages}, status=400)
        return Response({"detail": "Biometric consent updated.", **_consent_data(student)})


class FaceEnrollmentView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "biometric_enrolment"

    def post(self, request):
        student = _student_profile(request)
        frames = request.FILES.getlist("frames")
        consent = _current_consent(student)
        if not consent or not consent.is_granted or consent.policy_version != getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0"):
            return Response({"detail": "Current biometric consent is required before facial enrolment."}, status=403)
        try:
            enrollment = create_or_replace_face_enrollment(student=student, frames=frames)
        except BiometricServiceUnavailable as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=503)
        except BiometricServiceError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=400)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages), "errors": exc.messages}, status=400)
        return Response({
            "detail": "Facial enrolment completed. Your encrypted facial template has been stored.",
            "isEnrolled": True,
            "enrolledAt": enrollment.enrolled_at.isoformat(),
            "modelVersion": enrollment.model_version,
        }, status=201)

    def delete(self, request):
        student = _student_profile(request)
        moment = timezone.now()
        with transaction.atomic():
            list(FaceEnrollment.objects.select_for_update().filter(student=student).values_list("pk", flat=True))
            deleted, _ = FaceEnrollment.objects.filter(student=student).delete()
            AttendanceVerification.objects.filter(
                student=student,
                status=AttendanceVerification.STATUS_QR_VERIFIED,
            ).update(status=AttendanceVerification.STATUS_EXPIRED, updated_at=moment)
        return Response({
            "detail": "Your stored facial template has been deleted." if deleted else "No facial template was stored.",
            "isEnrolled": False,
        })


class FaceChallengeView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "biometric_challenge"

    def post(self, request, verification_id):
        student = _student_profile(request)
        verification = _verification_for_student(verification_id, student)
        now = timezone.now()
        consent = _current_consent(student)
        enrollment = FaceEnrollment.objects.filter(student=student, is_active=True).first()
        if not consent or not consent.is_granted or consent.policy_version != getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0"):
            return Response({"detail": "Grant current biometric consent before facial verification."}, status=403)
        if not enrollment:
            return Response({"detail": "Complete facial enrolment before checking in."}, status=409)
        if enrollment.encryption_key_version != getattr(settings, "BIOMETRIC_ENCRYPTION_KEY_VERSION", "v1"):
            return Response({"detail": "The biometric encryption key version has changed. Re-enrolment or controlled key migration is required."}, status=503)
        if not biometric_models_available():
            return Response({"detail": "Facial recognition models are not installed on this server."}, status=503)
        if not getattr(settings, "BIOMETRIC_ENCRYPTION_KEY", ""):
            return Response({"detail": "Biometric encryption is not configured on this server."}, status=503)
        if verification.status != AttendanceVerification.STATUS_QR_VERIFIED:
            return Response({"detail": "This QR verification is no longer awaiting facial verification."}, status=409)
        if verification.expires_at <= now or verification.session.status != AttendanceSession.STATUS_ACTIVE or not verification.session.is_open_at(now):
            return Response({"detail": "This attendance verification has expired. Scan the current QR Code again."}, status=410)

        direction = secrets.choice([BiometricChallenge.DIRECTION_LEFT, BiometricChallenge.DIRECTION_RIGHT])
        BiometricChallenge.objects.filter(
            verification=verification,
            student=student,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        challenge = BiometricChallenge.objects.create(
            verification=verification,
            student=student,
            direction=direction,
            expires_at=min(now + CHALLENGE_TTL, verification.expires_at),
            created_at=now,
        )
        return Response({
            "challengeId": str(challenge.pk),
            "direction": direction,
            "prompt": "Turn your head toward the left side of the screen." if direction == BiometricChallenge.DIRECTION_LEFT else "Turn your head toward the right side of the screen.",
            "expiresAt": challenge.expires_at.isoformat(),
            "ttlSeconds": max(0, int((challenge.expires_at - now).total_seconds())),
        }, status=201)


class FaceVerificationView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "biometric_verify"

    def post(self, request, verification_id):
        student = _student_profile(request)
        challenge_id = request.data.get("challengeId", "")
        baseline_frame = request.FILES.get("baselineFrame")
        challenge_frame = request.FILES.get("challengeFrame")
        if not challenge_id or not baseline_frame or not challenge_frame:
            return Response({"detail": "A challenge and both camera frames are required."}, status=400)

        now = timezone.now()
        with transaction.atomic():
            verification = get_object_or_404(
                AttendanceVerification.objects.select_for_update().select_related("session"),
                pk=verification_id,
                student=student,
            )
            challenge = get_object_or_404(
                BiometricChallenge.objects.select_for_update(),
                pk=challenge_id,
                verification=verification,
                student=student,
            )
            if challenge.consumed_at:
                return Response({"detail": "This facial challenge has already been used. Request a new challenge."}, status=409)
            if challenge.expires_at <= now:
                challenge.consumed_at = now
                challenge.save(update_fields=["consumed_at"])
                return Response({"detail": "The facial challenge expired. Request a new challenge."}, status=410)
            if verification.status != AttendanceVerification.STATUS_QR_VERIFIED or verification.expires_at <= now:
                challenge.consumed_at = now
                challenge.save(update_fields=["consumed_at"])
                return Response({"detail": "The QR verification has expired. Scan the current QR Code again."}, status=410)
            if verification.session.status != AttendanceSession.STATUS_ACTIVE or not verification.session.is_open_at(now):
                challenge.consumed_at = now
                challenge.save(update_fields=["consumed_at"])
                return Response({"detail": "The attendance session is no longer open."}, status=410)
            challenge.consumed_at = now
            challenge.save(update_fields=["consumed_at"])

        consent = _current_consent(student)
        enrollment = FaceEnrollment.objects.filter(student=student, is_active=True).first()
        if (
            not consent
            or not consent.is_granted
            or consent.policy_version != getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0")
            or not enrollment
        ):
            return Response({"detail": "Current biometric consent and an active facial enrolment are required."}, status=403)
        if enrollment.encryption_key_version != getattr(settings, "BIOMETRIC_ENCRYPTION_KEY_VERSION", "v1"):
            return Response({"detail": "The biometric encryption key version has changed. Re-enrolment or controlled key migration is required."}, status=503)

        try:
            result = verify_face_challenge(
                baseline_frame=baseline_frame,
                challenge_frame=challenge_frame,
                encrypted_template=enrollment.encrypted_template,
                direction=challenge.direction,
            )
        except BiometricServiceUnavailable as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=503)
        except BiometricServiceError as exc:
            with transaction.atomic():
                locked_verification = AttendanceVerification.objects.select_for_update().get(pk=verification.pk)
                failed_count = BiometricVerificationAttempt.objects.filter(
                    verification=locked_verification,
                    result=BiometricVerificationAttempt.RESULT_FAILED,
                ).count() + 1
                BiometricVerificationAttempt.objects.create(
                    verification=locked_verification,
                    student=student,
                    challenge=challenge,
                    result=BiometricVerificationAttempt.RESULT_FAILED,
                    failure_code=exc.code,
                    liveness_passed=False,
                    model_version=MODEL_VERSION,
                    occurred_at=now,
                )
                attempts_remaining = max(0, MAX_FACE_ATTEMPTS - failed_count)
                if attempts_remaining == 0 and locked_verification.status == AttendanceVerification.STATUS_QR_VERIFIED:
                    locked_verification.status = AttendanceVerification.STATUS_FAILED
                    locked_verification.save(update_fields=["status", "updated_at"])
                verification_failed = locked_verification.status == AttendanceVerification.STATUS_FAILED
            return Response({
                "detail": exc.message,
                "code": exc.code,
                "attemptsRemaining": attempts_remaining,
                "verificationFailed": verification_failed,
            }, status=400)

        try:
            with transaction.atomic():
                locked_consent = BiometricConsent.objects.select_for_update().filter(
                    student=student,
                    status=BiometricConsent.STATUS_GRANTED,
                    policy_version=getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.0"),
                ).first()
                locked_enrollment = FaceEnrollment.objects.select_for_update().filter(
                    pk=enrollment.pk,
                    student=student,
                    is_active=True,
                ).first()
                if not locked_consent or not locked_enrollment:
                    return Response({"detail": "Biometric consent or enrolment changed during verification. Start again or request a manual attendance exception."}, status=403)
                record = complete_attendance_verification(verification_id=verification.pk, verified_at=now)
                BiometricVerificationAttempt.objects.create(
                    verification=verification,
                    student=student,
                    challenge=challenge,
                    result=BiometricVerificationAttempt.RESULT_PASSED,
                    liveness_passed=result["liveness_passed"],
                    model_version=result["model_version"],
                    occurred_at=now,
                )
                FaceEnrollment.objects.filter(pk=enrollment.pk).update(last_verified_at=now)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages), "errors": exc.messages}, status=400)
        return Response({
            "detail": "Facial verification succeeded. Your attendance has been recorded.",
            "status": "completed",
            "attendanceRecordId": record.pk,
            "recordedAt": record.recorded_at.isoformat(),
        })
