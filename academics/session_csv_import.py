import csv
import io
import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AcademicSession, Semester


SESSION_COLUMNS = [
    "academic_session",
    "session_start_date",
    "session_end_date",
    "semester",
    "semester_start_date",
    "semester_end_date",
]
OPTIONAL_COLUMNS = ["source_url", "source_note"]
ALLOWED_COLUMNS = set(SESSION_COLUMNS + OPTIONAL_COLUMNS)
MAX_FILE_BYTES = 1_000_000
MAX_DATA_ROWS = 500
SESSION_PATTERN = re.compile(r"^(\d{4})/(\d{4})$")
SEMESTER_VALUES = {
    "FIRST": Semester.FIRST,
    "FIRST SEMESTER": Semester.FIRST,
    "1": Semester.FIRST,
    "SECOND": Semester.SECOND,
    "SECOND SEMESTER": Semester.SECOND,
    "2": Semester.SECOND,
    "SUMMER": Semester.SUMMER,
    "SUMMER SEMESTER": Semester.SUMMER,
}


def parse_session_csv(upload):
    if upload is None or not getattr(upload, "name", "").lower().endswith(".csv"):
        return [], ["Choose an academic sessions CSV file."]
    if upload.size > MAX_FILE_BYTES:
        return [], ["The CSV file exceeds the 1 MB upload limit."]

    try:
        raw = upload.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            return [], ["The CSV file exceeds the 1 MB upload limit."]
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["The CSV must use UTF-8 encoding. Save it as CSV UTF-8 and upload again."]
    except Exception:
        return [], ["The uploaded CSV could not be read."]

    try:
        reader = csv.DictReader(io.StringIO(content, newline=""))
        raw_headers = reader.fieldnames or []
        headers = [(header or "").strip().lower() for header in raw_headers]
        if not headers or any(not header for header in headers):
            return [], ["The CSV must contain a header row with column names."]
        if len(headers) != len(set(headers)):
            return [], ["The CSV contains duplicate column headings."]
        missing = [column for column in SESSION_COLUMNS if column not in headers]
        unknown = sorted(set(headers) - ALLOWED_COLUMNS)
        errors = []
        if missing:
            errors.append("Missing required columns: " + ", ".join(missing) + ".")
        if unknown:
            errors.append("Unrecognised column(s): " + ", ".join(unknown) + ".")
        if errors:
            return [], errors

        reader.fieldnames = headers
        rows = []
        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                errors.append(
                    f"Row {line_number}: the row contains more values than the CSV header defines."
                )
                continue
            row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in raw_row.items()
                if key is not None
            }
            if not any(row.values()):
                continue
            row["line_number"] = line_number
            rows.append(row)
            if len(rows) > MAX_DATA_ROWS:
                return [], [f"The CSV contains more than {MAX_DATA_ROWS} data rows."]
        if not rows:
            errors.append("The CSV has a header but no populated data rows.")
        return rows, errors
    except csv.Error as exc:
        return [], [f"Could not parse the CSV: {exc}"]


def _parse_date(value, label, line, errors):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"Row {line}: {label} must use YYYY-MM-DD format or be blank.")
        return None


def _merge_optional_date(target, field, value, label, line, errors):
    if value is None:
        return
    if target[field] is not None and target[field] != value:
        errors.append(
            f"Row {line}: conflicting {label} values are supplied for the same academic record."
        )
    else:
        target[field] = value


def build_session_import_plan(rows):
    errors = []
    sessions = {}
    semesters = {}

    for row in rows:
        line = row.get("line_number", "?")
        name = row.get("academic_session", "").strip()
        semester_raw = row.get("semester", "").strip().upper()

        match = SESSION_PATTERN.fullmatch(name)
        if not match:
            errors.append(
                f"Row {line}: academic_session must use YYYY/YYYY format, for example 2026/2027."
            )
            continue
        first_year, second_year = (int(part) for part in match.groups())
        if second_year != first_year + 1:
            errors.append(f"Row {line}: the ending year must be one year after the starting year.")
            continue

        semester = SEMESTER_VALUES.get(semester_raw)
        if not semester:
            errors.append(
                f"Row {line}: semester must be FIRST, SECOND or SUMMER."
            )
            continue

        session_start = _parse_date(
            row.get("session_start_date", ""), "session_start_date", line, errors
        )
        session_end = _parse_date(
            row.get("session_end_date", ""), "session_end_date", line, errors
        )
        semester_start = _parse_date(
            row.get("semester_start_date", ""), "semester_start_date", line, errors
        )
        semester_end = _parse_date(
            row.get("semester_end_date", ""), "semester_end_date", line, errors
        )

        if session_start and session_end and session_start > session_end:
            errors.append(f"Row {line}: session_start_date cannot be later than session_end_date.")
        if semester_start and semester_end and semester_start > semester_end:
            errors.append(f"Row {line}: semester_start_date cannot be later than semester_end_date.")

        session_item = sessions.setdefault(name, {
            "name": name,
            "start_date": None,
            "end_date": None,
            "line_number": line,
        })
        _merge_optional_date(
            session_item, "start_date", session_start, "session_start_date", line, errors
        )
        _merge_optional_date(
            session_item, "end_date", session_end, "session_end_date", line, errors
        )

        semester_key = (name, semester)
        semester_item = semesters.setdefault(semester_key, {
            "session_name": name,
            "name": semester,
            "start_date": None,
            "end_date": None,
            "line_number": line,
        })
        _merge_optional_date(
            semester_item, "start_date", semester_start, "semester_start_date", line, errors
        )
        _merge_optional_date(
            semester_item, "end_date", semester_end, "semester_end_date", line, errors
        )

    for item in sessions.values():
        if item["start_date"] and item["end_date"] and item["start_date"] > item["end_date"]:
            errors.append(
                f"Academic session {item['name']}: start date cannot be later than end date."
            )

    for item in semesters.values():
        session_item = sessions[item["session_name"]]
        if (
            item["start_date"] and session_item["start_date"]
            and item["start_date"] < session_item["start_date"]
        ):
            errors.append(
                f"{item['session_name']} {item['name']}: semester starts before its academic session."
            )
        if (
            item["end_date"] and session_item["end_date"]
            and item["end_date"] > session_item["end_date"]
        ):
            errors.append(
                f"{item['session_name']} {item['name']}: semester ends after its academic session."
            )

    resolved_sessions = {}
    for name, item in sessions.items():
        existing = AcademicSession.objects.filter(name=name).first()
        if existing and not existing.is_active:
            errors.append(
                f"Academic session {name} already exists but is inactive. Reactivate it in Academic Management first."
            )
        if existing:
            for field in ("start_date", "end_date"):
                supplied = item[field]
                stored = getattr(existing, field)
                if supplied and stored and supplied != stored:
                    errors.append(
                        f"Academic session {name}: {field} conflicts with the existing record. "
                        "The importer will not overwrite existing dates."
                    )
        resolved_sessions[name] = {
            **item,
            "existing_id": existing.pk if existing else None,
        }

    resolved_semesters = {}
    for key, item in semesters.items():
        session_item = resolved_sessions.get(item["session_name"])
        if not session_item:
            continue
        existing = None
        if session_item["existing_id"]:
            existing = Semester.objects.filter(
                session_id=session_item["existing_id"], name=item["name"]
            ).first()
        if existing and not existing.is_active:
            errors.append(
                f"{item['session_name']} {item['name']} already exists but is inactive. "
                "Reactivate it in Academic Management first."
            )
        if existing:
            for field in ("start_date", "end_date"):
                supplied = item[field]
                stored = getattr(existing, field)
                if supplied and stored and supplied != stored:
                    errors.append(
                        f"{item['session_name']} {item['name']}: {field} conflicts with the existing record. "
                        "The importer will not overwrite existing dates."
                    )
        resolved_semesters[key] = {
            **item,
            "existing_id": existing.pk if existing else None,
        }

    counts = {
        "sessions_total": len(resolved_sessions),
        "sessions_create": sum(1 for item in resolved_sessions.values() if item["existing_id"] is None),
        "sessions_unchanged": sum(1 for item in resolved_sessions.values() if item["existing_id"] is not None),
        "semesters_total": len(resolved_semesters),
        "semesters_create": sum(1 for item in resolved_semesters.values() if item["existing_id"] is None),
        "semesters_unchanged": sum(1 for item in resolved_semesters.values() if item["existing_id"] is not None),
    }

    plan = {
        "sessions": list(resolved_sessions.values()),
        "semesters": list(resolved_semesters.values()),
    }
    return plan, counts, errors


def apply_session_import_plan(plan):
    result = {
        "sessions_created": 0,
        "sessions_unchanged": 0,
        "sessions_dates_filled": 0,
        "semesters_created": 0,
        "semesters_unchanged": 0,
        "semesters_dates_filled": 0,
    }

    with transaction.atomic():
        session_objects = {}
        for item in plan["sessions"]:
            if item["existing_id"]:
                session = AcademicSession.objects.get(pk=item["existing_id"])
                changed = False
                for field in ("start_date", "end_date"):
                    if getattr(session, field) is None and item[field] is not None:
                        setattr(session, field, item[field])
                        changed = True
                if changed:
                    session.full_clean()
                    session.save()
                    result["sessions_dates_filled"] += 1
                else:
                    result["sessions_unchanged"] += 1
            else:
                session = AcademicSession(
                    name=item["name"],
                    start_date=item["start_date"],
                    end_date=item["end_date"],
                    is_active=True,
                    is_current=False,
                )
                session.full_clean()
                session.save()
                result["sessions_created"] += 1
            session_objects[item["name"]] = session

        for item in plan["semesters"]:
            session = session_objects[item["session_name"]]
            if item["existing_id"]:
                semester = Semester.objects.get(pk=item["existing_id"])
                changed = False
                for field in ("start_date", "end_date"):
                    if getattr(semester, field) is None and item[field] is not None:
                        setattr(semester, field, item[field])
                        changed = True
                if changed:
                    semester.full_clean()
                    semester.save()
                    result["semesters_dates_filled"] += 1
                else:
                    result["semesters_unchanged"] += 1
            else:
                semester = Semester(
                    session=session,
                    name=item["name"],
                    start_date=item["start_date"],
                    end_date=item["end_date"],
                    is_active=True,
                    is_current=False,
                )
                semester.full_clean()
                semester.save()
                result["semesters_created"] += 1

    return result
