from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import UserProfile
from academics.models import Department, Programme

User = get_user_model()


class AdminCreateAccountForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "e.g. ada.okafor"}),
    )
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")
    role = forms.ChoiceField(
        choices=[
            (UserProfile.ROLE_STUDENT, "Student"),
            (UserProfile.ROLE_LECTURER, "Lecturer"),
        ],
        label="Account role",
    )
    institutional_id = forms.CharField(
        max_length=60,
        required=False,
        label="Institutional ID",
        help_text="Optional at this stage. We can align this with the university's ID format later.",
    )
    phone_number = forms.CharField(max_length=30, required=False, label="Phone number")
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), required=False, label="Department",
        help_text="Required for lecturer accounts once departments have been configured.",
    )
    programme = forms.ModelChoiceField(
        queryset=Programme.objects.none(), required=False, label="Programme",
        help_text="Required for student accounts once programmes have been configured.",
    )
    current_level = forms.ChoiceField(
        choices=[("", "Select level")] + UserProfile.LEVEL_CHOICES,
        required=False, label="Current level",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True, faculty__is_active=True).select_related("faculty").order_by("name")
        self.fields["programme"].queryset = Programme.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).select_related("department").order_by("name")

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        department = cleaned.get("department")
        programme = cleaned.get("programme")
        if role == UserProfile.ROLE_STUDENT:
            if Programme.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).exists() and not programme:
                self.add_error("programme", "Select the student's programme.")
            if department:
                self.add_error("department", "Student academic assignment is determined by the selected programme.")
        elif role == UserProfile.ROLE_LECTURER:
            if Department.objects.filter(is_active=True, faculty__is_active=True).exists() and not department:
                self.add_error("department", "Select the lecturer's department.")
            if programme:
                self.add_error("programme", "Lecturer accounts are assigned to a department, not a student programme.")
            if cleaned.get("current_level"):
                self.add_error("current_level", "Current level applies to student accounts only.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class AdminUpdateAccountForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")
    institutional_id = forms.CharField(max_length=60, required=False, label="Institutional ID")
    phone_number = forms.CharField(max_length=30, required=False, label="Phone number")
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), required=False, label="Department",
        help_text="Required for lecturer accounts once departments have been configured.",
    )
    programme = forms.ModelChoiceField(
        queryset=Programme.objects.none(), required=False, label="Programme",
        help_text="Required for student accounts once programmes have been configured.",
    )
    current_level = forms.ChoiceField(
        choices=[("", "Select level")] + UserProfile.LEVEL_CHOICES,
        required=False, label="Current level",
    )

    def __init__(self, *args, user, **kwargs):
        self.user = user
        self.profile = user.profile
        initial = kwargs.pop("initial", {})
        initial.update({
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "institutional_id": self.profile.institutional_id,
            "phone_number": self.profile.phone_number,
            "department": self.profile.department_id,
            "programme": self.profile.programme_id,
            "current_level": self.profile.current_level,
        })
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(
            is_active=True, faculty__is_active=True
        ).select_related("faculty").order_by("name")
        self.fields["programme"].queryset = Programme.objects.filter(
            is_active=True, department__is_active=True, department__faculty__is_active=True
        ).select_related("department").order_by("name")
        if self.profile.role == UserProfile.ROLE_STUDENT:
            self.fields["department"].disabled = True
        elif self.profile.role == UserProfile.ROLE_LECTURER:
            self.fields["programme"].disabled = True
            self.fields["current_level"].disabled = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if self.profile.role == UserProfile.ROLE_STUDENT:
            if Programme.objects.filter(is_active=True, department__is_active=True, department__faculty__is_active=True).exists() and not cleaned.get("programme"):
                self.add_error("programme", "Select the student's programme.")
        elif self.profile.role == UserProfile.ROLE_LECTURER:
            if Department.objects.filter(is_active=True, faculty__is_active=True).exists() and not cleaned.get("department"):
                self.add_error("department", "Select the lecturer's department.")
            if cleaned.get("programme"):
                self.add_error("programme", "Lecturer accounts are assigned to a department, not a student programme.")
            if cleaned.get("current_level"):
                self.add_error("current_level", "Current level applies to student accounts only.")
        return cleaned


class InitialAdminSetupForm(forms.Form):
    bootstrap_token = forms.CharField(
        label="One-time setup token",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
    username = forms.CharField(max_length=150, label="Administrator username")
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Administrator email")
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The passwords do not match.")
        if password1 and not self.errors.get("password1"):
            candidate = User(
                username=cleaned.get("username", ""),
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(password1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned
