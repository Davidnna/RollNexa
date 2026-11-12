from django import forms
import re

from accounts.models import UserProfile
from .models import (
    Course, CourseLecturerAssignment, CourseOffering, CourseRegistration,
    Department, Programme, Semester,
)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["department", "code", "title", "credit_units", "stress_code", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(
            is_active=True, faculty__is_active=True
        ).select_related("faculty").order_by("faculty__name", "name")
        if self.instance.pk and self.instance.offerings.exists():
            self.fields["department"].disabled = True
            self.fields["code"].disabled = True
            self.fields["department"].help_text = "Department ownership is locked after a course has been offered, to preserve academic history."
            self.fields["code"].help_text = "The course code is locked after an offering has been created."
        self._style_fields()

    def clean_code(self):
        return re.sub(r"\s+", " ", self.cleaned_data["code"].strip()).upper()

    def _style_fields(self):
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                field.widget.attrs.get("class", "") + " form-control"
            ).strip()


class CourseOfferingForm(forms.ModelForm):
    class Meta:
        model = CourseOffering
        fields = [
            "course", "programme", "semester", "level",
            "credit_units", "stress_code", "source_url", "source_note",
            "max_students", "registration_open", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(
            is_active=True, department__is_active=True, department__faculty__is_active=True
        ).select_related("department").order_by("code")
        self.fields["programme"].queryset = Programme.objects.filter(
            is_active=True, department__is_active=True, department__faculty__is_active=True
        ).select_related("department").order_by("name")
        self.fields["semester"].queryset = Semester.objects.filter(
            is_active=True, session__is_active=True
        ).select_related("session").order_by("-session__name", "name")
        if self.instance.pk and (self.instance.registrations.exists() or self.instance.lecturer_assignments.exists()):
            for field_name in ("course", "programme", "semester", "level"):
                self.fields[field_name].disabled = True
            self.fields["course"].help_text = "Offering identity is locked after a lecturer or student has been assigned, to preserve academic history."
        self.fields["course"].help_text = self.fields["course"].help_text or (
            "The department that owns the course may differ from the programme receiving it; "
            "this supports service courses."
        )
        self.fields["credit_units"].help_text = (
            "Enter the approved units for this programme and semester. The same course code "
            "may carry a different unit value in another programme."
        )
        self.fields["stress_code"].help_text = (
            "Optional classification for this programme offering: C, R, E, G or AR."
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                field.widget.attrs.get("class", "") + " form-control"
            ).strip()

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and cleaned.get("max_students"):
            current_count = self.instance.registrations.filter(
                status=CourseRegistration.STATUS_REGISTERED
            ).count()
            if cleaned["max_students"] < current_count:
                self.add_error(
                    "max_students",
                    f"There are already {current_count} registered students.",
                )
        return cleaned


class LecturerProfileChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, offering=None, **kwargs):
        self.offering = offering
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        name = obj.user.get_full_name() or obj.user.get_username()
        department = obj.department.name if obj.department_id else "Department not assigned"
        if self.offering and obj.department_id and obj.department_id != self.offering.course.department_id:
            return f"{name} — {department} (cross-department)"
        return f"{name} — {department}"


class LecturerAssignmentForm(forms.Form):
    lecturer = LecturerProfileChoiceField(
        queryset=UserProfile.objects.none(),
        label="Lecturer",
        empty_label="Select a lecturer",
    )

    def __init__(self, *args, offering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lecturer"].offering = offering
        self.fields["lecturer"].queryset = UserProfile.objects.filter(
            role=UserProfile.ROLE_LECTURER,
            user__is_active=True,
        ).select_related("user", "department").order_by(
            "user__last_name", "user__first_name", "user__username"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class TeachingAssignmentCreateForm(forms.Form):
    offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.none(),
        label="Course offering",
        empty_label="Select a course offering",
    )
    lecturer = LecturerProfileChoiceField(
        queryset=UserProfile.objects.none(),
        label="Lecturer",
        empty_label="Select a lecturer",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = CourseOffering.objects.filter(
            is_active=True, course__is_active=True,
            course__department__is_active=True, course__department__faculty__is_active=True,
            programme__is_active=True, programme__department__is_active=True,
            programme__department__faculty__is_active=True,
            semester__is_active=True, semester__session__is_active=True,
        ).select_related("course", "programme", "semester", "semester__session").order_by(
            "course__code", "programme__name", "level", "semester__session__name"
        )
        self.fields["offering"].label_from_instance = lambda obj: (
            f"{obj.course.code} — {obj.course.title} · {obj.programme.name} · "
            f"{obj.get_level_display()} · {obj.semester.get_name_display()} {obj.semester.session.name}"
        )
        self.fields["lecturer"].queryset = UserProfile.objects.filter(
            role=UserProfile.ROLE_LECTURER, user__is_active=True,
        ).select_related("user", "department").order_by(
            "user__last_name", "user__first_name", "user__username"
        )
        self.fields["lecturer"].help_text = (
            "Lecturers may be assigned outside their home department. "
            "RollNexa will flag cross-department assignments without blocking them."
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned = super().clean()
        offering = cleaned.get("offering")
        lecturer = cleaned.get("lecturer")
        if offering and lecturer and CourseLecturerAssignment.objects.filter(
            offering=offering, lecturer=lecturer, is_active=True
        ).exists():
            self.add_error("lecturer", "This lecturer is already assigned to the selected offering.")
        return cleaned


class StudentCourseFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search courses")
