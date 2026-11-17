from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import UserProfile
from academics.models import (
    AcademicSession,
    Course,
    CourseLecturerAssignment,
    CourseOffering,
    CourseRegistration,
    Department,
    Faculty,
    Programme,
    Semester,
)
from attendance.models import AttendanceRecord, AttendanceSession

User = get_user_model()


class NoCacheAPIView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response


def serialize_user(user):
    profile = getattr(user, "profile", None)
    if user.is_superuser:
        role = UserProfile.ROLE_ADMIN
    elif profile:
        role = profile.role
    else:
        role = None

    return {
        "id": user.pk,
        "username": user.get_username(),
        "firstName": user.first_name,
        "lastName": user.last_name,
        "fullName": user.get_full_name().strip() or user.get_username(),
        "email": user.email,
        "role": role,
        "institutionalId": profile.institutional_id if profile else "",
        "phoneNumber": profile.phone_number if profile else "",
        "department": profile.department.name if profile and profile.department_id else None,
        "programme": profile.programme.name if profile and profile.programme_id else None,
        "currentLevel": profile.current_level if profile else "",
        "mustChangePassword": profile.must_change_password if profile else False,
        "isActive": user.is_active,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(NoCacheAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(NoCacheAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))

        if not username or not password:
            return Response(
                {"detail": "Enter your username and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request=request._request, username=username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"detail": "The username or password is incorrect, or the account is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request._request, user)
        return Response({
            "authenticated": True,
            "user": serialize_user(user),
            "redirectTo": "/app/",
            "csrfToken": get_token(request._request),
        })


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(NoCacheAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request._request)
        return Response({"authenticated": False, "csrfToken": get_token(request._request)})


class SessionView(NoCacheAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})

        return Response({
            "authenticated": True,
            "user": serialize_user(request.user),
        })


class PasswordChangeView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = str(request.data.get("currentPassword", ""))
        new_password = str(request.data.get("newPassword", ""))
        confirm_password = str(request.data.get("confirmPassword", ""))

        if not request.user.check_password(current_password):
            return Response(
                {"detail": "Your current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password:
            return Response(
                {"detail": "Enter a new password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"detail": "The new password and confirmation do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            return Response(
                {"detail": " ".join(exc.messages), "errors": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        profile = getattr(request.user, "profile", None)
        if profile and profile.must_change_password:
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password", "updated_at"])

        update_session_auth_hash(request._request, request.user)
        return Response({
            "detail": "Your password has been updated.",
            "user": serialize_user(request.user),
        })


class DashboardSummaryView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)

        if user.is_superuser:
            return Response(self._admin_summary())

        if profile and profile.must_change_password:
            return Response(
                {"detail": "Change your temporary password before accessing dashboard data."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if profile and profile.role == UserProfile.ROLE_LECTURER:
            return Response(self._lecturer_summary(profile))

        if profile and profile.role == UserProfile.ROLE_STUDENT:
            return Response(self._student_summary(profile))

        return Response(
            {"detail": "This account does not have a recognised RollNexa role."},
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def _admin_summary():
        users = User.objects.filter(is_superuser=False)
        students = UserProfile.objects.filter(role=UserProfile.ROLE_STUDENT, user__is_superuser=False)
        lecturers = UserProfile.objects.filter(role=UserProfile.ROLE_LECTURER, user__is_superuser=False)
        recent_users = users.select_related("profile").order_by("-date_joined")[:6]

        return {
            "role": UserProfile.ROLE_ADMIN,
            "cards": [
                {"key": "students", "label": "Students", "value": students.count(), "description": "Student accounts"},
                {"key": "lecturers", "label": "Lecturers", "value": lecturers.count(), "description": "Lecturer accounts"},
                {"key": "activeUsers", "label": "Active accounts", "value": users.filter(is_active=True).count(), "description": "Non-administrator accounts"},
                {"key": "attendanceSessions", "label": "Attendance sessions", "value": AttendanceSession.objects.count(), "description": "All recorded sessions"},
            ],
            "academic": {
                "faculties": Faculty.objects.count(),
                "departments": Department.objects.count(),
                "programmes": Programme.objects.count(),
                "courses": Course.objects.count(),
                "courseOfferings": CourseOffering.objects.count(),
                "academicSessions": AcademicSession.objects.count(),
                "semesters": Semester.objects.count(),
            },
            "recentUsers": [
                {
                    "id": item.pk,
                    "name": item.get_full_name().strip() or item.get_username(),
                    "username": item.get_username(),
                    "role": item.profile.role if hasattr(item, "profile") else "unknown",
                    "joinedAt": item.date_joined.isoformat(),
                    "isActive": item.is_active,
                }
                for item in recent_users
            ],
        }

    @staticmethod
    def _lecturer_summary(profile):
        assignments = CourseLecturerAssignment.objects.filter(
            lecturer=profile,
            is_active=True,
            offering__is_active=True,
        ).select_related(
            "offering__course",
            "offering__programme",
            "offering__semester__session",
        )
        offering_ids = assignments.values_list("offering_id", flat=True)
        registered_count = CourseRegistration.objects.filter(
            offering_id__in=offering_ids,
            status=CourseRegistration.STATUS_REGISTERED,
        ).count()
        session_queryset = AttendanceSession.objects.filter(offering_id__in=offering_ids)
        current_time = timezone.now()

        return {
            "role": UserProfile.ROLE_LECTURER,
            "cards": [
                {"key": "assignedCourses", "label": "Assigned courses", "value": assignments.count(), "description": "Active teaching assignments"},
                {"key": "registeredEnrolments", "label": "Registered enrolments", "value": registered_count, "description": "Across your assigned courses"},
                {"key": "attendanceSessions", "label": "Attendance sessions", "value": session_queryset.count(), "description": "Sessions for your courses"},
                {"key": "activeSessions", "label": "Open sessions", "value": session_queryset.filter(
                    status=AttendanceSession.STATUS_ACTIVE,
                    starts_at__lte=current_time,
                    ends_at__gt=current_time,
                ).count(), "description": "Sessions currently within their time window"},
            ],
            "courses": [
                {
                    "id": assignment.offering_id,
                    "code": assignment.offering.course.code,
                    "title": assignment.offering.course.title,
                    "programme": assignment.offering.programme.name,
                    "level": assignment.offering.level,
                    "semester": assignment.offering.semester.get_name_display(),
                    "academicSession": assignment.offering.semester.session.name,
                }
                for assignment in assignments[:8]
            ],
        }

    @staticmethod
    def _student_summary(profile):
        registrations = CourseRegistration.objects.filter(
            student=profile,
            status=CourseRegistration.STATUS_REGISTERED,
        ).select_related(
            "offering__course",
            "offering__programme",
            "offering__semester__session",
        )
        offering_ids = registrations.values_list("offering_id", flat=True)
        attendance_records = AttendanceRecord.objects.filter(student=profile)
        current_time = timezone.now()

        return {
            "role": UserProfile.ROLE_STUDENT,
            "cards": [
                {"key": "registeredCourses", "label": "Registered courses", "value": registrations.count(), "description": "Your active course registrations"},
                {"key": "attendanceRecords", "label": "Attendance records", "value": attendance_records.count(), "description": "Verified attendance entries"},
                {"key": "availableSessions", "label": "Available sessions", "value": AttendanceSession.objects.filter(
                    offering_id__in=offering_ids,
                    status=AttendanceSession.STATUS_ACTIVE,
                    starts_at__lte=current_time,
                    ends_at__gt=current_time,
                ).count(), "description": "Active sessions for your courses"},
            ],
            "attendance": {
                "verifiedRecords": attendance_records.count(),
            },
            "courses": [
                {
                    "id": registration.offering_id,
                    "code": registration.offering.course.code,
                    "title": registration.offering.course.title,
                    "programme": registration.offering.programme.name,
                    "level": registration.offering.level,
                    "semester": registration.offering.semester.get_name_display(),
                    "academicSession": registration.offering.semester.session.name,
                }
                for registration in registrations[:8]
            ],
        }
