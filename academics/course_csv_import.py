import csv
import io
import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import AcademicSession, Course, CourseOffering, Department, Programme, Semester


COURSE_COLUMNS = [
    "faculty_code", "department_code", "course_code", "course_title",
    "credit_units", "stress_code", "programme_code", "academic_session",
    "semester", "level", "offering_active", "registration_open", "max_students",
]
OPTIONAL_COLUMNS = ["description", "source_url", "source_note"]
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_DATA_ROWS = 1500
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._/-]{1,19}$")
LEVELS = {"100", "200", "300", "400", "500", "600", "700"}
SEMESTERS = {
    "FIRST": Semester.FIRST,
    "FIRST SEMESTER": Semester.FIRST,
    "1": Semester.FIRST,
    "SECOND": Semester.SECOND,
    "SECOND SEMESTER": Semester.SECOND,
    "2": Semester.SECOND,
    "SUMMER": Semester.SUMMER,
    "SUMMER SEMESTER": Semester.SUMMER,
}
STRESS_CODES = {"", "C", "R", "E", "G", "AR"}


def parse_course_csv(uploaded):
    if uploaded is None:
        return [], ["Choose a CSV file to upload."]
    if uploaded.size > MAX_FILE_BYTES:
        return [], ["The CSV file exceeds the 2 MB upload limit."]
    try:
        raw = uploaded.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            return [], ["The CSV file exceeds the 2 MB upload limit."]
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["The CSV must use UTF-8 encoding. Save it as CSV UTF-8 and upload again."]
    except Exception:
        return [], ["The uploaded file could not be read."]

    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return [], ["The CSV is empty or has no header row."]
        headers = [(name or "").strip().lower() for name in reader.fieldnames]
        if len(headers) != len(set(headers)):
            return [], ["The CSV contains duplicate column headings."]
        missing = [name for name in COURSE_COLUMNS if name not in headers]
        if missing:
            return [], ["Missing required columns: " + ", ".join(missing)]
        rows = []
        errors = []
        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                errors.append(f"Row {line_number}: the row contains more values than the CSV header defines.")
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


def _bool_value(value, default, label, line, errors):
    if value == "":
        return default
    normal = value.strip().lower()
    if normal in {"1", "true", "yes", "y"}:
        return True
    if normal in {"0", "false", "no", "n"}:
        return False
    errors.append(f"Row {line}: {label} must be true or false.")
    return default


def build_course_import_plan(rows):
    errors = []
    course_rows = {}
    offering_rows = {}

    for row in rows:
        line = row.get("line_number", "?")
        faculty_code = row.get("faculty_code", "").strip().upper()
        department_code = row.get("department_code", "").strip().upper()
        course_code = re.sub(r"\s+", " ", row.get("course_code", "").strip()).upper()
        title = row.get("course_title", "").strip()
        stress_code = row.get("stress_code", "").strip().upper()
        description = row.get("description", "").strip()
        programme_code = row.get("programme_code", "").strip().upper()
        session_name = row.get("academic_session", "").strip().upper()
        semester_raw = row.get("semester", "").strip().upper()
        level = row.get("level", "").strip()
        units_raw = row.get("credit_units", "").strip()
        active = _bool_value(row.get("offering_active", ""), True, "offering_active", line, errors)
        registration_open = _bool_value(
            row.get("registration_open", ""), False, "registration_open", line, errors
        )
        max_students_raw = row.get("max_students", "").strip()

        for label, value in (
            ("faculty_code", faculty_code),
            ("department_code", department_code),
            ("course_code", course_code),
        ):
            if not value:
                errors.append(f"Row {line}: {label} is required.")
            elif not CODE_RE.fullmatch(value):
                errors.append(f"Row {line}: {label} must contain 2–20 valid code characters.")
        if not title:
            errors.append(f"Row {line}: course_title is required.")
        elif len(title) > 180:
            errors.append(f"Row {line}: course_title must not exceed 180 characters.")
        if description and len(description) > 5000:
            errors.append(f"Row {line}: description must not exceed 5,000 characters.")
        try:
            units = int(units_raw)
            if not 1 <= units <= 30:
                raise ValueError
        except (ValueError, TypeError):
            units = None
            errors.append(f"Row {line}: credit_units must be a whole number from 1 to 30.")
        if stress_code not in STRESS_CODES:
            errors.append(f"Row {line}: stress_code must be blank, C, R, E, G or AR.")
        if registration_open:
            errors.append(
                f"Row {line}: registration_open must be false. Imported offerings are kept closed; "
                "an administrator opens registration after reviewing them."
            )
        if max_students_raw:
            try:
                max_students = int(max_students_raw)
                if max_students < 1:
                    raise ValueError
            except ValueError:
                max_students = None
                errors.append(f"Row {line}: max_students must be a positive whole number or blank.")
        else:
            max_students = None

        course_key = (faculty_code, department_code, course_code)
        course_value = {
            "faculty_code": faculty_code,
            "department_code": department_code,
            "code": course_code,
            "title": title,
            "credit_units": units,
            "stress_code": stress_code,
            "description": description,
        }
        if course_code and department_code and faculty_code and title and units is not None:
            previous = course_rows.get(course_key)
            if previous and any(
                previous[field] != course_value[field]
                for field in ("title", "credit_units", "stress_code", "description")
            ):
                errors.append(
                    f"Row {line}: {course_code} has conflicting course details elsewhere in this file."
                )
            else:
                course_rows[course_key] = course_value

        if programme_code:
            if not CODE_RE.fullmatch(programme_code):
                errors.append(f"Row {line}: programme_code must contain 2–20 valid code characters.")
            if not session_name:
                errors.append(f"Row {line}: academic_session is required when programme_code is supplied.")
            if not semester_raw:
                errors.append(f"Row {line}: semester is required when programme_code is supplied.")
            if level not in LEVELS:
                errors.append(f"Row {line}: level must be one of {', '.join(sorted(LEVELS))}.")
            semester_value = SEMESTERS.get(semester_raw)
            if semester_raw and not semester_value:
                errors.append(f"Row {line}: semester must be FIRST, SECOND or SUMMER.")
            if registration_open:
                pass
            if programme_code and session_name and semester_value and level in LEVELS:
                offering_key = (
                    faculty_code, department_code, course_code, programme_code,
                    session_name, semester_value, level,
                )
                offering_value = {
                    "course_key": course_key,
                    "programme_code": programme_code,
                    "session_name": session_name,
                    "semester": semester_value,
                    "level": level,
                    "is_active": active,
                    "registration_open": False,
                    "max_students": max_students,
                }
                previous = offering_rows.get(offering_key)
                if previous and previous != offering_value:
                    errors.append(
                        f"Row {line}: duplicate offering for {course_code} has conflicting settings."
                    )
                else:
                    offering_rows[offering_key] = offering_value
        elif session_name or semester_raw or level:
            errors.append(
                f"Row {line}: programme_code is blank, so academic_session, semester and level must also be blank."
            )

    # Resolve academic hierarchy and term references before offering any import.
    resolved_courses = {}
    for key, item in course_rows.items():
        department_qs = Department.objects.filter(
            code__iexact=item["department_code"],
            faculty__code__iexact=item["faculty_code"],
            is_active=True,
            faculty__is_active=True,
        ).select_related("faculty")
        department = department_qs.first()
        if not department:
            errors.append(
                f"Course {item['code']}: active department {item['department_code']} "
                f"under faculty {item['faculty_code']} was not found."
            )
            continue
        existing = Course.objects.filter(department=department, code__iexact=item["code"]).first()
        if existing:
            if not existing.is_active:
                errors.append(
                    f"Course {item['code']} already exists but is inactive. Reactivate it before importing offerings."
                )
            elif (
                existing.title != item["title"]
                or existing.credit_units != item["credit_units"]
                or existing.stress_code != item["stress_code"]
                or existing.description != item["description"]
            ):
                errors.append(
                    f"Course {item['code']} already exists in {department.name} with different details. "
                    "The importer will not overwrite existing course records; reconcile it in the catalogue first."
                )
            else:
                pass
        resolved_courses[key] = {
            **item,
            "department_id": department.pk,
            "existing_id": existing.pk if existing else None,
        }

    resolved_offerings = {}
    for key, item in offering_rows.items():
        course_info = resolved_courses.get(item["course_key"])
        if not course_info:
            continue
        programme_qs = Programme.objects.filter(
            code__iexact=item["programme_code"],
            is_active=True,
            department__is_active=True,
            department__faculty__is_active=True,
        ).select_related("department", "department__faculty")
        programme_matches = list(programme_qs[:2])
        if len(programme_matches) != 1:
            errors.append(
                f"Offering {course_info['code']}: programme code {item['programme_code']} "
                "must identify exactly one active programme."
            )
            continue
        programme = programme_matches[0]

        if item["session_name"] == "CURRENT":
            session = AcademicSession.objects.filter(is_current=True, is_active=True).first()
            if not session:
                errors.append(
                    f"Offering {course_info['code']}: no active current academic session is set. "
                    "Create or activate a session and mark it current before importing."
                )
                continue
        else:
            session = AcademicSession.objects.filter(
                name__iexact=item["session_name"], is_active=True
            ).first()
            if not session:
                errors.append(
                    f"Offering {course_info['code']}: active academic session "
                    f"{item['session_name']} was not found."
                )
                continue
        semester = Semester.objects.filter(
            session=session, name=item["semester"], is_active=True
        ).first()
        if not semester:
            errors.append(
                f"Offering {course_info['code']}: active {item['semester']} semester "
                f"was not found under session {session.name}. Create it first."
            )
            continue

        course = Course.objects.filter(
            department_id=course_info["department_id"], code__iexact=course_info["code"]
        ).first()
        existing_offering = None
        if course:
            existing_offering = CourseOffering.objects.filter(
                course=course,
                programme=programme,
                semester=semester,
                level=item["level"],
            ).first()
            if existing_offering and not existing_offering.is_active:
                errors.append(
                    f"Offering {course.code} / {programme.code} / {item['level']} already exists but is inactive."
                )
        resolved_offerings[key] = {
            **item,
            "course_id": course.pk if course else None,
            "programme_id": programme.pk,
            "semester_id": semester.pk,
            "existing_id": existing_offering.pk if existing_offering else None,
            "session_name_resolved": session.name,
            "semester_label": semester.get_name_display(),
        }

    counts = {
        "course_create": sum(1 for item in resolved_courses.values() if item["existing_id"] is None),
        "course_unchanged": sum(1 for item in resolved_courses.values() if item["existing_id"] is not None),
        "offering_create": sum(1 for item in resolved_offerings.values() if item["existing_id"] is None),
        "offering_unchanged": sum(1 for item in resolved_offerings.values() if item["existing_id"] is not None),
        "course_total": len(resolved_courses),
        "offering_total": len(resolved_offerings),
    }
    plan = {
        "courses": list(resolved_courses.values()),
        "offerings": list(resolved_offerings.values()),
    }
    return plan, counts, errors


def apply_course_import_plan(plan):
    result = {
        "courses_created": 0, "courses_unchanged": 0,
        "offerings_created": 0, "offerings_unchanged": 0,
    }
    with transaction.atomic():
        course_objects = {}
        for item in plan["courses"]:
            if item["existing_id"]:
                course = Course.objects.get(pk=item["existing_id"])
                result["courses_unchanged"] += 1
            else:
                department = Department.objects.get(pk=item["department_id"])
                course = Course(
                    department=department,
                    code=item["code"],
                    title=item["title"],
                    credit_units=item["credit_units"],
                    stress_code=item["stress_code"],
                    description=item["description"],
                )
                course.full_clean()
                course.save()
                result["courses_created"] += 1
            course_objects[(item["faculty_code"], item["department_code"], item["code"])] = course

        for item in plan["offerings"]:
            if item["existing_id"]:
                result["offerings_unchanged"] += 1
                continue
            course = course_objects[item["course_key"]]
            programme = Programme.objects.get(pk=item["programme_id"])
            semester = Semester.objects.get(pk=item["semester_id"])
            offering = CourseOffering(
                course=course,
                programme=programme,
                semester=semester,
                level=item["level"],
                is_active=item["is_active"],
                registration_open=False,
                max_students=item["max_students"],
            )
            offering.full_clean()
            offering.save()
            result["offerings_created"] += 1
    return result
