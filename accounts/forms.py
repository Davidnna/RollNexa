from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import UserProfile

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
