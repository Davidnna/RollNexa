from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import UserProfile
from academics.models import CourseRegistration

from .forms import AttendanceSessionForm
from .models import AttendanceSession
from .services import (
    activate_attendance_session,
    cancel_attendance_session,
    close_attendance_session,
    create_attendance_session,
)


def _access_denied(request):
    return render(request, "accounts/access_denied.html", status=403)


def lecturer_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.is_superuser or request.user.profile.role != UserProfile.ROLE_LECTURER:
            return _access_denied(request)
        return view_func(request, *args, **kwargs)
    return wrapped


def _manageable_sessions(profile):
    return AttendanceSession.objects.filter(
        offering__lecturer_assignments__lecturer=profile,
        offering__lecturer_assignments__is_active=True,
        offering__is_active=True,
    ).select_related(
        "offering__course",
        "offering__programme",
        "offering__semester",
        "offering__semester__session",
        "created_by",
    ).annotate(
        registered_count=Count(
            "offering__registrations",
            filter=Q(offering__registrations__status=CourseRegistration.STATUS_REGISTERED),
            distinct=True,
        ),
        attendance_count=Count("records", distinct=True),
    ).distinct()


def _get_manageable_session(profile, pk):
    return get_object_or_404(
        AttendanceSession.objects.filter(
            offering__lecturer_assignments__lecturer=profile,
            offering__lecturer_assignments__is_active=True,
            offering__is_active=True,
        ).select_related(
            "offering__course",
            "offering__programme",
            "offering__semester",
            "offering__semester__session",
            "created_by",
        ),
        pk=pk,
    )


@lecturer_required
def lecturer_attendance_sessions(request):
    sessions = _manageable_sessions(request.user.profile)
    selected_status = request.GET.get("status", "").strip()
    if selected_status in {
        AttendanceSession.STATUS_SCHEDULED,
        AttendanceSession.STATUS_ACTIVE,
        AttendanceSession.STATUS_CLOSED,
        AttendanceSession.STATUS_CANCELLED,
    }:
        sessions = sessions.filter(status=selected_status)
    page_obj = Paginator(sessions, 20).get_page(request.GET.get("page"))
    return render(request, "attendance/session_list.html", {
        "page_obj": page_obj,
        "selected_status": selected_status,
        "status_choices": AttendanceSession.STATUS_CHOICES,
        "session_count": sessions.count(),
    })


@lecturer_required
@require_http_methods(["GET", "POST"])
def attendance_session_create(request):
    form = AttendanceSessionForm(
        request.POST or None,
        lecturer_profile=request.user.profile,
        created_by=request.user,
    )
    if request.method == "POST" and form.is_valid():
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
            for error in exc.messages:
                form.add_error(None, error)
        else:
            messages.success(request, "Attendance session scheduled successfully.")
            return redirect("attendance_session_detail", pk=session.pk)
    return render(request, "attendance/session_form.html", {
        "form": form,
        "title": "Schedule attendance session",
        "submit_label": "Schedule session",
    })


@lecturer_required
def attendance_session_detail(request, pk):
    session = _get_manageable_session(request.user.profile, pk)
    registrations = session.offering.registrations.filter(
        status=CourseRegistration.STATUS_REGISTERED,
    ).select_related("student__user").order_by(
        "student__user__last_name", "student__user__first_name", "student__user__username"
    )
    records = session.records.select_related("student__user").order_by(
        "student__user__last_name", "student__user__first_name"
    )
    present_student_ids = set(records.values_list("student_id", flat=True))
    return render(request, "attendance/session_detail.html", {
        "session": session,
        "registrations": registrations,
        "records": records,
        "present_student_ids": present_student_ids,
        "registered_count": registrations.count(),
        "attendance_count": records.count(),
        "is_expired": session.is_expired,
        "now": timezone.now(),
    })


def _run_session_action(request, pk, service, success_message):
    try:
        service(session_id=pk, lecturer_profile=request.user.profile)
    except AttendanceSession.DoesNotExist:
        return render(request, "errors/404.html", status=404)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, success_message)
    return redirect("attendance_session_detail", pk=pk)


@lecturer_required
@require_POST
def attendance_session_activate(request, pk):
    return _run_session_action(
        request, pk, activate_attendance_session,
        "Attendance session activated. QR and facial verification will be enabled in a subsequent release.",
    )


@lecturer_required
@require_POST
def attendance_session_close(request, pk):
    return _run_session_action(
        request, pk, close_attendance_session,
        "Attendance session closed.",
    )


@lecturer_required
@require_POST
def attendance_session_cancel(request, pk):
    return _run_session_action(
        request, pk, cancel_attendance_session,
        "Scheduled attendance session cancelled.",
    )
