from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_LECTURER = "lecturer"
    ROLE_STUDENT = "student"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "System administrator"),
        (ROLE_LECTURER, "Lecturer"),
        (ROLE_STUDENT, "Student"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        db_index=True,
    )
    institutional_id = models.CharField(max_length=60, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(
        "academics.Department", on_delete=models.PROTECT,
        null=True, blank=True, related_name="staff_profiles",
    )
    programme = models.ForeignKey(
        "academics.Programme", on_delete=models.PROTECT,
        null=True, blank=True, related_name="student_profiles",
    )
    LEVEL_CHOICES = [(str(level), f"{level} level") for level in (100, 200, 300, 400, 500, 600, 700)]
    current_level = models.CharField(max_length=3, choices=LEVEL_CHOICES, blank=True)
    must_change_password = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rollnexa_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    def __str__(self):
        return f"{self.user.get_username()} — {self.get_role_display()}"
