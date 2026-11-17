from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import UserProfile
from attendance.models import AttendanceSession, AttendanceVerification
from attendance.services import issue_attendance_qr_token, verify_attendance_qr

from .views import NoCacheAPIView


def _profile_for_role(request, role):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != role:
        raise PermissionDenied("You do not have permission to use this attendance verification function.")
    if profile.must_change_password:
        raise PermissionDenied("Change your temporary password before accessing attendance verification.")
    return profile


def _verification_data(verification, already_verified=False):
    session = verification.session
    offering = session.offering
    return {
        "verificationId": str(verification.pk),
        "status": verification.status,
        "qrVerifiedAt": verification.qr_verified_at.isoformat(),
        "faceVerifiedAt": verification.face_verified_at.isoformat() if verification.face_verified_at else None,
        "expiresAt": verification.expires_at.isoformat(),
        "alreadyVerified": already_verified,
        "session": {
            "id": session.pk,
            "title": session.title or "Attendance session",
            "courseCode": offering.course.code,
            "courseTitle": offering.course.title,
            "academicSession": offering.semester.session.name,
            "semester": offering.semester.get_name_display(),
        },
    }


class AttendanceQRView(NoCacheAPIView):
    """Return a short-lived signed QR token for an active session."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr_issue"

    def get(self, request, session_id):
        lecturer_profile = _profile_for_role(request, UserProfile.ROLE_LECTURER)
        try:
            result = issue_attendance_qr_token(
                session_id=session_id,
                lecturer_profile=lecturer_profile,
            )
        except AttendanceSession.DoesNotExist:
            return Response({"detail": "The attendance session is not available to this lecturer."}, status=404)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages), "errors": exc.messages}, status=400)

        return Response({
            "token": result["token"],
            "issuedAt": result["issued_at"].isoformat(),
            "expiresAt": result["expires_at"].isoformat(),
            "ttlSeconds": result["ttl_seconds"],
            "session": {
                "id": result["session"].pk,
                "title": result["session"].title or "Attendance session",
                "courseCode": result["session"].offering.course.code,
                "courseTitle": result["session"].offering.course.title,
            },
        })


class VerifyAttendanceQRView(NoCacheAPIView):
    """Verify a student's eligibility and register the QR stage only."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr_verify"

    def post(self, request):
        student_profile = _profile_for_role(request, UserProfile.ROLE_STUDENT)
        token = request.data.get("token", "") if isinstance(request.data, dict) else ""

        try:
            verification, already_verified = verify_attendance_qr(
                token=token,
                student_profile=student_profile,
            )
        except (ValidationError, UserProfile.DoesNotExist) as exc:
            messages = exc.messages if isinstance(exc, ValidationError) else ["The student account is unavailable."]
            return Response({"detail": " ".join(messages), "errors": messages}, status=400)

        return Response(
            _verification_data(verification, already_verified=already_verified),
            status=200 if already_verified else 201,
        )


class AttendanceVerificationStatusView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, verification_id):
        student_profile = _profile_for_role(request, UserProfile.ROLE_STUDENT)
        verification = get_object_or_404(
            AttendanceVerification.objects.select_related(
                "session__offering__course",
                "session__offering__semester__session",
            ),
            pk=verification_id,
            student=student_profile,
        )

        if (
            verification.status == AttendanceVerification.STATUS_QR_VERIFIED
            and (
                verification.expires_at <= timezone.now()
                or verification.session.status != AttendanceSession.STATUS_ACTIVE
            )
        ):
            verification.status = AttendanceVerification.STATUS_EXPIRED
            verification.save(update_fields=["status", "updated_at"])

        return Response(_verification_data(verification))
