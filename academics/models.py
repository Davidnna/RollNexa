import re

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


course_code_validator = RegexValidator(
    regex=r"^[A-Za-z0-9][A-Za-z0-9 ._/-]{1,19}$",
    message="Use 2–20 letters, numbers, spaces, dots, underscores, slashes or hyphens.",
)
code_validator = RegexValidator(
    regex=r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,19}$",
    message="Use 2–20 letters, numbers, dots, underscores, slashes or hyphens.",
)
session_name_validator = RegexValidator(
    regex=r"^\d{4}/\d{4}$",
    message="Enter the academic session in the format YYYY/YYYY, e.g. 2025/2026.",
)


class AcademicRecord(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Faculty(AcademicRecord):
    code = models.CharField(max_length=20, validators=[code_validator], unique=True)
    name = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "faculties"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(AcademicRecord):
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="departments")
    code = models.CharField(max_length=20, validators=[code_validator])
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "code"], name="uniq_department_code_per_faculty"),
            models.UniqueConstraint(fields=["faculty", "name"], name="uniq_department_name_per_faculty"),
        ]

    def clean(self):
        super().clean()
        if self.faculty_id and not self.faculty.is_active:
            raise ValidationError({"faculty": "Reactivate the faculty before adding or moving a department under it."})

    def __str__(self):
        return f"{self.name} — {self.faculty.name}"


class Programme(AcademicRecord):
    MODE_FULL_TIME = "full_time"
    MODE_PART_TIME = "part_time"
    MODE_CHOICES = [
        (MODE_FULL_TIME, "Full-time"),
        (MODE_PART_TIME, "Part-time"),
    ]

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="programmes")
    code = models.CharField(max_length=20, validators=[code_validator])
    name = models.CharField(max_length=180)
    award = models.CharField(
        max_length=40, blank=True, default="",
        help_text="Optional. For example: B.Sc., B.A., B.Eng. Leave blank if not confirmed.",
    )
    duration_years = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="Optional. Leave blank if the official duration has not been confirmed.",
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_FULL_TIME)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["department__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "code"], name="uniq_programme_code_per_department"),
            models.UniqueConstraint(fields=["department", "name"], name="uniq_programme_name_per_department"),
        ]

    def clean(self):
        super().clean()
        if self.department_id and (not self.department.is_active or not self.department.faculty.is_active):
            raise ValidationError({"department": "Reactivate the department and its faculty before adding or moving a programme under it."})

    def __str__(self):
        award_label = f" ({self.award})" if self.award else ""
        return f"{self.name}{award_label} — {self.department.name}"


class AcademicSession(AcademicRecord):
    name = models.CharField(max_length=9, unique=True, validators=[session_name_validator])
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"], condition=Q(is_current=True),
                name="one_current_academic_session",
            ),
        ]
        verbose_name = "academic session"
        verbose_name_plural = "academic sessions"

    def clean(self):
        super().clean()
        errors = {}
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors["end_date"] = "The end date cannot be earlier than the start date."
        if self.name:
            year_parts = self.name.split("/")
            if len(year_parts) == 2 and all(part.isdigit() and len(part) == 4 for part in year_parts):
                start_year, end_year = (int(part) for part in year_parts)
                if end_year != start_year + 1:
                    errors["name"] = "The ending year must be one year after the starting year."
        if self.is_current and not self.is_active:
            errors["is_current"] = "An inactive session cannot be the current session."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class Semester(AcademicRecord):
    FIRST = "first"
    SECOND = "second"
    SUMMER = "summer"
    NAME_CHOICES = [
        (FIRST, "First semester"),
        (SECOND, "Second semester"),
        (SUMMER, "Summer semester"),
    ]

    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="semesters")
    name = models.CharField(max_length=12, choices=NAME_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-session__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["session", "name"], name="uniq_semester_name_per_session"),
            models.UniqueConstraint(
                fields=["is_current"], condition=Q(is_current=True),
                name="one_current_semester",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors["end_date"] = "The end date cannot be earlier than the start date."
        if self.is_current and not self.is_active:
            errors["is_current"] = "An inactive semester cannot be current."
        if self.session_id and not self.session.is_active:
            errors["session"] = "Reactivate the academic session before adding or moving a semester under it."
        if self.is_current and self.session_id and not self.session.is_current:
            errors["session"] = "A semester can only be current within the current academic session."
        if self.session_id and self.start_date and self.session.start_date and self.start_date < self.session.start_date:
            errors["start_date"] = "The semester cannot start before its academic session."
        if self.session_id and self.end_date and self.session.end_date and self.end_date > self.session.end_date:
            errors["end_date"] = "The semester cannot end after its academic session."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.get_name_display()} — {self.session.name}"


class Course(AcademicRecord):
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="courses"
    )
    code = models.CharField(max_length=20, validators=[course_code_validator])
    title = models.CharField(max_length=180)
    credit_units = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="Enter the approved course unit value (1–6).",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["department__name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["department", "code"], name="uniq_course_code_per_department"),
            models.CheckConstraint(
                condition=Q(credit_units__gte=1) & Q(credit_units__lte=6),
                name="course_credit_units_between_1_6",
            ),
        ]
        indexes = [
            models.Index(fields=["code"], name="course_code_idx"),
            models.Index(fields=["title"], name="course_title_idx"),
        ]

    def clean(self):
        super().clean()
        if self.code:
            self.code = re.sub(r"\s+", " ", self.code.strip()).upper()
        if self.department_id and (
            not self.department.is_active or not self.department.faculty.is_active
        ):
            raise ValidationError({
                "department": "The course must belong to an active department and faculty."
            })

    def __str__(self):
        return f"{self.code} — {self.title}"


class CourseOffering(AcademicRecord):
    LEVEL_CHOICES = [
        ("100", "100 level"),
        ("200", "200 level"),
        ("300", "300 level"),
        ("400", "400 level"),
        ("500", "500 level"),
        ("600", "600 level"),
        ("700", "700 level"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="offerings"
    )
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, related_name="course_offerings"
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name="course_offerings"
    )
    level = models.CharField(max_length=3, choices=LEVEL_CHOICES)
    registration_open = models.BooleanField(
        default=False,
        help_text="Students can register only while this offering is active and registration is open.",
    )
    max_students = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)],
        help_text="Optional enrolment limit. Leave blank for no configured limit.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-semester__session__name", "semester__name", "level", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "programme", "semester", "level"],
                name="uniq_course_offering_programme_term_level",
            ),
            models.CheckConstraint(
                condition=Q(max_students__isnull=True) | Q(max_students__gte=1),
                name="course_offering_capacity_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["programme", "level", "is_active"], name="offering_programme_level_idx"),
            models.Index(fields=["semester", "is_active"], name="offering_semester_active_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.course_id:
            if not self.course.is_active:
                errors["course"] = "Only active courses can be offered."
            elif not self.course.department.is_active or not self.course.department.faculty.is_active:
                errors["course"] = "The course's department and faculty must be active."
        if self.programme_id:
            if not self.programme.is_active:
                errors["programme"] = "Only active programmes can receive course offerings."
            elif not self.programme.department.is_active or not self.programme.department.faculty.is_active:
                errors["programme"] = "The programme's department and faculty must be active."
        if self.semester_id:
            if not self.semester.is_active or not self.semester.session.is_active:
                errors["semester"] = "The semester and its academic session must be active."
        if self.registration_open and not self.is_active:
            errors["registration_open"] = "Registration cannot be opened for an inactive offering."
        if self.max_students and self.pk:
            registered_count = self.registrations.filter(
                status=CourseRegistration.STATUS_REGISTERED
            ).count()
            if self.max_students < registered_count:
                errors["max_students"] = (
                    f"The limit cannot be below the {registered_count} students already registered."
                )
        if errors:
            raise ValidationError(errors)

    @property
    def session(self):
        return self.semester.session

    def __str__(self):
        return (
            f"{self.course.code} — {self.programme.name} — "
            f"{self.semester.get_name_display()} {self.semester.session.name}"
        )


class CourseLecturerAssignment(models.Model):
    offering = models.ForeignKey(
        CourseOffering, on_delete=models.PROTECT, related_name="lecturer_assignments"
    )
    lecturer = models.ForeignKey(
        "accounts.UserProfile", on_delete=models.PROTECT,
        related_name="course_lecturer_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lecturer__user__last_name", "lecturer__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "lecturer"], name="uniq_lecturer_per_course_offering"
            ),
        ]

    def clean(self):
        super().clean()
        if self.lecturer_id:
            if self.lecturer.role != "lecturer":
                raise ValidationError({"lecturer": "Only lecturer accounts can be assigned to course offerings."})
            if not self.lecturer.user.is_active:
                raise ValidationError({"lecturer": "An inactive lecturer cannot be assigned."})
        if self.offering_id and not self.offering.is_active:
            raise ValidationError({"offering": "Reactivate the course offering before assigning a lecturer."})

    def __str__(self):
        return f"{self.lecturer.user.get_full_name() or self.lecturer.user.username} — {self.offering.course.code}"


class CourseRegistration(models.Model):
    STATUS_REGISTERED = "registered"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = [
        (STATUS_REGISTERED, "Registered"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    ]

    offering = models.ForeignKey(
        CourseOffering, on_delete=models.PROTECT, related_name="registrations"
    )
    student = models.ForeignKey(
        "accounts.UserProfile", on_delete=models.PROTECT,
        related_name="course_registrations",
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_REGISTERED, db_index=True
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student__user__last_name", "student__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "student"], name="uniq_student_course_registration"
            ),
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="course_reg_student_status_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.student_id:
            if self.student.role != "student":
                errors["student"] = "Only student accounts can register for courses."
            elif not self.student.user.is_active:
                errors["student"] = "An inactive student cannot register for courses."
        if self.offering_id:
            if self.status == self.STATUS_REGISTERED:
                if not self.offering.is_active or not self.offering.course.is_active:
                    errors["offering"] = "This course offering is not available."
                elif not self.offering.registration_open:
                    errors["offering"] = "Registration is closed for this course offering."
                elif (
                    not self.offering.course.department.is_active
                    or not self.offering.course.department.faculty.is_active
                ):
                    errors["offering"] = "The course's department and faculty must be active."
                elif (
                    not self.offering.programme.is_active
                    or not self.offering.programme.department.is_active
                    or not self.offering.programme.department.faculty.is_active
                ):
                    errors["offering"] = "The programme and its academic hierarchy must be active."
                elif not self.offering.semester.is_active or not self.offering.semester.session.is_active:
                    errors["offering"] = "The academic period attached to this offering is inactive."
            if self.student_id and self.student.role == "student":
                if self.student.programme_id != self.offering.programme_id:
                    errors["student"] = "The course offering is not for the student's assigned programme."
                elif self.student.current_level != self.offering.level:
                    errors["student"] = "The course offering is not for the student's current level."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student.user.get_username()} — {self.offering.course.code} ({self.get_status_display()})"
