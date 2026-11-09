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
        fields = ["department", "code", "title", "credit_units", "description"]
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


class LecturerAssignmentForm(forms.Form):
    lecturer = forms.ModelChoiceField(
        queryset=UserProfile.objects.none(),
        label="Lecturer",
        empty_label="Select a lecturer",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lecturer"].queryset = UserProfile.objects.filter(
            role=UserProfile.ROLE_LECTURER,
            user__is_active=True,
        ).select_related("user", "department").order_by(
            "user__last_name", "user__first_name", "user__username"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class StudentCourseFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search courses")
