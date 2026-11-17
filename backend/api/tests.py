from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from academics.models import (
    AcademicSession,
    Course,
    CourseLecturerAssignment,
    CourseOffering,
    Department,
    Faculty,
    Programme,
    Semester,
)

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


class WorkspaceApiPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username="workspace.student",
            password="Strong-Test-Password-2026!",
            first_name="Ada",
            last_name="Student",
        )
        self.student.profile.role = UserProfile.ROLE_STUDENT
        self.student.profile.save(update_fields=["role", "updated_at"])

        self.lecturer = User.objects.create_user(
            username="workspace.lecturer",
            password="Strong-Test-Password-2026!",
            first_name="Grace",
            last_name="Lecturer",
        )
        self.lecturer.profile.role = UserProfile.ROLE_LECTURER
        self.lecturer.profile.save(update_fields=["role", "updated_at"])

        self.admin = User.objects.create_superuser(
            username="workspace.admin",
            email="workspace.admin@example.test",
            password="Strong-Test-Password-2026!",
        )

    def test_student_cannot_access_administrator_user_management(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/v1/workspace/users/")

        self.assertEqual(response.status_code, 403)

    def test_administrator_can_list_users(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/workspace/users/")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 2)
        self.assertIn("workspace.student", [item["username"] for item in response.data["results"]])

    def test_lecturer_can_access_lecturer_course_workspace(self):
        self.client.force_authenticate(user=self.lecturer)

        response = self.client.get("/api/v1/workspace/lecturer-courses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_lecturer_cannot_access_administrator_user_management(self):
        self.client.force_authenticate(user=self.lecturer)

        response = self.client.get("/api/v1/workspace/users/")

        self.assertEqual(response.status_code, 403)

    def test_student_course_workspace_reports_incomplete_academic_profile(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/v1/workspace/student-courses/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["profileComplete"])
        self.assertEqual(response.data["count"], 0)

    def test_profile_endpoint_returns_only_authenticated_user_profile(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/v1/workspace/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["item"]["username"], "workspace.student")
        self.assertNotIn("password", response.data["item"])

    def test_reports_are_available_to_administrators(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/workspace/reports/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], UserProfile.ROLE_ADMIN)
        self.assertIn("attendance", response.data)

    def test_student_cannot_access_administrator_reports(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/v1/workspace/reports/")

        self.assertEqual(response.status_code, 403)

    def test_lecturer_cannot_access_institution_wide_attendance_monitor(self):
        self.client.force_authenticate(user=self.lecturer)

        response = self.client.get("/api/v1/workspace/attendance-monitor/")

        self.assertEqual(response.status_code, 403)

    def test_administrator_can_list_academic_resources(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/workspace/faculties/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_student_cannot_access_lecturer_course_workspace(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/v1/workspace/lecturer-courses/")

        self.assertEqual(response.status_code, 403)

    def test_lecturer_cannot_access_student_course_workspace(self):
        self.client.force_authenticate(user=self.lecturer)

        response = self.client.get("/api/v1/workspace/student-courses/")

        self.assertEqual(response.status_code, 403)


class AcademicWorkflowImprovementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="workflow.admin",
            email="workflow.admin@example.test",
            password="Strong-Test-Password-2026!",
        )
        self.faculty = Faculty.objects.create(code="FSC", name="Faculty of Science")
        self.computer_science = Department.objects.create(
            faculty=self.faculty,
            code="CSC",
            name="Computer Science",
        )
        self.software_engineering = Department.objects.create(
            faculty=self.faculty,
            code="SEN",
            name="Software Engineering",
        )
        self.cs_programme = Programme.objects.create(
            department=self.computer_science,
            code="BSC-CS",
            name="Computer Science",
        )
        self.se_programme = Programme.objects.create(
            department=self.software_engineering,
            code="BSC-SE",
            name="Software Engineering",
        )
        self.session = AcademicSession.objects.create(name="2026/2027", is_current=True)
        self.semester = Semester.objects.create(
            session=self.session,
            name=Semester.FIRST,
            is_current=True,
        )
        self.course = Course.objects.create(
            department=self.computer_science,
            code="CSC201",
            title="Data Structures",
            credit_units=3,
        )
        self.cs_offering = CourseOffering.objects.create(
            course=self.course,
            programme=self.cs_programme,
            semester=self.semester,
            level="200",
            registration_open=True,
        )
        self.se_offering = CourseOffering.objects.create(
            course=self.course,
            programme=self.se_programme,
            semester=self.semester,
            level="200",
            registration_open=True,
        )
        self.other_level_offering = CourseOffering.objects.create(
            course=self.course,
            programme=self.cs_programme,
            semester=self.semester,
            level="300",
            registration_open=True,
        )
        lecturer_user = User.objects.create_user(
            username="workflow.lecturer",
            email="workflow.lecturer@example.test",
            password="Strong-Test-Password-2026!",
        )
        self.lecturer = lecturer_user.profile
        self.lecturer.role = UserProfile.ROLE_LECTURER
        self.lecturer.department = self.computer_science
        self.lecturer.save(update_fields=["role", "department", "updated_at"])

        student_user = User.objects.create_user(
            username="workflow.student",
            email="workflow.student@example.test",
            password="Strong-Test-Password-2026!",
        )
        self.student = student_user
        self.student.profile.role = UserProfile.ROLE_STUDENT
        self.student.profile.programme = self.cs_programme
        self.student.profile.current_level = "200"
        self.student.profile.save(update_fields=["role", "programme", "current_level", "updated_at"])

    def test_administrator_can_open_registration_for_all_active_offerings(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/registration-control/",
            {"action": "open"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated_count"], 3)
        self.assertFalse(CourseOffering.objects.filter(registration_open=False).exists())

    def test_administrator_can_close_registration_for_all_active_offerings(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/registration-control/",
            {"action": "close"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated_count"], 3)
        self.assertFalse(CourseOffering.objects.filter(registration_open=True).exists())

    def test_non_administrator_cannot_change_global_registration(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            "/api/v1/workspace/registration-control/",
            {"action": "close"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CourseOffering.objects.filter(registration_open=True).exists())

    def test_student_cannot_register_after_global_close(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            "/api/v1/workspace/registration-control/",
            {"action": "close"},
            format="json",
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f"/api/v1/workspace/student-courses/{self.cs_offering.pk}/register/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Registration is closed", response.data["detail"])

    def test_global_registration_summary_reports_open_and_closed_offerings(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/workspace/offerings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["registrationSummary"]["activeOfferings"], 3)
        self.assertEqual(response.data["registrationSummary"]["openOfferings"], 3)
        self.assertEqual(response.data["registrationSummary"]["state"], "open")

    def test_assignment_options_filter_same_course_semester_and_level(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            "/api/v1/workspace/assignment-options/",
            {
                "course": self.course.pk,
                "semester": self.semester.pk,
                "level": "200",
                "lecturer": self.lecturer.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["offerings"]), 2)
        self.assertEqual(
            {item["programme_name"] for item in response.data["offerings"]},
            {self.cs_programme.name, self.se_programme.name},
        )

    def test_administrator_can_assign_lecturer_to_multiple_programme_offerings(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/assignments/bulk/",
            {
                "lecturer": self.lecturer.pk,
                "offering_ids": [self.cs_offering.pk, self.se_offering.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_count"], 2)
        self.assertEqual(
            CourseLecturerAssignment.objects.filter(lecturer=self.lecturer, is_active=True).count(),
            2,
        )

    def test_bulk_assignment_skips_existing_active_assignments(self):
        CourseLecturerAssignment.objects.create(
            offering=self.cs_offering,
            lecturer=self.lecturer,
            assigned_by=self.admin,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/assignments/bulk/",
            {
                "lecturer": self.lecturer.pk,
                "offering_ids": [self.cs_offering.pk, self.se_offering.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(response.data["already_assigned_count"], 1)
        self.assertEqual(
            CourseLecturerAssignment.objects.filter(lecturer=self.lecturer, is_active=True).count(),
            2,
        )

    def test_bulk_assignment_rejects_mixed_levels(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/assignments/bulk/",
            {
                "lecturer": self.lecturer.pk,
                "offering_ids": [self.cs_offering.pk, self.other_level_offering.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("same course, semester and level", response.data["detail"])
        self.assertFalse(CourseLecturerAssignment.objects.exists())

    def test_student_cannot_create_bulk_teaching_assignments(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            "/api/v1/workspace/assignments/bulk/",
            {
                "lecturer": self.lecturer.pk,
                "offering_ids": [self.cs_offering.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseLecturerAssignment.objects.exists())

    def test_user_creation_validation_returns_field_specific_errors(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/users/",
            {
                "username": self.student.username,
                "first_name": "New",
                "last_name": "Student",
                "email": "new.student@example.test",
                "role": UserProfile.ROLE_STUDENT,
                "programme": self.cs_programme.pk,
                "current_level": "200",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data["errors"])
        self.assertIn("field errors", response.data["detail"])

    def test_user_creation_returns_one_time_temporary_password(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/workspace/users/",
            {
                "username": "new.workflow.student",
                "first_name": "New",
                "last_name": "Student",
                "email": "new.workflow.student@example.test",
                "role": UserProfile.ROLE_STUDENT,
                "programme": self.cs_programme.pk,
                "current_level": "200",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["temporary_password"])
        created_user = User.objects.get(username="new.workflow.student")
        self.assertTrue(created_user.check_password(response.data["temporary_password"]))
        self.assertTrue(created_user.profile.must_change_password)
