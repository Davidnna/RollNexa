from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AcademicSession, Department, Faculty, Programme, Semester

User = get_user_model()


class AcademicStructureTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="academicadmin", email="academicadmin@example.test", password="StrongTestPassword!2026"
        )
        self.student = User.objects.create_user(
            username="academicstudent", email="academicstudent@example.test", password="StrongTestPassword!2026"
        )

    def test_admin_can_open_academic_overview(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academic_overview"))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_open_academic_overview(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("academic_overview"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_faculty(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("academic_create", kwargs={"kind": "faculties"}), {
            "code": "SCI", "name": "Faculty of Science", "description": "Science disciplines"
        })
        self.assertRedirects(response, reverse("academic_list", kwargs={"kind": "faculties"}))
        self.assertTrue(Faculty.objects.filter(code="SCI").exists())

    def test_department_and_programme_hierarchy(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(faculty=faculty, code="CSC", name="Computer Science")
        programme = Programme.objects.create(department=department, code="BSC-CS", name="Computer Science", award="B.Sc.")
        self.assertEqual(programme.department.faculty, faculty)

    def test_only_one_current_session_can_be_set_through_view(self):
        first = AcademicSession.objects.create(name="2024/2025")
        second = AcademicSession.objects.create(name="2025/2026")
        self.client.force_login(self.admin)
        self.client.post(reverse("set_current_session", kwargs={"pk": first.pk}))
        self.client.post(reverse("set_current_session", kwargs={"pk": second.pk}))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_current_semester_requires_current_session(self):
        session = AcademicSession.objects.create(name="2025/2026")
        semester = Semester.objects.create(session=session, name=Semester.FIRST)
        self.client.force_login(self.admin)
        self.client.post(reverse("set_current_semester", kwargs={"pk": semester.pk}))
        semester.refresh_from_db()
        self.assertFalse(semester.is_current)

    def test_current_semester_can_be_set_after_session_is_current(self):
        session = AcademicSession.objects.create(name="2025/2026", is_current=True)
        semester = Semester.objects.create(session=session, name=Semester.FIRST)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("set_current_semester", kwargs={"pk": semester.pk}))
        self.assertRedirects(response, reverse("academic_list", kwargs={"kind": "semesters"}))
        semester.refresh_from_db()
        self.assertTrue(semester.is_current)


    def test_deactivating_faculty_deactivates_departments_and_programmes(self):
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(faculty=faculty, code="CSC", name="Computer Science")
        programme = Programme.objects.create(department=department, code="BSC-CS", name="Computer Science")
        self.client.force_login(self.admin)
        self.client.post(reverse("academic_toggle", kwargs={"kind": "faculties", "pk": faculty.pk}))
        department.refresh_from_db()
        programme.refresh_from_db()
        self.assertFalse(department.is_active)
        self.assertFalse(programme.is_active)

    def test_deactivating_current_session_deactivates_its_semesters(self):
        session = AcademicSession.objects.create(name="2025/2026", is_current=True)
        semester = Semester.objects.create(session=session, name=Semester.FIRST, is_current=True)
        self.client.force_login(self.admin)
        self.client.post(reverse("academic_toggle", kwargs={"kind": "sessions", "pk": session.pk}))
        session.refresh_from_db()
        semester.refresh_from_db()
        self.assertFalse(session.is_current)
        self.assertFalse(semester.is_active)
        self.assertFalse(semester.is_current)

    def test_session_date_order_validation(self):
        session = AcademicSession(name="2025/2026", start_date=date(2026, 1, 1), end_date=date(2025, 1, 1))
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            session.full_clean()
