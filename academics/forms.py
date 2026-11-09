from django import forms
from django.core.exceptions import ValidationError

from .models import AcademicSession, Department, Faculty, Programme, Semester


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()


class FacultyForm(StyledModelForm):
    class Meta:
        model = Faculty
        fields = ["code", "name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class DepartmentForm(StyledModelForm):
    class Meta:
        model = Department
        fields = ["faculty", "code", "name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faculty"].queryset = Faculty.objects.filter(is_active=True).order_by("name")


class ProgrammeForm(StyledModelForm):
    class Meta:
        model = Programme
        fields = ["department", "code", "name", "award", "duration_years", "mode", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True, faculty__is_active=True).select_related("faculty").all()


class AcademicSessionForm(StyledModelForm):
    class Meta:
        model = AcademicSession
        fields = ["name", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class SemesterForm(StyledModelForm):
    class Meta:
        model = Semester
        fields = ["session", "name", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["session"].queryset = AcademicSession.objects.filter(is_active=True).order_by("-name")

    def clean(self):
        cleaned = super().clean()
        session = cleaned.get("session")
        if self.instance.pk and self.instance.is_current and session and session.pk != self.instance.session_id:
            self.instance.is_current = False
        return cleaned
