from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

User = get_user_model()


class SessionAuthenticationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username="api.student",
            password="Strong-Test-Password-2026!",
            first_name="Ada",
            last_name="Okafor",
        )
        self.user.profile.role = UserProfile.ROLE_STUDENT
        self.user.profile.save(update_fields=["role", "updated_at"])

    def obtain_csrf_token(self):
        response = self.client.get("/api/v1/csrf/")
        self.assertEqual(response.status_code, 200)
        return response.data["csrfToken"]

    def test_anonymous_session_is_explicit(self):
        response = self.client.get("/api/v1/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["authenticated"])
        self.assertIsNone(response.data["user"])

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_login_creates_session_and_returns_profile(self):
        csrf_token = self.obtain_csrf_token()
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])
        self.assertEqual(response.data["user"]["role"], UserProfile.ROLE_STUDENT)

        session_response = self.client.get("/api/v1/auth/session/")
        self.assertTrue(session_response.data["authenticated"])
        self.assertEqual(session_response.data["user"]["username"], "api.student")

    def test_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        csrf_token = self.obtain_csrf_token()

        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data.get("authenticated", False))

    def test_logout_ends_session_after_csrf_protected_request(self):
        csrf_token = self.obtain_csrf_token()
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)
        refreshed_csrf_token = login_response.data["csrfToken"]

        response = self.client.post(
            "/api/v1/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=refreshed_csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.get("/api/v1/auth/session/").data["authenticated"])


    def test_logout_rejects_request_without_csrf_token(self):
        csrf_token = self.obtain_csrf_token()
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)

        response = self.client.post(
            "/api/v1/auth/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.client.get("/api/v1/auth/session/").data["authenticated"])

    def test_password_change_updates_password_and_clears_temporary_flag(self):
        self.user.profile.must_change_password = True
        self.user.profile.save(update_fields=["must_change_password", "updated_at"])
        csrf_token = self.obtain_csrf_token()
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "api.student", "password": "Strong-Test-Password-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)

        response = self.client.post(
            "/api/v1/auth/password-change/",
            {
                "currentPassword": "Strong-Test-Password-2026!",
                "newPassword": "Different-Strong-Password-2027!",
                "confirmPassword": "Different-Strong-Password-2027!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=login_response.data["csrfToken"],
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.check_password("Different-Strong-Password-2027!"))
        self.assertFalse(self.user.profile.must_change_password)
        self.assertTrue(self.client.get("/api/v1/auth/session/").data["authenticated"])

    def test_dashboard_requires_authentication(self):
        response = self.client.get("/api/v1/dashboard/summary/")

        self.assertIn(response.status_code, {401, 403})

    def test_student_dashboard_returns_role_scoped_summary(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], UserProfile.ROLE_STUDENT)
        self.assertIn("cards", response.data)

    def test_temporary_password_blocks_dashboard_summary(self):
        self.user.profile.must_change_password = True
        self.user.profile.save(update_fields=["must_change_password", "updated_at"])
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/v1/dashboard/summary/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("Change your temporary password", response.data["detail"])
