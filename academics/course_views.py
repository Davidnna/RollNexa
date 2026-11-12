from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import UserProfile
from .course_forms import (
    CourseForm, CourseOfferingForm, LecturerAssignmentForm, TeachingAssignmentCreateForm,
)
from .models import (
    Course, CourseLecturerAssignment, CourseOffering, CourseRegistration,
)


def _access_denied(request):
    return render(request, "accounts/access_denied.html", status=403)


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return _access_denied(request)
        return view_func(request, *args, **kwargs)
    return wrapped


def student_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.is_superuser or request.user.profile.role != UserProfile.ROLE_STUDENT:
            return _access_denied(request)
        return view_func(request, *args, **kwargs)
    return wrapped


def lecturer_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.is_superuser or request.user.profile.role != UserProfile.ROLE_LECTURER:
            return _access_denied(request)
        return view_func(request, *args, **kwargs)
    return wrapped


@admin_required
def course_management(request):
    context = {
        "course_count": Course.objects.filter(is_active=True).count(),
        "offering_count": CourseOffering.objects.filter(is_active=True).count(),
        "open_offering_count": CourseOffering.objects.filter(
            is_active=True, registration_open=True
        ).count(),
        "registration_count": CourseRegistration.objects.filter(
            status=CourseRegistration.STATUS_REGISTERED
        ).count(),
        "lecturer_assignment_count": CourseLecturerAssignment.objects.filter(
            is_active=True, offering__is_active=True, lecturer__user__is_active=True
        ).count(),
    }
    return render(request, "courses/overview.html", context)


@admin_required
def course_catalogue(request):
    courses = Course.objects.select_related("department", "department__faculty").all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        courses = courses.filter(
            Q(code__icontains=query)
            | Q(title__icontains=query)
            | Q(department__name__icontains=query)
            | Q(department__faculty__name__icontains=query)
        )
    if status == "active":
        courses = courses.filter(is_active=True)
    elif status == "inactive":
        courses = courses.filter(is_active=False)
    page_obj = Paginator(courses, 25).get_page(request.GET.get("page"))
    return render(request, "courses/course_list.html", {
        "page_obj": page_obj, "search": query, "selected_status": status,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            course = form.save()
            messages.success(request, f"{course.code} — {course.title} was added to the catalogue.")
            return redirect("course_catalogue")
        except IntegrityError:
            form.add_error(None, "That course code is already used in the selected department.")
    return render(request, "courses/course_form.html", {
        "form": form, "title": "Add a course", "submit_label": "Create course",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        try:
            course = form.save()
            messages.success(request, f"{course.code} — {course.title} was updated.")
            return redirect("course_catalogue")
        except IntegrityError:
            form.add_error(None, "That course code is already used in the selected department.")
    return render(request, "courses/course_form.html", {
        "form": form, "title": f"Edit {course.code}", "submit_label": "Save changes",
    })


@admin_required
@require_POST
def course_toggle(request, pk):
    course = get_object_or_404(Course.objects.select_related("department", "department__faculty"), pk=pk)
    if not course.is_active:
        if not course.department.is_active or not course.department.faculty.is_active:
            messages.error(request, "Reactivate the course's department and faculty first.")
            return redirect("course_catalogue")
    with transaction.atomic():
        course.is_active = not course.is_active
        course.save(update_fields=["is_active", "updated_at"])
        if not course.is_active:
            CourseOffering.objects.filter(course=course, is_active=True).update(
                is_active=False, registration_open=False
            )
    messages.success(
        request,
        f"{course.code} was {'activated' if course.is_active else 'deactivated'}.",
    )
    return redirect("course_catalogue")


@admin_required
def offering_list(request):
    offerings = CourseOffering.objects.select_related(
        "course", "course__department", "programme", "semester", "semester__session"
    ).annotate(
        registered_count=Count(
            "registrations",
            filter=Q(registrations__status=CourseRegistration.STATUS_REGISTERED),
            distinct=True,
        )
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    session = request.GET.get("session", "").strip()
    if query:
        offerings = offerings.filter(
            Q(course__code__icontains=query)
            | Q(course__title__icontains=query)
            | Q(programme__name__icontains=query)
            | Q(course__department__name__icontains=query)
        )
    if status == "open":
        offerings = offerings.filter(is_active=True, registration_open=True)
    elif status == "closed":
        offerings = offerings.filter(registration_open=False)
    elif status == "inactive":
        offerings = offerings.filter(is_active=False)
    if session:
        offerings = offerings.filter(semester__session__name=session)
    page_obj = Paginator(offerings, 25).get_page(request.GET.get("page"))
    from .models import AcademicSession
    sessions = AcademicSession.objects.order_by("-name")
    return render(request, "courses/offering_list.html", {
        "page_obj": page_obj, "search": query, "selected_status": status,
        "selected_session": session, "sessions": sessions,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def offering_create(request):
    form = CourseOfferingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            offering = form.save()
            messages.success(request, f"Offering for {offering.course.code} was created.")
            return redirect("offering_detail", pk=offering.pk)
        except IntegrityError:
            form.add_error(None, "This course is already offered to that programme, semester and level.")
    return render(request, "courses/offering_form.html", {
        "form": form, "title": "Create a course offering", "submit_label": "Create offering",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def offering_edit(request, pk):
    offering = get_object_or_404(CourseOffering, pk=pk)
    form = CourseOfferingForm(request.POST or None, instance=offering)
    if request.method == "POST" and form.is_valid():
        try:
            offering = form.save()
            messages.success(request, "Course offering updated successfully.")
            return redirect("offering_detail", pk=offering.pk)
        except IntegrityError:
            form.add_error(None, "This course is already offered to that programme, semester and level.")
    return render(request, "courses/offering_form.html", {
        "form": form, "title": f"Edit offering: {offering.course.code}",
        "submit_label": "Save changes",
    })


@admin_required
@require_POST
def offering_toggle(request, pk):
    offering = get_object_or_404(
        CourseOffering.objects.select_related(
            "course__department__faculty", "programme__department__faculty", "semester__session"
        ), pk=pk
    )
    if not offering.is_active and (
        not offering.course.is_active
        or not offering.course.department.is_active
        or not offering.course.department.faculty.is_active
        or not offering.programme.is_active
        or not offering.programme.department.is_active
        or not offering.programme.department.faculty.is_active
        or not offering.semester.is_active
        or not offering.semester.session.is_active
    ):
        messages.error(request, "Reactivate the course, programme, department, faculty and academic period before reactivating this offering.")
        return redirect("offering_list")
    with transaction.atomic():
        offering.is_active = not offering.is_active
        if not offering.is_active:
            offering.registration_open = False
        offering.save(update_fields=["is_active", "registration_open", "updated_at"])
    messages.success(
        request,
        "Course offering " + ("activated." if offering.is_active else "deactivated and registration closed."),
    )
    return redirect("offering_list")


@admin_required
def offering_detail(request, pk):
    offering = get_object_or_404(
        CourseOffering.objects.select_related(
            "course", "course__department", "programme", "semester", "semester__session"
        ).prefetch_related("lecturer_assignments__lecturer__user"),
        pk=pk,
    )
    assignment_form = LecturerAssignmentForm(offering=offering)
    registered_count = offering.registrations.filter(
        status=CourseRegistration.STATUS_REGISTERED
    ).count()
    assignments = offering.lecturer_assignments.filter(
        is_active=True
    ).select_related("lecturer__user", "lecturer__department")
    assignment_history = offering.lecturer_assignments.filter(
        is_active=False
    ).select_related("lecturer__user", "lecturer__department", "removed_by").order_by("-removed_at", "-assigned_at")
    return render(request, "courses/offering_detail.html", {
        "offering": offering,
        "assignment_form": assignment_form,
        "registered_count": registered_count,
        "assignments": assignments,
        "assignment_history": assignment_history,
    })


@admin_required
@require_POST
def offering_assign_lecturer(request, pk):
    offering = get_object_or_404(CourseOffering, pk=pk)
    form = LecturerAssignmentForm(request.POST)
    if form.is_valid():
        lecturer = form.cleaned_data["lecturer"]
        assignment = CourseLecturerAssignment(
            offering=offering, lecturer=lecturer, assigned_by=request.user
        )
        try:
            assignment.full_clean()
            assignment.save()
            if lecturer.department_id != offering.course.department_id:
                messages.success(
                    request,
                    "Lecturer assigned. This is a permitted cross-department teaching assignment; "
                    "the lecturer's home department has been retained.",
                )
            else:
                messages.success(request, "Lecturer assigned to the course offering.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        except IntegrityError:
            messages.info(request, "That lecturer is already assigned to this offering.")
    else:
        messages.error(request, "Select a valid active lecturer account.")
    return redirect("offering_detail", pk=pk)


@admin_required
@require_POST
def offering_remove_lecturer(request, pk, assignment_id):
    assignment = get_object_or_404(
        CourseLecturerAssignment, pk=assignment_id, offering_id=pk
    )
    if not assignment.is_active:
        messages.info(request, "This lecturer assignment has already been removed.")
        return redirect("offering_detail", pk=pk)
    assignment.is_active = False
    assignment.removed_at = timezone.now()
    assignment.removed_by = request.user
    assignment.removal_note = request.POST.get("removal_note", "").strip()[:240]
    assignment.save(update_fields=["is_active", "removed_at", "removed_by", "removal_note"])
    messages.success(request, "Lecturer assignment removed. Its history has been retained.")
    return redirect("offering_detail", pk=pk)


@admin_required
@require_http_methods(["GET", "POST"])
def teaching_assignment_management(request):
    assignment_form = TeachingAssignmentCreateForm(request.POST or None)
    if request.method == "POST" and assignment_form.is_valid():
        offering = assignment_form.cleaned_data["offering"]
        lecturer = assignment_form.cleaned_data["lecturer"]
        assignment = CourseLecturerAssignment(
            offering=offering, lecturer=lecturer, assigned_by=request.user
        )
        try:
            assignment.full_clean()
            assignment.save()
            if lecturer.department_id != offering.course.department_id:
                messages.success(
                    request,
                    "Cross-department teaching assignment created. The lecturer's home department "
                    "remains unchanged.",
                )
            else:
                messages.success(request, "Teaching assignment created successfully.")
            return redirect("teaching_assignment_management")
        except ValidationError as exc:
            assignment_form.add_error(None, "; ".join(exc.messages))
        except IntegrityError:
            assignment_form.add_error("lecturer", "That lecturer is already assigned to this offering.")

    assignments = CourseLecturerAssignment.objects.select_related(
        "offering__course", "offering__course__department", "offering__programme",
        "offering__semester", "offering__semester__session", "lecturer__user",
        "lecturer__department", "assigned_by", "removed_by",
    )
    status = request.GET.get("status", "active").strip()
    if status == "active":
        assignments = assignments.filter(is_active=True)
    elif status == "history":
        assignments = assignments.filter(is_active=False)
    elif status != "all":
        status = "active"
        assignments = assignments.filter(is_active=True)

    query = request.GET.get("q", "").strip()
    if query:
        assignments = assignments.filter(
            Q(lecturer__user__first_name__icontains=query)
            | Q(lecturer__user__last_name__icontains=query)
            | Q(lecturer__user__username__icontains=query)
            | Q(lecturer__institutional_id__icontains=query)
            | Q(offering__course__code__icontains=query)
            | Q(offering__course__title__icontains=query)
            | Q(offering__programme__name__icontains=query)
            | Q(lecturer__department__name__icontains=query)
            | Q(offering__course__department__name__icontains=query)
        )

    page_obj = Paginator(assignments.order_by("-assigned_at", "-pk"), 30).get_page(
        request.GET.get("page")
    )
    return render(request, "courses/teaching_assignment_list.html", {
        "assignment_form": assignment_form,
        "page_obj": page_obj,
        "search": query,
        "selected_status": status,
        "active_assignment_count": CourseLecturerAssignment.objects.filter(
            is_active=True, lecturer__user__is_active=True
        ).count(),
        "history_count": CourseLecturerAssignment.objects.filter(is_active=False).count(),
    })


@admin_required
@require_POST
def teaching_assignment_revoke(request, assignment_id):
    assignment = get_object_or_404(
        CourseLecturerAssignment.objects.select_related("offering__course", "lecturer__user"),
        pk=assignment_id,
    )
    if not assignment.is_active:
        messages.info(request, "This assignment is already in the history archive.")
        return redirect("teaching_assignment_management")
    assignment.is_active = False
    assignment.removed_at = timezone.now()
    assignment.removed_by = request.user
    assignment.removal_note = request.POST.get("removal_note", "").strip()[:240]
    assignment.save(update_fields=["is_active", "removed_at", "removed_by", "removal_note"])
    messages.success(request, "Teaching assignment revoked and retained in the audit history.")
    return redirect("teaching_assignment_management")


@admin_required
def offering_registrations(request, pk):
    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "programme", "semester", "semester__session"),
        pk=pk,
    )
    registrations = offering.registrations.filter(
        status=CourseRegistration.STATUS_REGISTERED
    ).select_related("student__user", "student__programme")
    query = request.GET.get("q", "").strip()
    if query:
        registrations = registrations.filter(
            Q(student__user__username__icontains=query)
            | Q(student__user__first_name__icontains=query)
            | Q(student__user__last_name__icontains=query)
            | Q(student__institutional_id__icontains=query)
        )
    page_obj = Paginator(registrations, 50).get_page(request.GET.get("page"))
    return render(request, "courses/registration_list.html", {
        "offering": offering, "page_obj": page_obj, "search": query,
    })


@student_required
def student_course_list(request):
    profile = request.user.profile
    if not profile.programme_id or not profile.current_level:
        return render(request, "courses/student_courses.html", {
            "profile_incomplete": True, "offerings": [],
        })
    registered = CourseRegistration.objects.filter(
        offering=OuterRef("pk"), student=profile,
        status=CourseRegistration.STATUS_REGISTERED,
    )
    offerings = CourseOffering.objects.filter(
        is_active=True,
        course__is_active=True,
        programme_id=profile.programme_id,
        level=profile.current_level,
        programme__is_active=True,
        programme__department__is_active=True,
        programme__department__faculty__is_active=True,
        course__department__is_active=True,
        course__department__faculty__is_active=True,
        semester__is_active=True,
        semester__session__is_active=True,
    ).select_related(
        "course", "course__department", "programme", "semester", "semester__session"
    ).annotate(is_registered=Exists(registered))
    query = request.GET.get("q", "").strip()
    if query:
        offerings = offerings.filter(
            Q(course__code__icontains=query) | Q(course__title__icontains=query)
        )
    my_registrations = CourseRegistration.objects.filter(
        student=profile
    ).select_related(
        "offering__course", "offering__programme", "offering__semester",
        "offering__semester__session",
    )
    return render(request, "courses/student_courses.html", {
        "profile_incomplete": False,
        "offerings": offerings,
        "my_registrations": my_registrations,
        "search": query,
    })


@student_required
@require_POST
def student_course_register(request, pk):
    profile = request.user.profile
    if not profile.programme_id or not profile.current_level:
        messages.error(request, "Your academic programme and current level must be set before course registration.")
        return redirect("student_course_list")

    try:
        with transaction.atomic():
            offering = get_object_or_404(
                CourseOffering.objects.select_for_update().select_related(
                    "course__department__faculty", "programme__department__faculty", "semester", "semester__session"
                ),
                pk=pk,
                programme_id=profile.programme_id,
                level=profile.current_level,
                is_active=True,
            )
            if not offering.registration_open:
                messages.error(request, "Registration is closed for this course offering.")
                return redirect("student_course_list")

            registration = CourseRegistration.objects.filter(
                offering=offering, student=profile
            ).first()
            if registration and registration.status == CourseRegistration.STATUS_REGISTERED:
                messages.info(request, "You are already registered for this course.")
                return redirect("student_course_list")

            current_count = offering.registrations.filter(
                status=CourseRegistration.STATUS_REGISTERED
            ).count()
            if offering.max_students and current_count >= offering.max_students:
                messages.error(request, "This course offering has reached its registration limit.")
                return redirect("student_course_list")

            if registration:
                registration.status = CourseRegistration.STATUS_REGISTERED
                registration.full_clean()
                registration.save(update_fields=["status", "updated_at"])
            else:
                registration = CourseRegistration(offering=offering, student=profile)
                registration.full_clean()
                registration.save()
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("student_course_list")
    except IntegrityError:
        messages.info(request, "Your registration has already been recorded.")
        return redirect("student_course_list")

    messages.success(request, "Course registration completed.")
    return redirect("student_course_list")


@student_required
@require_POST
def student_course_withdraw(request, pk):
    profile = request.user.profile
    with transaction.atomic():
        registration = get_object_or_404(
            CourseRegistration.objects.select_for_update().select_related("offering"),
            offering_id=pk,
            student=profile,
            status=CourseRegistration.STATUS_REGISTERED,
        )
        if not registration.offering.registration_open:
            messages.error(request, "Withdrawal is closed for this course offering.")
            return redirect("student_course_list")
        registration.status = CourseRegistration.STATUS_WITHDRAWN
        registration.save(update_fields=["status", "updated_at"])
    messages.success(request, "You have withdrawn from the course.")
    return redirect("student_course_list")


@lecturer_required
def lecturer_course_list(request):
    profile = request.user.profile
    assignments = CourseLecturerAssignment.objects.filter(
        lecturer=profile,
        is_active=True,
        offering__is_active=True,
    ).select_related(
        "offering__course", "offering__programme", "offering__semester",
        "offering__semester__session",
    ).annotate(
        registered_count=Count(
            "offering__registrations",
            filter=Q(offering__registrations__status=CourseRegistration.STATUS_REGISTERED),
            distinct=True,
        )
    )
    return render(request, "courses/lecturer_courses.html", {"assignments": assignments})


@lecturer_required
def lecturer_course_roster(request, pk):
    profile = request.user.profile
    offering = get_object_or_404(
        CourseOffering.objects.filter(
            lecturer_assignments__lecturer=profile,
            lecturer_assignments__is_active=True,
            is_active=True,
        ).select_related("course", "programme", "semester", "semester__session"),
        pk=pk,
    )
    registrations = offering.registrations.filter(
        status=CourseRegistration.STATUS_REGISTERED
    ).select_related("student__user")
    return render(request, "courses/lecturer_roster.html", {
        "offering": offering, "registrations": registrations,
    })
