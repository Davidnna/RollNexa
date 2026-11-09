from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


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
