import csv
import time
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone

from .forms import AcademicSessionForm, DepartmentForm, FacultyForm, ProgrammeForm, SemesterForm
from .models import AcademicSession, Course, CourseOffering, Department, Faculty, Programme, Semester
from .csv_import import ACADEMIC_COLUMNS, apply_import_plan, build_import_plan, parse_academic_csv


ACADEMIC_CONFIG = {
    "faculties": {
        "model": Faculty, "form": FacultyForm, "singular": "Faculty", "plural": "Faculties",
        "headers": ["CODE", "FACULTY", "DEPARTMENTS", "STATUS"],
        "search": ("code", "name"),
    },
    "departments": {
        "model": Department, "form": DepartmentForm, "singular": "Department", "plural": "Departments",
        "headers": ["CODE", "DEPARTMENT", "FACULTY", "PROGRAMMES", "STATUS"],
        "search": ("code", "name", "faculty__name"),
    },
    "programmes": {
        "model": Programme, "form": ProgrammeForm, "singular": "Programme", "plural": "Programmes",
        "headers": ["CODE", "PROGRAMME", "DEPARTMENT", "AWARD", "STATUS"],
        "search": ("code", "name", "department__name", "department__faculty__name"),
    },
    "sessions": {
        "model": AcademicSession, "form": AcademicSessionForm, "singular": "Academic session", "plural": "Academic sessions",
        "headers": ["SESSION", "START", "END", "CURRENT", "STATUS"],
        "search": ("name",),
    },
    "semesters": {
        "model": Semester, "form": SemesterForm, "singular": "Semester", "plural": "Semesters",
        "headers": ["SEMESTER", "SESSION", "START", "END", "CURRENT", "STATUS"],
        "search": ("name", "session__name"),
    },
}


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "accounts/access_denied.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


def _config(kind):
    try:
        return ACADEMIC_CONFIG[kind]
    except KeyError:
        raise Http404("Unknown academic resource.")


@admin_required
def academic_overview(request):
    context = {
        "faculty_count": Faculty.objects.filter(is_active=True).count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "programme_count": Programme.objects.filter(is_active=True).count(),
        "session_count": AcademicSession.objects.filter(is_active=True).count(),
        "semester_count": Semester.objects.filter(is_active=True).count(),
        "current_session": AcademicSession.objects.filter(is_current=True, is_active=True).first(),
        "current_semester": Semester.objects.filter(is_current=True, is_active=True).select_related("session").first(),
    }
    return render(request, "academics/overview.html", context)


def _rows(kind, objects):
    rows = []
    for obj in objects:
        if kind == "faculties":
            cells = [obj.code, obj.name, obj.departments.filter(is_active=True).count(), "Active" if obj.is_active else "Inactive"]
        elif kind == "departments":
            cells = [obj.code, obj.name, obj.faculty.name, obj.programmes.filter(is_active=True).count(), "Active" if obj.is_active else "Inactive"]
        elif kind == "programmes":
            cells = [obj.code, obj.name, obj.department.name, obj.award or "Not specified", "Active" if obj.is_active else "Inactive"]
        elif kind == "sessions":
            cells = [obj.name, obj.start_date or "—", obj.end_date or "—", "Current" if obj.is_current else "—", "Active" if obj.is_active else "Inactive"]
        else:
            cells = [obj.get_name_display(), obj.session.name, obj.start_date or "—", obj.end_date or "—", "Current" if obj.is_current else "—", "Active" if obj.is_active else "Inactive"]
        rows.append({
            "id": obj.pk,
            "cells": cells,
            "is_active": obj.is_active,
            "is_current": getattr(obj, "is_current", False),
            "edit_url": f"/management/academic/{kind}/{obj.pk}/edit/",
            "toggle_url": f"/management/academic/{kind}/{obj.pk}/toggle/",
            "current_url": f"/management/academic/{kind}/{obj.pk}/set-current/" if kind in {"sessions", "semesters"} else None,
        })
    return rows


@admin_required
def academic_list(request, kind):
    config = _config(kind)
    model = config["model"]
    objects = model.objects.all()
    if kind == "departments":
        objects = objects.select_related("faculty")
    elif kind == "programmes":
        objects = objects.select_related("department", "department__faculty")
    elif kind == "semesters":
        objects = objects.select_related("session")

    query = request.GET.get("q", "").strip()
    if query:
        condition = Q()
        for field in config["search"]:
            condition |= Q(**{f"{field}__icontains": query})
        objects = objects.filter(condition)

    status = request.GET.get("status", "")
    if status == "active":
        objects = objects.filter(is_active=True)
    elif status == "inactive":
        objects = objects.filter(is_active=False)

    page_obj = Paginator(objects, 20).get_page(request.GET.get("page"))
    return render(request, "academics/list.html", {
        "kind": kind,
        "title": config["plural"],
        "singular": config["singular"],
        "headers": config["headers"],
        "rows": _rows(kind, page_obj.object_list),
        "page_obj": page_obj,
        "search": query,
        "selected_status": status,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def academic_create(request, kind):
    config = _config(kind)
    form = config["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, f"{config['singular']} created successfully.")
            return redirect("academic_list", kind=kind)
        except IntegrityError:
            form.add_error(None, "A record with the same code or name already exists in this academic structure.")
    return render(request, "academics/form.html", {
        "form": form, "title": f"Create {config['singular']}", "kind": kind,
        "back_url": f"/management/academic/{kind}/", "submit_label": "Create record",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def academic_edit(request, kind, pk):
    config = _config(kind)
    obj = get_object_or_404(config["model"], pk=pk)
    form = config["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, f"{config['singular']} updated successfully.")
            return redirect("academic_list", kind=kind)
        except IntegrityError:
            form.add_error(None, "A record with the same code or name already exists in this academic structure.")
    return render(request, "academics/form.html", {
        "form": form, "title": f"Edit {config['singular']}", "kind": kind,
        "back_url": f"/management/academic/{kind}/", "submit_label": "Save changes",
    })


@admin_required
@require_POST
def academic_toggle(request, kind, pk):
    config = _config(kind)
    obj = get_object_or_404(config["model"], pk=pk)
    if isinstance(obj, Department) and not obj.is_active and not obj.faculty.is_active:
        messages.error(request, "Reactivate the parent faculty before reactivating this department.")
        return redirect("academic_list", kind=kind)
    if isinstance(obj, Programme) and not obj.is_active and (not obj.department.is_active or not obj.department.faculty.is_active):
        messages.error(request, "Reactivate the parent department and faculty before reactivating this programme.")
        return redirect("academic_list", kind=kind)
    obj.is_active = not obj.is_active
    with transaction.atomic():
        if isinstance(obj, AcademicSession) and not obj.is_active:
            obj.is_current = False
            obj.save(update_fields=["is_active", "is_current", "updated_at"])
            Semester.objects.filter(session=obj, is_active=True).update(
                is_active=False, is_current=False, updated_at=timezone.now()
            )
            CourseOffering.objects.filter(semester__session=obj, is_active=True).update(
                is_active=False, registration_open=False, updated_at=timezone.now()
            )
        elif isinstance(obj, Semester) and not obj.is_active:
            obj.is_current = False
            obj.save(update_fields=["is_active", "is_current", "updated_at"])
            CourseOffering.objects.filter(semester=obj, is_active=True).update(
                is_active=False, registration_open=False, updated_at=timezone.now()
            )
        else:
            obj.save(update_fields=["is_active", "updated_at"])

        # Keep the hierarchy coherent: an inactive parent cannot have active
        # child records available for new academic assignments.
        if isinstance(obj, Faculty) and not obj.is_active:
            Department.objects.filter(faculty=obj, is_active=True).update(is_active=False, updated_at=timezone.now())
            Programme.objects.filter(department__faculty=obj, is_active=True).update(is_active=False, updated_at=timezone.now())
            Course.objects.filter(department__faculty=obj, is_active=True).update(is_active=False, updated_at=timezone.now())
            CourseOffering.objects.filter(
                Q(course__department__faculty=obj) | Q(programme__department__faculty=obj),
                is_active=True,
            ).update(is_active=False, registration_open=False, updated_at=timezone.now())
        elif isinstance(obj, Department) and not obj.is_active:
            Programme.objects.filter(department=obj, is_active=True).update(is_active=False, updated_at=timezone.now())
            Course.objects.filter(department=obj, is_active=True).update(is_active=False, updated_at=timezone.now())
            CourseOffering.objects.filter(
                Q(course__department=obj) | Q(programme__department=obj),
                is_active=True,
            ).update(is_active=False, registration_open=False, updated_at=timezone.now())
        elif isinstance(obj, Programme) and not obj.is_active:
            CourseOffering.objects.filter(programme=obj, is_active=True).update(
                is_active=False, registration_open=False, updated_at=timezone.now()
            )
    messages.success(request, f"{config['singular']} {'activated' if obj.is_active else 'deactivated'}.")
    return redirect("academic_list", kind=kind)


CSV_PREVIEW_SESSION_KEY = "rollnexa_academic_csv_preview"
CSV_PREVIEW_MAX_AGE_SECONDS = 15 * 60


def _csv_preview_rows(plan, limit=12):
    faculty_names = {item["code"]: item["name"] for item in plan["faculties"]}
    department_names = {
        (item["faculty_code"], item["code"]): item["name"]
        for item in plan["departments"]
    }
    preview_rows = []
    for item in plan["programmes"]:
        preview_rows.append({
            "faculty": faculty_names.get(item["faculty_code"], item["faculty_code"]),
            "department": department_names.get((item["faculty_code"], item["department_code"]), item["department_code"]),
            "programme": item["name"],
            "award": item["award"] or "Not specified",
        })
        if len(preview_rows) >= limit:
            break
    return preview_rows


@admin_required
def academic_csv_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rollnexa_academic_structure_template.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(ACADEMIC_COLUMNS + ["source_url", "source_session", "verification_status", "notes"])
    return response


@admin_required
@require_http_methods(["GET", "POST"])
def academic_csv_import(request):
    context = {"title": "Import academic structure", "errors": [], "preview": None}
    if request.method == "POST":
        action = request.POST.get("action", "preview")
        if action == "preview":
            request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
            uploaded = request.FILES.get("csv_file")
            rows, parse_errors = parse_academic_csv(uploaded)
            if parse_errors:
                context["errors"] = parse_errors
                return render(request, "academics/import_csv.html", context, status=400)
            plan, counts, plan_errors = build_import_plan(rows)
            if plan_errors:
                context["errors"] = plan_errors
                context["counts"] = counts
                return render(request, "academics/import_csv.html", context, status=400)
            request.session[CSV_PREVIEW_SESSION_KEY] = {
                "created_at": time.time(),
                "rows": rows,
            }
            context["preview"] = counts
            context["record_totals"] = {
                "faculties": len(plan["faculties"]),
                "departments": len(plan["departments"]),
                "programmes": len(plan["programmes"]),
            }
            context["sample_rows"] = _csv_preview_rows(plan)
            context["sample_rows_truncated"] = len(plan["programmes"]) > len(context["sample_rows"])
            return render(request, "academics/import_csv.html", context)

        if action == "cancel":
            request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
            messages.info(request, "CSV import preview cancelled. No records were changed.")
            return redirect("academic_csv_import")

        if action == "import":
            pending = request.session.get(CSV_PREVIEW_SESSION_KEY)
            if not pending or time.time() - pending.get("created_at", 0) > CSV_PREVIEW_MAX_AGE_SECONDS:
                request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
                messages.error(request, "The CSV preview has expired. Upload the file again.")
                return redirect("academic_csv_import")
            plan, counts, plan_errors = build_import_plan(pending.get("rows", []))
            if plan_errors:
                request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
                context["errors"] = plan_errors
                return render(request, "academics/import_csv.html", context, status=400)
            try:
                result = apply_import_plan(plan)
            except (IntegrityError, ValidationError) as exc:
                request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
                messages.error(request, f"The import was rolled back because a record failed validation: {exc}")
                return redirect("academic_csv_import")
            request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
            messages.success(
                request,
                "Import completed: "
                f"{result['faculties_created']} faculties, {result['departments_created']} departments and "
                f"{result['programmes_created']} programmes created; "
                f"{result['faculties_updated'] + result['departments_updated'] + result['programmes_updated']} records updated. "
                "Existing records not changed by this file were preserved."
            )
            return redirect("academic_overview")

        context["errors"] = ["Unknown import action. Upload the CSV again."]
        return render(request, "academics/import_csv.html", context, status=400)

    pending = request.session.get(CSV_PREVIEW_SESSION_KEY)
    if pending and time.time() - pending.get("created_at", 0) <= CSV_PREVIEW_MAX_AGE_SECONDS:
        plan, counts, errors = build_import_plan(pending.get("rows", []))
        if not errors:
            context["preview"] = counts
            context["record_totals"] = {
                "faculties": len(plan["faculties"]),
                "departments": len(plan["departments"]),
                "programmes": len(plan["programmes"]),
            }
            context["sample_rows"] = _csv_preview_rows(plan)
            context["sample_rows_truncated"] = len(plan["programmes"]) > len(context["sample_rows"])
        else:
            context["errors"] = errors
            request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
    elif pending:
        request.session.pop(CSV_PREVIEW_SESSION_KEY, None)
    return render(request, "academics/import_csv.html", context)


@admin_required
@require_POST
def set_current_session(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk)
    with transaction.atomic():
        AcademicSession.objects.filter(is_current=True).exclude(pk=session.pk).update(is_current=False, updated_at=timezone.now())
        Semester.objects.filter(is_current=True).update(is_current=False, updated_at=timezone.now())
        session.is_active = True
        session.is_current = True
        session.save(update_fields=["is_active", "is_current", "updated_at"])
    messages.success(request, f"{session.name} is now the current academic session.")
    return redirect("academic_list", kind="sessions")


@admin_required
@require_POST
def set_current_semester(request, pk):
    semester = get_object_or_404(Semester.objects.select_related("session"), pk=pk)
    if not semester.session.is_current or not semester.session.is_active:
        messages.error(request, "Set this semester's academic session as current before activating the semester.")
        return redirect("academic_list", kind="semesters")
    with transaction.atomic():
        Semester.objects.filter(is_current=True).exclude(pk=semester.pk).update(is_current=False, updated_at=timezone.now())
        semester.is_active = True
        semester.is_current = True
        semester.save(update_fields=["is_active", "is_current", "updated_at"])
    messages.success(request, f"{semester.get_name_display()} ({semester.session.name}) is now the current semester.")
    return redirect("academic_list", kind="semesters")
