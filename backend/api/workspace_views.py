import secrets
from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .views import NoCacheAPIView
from core.audit import record_audit_event

from accounts.forms import AdminCreateAccountForm, AdminUpdateAccountForm
from accounts.models import UserProfile
from academics.course_forms import (
    CourseForm,
    CourseOfferingForm,
    LecturerAssignmentForm,
    TeachingAssignmentCreateForm,
)
from academics.forms import (
    AcademicSessionForm,
    DepartmentForm,
    FacultyForm,
    ProgrammeForm,
    SemesterForm,
)
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
from attendance.forms import AttendanceSessionForm
from attendance.models import AttendanceRecord, AttendanceSession
from attendance.services import (
    activate_attendance_session,
    cancel_attendance_session,
    close_attendance_session,
    create_attendance_session,
)

User = get_user_model()

ACADEMIC_FORMS = {
    "faculties": (Faculty, FacultyForm),
    "departments": (Department, DepartmentForm),
    "programmes": (Programme, ProgrammeForm),
    "sessions": (AcademicSession, AcademicSessionForm),
    "semesters": (Semester, SemesterForm),
}
ACADEMIC_RESOURCE_LABELS = {
    "faculties": "faculty",
    "departments": "department",
    "programmes": "programme",
    "sessions": "academic session",
    "semesters": "semester",
}

ADMIN_RESOURCES = {
    "users",
    "faculties",
    "departments",
    "programmes",
    "sessions",
    "semesters",
    "courses",
    "offerings",
    "assignments",
    "attendance-monitor",
    "reports",
}


def _role_for(user):
    if user.is_superuser:
        return UserProfile.ROLE_ADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


def _require_roles(request, *roles):
    if _role_for(request.user) not in roles:
        raise PermissionDenied("You do not have permission to access this workspace resource.")
    profile = getattr(request.user, "profile", None)
    if profile and profile.must_change_password:
        raise PermissionDenied("Change your temporary password before accessing workspace data.")


def _form_errors(form):
    return {
        field: [str(message) for message in messages]
        for field, messages in form.errors.items()
    }


def _invalid_form(form):
    return Response(
        {"detail": "Some fields need attention. Review the field errors shown below.", "errors": _form_errors(form)},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _active_course_offerings():
    return CourseOffering.objects.filter(
        is_active=True,
        course__is_active=True,
        course__department__is_active=True,
        course__department__faculty__is_active=True,
        programme__is_active=True,
        programme__department__is_active=True,
        programme__department__faculty__is_active=True,
        semester__is_active=True,
        semester__session__is_active=True,
    )


def _paginate(queryset, request, serializer):
    try:
        page_number = max(1, int(request.query_params.get("page", "1")))
    except (TypeError, ValueError):
        page_number = 1
    try:
        page_size = min(100, max(1, int(request.query_params.get("page_size", "20"))))
    except (TypeError, ValueError):
        page_size = 20
    page = Paginator(queryset, page_size).get_page(page_number)
    return {
        "results": [serializer(item) for item in page.object_list],
        "count": page.paginator.count,
        "page": page.number,
        "pageSize": page_size,
        "pages": page.paginator.num_pages,
        "hasNext": page.has_next(),
        "hasPrevious": page.has_previous(),
    }


def _user_data(user):
    profile = getattr(user, "profile", None)
    role = _role_for(user)
    return {
        "id": user.pk,
        "username": user.get_username(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name().strip() or user.get_username(),
        "email": user.email,
        "role": role,
        "institutional_id": profile.institutional_id if profile else "",
        "phone_number": profile.phone_number if profile else "",
        "department_id": profile.department_id if profile else None,
        "department_name": profile.department.name if profile and profile.department_id else "",
        "programme_id": profile.programme_id if profile else None,
        "programme_name": profile.programme.name if profile and profile.programme_id else "",
        "current_level": profile.current_level if profile else "",
        "must_change_password": profile.must_change_password if profile else False,
        "is_active": user.is_active,
        "joined_at": user.date_joined.isoformat(),
    }


def _academic_data(resource, item):
    data = {"id": item.pk, "is_active": item.is_active}
    if resource == "faculties":
        data.update({
            "code": item.code,
            "name": item.name,
            "description": item.description,
            "department_count": item.departments.filter(is_active=True).count(),
        })
    elif resource == "departments":
        data.update({
            "faculty_id": item.faculty_id,
            "faculty_name": item.faculty.name,
            "code": item.code,
            "name": item.name,
            "description": item.description,
            "programme_count": item.programmes.filter(is_active=True).count(),
        })
    elif resource == "programmes":
        data.update({
            "department_id": item.department_id,
            "department_name": item.department.name,
            "code": item.code,
            "name": item.name,
            "award": item.award,
            "duration_years": item.duration_years,
            "mode": item.mode,
            "description": item.description,
        })
    elif resource == "sessions":
        data.update({
            "name": item.name,
            "start_date": item.start_date.isoformat() if item.start_date else "",
            "end_date": item.end_date.isoformat() if item.end_date else "",
            "is_current": item.is_current,
            "semester_count": item.semesters.count(),
        })
    elif resource == "semesters":
        data.update({
            "session_id": item.session_id,
            "session_name": item.session.name,
            "name": item.name,
            "name_display": item.get_name_display(),
            "start_date": item.start_date.isoformat() if item.start_date else "",
            "end_date": item.end_date.isoformat() if item.end_date else "",
            "is_current": item.is_current,
            "offering_count": item.course_offerings.count(),
        })
    return data


def _course_data(item):
    return {
        "id": item.pk,
        "department_id": item.department_id,
        "department_name": item.department.name,
        "faculty_name": item.department.faculty.name,
        "code": item.code,
        "title": item.title,
        "credit_units": item.credit_units,
        "stress_code": item.stress_code,
        "description": item.description,
        "is_active": item.is_active,
        "offering_count": item.offerings.count(),
    }


def _offering_data(item):
    active_assignments = item.lecturer_assignments.filter(
        is_active=True,
    ).select_related("lecturer__user", "lecturer__department")
    return {
        "id": item.pk,
        "course_id": item.course_id,
        "course_code": item.course.code,
        "course_title": item.course.title,
        "course_department": item.course.department.name,
        "programme_id": item.programme_id,
        "programme_name": item.programme.name,
        "semester_id": item.semester_id,
        "semester_name": item.semester.get_name_display(),
        "academic_session": item.semester.session.name,
        "level": item.level,
        "credit_units": item.credit_units,
        "stress_code": item.stress_code,
        "source_url": item.source_url,
        "source_note": item.source_note,
        "max_students": item.max_students,
        "registration_open": item.registration_open,
        "notes": item.notes,
        "is_active": item.is_active,
        "registered_count": item.registrations.filter(
            status=CourseRegistration.STATUS_REGISTERED
        ).count(),
        "lecturers": [
            {
                "assignment_id": assignment.pk,
                "profile_id": assignment.lecturer_id,
                "name": assignment.lecturer.user.get_full_name() or assignment.lecturer.user.username,
                "department": assignment.lecturer.department.name if assignment.lecturer.department_id else "",
                "cross_department": assignment.is_cross_department,
            }
            for assignment in active_assignments
        ],
    }


def _assignment_data(item):
    return {
        "id": item.pk,
        "offering_id": item.offering_id,
        "course_code": item.offering.course.code,
        "course_title": item.offering.course.title,
        "programme_name": item.offering.programme.name,
        "semester_name": item.offering.semester.get_name_display(),
        "academic_session": item.offering.semester.session.name,
        "lecturer_profile_id": item.lecturer_id,
        "lecturer_name": item.lecturer.user.get_full_name() or item.lecturer.user.username,
        "lecturer_username": item.lecturer.user.username,
        "lecturer_department": item.lecturer.department.name if item.lecturer.department_id else "",
        "is_cross_department": item.is_cross_department,
        "is_active": item.is_active,
        "assigned_at": item.assigned_at.isoformat(),
        "removed_at": item.removed_at.isoformat() if item.removed_at else None,
        "removal_note": item.removal_note,
    }


def _attendance_session_data(item):
    return {
        "id": item.pk,
        "offering_id": item.offering_id,
        "course_code": item.offering.course.code,
        "course_title": item.offering.course.title,
        "programme_name": item.offering.programme.name,
        "level": item.offering.level,
        "semester_name": item.offering.semester.get_name_display(),
        "academic_session": item.offering.semester.session.name,
        "title": item.title,
        "starts_at": item.starts_at.isoformat(),
        "ends_at": item.ends_at.isoformat(),
        "status": item.status,
        "is_open": item.is_open,
        "is_expired": item.is_expired,
        "can_activate": (
            item.status == AttendanceSession.STATUS_SCHEDULED
            and item.starts_at <= timezone.now() < item.ends_at
        ),
        "registered_count": item.offering.registrations.filter(
            status=CourseRegistration.STATUS_REGISTERED
        ).count(),
        "qr_verified_count": item.verifications.filter(
            status="qr_verified", expires_at__gt=timezone.now()
        ).count(),
        "attendance_count": item.records.count(),
        "automated_attendance_count": item.records.filter(
            recording_method=AttendanceRecord.METHOD_DUAL_VERIFIED
        ).count(),
        "manual_attendance_count": item.records.filter(
            recording_method=AttendanceRecord.METHOD_MANUAL_EXCEPTION
        ).count(),
        "created_at": item.created_at.isoformat(),
        "notes": item.notes,
    }


def _registration_data(item):
    offering = item.offering
    return {
        "id": item.pk,
        "offering_id": offering.pk,
        "course_code": offering.course.code,
        "course_title": offering.course.title,
        "programme_name": offering.programme.name,
        "level": offering.level,
        "semester_name": offering.semester.get_name_display(),
        "academic_session": offering.semester.session.name,
        "status": item.status,
        "registered_at": item.registered_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "registration_open": offering.registration_open,
    }


def _record_data(item):
    return {
        "id": item.pk,
        "session_id": item.session_id,
        "session_title": item.session.title or "Attendance session",
        "course_code": item.session.offering.course.code,
        "course_title": item.session.offering.course.title,
        "academic_session": item.session.offering.semester.session.name,
        "semester_name": item.session.offering.semester.get_name_display(),
        "recorded_at": item.recorded_at.isoformat(),
        "qr_verified_at": item.qr_verified_at.isoformat() if item.qr_verified_at else None,
        "face_verified_at": item.face_verified_at.isoformat() if item.face_verified_at else None,
        "recording_method": item.recording_method,
        "manual_reason": item.get_manual_reason_display() if item.manual_reason else "",
        "student_name": item.student.user.get_full_name() or item.student.user.username,
        "student_id": item.student.institutional_id,
    }


def _get_queryset(resource, request):
    role = _role_for(request.user)
    if resource in ADMIN_RESOURCES:
        _require_roles(request, UserProfile.ROLE_ADMIN)
    elif resource in {"lecturer-courses", "rosters", "attendance-sessions"}:
        _require_roles(request, UserProfile.ROLE_LECTURER, UserProfile.ROLE_ADMIN)
    elif resource in {"student-courses", "attendance-history"}:
        _require_roles(request, UserProfile.ROLE_STUDENT)
    else:
        raise PermissionDenied("This workspace resource is not available.")

    if resource == "users":
        return User.objects.filter(is_superuser=False).select_related(
            "profile__department", "profile__programme"
        ).order_by("last_name", "first_name", "username")
    if resource in ACADEMIC_FORMS:
        model = ACADEMIC_FORMS[resource][0]
        return model.objects.all()
    if resource == "courses":
        return Course.objects.select_related("department", "department__faculty").all()
    if resource == "offerings":
        return CourseOffering.objects.select_related(
            "course", "course__department", "programme", "semester", "semester__session"
        ).prefetch_related("lecturer_assignments__lecturer__user", "lecturer_assignments__lecturer__department")
    if resource == "assignments":
        return CourseLecturerAssignment.objects.select_related(
            "offering__course", "offering__programme", "offering__semester__session",
            "lecturer__user", "lecturer__department",
        )
    if resource == "lecturer-courses":
        profile = request.user.profile
        if role == UserProfile.ROLE_ADMIN:
            raise PermissionDenied("Use the administrative course offering workspace.")
        return CourseOffering.objects.filter(
            lecturer_assignments__lecturer=profile,
            lecturer_assignments__is_active=True,
            is_active=True,
        ).select_related("course", "programme", "semester__session").distinct()
    if resource == "rosters":
        _require_roles(request, UserProfile.ROLE_LECTURER)
        profile = request.user.profile
        offering_id = request.query_params.get("offering")
        if not offering_id:
            raise PermissionDenied("Select one of your assigned course offerings.")
        offering = get_object_or_404(
            CourseOffering.objects.filter(
                pk=offering_id,
                lecturer_assignments__lecturer=profile,
                lecturer_assignments__is_active=True,
                is_active=True,
            ),
        )
        return CourseRegistration.objects.filter(
            offering=offering,
            status=CourseRegistration.STATUS_REGISTERED,
        ).select_related("student__user", "student__programme", "student__department")
    if resource == "student-courses":
        profile = request.user.profile
        if not profile.programme_id or not profile.current_level:
            return CourseOffering.objects.none()
        registered = CourseRegistration.objects.filter(
            offering=OuterRef("pk"),
            student=profile,
            status=CourseRegistration.STATUS_REGISTERED,
        )
        return CourseOffering.objects.filter(
            is_active=True,
            course__is_active=True,
            programme_id=profile.programme_id,
            level=profile.current_level,
            programme__is_active=True,
            semester__is_active=True,
            semester__session__is_active=True,
        ).select_related("course", "programme", "semester__session").annotate(
            is_registered=Exists(registered)
        )
    if resource == "attendance-sessions":
        profile = request.user.profile
        queryset = AttendanceSession.objects.select_related(
            "offering__course", "offering__programme", "offering__semester__session"
        )
        if role == UserProfile.ROLE_LECTURER:
            queryset = queryset.filter(
                offering__lecturer_assignments__lecturer=profile,
                offering__lecturer_assignments__is_active=True,
                offering__is_active=True,
            )
        return queryset.distinct()
    if resource == "attendance-history":
        return AttendanceRecord.objects.filter(
            student=request.user.profile
        ).select_related("session__offering__course", "session__offering__semester__session", "student__user")
    if resource == "attendance-monitor":
        return AttendanceSession.objects.select_related(
            "offering__course", "offering__programme", "offering__semester__session"
        )
    return None


def _serialize(resource, item):
    if resource == "users":
        return _user_data(item)
    if resource in ACADEMIC_FORMS:
        return _academic_data(resource, item)
    if resource == "courses":
        return _course_data(item)
    if resource in {"offerings", "lecturer-courses", "student-courses"}:
        data = _offering_data(item)
        if resource == "student-courses":
            data["is_registered"] = bool(getattr(item, "is_registered", False))
        return data
    if resource == "assignments":
        return _assignment_data(item)
    if resource == "rosters":
        student = item.student
        return {
            "id": student.pk,
            "username": student.user.username,
            "name": student.user.get_full_name() or student.user.username,
            "email": student.user.email,
            "institutional_id": student.institutional_id,
            "programme": student.programme.name if student.programme_id else "",
            "level": student.current_level,
            "registered_at": item.registered_at.isoformat(),
        }
    if resource in {"attendance-sessions", "attendance-monitor"}:
        return _attendance_session_data(item)
    if resource == "attendance-history":
        return _record_data(item)
    return {}


def _filter_queryset(resource, queryset, request):
    query = request.query_params.get("q", "").strip()
    selected_status = request.query_params.get("status", "").strip()
    if query:
        search_map = {
            "users": ("username", "first_name", "last_name", "email", "profile__institutional_id", "profile__department__name", "profile__programme__name"),
            "faculties": ("code", "name"),
            "departments": ("code", "name", "faculty__name"),
            "programmes": ("code", "name", "department__name"),
            "sessions": ("name",),
            "semesters": ("name", "session__name"),
            "courses": ("code", "title", "department__name"),
            "offerings": ("course__code", "course__title", "programme__name", "course__department__name"),
            "assignments": ("lecturer__user__username", "lecturer__user__first_name", "lecturer__user__last_name", "offering__course__code", "offering__course__title", "offering__programme__name"),
            "lecturer-courses": ("course__code", "course__title", "programme__name"),
            "student-courses": ("course__code", "course__title", "programme__name"),
            "attendance-sessions": ("title", "offering__course__code", "offering__course__title"),
            "attendance-monitor": ("title", "offering__course__code", "offering__course__title"),
            "attendance-history": ("session__offering__course__code", "session__offering__course__title"),
        }
        fields = search_map.get(resource, ())
        if fields:
            query_filter = reduce(or_, [Q(**{f"{field}__icontains": query}) for field in fields])
            queryset = queryset.filter(query_filter)
    if selected_status in {"active", "inactive"} and resource in {
        "users", "faculties", "departments", "programmes", "sessions", "semesters", "courses", "offerings"
    }:
        queryset = queryset.filter(is_active=(selected_status == "active"))
    if resource == "users":
        role = request.query_params.get("role", "").strip()
        if role in {UserProfile.ROLE_STUDENT, UserProfile.ROLE_LECTURER}:
            queryset = queryset.filter(profile__role=role)
    if resource == "assignments" and selected_status in {"active", "history", "all"}:
        if selected_status == "active":
            queryset = queryset.filter(is_active=True)
        elif selected_status == "history":
            queryset = queryset.filter(is_active=False)
    if resource in {"attendance-sessions", "attendance-monitor"} and selected_status in {
        AttendanceSession.STATUS_SCHEDULED,
        AttendanceSession.STATUS_ACTIVE,
        AttendanceSession.STATUS_CLOSED,
        AttendanceSession.STATUS_CANCELLED,
    }:
        queryset = queryset.filter(status=selected_status)
    if resource == "offerings":
        session_name = request.query_params.get("session", "").strip()
        if session_name:
            queryset = queryset.filter(semester__session__name=session_name)
        if selected_status == "open":
            queryset = queryset.filter(is_active=True, registration_open=True)
        elif selected_status == "closed":
            queryset = queryset.filter(registration_open=False)
    return queryset


def _options(resource, request):
    options = {}
    if resource == "users":
        options["departments"] = [
            {"value": item.pk, "label": item.name}
            for item in Department.objects.filter(is_active=True, faculty__is_active=True).order_by("name")
        ]
        options["programmes"] = [
            {"value": item.pk, "label": item.name}
            for item in Programme.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).order_by("name")
        ]
    elif resource == "departments":
        options["faculties"] = [
            {"value": item.pk, "label": item.name}
            for item in Faculty.objects.filter(is_active=True).order_by("name")
        ]
    elif resource == "programmes":
        options["departments"] = [
            {"value": item.pk, "label": f"{item.name} — {item.faculty.name}"}
            for item in Department.objects.filter(is_active=True, faculty__is_active=True).select_related("faculty").order_by("name")
        ]
    elif resource == "semesters":
        options["sessions"] = [
            {"value": item.pk, "label": item.name}
            for item in AcademicSession.objects.filter(is_active=True).order_by("-name")
        ]
    elif resource == "courses":
        options["departments"] = [
            {"value": item.pk, "label": f"{item.name} — {item.faculty.name}"}
            for item in Department.objects.filter(is_active=True, faculty__is_active=True).select_related("faculty").order_by("name")
        ]
    elif resource == "offerings":
        options["courses"] = [
            {"value": item.pk, "label": f"{item.code} — {item.title}"}
            for item in Course.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).order_by("code")
        ]
        options["programmes"] = [
            {"value": item.pk, "label": item.name}
            for item in Programme.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).order_by("name")
        ]
        options["semesters"] = [
            {"value": item.pk, "label": f"{item.get_name_display()} — {item.session.name}"}
            for item in Semester.objects.filter(is_active=True, session__is_active=True).select_related("session").order_by("-session__name", "name")
        ]
    elif resource == "attendance-sessions":
        profile = getattr(request.user, "profile", None)
        if profile and profile.role == UserProfile.ROLE_LECTURER:
            offerings = CourseOffering.objects.filter(
                is_active=True,
                lecturer_assignments__lecturer=profile,
                lecturer_assignments__is_active=True,
                course__is_active=True,
                programme__is_active=True,
                semester__is_active=True,
                semester__session__is_active=True,
            ).select_related("course", "programme", "semester__session").distinct()
            options["offerings"] = [
                {"value": item.pk, "label": f"{item.course.code} — {item.course.title} · {item.programme.name} · {item.semester.session.name}"}
                for item in offerings
            ]
    return options


class CourseRegistrationControlView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_roles(request, UserProfile.ROLE_ADMIN)
        action = str(request.data.get("action", "")).strip().lower()
        if action not in {"open", "close"}:
            return Response(
                {"detail": "Choose either open or close for the global registration action."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        should_open = action == "open"
        with transaction.atomic():
            offering_ids = list(
                _active_course_offerings()
                .select_for_update()
                .values_list("pk", flat=True)
            )
            updated_count = CourseOffering.objects.filter(pk__in=offering_ids).update(
                registration_open=should_open,
                updated_at=timezone.now(),
            )
            record_audit_event(
                actor=request.user,
                event_type=f"course_registration.globally_{action}",
                object_type="course_offerings",
                object_id="all_active",
                summary="Global course registration was opened." if should_open else "Global course registration was closed.",
                metadata={"updated_count": updated_count},
            )

        state = "open" if should_open else "closed"
        return Response({
            "state": state,
            "updated_count": updated_count,
            "detail": (
                f"Registration opened for {updated_count} active course offering(s)."
                if should_open
                else f"Registration closed for {updated_count} active course offering(s)."
            ),
        })


class AssignmentOptionsView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_roles(request, UserProfile.ROLE_ADMIN)

        courses = Course.objects.filter(
            is_active=True,
            department__is_active=True,
            department__faculty__is_active=True,
        ).select_related("department").order_by("code", "department__name")
        semesters = Semester.objects.filter(
            is_active=True,
            session__is_active=True,
        ).select_related("session").order_by("-session__name", "name")
        lecturers = UserProfile.objects.filter(
            role=UserProfile.ROLE_LECTURER,
            user__is_active=True,
        ).select_related("user", "department").order_by(
            "user__last_name", "user__first_name", "user__username"
        )

        options = {
            "courses": [
                {
                    "value": item.pk,
                    "label": f"{item.code} — {item.title} · {item.department.name}",
                }
                for item in courses
            ],
            "semesters": [
                {
                    "value": item.pk,
                    "label": f"{item.get_name_display()} · {item.session.name}",
                }
                for item in semesters
            ],
            "lecturers": [
                {
                    "value": item.pk,
                    "label": (
                        f"{item.user.get_full_name() or item.user.username} · "
                        f"{item.department.name if item.department_id else 'No home department'}"
                    ),
                }
                for item in lecturers
            ],
            "levels": [
                {"value": value, "label": label}
                for value, label in CourseOffering.LEVEL_CHOICES
            ],
            "offerings": [],
        }

        course_id = request.query_params.get("course", "").strip()
        semester_id = request.query_params.get("semester", "").strip()
        level = request.query_params.get("level", "").strip()
        lecturer_id = request.query_params.get("lecturer", "").strip()
        if all((course_id, semester_id, level, lecturer_id)):
            try:
                course_id = int(course_id)
                semester_id = int(semester_id)
                lecturer_id = int(lecturer_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Select a valid course, semester, level and lecturer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            lecturer = get_object_or_404(lecturers, pk=lecturer_id)
            assigned_offering_ids = set(
                CourseLecturerAssignment.objects.filter(
                    lecturer=lecturer,
                    is_active=True,
                ).values_list("offering_id", flat=True)
            )
            matching_offerings = _active_course_offerings().filter(
                course_id=course_id,
                semester_id=semester_id,
                level=level,
            ).select_related(
                "course", "programme", "programme__department", "semester__session"
            ).order_by("programme__department__name", "programme__name")
            options["offerings"] = [
                {
                    "value": item.pk,
                    "label": (
                        f"{item.programme.name} · {item.programme.department.name}"
                    ),
                    "programme_name": item.programme.name,
                    "department_name": item.programme.department.name,
                    "level": item.get_level_display(),
                    "already_assigned": item.pk in assigned_offering_ids,
                }
                for item in matching_offerings
            ]

        return Response(options)


class BulkTeachingAssignmentView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_roles(request, UserProfile.ROLE_ADMIN)

        lecturer_id = request.data.get("lecturer")
        offering_ids = request.data.get("offering_ids")
        if not isinstance(offering_ids, list) or not offering_ids or len(offering_ids) > 100:
            return Response(
                {"detail": "Select between 1 and 100 course offerings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lecturer_id = int(lecturer_id)
            selected_ids = [int(value) for value in offering_ids]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Select a valid lecturer and course offerings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(set(selected_ids)) != len(selected_ids):
            return Response(
                {"detail": "The same course offering cannot be selected more than once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lecturer = get_object_or_404(
            UserProfile.objects.select_related("user", "department"),
            pk=lecturer_id,
            role=UserProfile.ROLE_LECTURER,
            user__is_active=True,
        )

        try:
            with transaction.atomic():
                offerings = list(
                    _active_course_offerings()
                    .filter(pk__in=selected_ids)
                    .select_for_update()
                    .select_related("course", "programme", "semester__session")
                )
                if len(offerings) != len(selected_ids):
                    return Response(
                        {"detail": "One or more selected course offerings are no longer active or available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                offering_groups = {
                    (item.course_id, item.semester_id, item.level)
                    for item in offerings
                }
                if len(offering_groups) != 1:
                    return Response(
                        {"detail": "A bulk assignment must cover the same course, semester and level."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                existing_ids = set(
                    CourseLecturerAssignment.objects.filter(
                        lecturer=lecturer,
                        offering_id__in=selected_ids,
                        is_active=True,
                    ).values_list("offering_id", flat=True)
                )
                assignments = []
                for offering in offerings:
                    if offering.pk in existing_ids:
                        continue
                    assignment = CourseLecturerAssignment(
                        offering=offering,
                        lecturer=lecturer,
                        assigned_by=request.user,
                    )
                    assignment.full_clean()
                    assignment.save()
                    assignments.append(assignment)
                record_audit_event(
                    actor=request.user,
                    event_type="teaching_assignments.bulk_created",
                    object_type="teaching_assignments",
                    object_id="bulk",
                    summary="A lecturer was assigned across multiple course offerings.",
                    metadata={
                        "lecturer_profile_id": lecturer.pk,
                        "offering_ids": [item.offering_id for item in assignments],
                        "created_count": len(assignments),
                        "already_assigned_count": len(existing_ids),
                    },
                )
        except ValidationError as exc:
            return Response(
                {"detail": "One or more teaching assignments are invalid.", "errors": {"__all__": exc.messages}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {"detail": "An assignment changed while this operation was being processed. Refresh and try again."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            "created_count": len(assignments),
            "already_assigned_count": len(existing_ids),
            "assignments": [_assignment_data(item) for item in assignments],
            "detail": (
                f"Assigned the lecturer to {len(assignments)} course offering(s). "
                f"{len(existing_ids)} existing assignment(s) were left unchanged."
            ) if assignments else (
                f"No new assignments were created. The lecturer is already assigned to all "
                f"{len(existing_ids)} selected course offering(s)."
            ),
        }, status=status.HTTP_201_CREATED if assignments else status.HTTP_200_OK)


class WorkspaceCollectionView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, resource):
        queryset = _get_queryset(resource, request)
        queryset = _filter_queryset(resource, queryset, request)
        if resource == "student-courses":
            queryset = queryset.order_by("course__code")
        elif resource == "attendance-history":
            queryset = queryset.order_by("-recorded_at")
        elif resource in {"attendance-sessions", "attendance-monitor"}:
            queryset = queryset.order_by("-starts_at")
        elif resource == "assignments":
            queryset = queryset.order_by("-assigned_at")
        else:
            queryset = queryset.order_by("-pk") if resource in {"users", "offerings"} else queryset
        payload = _paginate(queryset, request, lambda item: _serialize(resource, item))
        payload["options"] = _options(resource, request)
        if resource == "offerings":
            active_offerings = _active_course_offerings()
            active_count = active_offerings.count()
            open_count = active_offerings.filter(registration_open=True).count()
            payload["registrationSummary"] = {
                "activeOfferings": active_count,
                "openOfferings": open_count,
                "closedOfferings": active_count - open_count,
                "state": "closed" if open_count == 0 else "open" if open_count == active_count else "partial",
            }
        if resource == "student-courses":
            payload["profileComplete"] = bool(request.user.profile.programme_id and request.user.profile.current_level)
        return Response(payload)

    def post(self, request, resource):
        _require_roles(request, UserProfile.ROLE_ADMIN, UserProfile.ROLE_LECTURER)
        data = request.data
        if resource == "users":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            form = AdminCreateAccountForm(data)
            if not form.is_valid():
                return _invalid_form(form)
            temporary_password = secrets.token_urlsafe(14)
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=form.cleaned_data["username"],
                        email=form.cleaned_data["email"],
                        first_name=form.cleaned_data["first_name"].strip(),
                        last_name=form.cleaned_data["last_name"].strip(),
                        password=temporary_password,
                    )
                    profile = user.profile
                    profile.role = form.cleaned_data["role"]
                    profile.institutional_id = form.cleaned_data["institutional_id"].strip()
                    profile.phone_number = form.cleaned_data["phone_number"].strip()
                    if profile.role == UserProfile.ROLE_STUDENT:
                        profile.programme = form.cleaned_data.get("programme")
                        profile.department = profile.programme.department if profile.programme else None
                        profile.current_level = form.cleaned_data.get("current_level") or ""
                    else:
                        profile.department = form.cleaned_data.get("department")
                        profile.programme = None
                        profile.current_level = ""
                    profile.must_change_password = True
                    profile.created_by = request.user
                    profile.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="account.created",
                        object_type="user",
                        object_id=user.pk,
                        summary="An administrator created a user account.",
                        metadata={"role": profile.role},
                    )
            except IntegrityError:
                return Response({"detail": "The account could not be created because a unique value is already in use."}, status=400)
            return Response({"item": _user_data(user), "temporary_password": temporary_password}, status=201)

        if resource in ACADEMIC_FORMS:
            _require_roles(request, UserProfile.ROLE_ADMIN)
            model, form_class = ACADEMIC_FORMS[resource]
            form = form_class(data)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type=f"academic.{resource}_created",
                        object_type=resource,
                        object_id=item.pk,
                        summary=f"An administrator created a {ACADEMIC_RESOURCE_LABELS[resource]} record.",
                    )
            except IntegrityError:
                return Response({"detail": "A record with the same unique values already exists."}, status=400)
            return Response({"item": _academic_data(resource, item)}, status=201)

        if resource == "courses":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            form = CourseForm(data)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="course.created",
                        object_type="course",
                        object_id=item.pk,
                        summary="An administrator created a course.",
                        metadata={"course_code": item.code},
                    )
            except IntegrityError:
                return Response({"detail": "That course code is already used in the selected department."}, status=400)
            return Response({"item": _course_data(item)}, status=201)

        if resource == "offerings":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            form = CourseOfferingForm(data)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="course_offering.created",
                        object_type="course_offering",
                        object_id=item.pk,
                        summary="An administrator created a course offering.",
                        metadata={"course_id": item.course_id, "programme_id": item.programme_id},
                    )
            except IntegrityError:
                return Response({"detail": "This course is already offered to that programme, semester and level."}, status=400)
            return Response({"item": _offering_data(item)}, status=201)

        if resource == "assignments":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            form = TeachingAssignmentCreateForm(data)
            if not form.is_valid():
                return _invalid_form(form)
            assignment = CourseLecturerAssignment(
                offering=form.cleaned_data["offering"],
                lecturer=form.cleaned_data["lecturer"],
                assigned_by=request.user,
            )
            try:
                with transaction.atomic():
                    assignment.full_clean()
                    assignment.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="teaching_assignment.created",
                        object_type="teaching_assignment",
                        object_id=assignment.pk,
                        summary="An administrator assigned a lecturer to a course offering.",
                        metadata={"offering_id": assignment.offering_id, "lecturer_profile_id": assignment.lecturer_id},
                    )
            except ValidationError as exc:
                return Response({"detail": "The teaching assignment is invalid.", "errors": {"__all__": exc.messages}}, status=400)
            except IntegrityError:
                return Response({"detail": "That lecturer is already assigned to this offering."}, status=400)
            return Response({"item": _assignment_data(assignment)}, status=201)

        if resource == "attendance-sessions":
            _require_roles(request, UserProfile.ROLE_LECTURER)
            form = AttendanceSessionForm(
                data,
                lecturer_profile=request.user.profile,
                created_by=request.user,
            )
            if not form.is_valid():
                return _invalid_form(form)
            try:
                session = create_attendance_session(
                    offering_id=form.cleaned_data["offering"].pk,
                    created_by=request.user,
                    title=form.cleaned_data["title"],
                    starts_at=form.cleaned_data["starts_at"],
                    ends_at=form.cleaned_data["ends_at"],
                    notes=form.cleaned_data["notes"],
                )
            except ValidationError as exc:
                return Response({"detail": "The attendance session could not be scheduled.", "errors": {"__all__": exc.messages}}, status=400)
            return Response({"item": _attendance_session_data(session)}, status=201)

        return Response({"detail": "Creating records in this workspace is not supported."}, status=405)


class WorkspaceDetailView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, resource, pk):
        queryset = _get_queryset(resource, request)
        item = get_object_or_404(queryset, pk=pk)
        return Response({"item": _serialize(resource, item)})

    def put(self, request, resource, pk):
        return self._update(request, resource, pk)

    def patch(self, request, resource, pk):
        return self._update(request, resource, pk)

    def _update(self, request, resource, pk):
        queryset = _get_queryset(resource, request)
        item = get_object_or_404(queryset, pk=pk)
        data = request.data
        if resource == "users":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            if item.is_superuser:
                raise PermissionDenied("Administrator accounts cannot be edited through this workspace.")
            data = {
                "first_name": item.first_name,
                "last_name": item.last_name,
                "email": item.email,
                "institutional_id": item.profile.institutional_id,
                "phone_number": item.profile.phone_number,
                "department": item.profile.department_id,
                "programme": item.profile.programme_id,
                "current_level": item.profile.current_level,
                **dict(request.data),
            }
            form = AdminUpdateAccountForm(data, user=item)
            if not form.is_valid():
                return _invalid_form(form)
            with transaction.atomic():
                item.first_name = form.cleaned_data["first_name"].strip()
                item.last_name = form.cleaned_data["last_name"].strip()
                item.email = form.cleaned_data["email"].strip().lower()
                item.save(update_fields=["first_name", "last_name", "email"])
                profile = item.profile
                profile.institutional_id = form.cleaned_data["institutional_id"].strip()
                profile.phone_number = form.cleaned_data["phone_number"].strip()
                if profile.role == UserProfile.ROLE_STUDENT:
                    profile.programme = form.cleaned_data.get("programme")
                    profile.department = profile.programme.department if profile.programme else None
                    profile.current_level = form.cleaned_data.get("current_level") or ""
                elif profile.role == UserProfile.ROLE_LECTURER:
                    profile.department = form.cleaned_data.get("department")
                profile.save()
                record_audit_event(
                    actor=request.user,
                    event_type="account.updated",
                    object_type="user",
                    object_id=item.pk,
                    summary="An administrator updated a user account.",
                    metadata={"role": profile.role},
                )
            return Response({"item": _user_data(item)})

        if resource in ACADEMIC_FORMS:
            _require_roles(request, UserProfile.ROLE_ADMIN)
            model, form_class = ACADEMIC_FORMS[resource]
            merged_data = model_to_dict(item)
            merged_data.update(dict(request.data))
            form = form_class(merged_data, instance=item)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type=f"academic.{resource}_updated",
                        object_type=resource,
                        object_id=item.pk,
                        summary=f"An administrator updated a {ACADEMIC_RESOURCE_LABELS[resource]} record.",
                    )
            except IntegrityError:
                return Response({"detail": "A record with the same unique values already exists."}, status=400)
            return Response({"item": _academic_data(resource, item)})

        if resource == "courses":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            merged_data = model_to_dict(item)
            merged_data.update(dict(request.data))
            form = CourseForm(merged_data, instance=item)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="course.updated",
                        object_type="course",
                        object_id=item.pk,
                        summary="An administrator updated a course.",
                        metadata={"course_code": item.code},
                    )
            except IntegrityError:
                return Response({"detail": "That course code is already used in the selected department."}, status=400)
            return Response({"item": _course_data(item)})

        if resource == "offerings":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            merged_data = model_to_dict(item)
            merged_data.update(dict(request.data))
            form = CourseOfferingForm(merged_data, instance=item)
            if not form.is_valid():
                return _invalid_form(form)
            try:
                with transaction.atomic():
                    item = form.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="course_offering.updated",
                        object_type="course_offering",
                        object_id=item.pk,
                        summary="An administrator updated a course offering.",
                        metadata={"course_id": item.course_id, "programme_id": item.programme_id},
                    )
            except IntegrityError:
                return Response({"detail": "This course is already offered to that programme, semester and level."}, status=400)
            return Response({"item": _offering_data(item)})

        return Response({"detail": "Updating this workspace record is not supported."}, status=405)


class WorkspaceActionView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, resource, pk, action):
        queryset = _get_queryset(resource, request)
        item = get_object_or_404(queryset, pk=pk)
        if action == "toggle":
            return self._toggle(request, resource, item)
        if action == "set-current":
            return self._set_current(request, resource, item)
        if action == "assign" and resource == "offerings":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            form = LecturerAssignmentForm(request.data, offering=item)
            if not form.is_valid():
                return _invalid_form(form)
            assignment = CourseLecturerAssignment(
                offering=item,
                lecturer=form.cleaned_data["lecturer"],
                assigned_by=request.user,
            )
            try:
                with transaction.atomic():
                    assignment.full_clean()
                    assignment.save()
                    record_audit_event(
                        actor=request.user,
                        event_type="teaching_assignment.created",
                        object_type="teaching_assignment",
                        object_id=assignment.pk,
                        summary="An administrator assigned a lecturer to a course offering.",
                        metadata={"offering_id": assignment.offering_id, "lecturer_profile_id": assignment.lecturer_id},
                    )
            except ValidationError as exc:
                return Response({"detail": "The teaching assignment is invalid.", "errors": {"__all__": exc.messages}}, status=400)
            except IntegrityError:
                return Response({"detail": "That lecturer is already assigned to this offering."}, status=400)
            return Response({"item": _assignment_data(assignment)}, status=201)
        if action == "revoke" and resource == "assignments":
            _require_roles(request, UserProfile.ROLE_ADMIN)
            if not item.is_active:
                return Response({"detail": "This assignment has already been revoked."}, status=400)
            with transaction.atomic():
                item.is_active = False
                item.removed_at = timezone.now()
                item.removed_by = request.user
                item.removal_note = str(request.data.get("removal_note", "")).strip()[:240]
                item.save(update_fields=["is_active", "removed_at", "removed_by", "removal_note"])
                record_audit_event(
                    actor=request.user,
                    event_type="teaching_assignment.revoked",
                    object_type="teaching_assignment",
                    object_id=item.pk,
                    summary="An administrator revoked a lecturer assignment.",
                    metadata={"offering_id": item.offering_id, "lecturer_profile_id": item.lecturer_id},
                )
            return Response({"item": _assignment_data(item)})
        if action in {"activate", "close", "cancel"} and resource == "attendance-sessions":
            _require_roles(request, UserProfile.ROLE_LECTURER)
            service = {
                "activate": activate_attendance_session,
                "close": close_attendance_session,
                "cancel": cancel_attendance_session,
            }[action]
            try:
                session = service(session_id=item.pk, lecturer_profile=request.user.profile)
            except AttendanceSession.DoesNotExist:
                raise PermissionDenied("You no longer have an active teaching assignment for this session.")
            except ValidationError as exc:
                return Response({"detail": "The attendance session action could not be completed.", "errors": {"__all__": exc.messages}}, status=400)
            return Response({"item": _attendance_session_data(session)})
        if action in {"register", "withdraw"} and resource == "student-courses":
            _require_roles(request, UserProfile.ROLE_STUDENT)
            return self._student_registration(request, item, action)
        return Response({"detail": "This action is not supported for the selected resource."}, status=405)

    @staticmethod
    def _toggle(request, resource, item):
        _require_roles(request, UserProfile.ROLE_ADMIN)
        if resource == "users":
            if item.is_superuser or item.pk == request.user.pk:
                raise PermissionDenied("This administrator account cannot be changed here.")
            with transaction.atomic():
                item.is_active = not item.is_active
                item.save(update_fields=["is_active"])
                if not item.is_active and item.profile.role == UserProfile.ROLE_LECTURER:
                    CourseLecturerAssignment.objects.filter(
                        lecturer=item.profile, is_active=True
                    ).update(
                        is_active=False,
                        removed_at=timezone.now(),
                        removed_by=request.user,
                        removal_note="Lecturer account deactivated by administrator",
                    )
                record_audit_event(
                    actor=request.user,
                    event_type="account.activated" if item.is_active else "account.deactivated",
                    object_type="user",
                    object_id=item.pk,
                    summary="An administrator changed a user account's active status.",
                    metadata={"is_active": item.is_active},
                )
            return Response({"item": _user_data(item)})
        if resource in ACADEMIC_FORMS:
            if isinstance(item, Department) and not item.is_active and not item.faculty.is_active:
                return Response({"detail": "Reactivate the parent faculty before reactivating this department."}, status=400)
            if isinstance(item, Programme) and not item.is_active and (
                not item.department.is_active or not item.department.faculty.is_active
            ):
                return Response({"detail": "Reactivate the parent department and faculty before reactivating this programme."}, status=400)
            if isinstance(item, Semester) and not item.is_active and not item.session.is_active:
                return Response({"detail": "Reactivate the parent academic session before reactivating this semester."}, status=400)
            with transaction.atomic():
                item.is_active = not item.is_active
                if isinstance(item, AcademicSession) and not item.is_active:
                    item.is_current = False
                    item.save(update_fields=["is_active", "is_current", "updated_at"])
                    Semester.objects.filter(session=item, is_active=True).update(
                        is_active=False, is_current=False, updated_at=timezone.now()
                    )
                    CourseOffering.objects.filter(semester__session=item, is_active=True).update(
                        is_active=False, registration_open=False, updated_at=timezone.now()
                    )
                elif isinstance(item, Semester) and not item.is_active:
                    item.is_current = False
                    item.save(update_fields=["is_active", "is_current", "updated_at"])
                    CourseOffering.objects.filter(semester=item, is_active=True).update(
                        is_active=False, registration_open=False, updated_at=timezone.now()
                    )
                else:
                    item.save(update_fields=["is_active", "updated_at"])
                if isinstance(item, Faculty) and not item.is_active:
                    Department.objects.filter(faculty=item, is_active=True).update(is_active=False, updated_at=timezone.now())
                    Programme.objects.filter(department__faculty=item, is_active=True).update(is_active=False, updated_at=timezone.now())
                    Course.objects.filter(department__faculty=item, is_active=True).update(is_active=False, updated_at=timezone.now())
                    CourseOffering.objects.filter(
                        Q(course__department__faculty=item) | Q(programme__department__faculty=item),
                        is_active=True,
                    ).update(is_active=False, registration_open=False, updated_at=timezone.now())
                elif isinstance(item, Department) and not item.is_active:
                    Programme.objects.filter(department=item, is_active=True).update(is_active=False, updated_at=timezone.now())
                    Course.objects.filter(department=item, is_active=True).update(is_active=False, updated_at=timezone.now())
                    CourseOffering.objects.filter(
                        Q(course__department=item) | Q(programme__department=item), is_active=True
                    ).update(is_active=False, registration_open=False, updated_at=timezone.now())
                elif isinstance(item, Programme) and not item.is_active:
                    CourseOffering.objects.filter(programme=item, is_active=True).update(
                        is_active=False, registration_open=False, updated_at=timezone.now()
                    )
                record_audit_event(
                    actor=request.user,
                    event_type=f"academic.{resource}_status_changed",
                    object_type=resource,
                    object_id=item.pk,
                    summary=f"An administrator changed the active status of a {ACADEMIC_RESOURCE_LABELS[resource]} record.",
                    metadata={"is_active": item.is_active},
                )
            return Response({"item": _academic_data(resource, item)})
        if resource == "courses":
            if not item.is_active and (not item.department.is_active or not item.department.faculty.is_active):
                return Response({"detail": "Reactivate the course's department and faculty first."}, status=400)
            with transaction.atomic():
                item.is_active = not item.is_active
                item.save(update_fields=["is_active", "updated_at"])
                if not item.is_active:
                    CourseOffering.objects.filter(course=item, is_active=True).update(
                        is_active=False, registration_open=False
                    )
                record_audit_event(
                    actor=request.user,
                    event_type="course.status_changed",
                    object_type="course",
                    object_id=item.pk,
                    summary="An administrator changed a course's active status.",
                    metadata={"is_active": item.is_active},
                )
            return Response({"item": _course_data(item)})
        if resource == "offerings":
            if not item.is_active and (
                not item.course.is_active
                or not item.course.department.is_active
                or not item.course.department.faculty.is_active
                or not item.programme.is_active
                or not item.programme.department.is_active
                or not item.programme.department.faculty.is_active
                or not item.semester.is_active
                or not item.semester.session.is_active
            ):
                return Response({"detail": "Reactivate the course, programme, department, faculty and academic period before reactivating this offering."}, status=400)
            with transaction.atomic():
                item.is_active = not item.is_active
                if not item.is_active:
                    item.registration_open = False
                item.save(update_fields=["is_active", "registration_open", "updated_at"])
                record_audit_event(
                    actor=request.user,
                    event_type="course_offering.status_changed",
                    object_type="course_offering",
                    object_id=item.pk,
                    summary="An administrator changed a course offering's active status.",
                    metadata={"is_active": item.is_active, "registration_open": item.registration_open},
                )
            return Response({"item": _offering_data(item)})
        return Response({"detail": "This record cannot be activated or deactivated here."}, status=405)

    @staticmethod
    def _set_current(request, resource, item):
        _require_roles(request, UserProfile.ROLE_ADMIN)
        with transaction.atomic():
            if resource == "sessions" and isinstance(item, AcademicSession):
                AcademicSession.objects.filter(is_current=True).exclude(pk=item.pk).update(
                    is_current=False, updated_at=timezone.now()
                )
                Semester.objects.filter(is_current=True).update(is_current=False, updated_at=timezone.now())
                item.is_active = True
                item.is_current = True
                item.save(update_fields=["is_active", "is_current", "updated_at"])
                record_audit_event(
                    actor=request.user,
                    event_type="academic.session_set_current",
                    object_type="academic_session",
                    object_id=item.pk,
                    summary="An administrator set the current academic session.",
                )
            elif resource == "semesters" and isinstance(item, Semester):
                if not item.session.is_current or not item.session.is_active:
                    return Response({"detail": "Set this semester's academic session as current before activating the semester."}, status=400)
                Semester.objects.filter(is_current=True).exclude(pk=item.pk).update(
                    is_current=False, updated_at=timezone.now()
                )
                item.is_active = True
                item.is_current = True
                item.save(update_fields=["is_active", "is_current", "updated_at"])
                record_audit_event(
                    actor=request.user,
                    event_type="academic.semester_set_current",
                    object_type="semester",
                    object_id=item.pk,
                    summary="An administrator set the current semester.",
                )
            else:
                return Response({"detail": "Only academic sessions and semesters can be set as current."}, status=400)
        return Response({"item": _academic_data(resource, item)})

    @staticmethod
    def _student_registration(request, offering, action):
        profile = request.user.profile
        if not profile.programme_id or not profile.current_level:
            return Response({"detail": "Your academic programme and current level must be set before course registration."}, status=400)
        if offering.programme_id != profile.programme_id or offering.level != profile.current_level:
            raise PermissionDenied("This course offering is not available to your programme and current level.")
        if not offering.is_active or not offering.registration_open:
            return Response({"detail": "Registration is closed for this course offering."}, status=400)
        with transaction.atomic():
            locked_offering = CourseOffering.objects.select_for_update().get(pk=offering.pk)
            if not locked_offering.is_active or not locked_offering.registration_open:
                return Response({"detail": "Registration is closed for this course offering."}, status=400)
            if locked_offering.programme_id != profile.programme_id or locked_offering.level != profile.current_level:
                raise PermissionDenied("This course offering is not available to your programme and current level.")
            registration = CourseRegistration.objects.select_for_update().filter(
                offering=locked_offering, student=profile
            ).first()
            if action == "register":
                if registration and registration.status == CourseRegistration.STATUS_REGISTERED:
                    return Response({"detail": "You are already registered for this course."}, status=400)
                current_count = locked_offering.registrations.filter(
                    status=CourseRegistration.STATUS_REGISTERED
                ).count()
                if locked_offering.max_students and current_count >= locked_offering.max_students:
                    return Response({"detail": "This course offering has reached its registration limit."}, status=400)
                if registration:
                    registration.status = CourseRegistration.STATUS_REGISTERED
                    registration.full_clean()
                    registration.save(update_fields=["status", "updated_at"])
                else:
                    registration = CourseRegistration(offering=locked_offering, student=profile)
                    registration.full_clean()
                    registration.save()
                record_audit_event(
                    actor=request.user,
                    event_type="course_registration.registered",
                    object_type="course_registration",
                    object_id=registration.pk,
                    summary="A student registered for a course offering.",
                    metadata={"offering_id": locked_offering.pk, "student_profile_id": profile.pk},
                )
            else:
                if not registration or registration.status != CourseRegistration.STATUS_REGISTERED:
                    return Response({"detail": "You are not currently registered for this course."}, status=400)
                registration.status = CourseRegistration.STATUS_WITHDRAWN
                registration.save(update_fields=["status", "updated_at"])
                record_audit_event(
                    actor=request.user,
                    event_type="course_registration.withdrawn",
                    object_type="course_registration",
                    object_id=registration.pk,
                    summary="A student withdrew from a course offering.",
                    metadata={"offering_id": locked_offering.pk, "student_profile_id": profile.pk},
                )
        return Response({"item": _registration_data(registration)})


class ProfileView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_roles(request, UserProfile.ROLE_ADMIN, UserProfile.ROLE_LECTURER, UserProfile.ROLE_STUDENT)
        return Response({"item": _user_data(request.user)})

    def patch(self, request):
        _require_roles(request, UserProfile.ROLE_ADMIN, UserProfile.ROLE_LECTURER, UserProfile.ROLE_STUDENT)
        user = request.user
        first_name = str(request.data.get("first_name", user.first_name)).strip()
        last_name = str(request.data.get("last_name", user.last_name)).strip()
        email = str(request.data.get("email", user.email)).strip().lower()
        phone_number = str(request.data.get("phone_number", user.profile.phone_number)).strip()
        if not first_name or not last_name:
            return Response({"detail": "First name and last name are required."}, status=400)
        if len(first_name) > 150 or len(last_name) > 150 or len(phone_number) > 30:
            return Response({"detail": "One or more profile fields exceed their permitted length."}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"detail": "Enter a valid email address."}, status=400)
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return Response({"detail": "This email address is already associated with another account."}, status=400)
        with transaction.atomic():
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save(update_fields=["first_name", "last_name", "email"])
            user.profile.phone_number = phone_number
            user.profile.save(update_fields=["phone_number", "updated_at"])
            record_audit_event(
                actor=request.user,
                event_type="account.profile_updated",
                object_type="user",
                object_id=user.pk,
                summary="A user updated their own profile details.",
            )
        return Response({"item": _user_data(user)})


class ReportsView(NoCacheAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = _role_for(request.user)
        if role == UserProfile.ROLE_ADMIN:
            _require_roles(request, UserProfile.ROLE_ADMIN)
            total_sessions = AttendanceSession.objects.count()
            records = AttendanceRecord.objects.count()
            automated_records = AttendanceRecord.objects.filter(
                recording_method=AttendanceRecord.METHOD_DUAL_VERIFIED
            ).count()
            manual_records = AttendanceRecord.objects.filter(
                recording_method=AttendanceRecord.METHOD_MANUAL_EXCEPTION
            ).count()
            return Response({
                "role": role,
                "attendance": {
                    "sessions": total_sessions,
                    "presentRecords": records,
                    "verifiedRecords": automated_records,
                    "manualExceptions": manual_records,
                    "scheduled": AttendanceSession.objects.filter(status=AttendanceSession.STATUS_SCHEDULED).count(),
                    "active": AttendanceSession.objects.filter(status=AttendanceSession.STATUS_ACTIVE).count(),
                    "closed": AttendanceSession.objects.filter(status=AttendanceSession.STATUS_CLOSED).count(),
                    "cancelled": AttendanceSession.objects.filter(status=AttendanceSession.STATUS_CANCELLED).count(),
                },
                "academic": {
                    "students": UserProfile.objects.filter(role=UserProfile.ROLE_STUDENT).count(),
                    "lecturers": UserProfile.objects.filter(role=UserProfile.ROLE_LECTURER).count(),
                    "courses": Course.objects.count(),
                    "offerings": CourseOffering.objects.count(),
                    "registrations": CourseRegistration.objects.filter(status=CourseRegistration.STATUS_REGISTERED).count(),
                },
                "recentSessions": [
                    _attendance_session_data(item)
                    for item in AttendanceSession.objects.select_related(
                        "offering__course", "offering__programme", "offering__semester__session"
                    ).order_by("-starts_at")[:10]
                ],
            })
        if role == UserProfile.ROLE_LECTURER:
            _require_roles(request, UserProfile.ROLE_LECTURER)
            offering_ids = CourseLecturerAssignment.objects.filter(
                lecturer=request.user.profile,
                is_active=True,
                offering__is_active=True,
            ).values_list("offering_id", flat=True)
            sessions = AttendanceSession.objects.filter(offering_id__in=offering_ids)
            lecturer_records = AttendanceRecord.objects.filter(session__offering_id__in=offering_ids)
            return Response({
                "role": role,
                "attendance": {
                    "sessions": sessions.count(),
                    "presentRecords": lecturer_records.count(),
                    "verifiedRecords": lecturer_records.filter(
                        recording_method=AttendanceRecord.METHOD_DUAL_VERIFIED
                    ).count(),
                    "manualExceptions": lecturer_records.filter(
                        recording_method=AttendanceRecord.METHOD_MANUAL_EXCEPTION
                    ).count(),
                    "scheduled": sessions.filter(status=AttendanceSession.STATUS_SCHEDULED).count(),
                    "active": sessions.filter(status=AttendanceSession.STATUS_ACTIVE).count(),
                    "closed": sessions.filter(status=AttendanceSession.STATUS_CLOSED).count(),
                },
                "recentSessions": [
                    _attendance_session_data(item)
                    for item in sessions.select_related(
                        "offering__course", "offering__programme", "offering__semester__session"
                    ).order_by("-starts_at")[:10]
                ],
                "notice": "Automated attendance requires both QR Code and facial verification. Lecturer-approved manual exceptions are labelled separately and retained in the attendance history.",
            })
        raise PermissionDenied("Reports are not available for this account role.")
