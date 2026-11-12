from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import UserProfile
from academics.models import (
    AcademicSession, Course, CourseLecturerAssignment, CourseOffering, Department,
    Faculty, Programme, Semester,
)

User = get_user_model()


class RollNexaAccountTests(TestCase):
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

    def test_student_creation_requires_programme_when_programmes_exist(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(faculty=faculty, code="CSC", name="Computer Science")
        Programme.objects.create(department=department, code="BSC-CS", name="Computer Science")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "student02", "first_name": "Ada", "last_name": "Okafor",
                "email": "student02@example.test", "role": UserProfile.ROLE_STUDENT,
                "institutional_id": "STU-002", "phone_number": "", "programme": "",
                "department": "", "current_level": "100",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select the student's programme.")

    def test_admin_can_assign_existing_student_to_programme(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(faculty=faculty, code="CSC", name="Computer Science")
        programme = Programme.objects.create(department=department, code="BSC-CS", name="Computer Science")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_edit", kwargs={"user_id": self.student.pk}),
            {
                "first_name": "Test", "last_name": "Student", "email": "student@example.test",
                "institutional_id": "STU-001", "phone_number": "", "programme": str(programme.pk),
                "department": "", "current_level": "400",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.profile.programme, programme)
        self.assertEqual(self.student.profile.current_level, "400")

    def test_student_profile_can_be_assigned_to_programme(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(faculty=faculty, code="CSC", name="Computer Science")
        programme = Programme.objects.create(department=department, code="BSC-CS", name="Computer Science")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "student03", "first_name": "Ada", "last_name": "Okafor",
                "email": "student03@example.test", "role": UserProfile.ROLE_STUDENT,
                "institutional_id": "STU-003", "phone_number": "", "programme": str(programme.pk),
                "department": "", "current_level": "300",
            },
        )
        self.assertRedirects(response, reverse("user_created"), fetch_redirect_response=False)
        student = User.objects.get(username="student03")
        self.assertEqual(student.profile.programme, programme)
        self.assertEqual(student.profile.department, department)
        self.assertEqual(student.profile.current_level, "300")

    def test_create_lecturer_account_link_preselects_lecturer_role(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("user_create"), {"role": "lecturer"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["role"].value(), UserProfile.ROLE_LECTURER)

    def test_admin_can_open_lecturer_directory_and_profile(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(
            faculty=faculty, code="BIO", name="Applied Biology"
        )
        lecturer_user = User.objects.create_user(
            username="lecturer_directory", email="lecturer_directory@example.test",
            password="StrongTestPassword!2026",
        )
        lecturer_user.profile.role = UserProfile.ROLE_LECTURER
        lecturer_user.profile.department = department
        lecturer_user.profile.save()
        self.client.force_login(self.admin)
        directory = self.client.get(reverse("lecturer_management"))
        self.assertEqual(directory.status_code, 200)
        self.assertContains(directory, "Lecturer management")
        self.assertContains(directory, "lecturer_directory")
        detail = self.client.get(reverse(
            "lecturer_profile_detail", kwargs={"profile_id": lecturer_user.profile.pk}
        ))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Applied Biology")

    def test_student_cannot_open_lecturer_management(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("lecturer_management"))
        self.assertEqual(response.status_code, 403)

    def test_deactivating_lecturer_revokes_active_assignments_and_keeps_history(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(
            faculty=faculty, code="CSC", name="Computer Science"
        )
        programme = Programme.objects.create(
            department=department, code="BSC-CS", name="Computer Science"
        )
        session = AcademicSession.objects.create(name="2025/2026", is_current=True)
        semester = Semester.objects.create(
            session=session, name=Semester.FIRST, is_current=True
        )
        course = Course.objects.create(
            department=department, code="CSC101", title="Introduction to Computing", credit_units=2
        )
        offering = CourseOffering.objects.create(
            course=course, programme=programme, semester=semester, level="100"
        )
        lecturer_user = User.objects.create_user(
            username="lecturer_deactivate", email="lecturer_deactivate@example.test",
            password="StrongTestPassword!2026",
        )
        lecturer_user.profile.role = UserProfile.ROLE_LECTURER
        lecturer_user.profile.department = department
        lecturer_user.profile.save()
        assignment = CourseLecturerAssignment.objects.create(
            offering=offering, lecturer=lecturer_user.profile, assigned_by=self.admin
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("toggle_account_status", kwargs={"user_id": lecturer_user.pk}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        lecturer_user.refresh_from_db()
        assignment.refresh_from_db()
        self.assertFalse(lecturer_user.is_active)
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.removed_by, self.admin)
        self.assertIsNotNone(assignment.removed_at)
        self.assertContains(response, "1 active teaching assignment(s) were revoked")

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
