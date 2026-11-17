import csv
import time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .session_csv_import import (
    SESSION_COLUMNS,
    apply_session_import_plan,
    build_session_import_plan,
    parse_session_csv,
)
from .views import admin_required


SESSION_CSV_PREVIEW_KEY = "rollnexa_academic_session_csv_preview"
SESSION_CSV_PREVIEW_MAX_AGE = 15 * 60


@admin_required
@require_http_methods(["GET", "POST"])
def academic_session_csv_import(request):
    context = {
        "title": "Import academic sessions and semesters",
        "errors": [],
        "preview": None,
    }

    if request.method == "POST":
        action = request.POST.get("action", "preview")

        if action == "preview":
            request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
            rows, parse_errors = parse_session_csv(request.FILES.get("csv_file"))
            if parse_errors:
                context["errors"] = parse_errors
                return render(request, "academics/import_sessions_csv.html", context, status=400)

            plan, counts, plan_errors = build_session_import_plan(rows)
            if plan_errors:
                context["errors"] = plan_errors
                context["counts"] = counts
                return render(request, "academics/import_sessions_csv.html", context, status=400)

            request.session[SESSION_CSV_PREVIEW_KEY] = {
                "created_at": time.time(),
                "user_id": request.user.pk,
                "rows": rows,
            }
            context["preview"] = counts
            context["sample_rows"] = [
                {
                    "session": item["session_name"],
                    "semester": item["name"].title(),
                    "start": item["start_date"] or "Not specified",
                    "end": item["end_date"] or "Not specified",
                    "action": "New" if item["existing_id"] is None else "Unchanged",
                }
                for item in plan["semesters"][:20]
            ]
            context["rows_truncated"] = len(plan["semesters"]) > 20
            return render(request, "academics/import_sessions_csv.html", context)

        if action == "cancel":
            request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
            messages.info(request, "Academic session CSV preview cancelled. No records were changed.")
            return redirect("academic_session_csv_import")

        if action == "import":
            pending = request.session.get(SESSION_CSV_PREVIEW_KEY)
            if (
                not pending
                or pending.get("user_id") != request.user.pk
                or time.time() - pending.get("created_at", 0) > SESSION_CSV_PREVIEW_MAX_AGE
            ):
                request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
                messages.error(request, "The academic session CSV preview expired. Upload the file again.")
                return redirect("academic_session_csv_import")

            plan, counts, plan_errors = build_session_import_plan(pending.get("rows", []))
            if plan_errors:
                request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
                context["errors"] = plan_errors
                return render(request, "academics/import_sessions_csv.html", context, status=400)

            try:
                result = apply_session_import_plan(plan)
            except (IntegrityError, ValidationError) as exc:
                request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
                messages.error(
                    request,
                    f"The import was rolled back because an academic session or semester failed validation: {exc}",
                )
                return redirect("academic_session_csv_import")

            request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
            messages.success(
                request,
                "Academic calendar import completed: "
                f"{result['sessions_created']} sessions created, "
                f"{result['semesters_created']} semesters created; "
                f"{result['sessions_unchanged']} sessions and "
                f"{result['semesters_unchanged']} semesters already present. "
                "No session or semester was automatically marked current."
            )
            return redirect("academic_list", kind="sessions")

        context["errors"] = ["Unknown import action. Upload the CSV again."]
        return render(request, "academics/import_sessions_csv.html", context, status=400)

    pending = request.session.get(SESSION_CSV_PREVIEW_KEY)
    if pending:
        if (
            pending.get("user_id") == request.user.pk
            and time.time() - pending.get("created_at", 0) <= SESSION_CSV_PREVIEW_MAX_AGE
        ):
            plan, counts, errors = build_session_import_plan(pending.get("rows", []))
            if not errors:
                context["preview"] = counts
                context["sample_rows"] = [
                    {
                        "session": item["session_name"],
                        "semester": item["name"].title(),
                        "start": item["start_date"] or "Not specified",
                        "end": item["end_date"] or "Not specified",
                        "action": "New" if item["existing_id"] is None else "Unchanged",
                    }
                    for item in plan["semesters"][:20]
                ]
                context["rows_truncated"] = len(plan["semesters"]) > 20
            else:
                context["errors"] = errors
                request.session.pop(SESSION_CSV_PREVIEW_KEY, None)
        else:
            request.session.pop(SESSION_CSV_PREVIEW_KEY, None)

    return render(request, "academics/import_sessions_csv.html", context)


@admin_required
def academic_session_csv_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="rollnexa_academic_sessions_template.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(SESSION_COLUMNS + ["source_url", "source_note"])
    return response
