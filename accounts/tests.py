from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import UserProfile

User = get_user_model()


class AttendIQAccountTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="systemadmin",
            email="admin@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = User.objects.create_user(
            username="student01",
            email="student@example.test",
            password="StudentTestPassword!2026",
        )

    def test_new_users_receive_a_student_profile_by_default(self):
        self.assertEqual(self.student.profile.role, UserProfile.ROLE_STUDENT)

    def test_public_self_registration_is_not_available(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 404)

    def test_student_dashboard_is_selected_for_student(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("student_dashboard"))

    def test_student_cannot_open_user_management(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("user_list"))
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_create_lecturer_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "lecturer01",
                "first_name": "Ada",
                "last_name": "Okafor",
                "email": "ada@example.test",
                "role": UserProfile.ROLE_LECTURER,
                "institutional_id": "LEC-001",
                "phone_number": "",
            },
        )
        self.assertRedirects(response, reverse("user_created"), fetch_redirect_response=False)
        confirmation = self.client.get(reverse("user_created"))
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "TEMPORARY PASSWORD")
        lecturer = User.objects.get(username="lecturer01")
        self.assertEqual(lecturer.profile.role, UserProfile.ROLE_LECTURER)
        self.assertTrue(lecturer.profile.must_change_password)
        self.assertEqual(lecturer.profile.created_by, self.admin)

    @override_settings(BOOTSTRAP_ADMIN_TOKEN="test-bootstrap-token")
    def test_one_time_admin_setup_creates_a_superuser(self):
        # Remove the setUp superuser to exercise the first-admin bootstrap.
        self.admin.delete()
        response = self.client.post(
            reverse("initial_admin_setup"),
            {
                "bootstrap_token": "test-bootstrap-token",
                "username": "firstadmin",
                "first_name": "First",
                "last_name": "Administrator",
                "email": "firstadmin@example.test",
                "password1": "A-Long-Test-Password-2026!",
                "password2": "A-Long-Test-Password-2026!",
            },
        )
        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertTrue(User.objects.filter(username="firstadmin", is_superuser=True).exists())
        self.assertEqual(User.objects.get(username="firstadmin").profile.role, UserProfile.ROLE_ADMIN)
