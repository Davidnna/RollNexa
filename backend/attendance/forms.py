from django import forms

from academics.models import CourseOffering

from .models import AttendanceSession


class AttendanceSessionForm(forms.ModelForm):
    starts_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"},
            format="%Y-%m-%dT%H:%M",
        ),
        label="Starts at",
    )
    ends_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"},
            format="%Y-%m-%dT%H:%M",
        ),
        label="Ends at",
    )

    class Meta:
        model = AttendanceSession
        fields = ["offering", "title", "starts_at", "ends_at", "notes"]
        widgets = {
            "offering": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Lecture 1 or Week 3 tutorial"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional lecturer notes"}),
        }
        help_texts = {
            "offering": "Only active course offerings assigned to your lecturer account are available.",
            "title": "Optional. Leave blank to use the course and date as the session label.",
            "notes": "For lecturer reference only; do not enter student biometric information.",
        }

    def __init__(self, *args, lecturer_profile, created_by, **kwargs):
        super().__init__(*args, **kwargs)
        self.lecturer_profile = lecturer_profile
        self.instance.created_by = created_by
        self.fields["offering"].queryset = CourseOffering.objects.filter(
            is_active=True,
            lecturer_assignments__lecturer=lecturer_profile,
            lecturer_assignments__is_active=True,
            course__is_active=True,
            programme__is_active=True,
            semester__is_active=True,
            semester__session__is_active=True,
            course__department__is_active=True,
            course__department__faculty__is_active=True,
            programme__department__is_active=True,
            programme__department__faculty__is_active=True,
        ).select_related(
            "course", "programme", "semester", "semester__session"
        ).distinct()
        self.fields["offering"].label_from_instance = self._offering_label

    @staticmethod
    def _offering_label(offering):
        return (
            f"{offering.course.code} — {offering.course.title} | "
            f"{offering.programme.name} | {offering.get_level_display()} | "
            f"{offering.semester.get_name_display()} {offering.semester.session.name}"
        )

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "The session end time must be later than its start time.")
        return cleaned_data
