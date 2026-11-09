import time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .course_views import admin_required
from .course_csv_import import (
    COURSE_COLUMNS, apply_course_import_plan, build_course_import_plan,
    parse_course_csv,
)


COURSE_CSV_PREVIEW_KEY = "rollnexa_course_csv_preview"
COURSE_CSV_PREVIEW_MAX_AGE = 15 * 60


@admin_required
@require_http_methods(["GET", "POST"])
def course_csv_import(request):
    context = {"title": "Import courses and offerings", "errors": [], "preview": None}

    if request.method == "POST":
        action = request.POST.get("action", "preview")

        if action == "preview":
            request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
            uploaded = request.FILES.get("csv_file")
            rows, parse_errors = parse_course_csv(uploaded)
            if parse_errors:
                context["errors"] = parse_errors
                return render(request, "courses/import_csv.html", context, status=400)

            plan, counts, plan_errors = build_course_import_plan(rows)
            if plan_errors:
                context["errors"] = plan_errors
                context["counts"] = counts
                return render(request, "courses/import_csv.html", context, status=400)

            request.session[COURSE_CSV_PREVIEW_KEY] = {
                "created_at": time.time(),
                "user_id": request.user.pk,
                "rows": rows,
            }
            context["preview"] = counts
            context["sample_rows"] = [
                {
                    "code": item["code"],
                    "title": item["title"],
                    "department": item["department_code"],
                    "course_action": "New" if item["existing_id"] is None else "Unchanged",
                }
                for item in plan["courses"][:15]
            ]
            course_lookup = {
                (item["faculty_code"], item["department_code"], item["code"]): item["code"]
                for item in plan["courses"]
            }
            context["sample_offerings"] = [
                {
                    "code": course_lookup.get(item["course_key"], ""),
                    "programme": item["programme_code"],
                    "session": item["session_name_resolved"],
                    "semester": item["semester_label"],
                    "level": item["level"],
                    "action": "New" if item["existing_id"] is None else "Unchanged",
                }
                for item in plan["offerings"][:15]
            ]
            context["courses_truncated"] = len(plan["courses"]) > 15
            context["offerings_truncated"] = len(plan["offerings"]) > 15
            return render(request, "courses/import_csv.html", context)

        if action == "cancel":
            request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
            messages.info(request, "Course CSV preview cancelled. No records were changed.")
            return redirect("course_csv_import")

        if action == "import":
            pending = request.session.get(COURSE_CSV_PREVIEW_KEY)
            if (
                not pending
                or pending.get("user_id") != request.user.pk
                or time.time() - pending.get("created_at", 0) > COURSE_CSV_PREVIEW_MAX_AGE
            ):
                request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
                messages.error(request, "The course CSV preview expired. Upload the file again.")
                return redirect("course_csv_import")

            plan, counts, plan_errors = build_course_import_plan(pending.get("rows", []))
            if plan_errors:
                request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
                context["errors"] = plan_errors
                return render(request, "courses/import_csv.html", context, status=400)

            try:
                result = apply_course_import_plan(plan)
            except (IntegrityError, ValidationError) as exc:
                request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
                messages.error(
                    request,
                    f"The import was rolled back because a course or offering failed validation: {exc}",
                )
                return redirect("course_csv_import")

            request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
            messages.success(
                request,
                "Course import completed: "
                f"{result['courses_created']} courses created, "
                f"{result['courses_unchanged']} already present; "
                f"{result['offerings_created']} offerings created, "
                f"{result['offerings_unchanged']} already present. "
                "Registration remains closed on imported offerings."
            )
            return redirect("course_management")

        context["errors"] = ["Unknown import action. Upload the CSV again."]
        return render(request, "courses/import_csv.html", context, status=400)

    pending = request.session.get(COURSE_CSV_PREVIEW_KEY)
    if pending:
        if (
            pending.get("user_id") == request.user.pk
            and time.time() - pending.get("created_at", 0) <= COURSE_CSV_PREVIEW_MAX_AGE
        ):
            plan, counts, errors = build_course_import_plan(pending.get("rows", []))
            if not errors:
                context["preview"] = counts
                context["sample_rows"] = [
                    {
                        "code": item["code"],
                        "title": item["title"],
                        "department": item["department_code"],
                        "course_action": "New" if item["existing_id"] is None else "Unchanged",
                    }
                    for item in plan["courses"][:15]
                ]
                course_lookup = {
                    (item["faculty_code"], item["department_code"], item["code"]): item["code"]
                    for item in plan["courses"]
                }
                context["sample_offerings"] = [
                    {
                        "code": course_lookup.get(item["course_key"], ""),
                        "programme": item["programme_code"],
                        "session": item["session_name_resolved"],
                        "semester": item["semester_label"],
                        "level": item["level"],
                        "action": "New" if item["existing_id"] is None else "Unchanged",
                    }
                    for item in plan["offerings"][:15]
                ]
                context["courses_truncated"] = len(plan["courses"]) > 15
                context["offerings_truncated"] = len(plan["offerings"]) > 15
            else:
                context["errors"] = errors
                request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
        else:
            request.session.pop(COURSE_CSV_PREVIEW_KEY, None)
    return render(request, "courses/import_csv.html", context)


@admin_required
def course_csv_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rollnexa_course_catalogue_template.csv"'
    response.write("\ufeff")
    import csv
    writer = csv.writer(response)
    writer.writerow(COURSE_COLUMNS + ["description", "source_url", "source_note"])
    writer.writerow([
        "FSC", "FSC-CS", "CSC 101", "Introduction to Computer Science", "2", "C",
        "FSC-CS-P01", "CURRENT", "FIRST", "100", "true", "false", "",
        "", "https://ebsu.edu.ng/department-of-computer-science/",
        "Replace or retain source note as appropriate.",
    ])
    return response
