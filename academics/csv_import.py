import csv
import io
import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import Department, Faculty, Programme

MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 2_000
CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,19}$")

ACADEMIC_COLUMNS = [
    "faculty_code", "faculty_name", "department_code", "department_name",
    "programme_code", "programme_name", "award", "duration_years", "mode",
]
METADATA_COLUMNS = ["source_url", "source_session", "verification_status", "notes"]
ALLOWED_COLUMNS = set(ACADEMIC_COLUMNS + METADATA_COLUMNS)
REQUIRED_COLUMNS = {"faculty_code", "faculty_name"}


def parse_academic_csv(upload):
    """Return cleaned rows and row-level errors without writing to the database."""
    errors = []
    if not upload or not getattr(upload, "name", "").lower().endswith(".csv"):
        return [], ["Upload a .csv file."]
    if upload.size > MAX_CSV_BYTES:
        return [], ["The CSV file is larger than the 1 MB upload limit."]
    try:
        raw = upload.read(MAX_CSV_BYTES + 1)
        if len(raw) > MAX_CSV_BYTES:
            return [], ["The CSV file is larger than the 1 MB upload limit."]
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["The file must be saved as UTF-8 CSV. In Excel, choose CSV UTF-8 (Comma delimited)."]

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        raw_headers = reader.fieldnames or []
        headers = [(header or "").strip().lower() for header in raw_headers]
        if not headers or any(not header for header in headers):
            return [], ["The CSV must contain a header row with column names."]
        if len(headers) != len(set(headers)):
            return [], ["The CSV contains duplicate column names after normalisation."]
        missing = sorted(REQUIRED_COLUMNS - set(headers))
        unknown = sorted(set(headers) - ALLOWED_COLUMNS)
        if missing:
            errors.append("Missing required column(s): " + ", ".join(missing) + ".")
        if unknown:
            errors.append("Unrecognised column(s): " + ", ".join(unknown) + ". Download the RollNexa template for the supported format.")
        if errors:
            return [], errors
        reader.fieldnames = headers
        rows = []
        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                errors.append(f"Row {line_number}: the row contains more values than the header defines.")
                continue
            if line_number > MAX_CSV_ROWS + 1:
                errors.append(f"The CSV exceeds the {MAX_CSV_ROWS:,}-row limit.")
                break
            row = {column: (raw_row.get(column) or "").strip() for column in headers}
            if not any(row.values()):
                continue
            for column in ALLOWED_COLUMNS:
                row.setdefault(column, "")
            row["line_number"] = line_number
            rows.append(row)
        if not rows and not errors:
            errors.append("The CSV contains a header but no data rows.")
        return rows, errors
    except csv.Error as exc:
        return [], [f"Could not read the CSV file: {exc}"]


def _check_code(value, label, line, errors):
    if not value:
        errors.append(f"Row {line}: {label} is required.")
    elif not CODE_PATTERN.fullmatch(value):
        errors.append(f"Row {line}: {label} must contain 2–20 letters, numbers, dots, underscores, slashes or hyphens.")


def build_import_plan(rows):
    """Validate hierarchy, duplicates and current database conflicts; return an idempotent plan."""
    errors = []
    faculties = {}
    departments = {}
    programmes = {}
    faculty_names = {}
    department_names = {}
    programme_names = {}

    for row in rows:
        line = row.get("line_number", "?")
        f_code = row.get("faculty_code", "").upper()
        f_name = row.get("faculty_name", "").strip()
        d_code = row.get("department_code", "").upper()
        d_name = row.get("department_name", "").strip()
        p_code = row.get("programme_code", "").upper()
        p_name = row.get("programme_name", "").strip()
        award = row.get("award", "").strip()
        duration_raw = row.get("duration_years", "").strip()
        mode_raw = row.get("mode", "").strip().lower().replace("-", "_")

        _check_code(f_code, "faculty_code", line, errors)
        if not f_name:
            errors.append(f"Row {line}: faculty_name is required.")
        elif len(f_name) > 160:
            errors.append(f"Row {line}: faculty_name must not exceed 160 characters.")
        if award and len(award) > 40:
            errors.append(f"Row {line}: award must not exceed 40 characters.")
        if duration_raw:
            try:
                duration = int(duration_raw)
                if not 1 <= duration <= 8:
                    raise ValueError
            except ValueError:
                errors.append(f"Row {line}: duration_years must be a whole number from 1 to 8, or blank if unknown.")
                duration = None
        else:
            duration = None
        if mode_raw and mode_raw not in {"full_time", "part_time"}:
            errors.append(f"Row {line}: mode must be full_time, part_time or blank.")
        mode = mode_raw

        if bool(d_code) != bool(d_name):
            errors.append(f"Row {line}: provide both department_code and department_name, or leave both blank.")
        if bool(p_code) != bool(p_name):
            errors.append(f"Row {line}: provide both programme_code and programme_name, or leave both blank.")
        if p_code and not d_code:
            errors.append(f"Row {line}: a programme must belong to a department.")
        if d_code:
            _check_code(d_code, "department_code", line, errors)
            if len(d_name) > 160:
                errors.append(f"Row {line}: department_name must not exceed 160 characters.")
        if p_code:
            _check_code(p_code, "programme_code", line, errors)
            if len(p_name) > 180:
                errors.append(f"Row {line}: programme_name must not exceed 180 characters.")

        if not f_code or not f_name:
            continue
        if f_code in faculties and faculties[f_code]["name"].casefold() != f_name.casefold():
            errors.append(f"Row {line}: faculty_code {f_code} is assigned to more than one faculty name in this file.")
        faculties[f_code] = {"code": f_code, "name": f_name}
        f_name_key = f_name.casefold()
        if f_name_key in faculty_names and faculty_names[f_name_key] != f_code:
            errors.append(f"Row {line}: faculty name {f_name} is assigned to multiple faculty codes in this file.")
        faculty_names[f_name_key] = f_code

        if d_code and d_name:
            d_key = (f_code, d_code)
            if d_key in departments and departments[d_key]["name"].casefold() != d_name.casefold():
                errors.append(f"Row {line}: department code {d_code} under {f_code} has conflicting names in this file.")
            departments[d_key] = {"faculty_code": f_code, "code": d_code, "name": d_name}
            dn_key = (f_code, d_name.casefold())
            if dn_key in department_names and department_names[dn_key] != d_code:
                errors.append(f"Row {line}: department name {d_name} under {f_code} has multiple department codes in this file.")
            department_names[dn_key] = d_code

        if p_code and p_name and d_code:
            p_key = (f_code, d_code, p_code)
            p_value = {
                "faculty_code": f_code,
                "department_code": d_code,
                "code": p_code,
                "name": p_name,
                "award": award,
                "duration_years": duration,
                "mode": mode,
            }
            if p_key in programmes:
                previous = programmes[p_key]
                for key in ("name", "award", "duration_years", "mode"):
                    if previous[key] != p_value[key] and p_value[key] not in ("", None):
                        errors.append(f"Row {line}: programme code {p_code} has conflicting values in this file.")
            else:
                programmes[p_key] = p_value
            pn_key = (f_code, d_code, p_name.casefold())
            if pn_key in programme_names and programme_names[pn_key] != p_code:
                errors.append(f"Row {line}: programme name {p_name} under {d_code} has multiple programme codes in this file.")
            programme_names[pn_key] = p_code

    # Validate faculty collisions against existing records.
    for code, item in faculties.items():
        existing = Faculty.objects.filter(code=code).first()
        collision = Faculty.objects.filter(name__iexact=item["name"])
        if existing:
            collision = collision.exclude(pk=existing.pk)
        if collision.exists():
            errors.append(f"Faculty {item['name']} conflicts with an existing faculty name using a different code.")

    # Validate departments and programmes against existing parents and names.
    for key, item in departments.items():
        faculty = Faculty.objects.filter(code=item["faculty_code"]).first()
        if faculty and not faculty.is_active:
            errors.append(f"Department {item['name']} cannot be imported because its existing faculty is inactive. Reactivate the faculty first.")
            continue
        if faculty:
            existing = Department.objects.filter(faculty=faculty, code=item["code"]).first()
            collision = Department.objects.filter(faculty=faculty, name__iexact=item["name"])
            if existing:
                collision = collision.exclude(pk=existing.pk)
            if collision.exists():
                errors.append(f"Department {item['name']} conflicts with an existing department name in {faculty.name}.")

    for key, item in programmes.items():
        department = Department.objects.filter(faculty__code=item["faculty_code"], code=item["department_code"]).select_related("faculty").first()
        if department:
            if not department.is_active or not department.faculty.is_active:
                errors.append(f"Programme {item['name']} cannot be imported because its existing department or faculty is inactive.")
                continue
            existing = Programme.objects.filter(department=department, code=item["code"]).first()
            collision = Programme.objects.filter(department=department, name__iexact=item["name"])
            if existing:
                collision = collision.exclude(pk=existing.pk)
            if collision.exists():
                errors.append(f"Programme {item['name']} conflicts with an existing programme name in {department.name}.")

    # Estimate create/update/unchanged counts for the preview.
    counts = {"faculties_create": 0, "faculties_update": 0, "faculties_unchanged": 0,
              "departments_create": 0, "departments_update": 0, "departments_unchanged": 0,
              "programmes_create": 0, "programmes_update": 0, "programmes_unchanged": 0}
    for code, item in faculties.items():
        existing = Faculty.objects.filter(code=code).first()
        bucket = "create" if not existing else ("update" if existing.name != item["name"] else "unchanged")
        counts[f"faculties_{bucket}"] += 1
    for (f_code, d_code), item in departments.items():
        existing = Department.objects.filter(faculty__code=f_code, code=d_code).first()
        bucket = "create" if not existing else ("update" if existing.name != item["name"] else "unchanged")
        counts[f"departments_{bucket}"] += 1
    for (f_code, d_code, p_code), item in programmes.items():
        existing = Programme.objects.filter(department__faculty__code=f_code, department__code=d_code, code=p_code).first()
        if not existing:
            bucket = "create"
        else:
            changed = existing.name != item["name"]
            changed = changed or bool(item["award"] and existing.award != item["award"])
            changed = changed or (item["duration_years"] is not None and existing.duration_years != item["duration_years"])
            changed = changed or (item["mode"] and existing.mode != item["mode"])
            bucket = "update" if changed else "unchanged"
        counts[f"programmes_{bucket}"] += 1

    plan = {
        "faculties": list(faculties.values()),
        "departments": list(departments.values()),
        "programmes": list(programmes.values()),
    }
    return plan, counts, errors


def apply_import_plan(plan):
    """Apply a validated import atomically. Existing records are updated by their scoped codes."""
    result = {"faculties_created": 0, "faculties_updated": 0,
              "departments_created": 0, "departments_updated": 0,
              "programmes_created": 0, "programmes_updated": 0}
    try:
        with transaction.atomic():
            for item in plan["faculties"]:
                obj = Faculty.objects.filter(code=item["code"]).first()
                if obj is None:
                    obj = Faculty(code=item["code"], name=item["name"])
                    obj.full_clean()
                    obj.save()
                    result["faculties_created"] += 1
                elif obj.name != item["name"]:
                    obj.name = item["name"]
                    obj.full_clean()
                    obj.save(update_fields=["name", "updated_at"])
                    result["faculties_updated"] += 1

            for item in plan["departments"]:
                faculty = Faculty.objects.get(code=item["faculty_code"])
                obj = Department.objects.filter(faculty=faculty, code=item["code"]).first()
                if obj is None:
                    obj = Department(faculty=faculty, code=item["code"], name=item["name"])
                    obj.full_clean()
                    obj.save()
                    result["departments_created"] += 1
                elif obj.name != item["name"]:
                    obj.name = item["name"]
                    obj.full_clean()
                    obj.save(update_fields=["name", "updated_at"])
                    result["departments_updated"] += 1

            for item in plan["programmes"]:
                department = Department.objects.get(faculty__code=item["faculty_code"], code=item["department_code"])
                obj = Programme.objects.filter(department=department, code=item["code"]).first()
                if obj is None:
                    obj = Programme(
                        department=department,
                        code=item["code"],
                        name=item["name"],
                        award=item["award"] or "",
                        duration_years=item["duration_years"],
                        mode=item["mode"] or Programme.MODE_FULL_TIME,
                    )
                    obj.full_clean()
                    obj.save()
                    result["programmes_created"] += 1
                else:
                    changed_fields = []
                    if obj.name != item["name"]:
                        obj.name = item["name"]
                        changed_fields.append("name")
                    # Blank optional CSV values never erase information already stored.
                    if item["award"] and obj.award != item["award"]:
                        obj.award = item["award"]
                        changed_fields.append("award")
                    if item["duration_years"] is not None and obj.duration_years != item["duration_years"]:
                        obj.duration_years = item["duration_years"]
                        changed_fields.append("duration_years")
                    if item["mode"] and obj.mode != item["mode"]:
                        obj.mode = item["mode"]
                        changed_fields.append("mode")
                    if changed_fields:
                        obj.full_clean()
                        obj.save(update_fields=changed_fields + ["updated_at"])
                        result["programmes_updated"] += 1
    except (IntegrityError, ValidationError):
        raise
    return result
