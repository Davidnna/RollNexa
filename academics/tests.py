from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile

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


class AcademicCSVImportTests(TestCase):
    CSV_CONTENT = (
        "faculty_code,faculty_name,department_code,department_name,programme_code,programme_name,award,duration_years,mode\n"
        "FSC,Faculty of Science,FSC-CSC,Computer Science,FSC-CSC-BSC,Computer Science,B.Sc.,,full_time\n"
        "FSC,Faculty of Science,FSC-BIO,Applied Biology,FSC-BIO-BSC,Applied Biology,,,full_time\n"
    )

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="csvadmin", email="csvadmin@example.test", password="StrongTestPassword!2026"
        )
        self.student = User.objects.create_user(
            username="csvstudent", email="csvstudent@example.test", password="StrongTestPassword!2026"
        )

    def upload(self):
        return SimpleUploadedFile("academic.csv", self.CSV_CONTENT.encode("utf-8"), content_type="text/csv")

    def test_non_admin_cannot_open_csv_import(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("academic_csv_import"))
        self.assertEqual(response.status_code, 403)

    def test_preview_does_not_write_until_confirmed(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("academic_csv_import"), {"action": "preview", "csv_file": self.upload()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import preview")
        self.assertEqual(Faculty.objects.count(), 0)
        response = self.client.post(reverse("academic_csv_import"), {"action": "import"})
        self.assertRedirects(response, reverse("academic_overview"))
        self.assertEqual(Faculty.objects.count(), 1)
        self.assertEqual(Department.objects.count(), 2)
        self.assertEqual(Programme.objects.count(), 2)

    def test_import_is_idempotent(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("academic_csv_import"), {"action": "preview", "csv_file": self.upload()})
        self.client.post(reverse("academic_csv_import"), {"action": "import"})
        self.client.post(reverse("academic_csv_import"), {"action": "preview", "csv_file": self.upload()})
        response = self.client.post(reverse("academic_csv_import"), {"action": "import"})
        self.assertRedirects(response, reverse("academic_overview"))
        self.assertEqual(Faculty.objects.count(), 1)
        self.assertEqual(Department.objects.count(), 2)
        self.assertEqual(Programme.objects.count(), 2)

    def test_invalid_department_pair_is_rejected(self):
        self.client.force_login(self.admin)
        content = "faculty_code,faculty_name,department_code,department_name\nFSC,Faculty of Science,FSC-CSC,\n"
        upload = SimpleUploadedFile("invalid.csv", content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(reverse("academic_csv_import"), {"action": "preview", "csv_file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "provide both department_code and department_name", status_code=400)
        self.assertEqual(Faculty.objects.count(), 0)


from .models import Course, CourseLecturerAssignment, CourseOffering, CourseRegistration
from accounts.models import UserProfile


class CourseManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="courseadmin", email="courseadmin@example.test", password="StrongTestPassword!2026"
        )
        self.faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        self.department = Department.objects.create(
            faculty=self.faculty, code="CSC", name="Computer Science"
        )
        self.programme = Programme.objects.create(
            department=self.department, code="BSC-CS", name="Computer Science", award="B.Sc."
        )
        self.session = AcademicSession.objects.create(name="2025/2026", is_current=True)
        self.semester = Semester.objects.create(
            session=self.session, name=Semester.FIRST, is_current=True
        )
        self.course = Course.objects.create(
            department=self.department, code="CSC301", title="Data Structures",
            credit_units=3,
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, programme=self.programme, semester=self.semester,
            level="300", registration_open=True,
        )
        self.student_user = User.objects.create_user(
            username="course_student", email="course_student@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = self.student_user.profile
        self.student.programme = self.programme
        self.student.current_level = "300"
        self.student.save()
        self.lecturer_user = User.objects.create_user(
            username="course_lecturer", email="course_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        self.lecturer = self.lecturer_user.profile
        self.lecturer.role = UserProfile.ROLE_LECTURER
        self.lecturer.department = self.department
        self.lecturer.save()

    def test_admin_can_open_course_management(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("course_management"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Course management")

    def test_student_cannot_open_course_management(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("course_management"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_course(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("course_create"), {
            "department": self.department.pk, "code": "CSC302",
            "title": "Algorithms", "credit_units": 3, "description": "",
        })
        self.assertRedirects(response, reverse("course_catalogue"))
        self.assertTrue(Course.objects.filter(code="CSC302").exists())

    def test_student_sees_only_matching_programme_and_level_offerings(self):
        other_offering = CourseOffering.objects.create(
            course=self.course,
            programme=Programme.objects.create(
                department=self.department, code="BSC-MATH", name="Mathematics"
            ),
            semester=self.semester, level="300", registration_open=True,
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("student_course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSC301")
        self.assertEqual(list(response.context["offerings"]), [self.offering])

    def test_student_can_register_for_eligible_open_offering(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse("student_course_register", kwargs={"pk": self.offering.pk}))
        self.assertRedirects(response, reverse("student_course_list"))
        self.assertTrue(CourseRegistration.objects.filter(
            offering=self.offering, student=self.student,
            status=CourseRegistration.STATUS_REGISTERED,
        ).exists())

    def test_student_cannot_register_for_another_programme(self):
        other_programme = Programme.objects.create(
            department=self.department, code="BSC-MATH", name="Mathematics"
        )
        other_offering = CourseOffering.objects.create(
            course=self.course, programme=other_programme, semester=self.semester,
            level="300", registration_open=True,
        )
        self.client.force_login(self.student_user)
        response = self.client.post(reverse("student_course_register", kwargs={"pk": other_offering.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(CourseRegistration.objects.filter(offering=other_offering).exists())

    def test_registration_capacity_is_enforced(self):
        self.offering.max_students = 1
        self.offering.save()
        another_user = User.objects.create_user(
            username="second_student", email="second_student@example.test",
            password="StrongTestPassword!2026",
        )
        another = another_user.profile
        another.programme = self.programme
        another.current_level = "300"
        another.save()
        CourseRegistration.objects.create(offering=self.offering, student=self.student)
        self.client.force_login(another_user)
        self.client.post(reverse("student_course_register", kwargs={"pk": self.offering.pk}))
        self.assertFalse(CourseRegistration.objects.filter(offering=self.offering, student=another).exists())

    def test_lecturer_only_sees_assigned_offerings(self):
        CourseLecturerAssignment.objects.create(offering=self.offering, lecturer=self.lecturer)
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("lecturer_course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSC301")

    def test_assigned_lecturer_can_view_roster_but_student_cannot(self):
        CourseLecturerAssignment.objects.create(offering=self.offering, lecturer=self.lecturer)
        CourseRegistration.objects.create(offering=self.offering, student=self.student)
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("lecturer_course_roster", kwargs={"pk": self.offering.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "course_student")
        self.client.force_login(self.student_user)
        denied = self.client.get(reverse("lecturer_course_roster", kwargs={"pk": self.offering.pk}))
        self.assertEqual(denied.status_code, 403)

    def test_course_offering_cannot_be_registered_when_closed(self):
        self.offering.registration_open = False
        self.offering.save()
        self.client.force_login(self.student_user)
        self.client.post(reverse("student_course_register", kwargs={"pk": self.offering.pk}))
        self.assertFalse(CourseRegistration.objects.filter(offering=self.offering).exists())

    def test_cross_department_lecturer_can_be_assigned_without_changing_home_department(self):
        other_faculty = Faculty.objects.create(code="MGT", name="Faculty of Management Sciences")
        other_department = Department.objects.create(
            faculty=other_faculty, code="ACC", name="Accountancy"
        )
        other_lecturer_user = User.objects.create_user(
            username="service_lecturer", email="service_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        other_lecturer = other_lecturer_user.profile
        other_lecturer.role = UserProfile.ROLE_LECTURER
        other_lecturer.department = other_department
        other_lecturer.save()

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("offering_assign_lecturer", kwargs={"pk": self.offering.pk}),
            {"lecturer": other_lecturer.pk}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        assignment = CourseLecturerAssignment.objects.get(
            offering=self.offering, lecturer=other_lecturer, is_active=True
        )
        self.assertEqual(assignment.assigned_by, self.admin)
        self.assertTrue(assignment.is_cross_department)
        other_lecturer.refresh_from_db()
        self.assertEqual(other_lecturer.department, other_department)
        self.assertContains(response, "permitted cross-department teaching assignment")

    def test_multiple_lecturers_can_be_assigned_to_one_offering(self):
        second_user = User.objects.create_user(
            username="second_lecturer", email="second_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        second = second_user.profile
        second.role = UserProfile.ROLE_LECTURER
        second.department = self.department
        second.save()
        self.client.force_login(self.admin)
        for lecturer in (self.lecturer, second):
            response = self.client.post(
                reverse("offering_assign_lecturer", kwargs={"pk": self.offering.pk}),
                {"lecturer": lecturer.pk},
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            CourseLecturerAssignment.objects.filter(offering=self.offering, is_active=True).count(), 2
        )

    def test_revoking_assignment_preserves_history_and_removes_lecturer_access(self):
        assignment = CourseLecturerAssignment.objects.create(
            offering=self.offering, lecturer=self.lecturer, assigned_by=self.admin
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("offering_remove_lecturer", kwargs={
                "pk": self.offering.pk, "assignment_id": assignment.pk,
            }), {"removal_note": "Semester teaching reassignment"}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertIsNotNone(assignment.removed_at)
        self.assertEqual(assignment.removed_by, self.admin)
        self.assertEqual(assignment.removal_note, "Semester teaching reassignment")
        self.client.force_login(self.lecturer_user)
        self.assertFalse(
            CourseLecturerAssignment.objects.filter(
                lecturer=self.lecturer, offering=self.offering, is_active=True
            ).exists()
        )
        denied = self.client.get(reverse("lecturer_course_roster", kwargs={"pk": self.offering.pk}))
        self.assertEqual(denied.status_code, 404)

    def test_reassignment_after_revocation_creates_a_new_audit_record(self):
        old_assignment = CourseLecturerAssignment.objects.create(
            offering=self.offering, lecturer=self.lecturer, assigned_by=self.admin
        )
        old_assignment.is_active = False
        from django.utils import timezone
        old_assignment.removed_at = timezone.now()
        old_assignment.removed_by = self.admin
        old_assignment.save(update_fields=["is_active", "removed_at", "removed_by"])
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("offering_assign_lecturer", kwargs={"pk": self.offering.pk}),
            {"lecturer": self.lecturer.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            CourseLecturerAssignment.objects.filter(
                offering=self.offering, lecturer=self.lecturer
            ).count(), 2,
        )
        self.assertEqual(
            CourseLecturerAssignment.objects.filter(
                offering=self.offering, lecturer=self.lecturer, is_active=True
            ).count(), 1,
        )

    def test_admin_can_open_central_teaching_assignment_register(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teaching_assignment_management"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teaching assignments")
        self.assertContains(response, "Cross-department teaching is permitted")

    def test_central_assignment_form_allows_cross_department_teaching(self):
        other_faculty = Faculty.objects.create(code="MGT", name="Faculty of Management Sciences")
        other_department = Department.objects.create(
            faculty=other_faculty, code="ACC", name="Accountancy"
        )
        lecturer_user = User.objects.create_user(
            username="central_cross_lecturer", email="central_cross@example.test",
            password="StrongTestPassword!2026",
        )
        lecturer = lecturer_user.profile
        lecturer.role = UserProfile.ROLE_LECTURER
        lecturer.department = other_department
        lecturer.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("teaching_assignment_management"),
            {"offering": self.offering.pk, "lecturer": lecturer.pk}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        assignment = CourseLecturerAssignment.objects.get(
            offering=self.offering, lecturer=lecturer, is_active=True
        )
        self.assertTrue(assignment.is_cross_department)
        self.assertContains(response, "Cross-department teaching assignment created")

    def test_lecturer_cannot_view_another_lecturers_roster(self):
        another_user = User.objects.create_user(
            username="unassigned_lecturer", email="unassigned_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        another = another_user.profile
        another.role = UserProfile.ROLE_LECTURER
        another.department = self.department
        another.save()
        CourseLecturerAssignment.objects.create(offering=self.offering, lecturer=self.lecturer)
        self.client.force_login(another_user)
        response = self.client.get(
            reverse("lecturer_course_roster", kwargs={"pk": self.offering.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_open_central_teaching_assignment_register(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("teaching_assignment_management"))
        self.assertEqual(response.status_code, 403)

    def test_lecturer_assignment_rejects_student_profile(self):
        assignment = CourseLecturerAssignment(
            offering=self.offering, lecturer=self.student
        )
        with self.assertRaises(Exception):
            assignment.full_clean()


class CourseCSVImportTests(TestCase):
    CSV_CONTENT = (
        "faculty_code,department_code,course_code,course_title,credit_units,stress_code,"
        "programme_code,academic_session,semester,level,offering_active,registration_open,max_students\n"
        "FSC,FSC-CS,CSC 101,Introduction to Computer Science,2,C,"
        "FSC-CS-P01,CURRENT,FIRST,100,true,false,\n"
        "FSC,FSC-CS,CSC 112,Problem Solving and Programming,3,C,"
        "FSC-CS-P01,CURRENT,SECOND,100,true,false,\n"
    )

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="coursecsvadmin", email="coursecsvadmin@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = User.objects.create_user(
            username="coursecsvstudent", email="coursecsvstudent@example.test",
            password="StrongTestPassword!2026",
        )
        self.faculty = Faculty.objects.create(code="FSC", name="Faculty of Science")
        self.department = Department.objects.create(
            faculty=self.faculty, code="FSC-CS", name="Computer Science"
        )
        self.programme = Programme.objects.create(
            department=self.department, code="FSC-CS-P01", name="Computer Science"
        )
        self.session = AcademicSession.objects.create(name="2026/2027", is_current=True)
        Semester.objects.create(session=self.session, name=Semester.FIRST)
        Semester.objects.create(session=self.session, name=Semester.SECOND)

    def upload(self, content=None):
        return SimpleUploadedFile(
            "courses.csv",
            (content or self.CSV_CONTENT).encode("utf-8"),
            content_type="text/csv",
        )

    def test_non_admin_cannot_access_course_csv_import(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("course_csv_import"))
        self.assertEqual(response.status_code, 403)

    def test_preview_does_not_write_until_confirmed(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import preview")
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(CourseOffering.objects.count(), 0)

    def test_confirm_creates_courses_and_offerings(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload()},
        )
        response = self.client.post(reverse("course_csv_import"), {"action": "import"})
        self.assertRedirects(response, reverse("course_management"))
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(CourseOffering.objects.count(), 2)
        self.assertFalse(CourseOffering.objects.filter(registration_open=True).exists())

    def test_reimport_is_idempotent(self):
        self.client.force_login(self.admin)
        for _ in range(2):
            self.client.post(
                reverse("course_csv_import"),
                {"action": "preview", "csv_file": self.upload()},
            )
            self.client.post(reverse("course_csv_import"), {"action": "import"})
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(CourseOffering.objects.count(), 2)

    def test_same_course_can_have_different_units_in_different_programmes(self):
        biology_department = Department.objects.create(
            faculty=self.faculty, code="FSC-AB", name="Applied Biology"
        )
        biology_programme = Programme.objects.create(
            department=biology_department,
            code="FSC-AB-P01",
            name="Applied Biology",
        )
        content = (
            "faculty_code,department_code,course_code,course_title,credit_units,stress_code,"
            "programme_code,academic_session,semester,level,offering_active,registration_open,max_students,source_url,source_note\n"
            "FSC,FSC-AB,BIO 101,General Biology I,2,R,FSC-CS-P01,CURRENT,FIRST,100,true,false,,https://ebsu.edu.ng/department-of-applied-biology/,Source for the CS programme listing.\n"
            "FSC,FSC-AB,BIO 101,General Biology I,3,R,FSC-AB-P01,CURRENT,FIRST,100,true,false,,https://ebsu.edu.ng/department-of-applied-biology/,Official Applied Biology curriculum.\n"
        )
        self.client.force_login(self.admin)
        preview = self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "Import preview")
        self.client.post(reverse("course_csv_import"), {"action": "import"})

        course = Course.objects.get(department=biology_department, code="BIO 101")
        self.assertEqual(Course.objects.filter(department=biology_department, code="BIO 101").count(), 1)
        computer_science_offering = CourseOffering.objects.get(
            course=course, programme=self.programme
        )
        biology_offering = CourseOffering.objects.get(
            course=course, programme=biology_programme
        )
        self.assertEqual(computer_science_offering.credit_units, 2)
        self.assertEqual(biology_offering.credit_units, 3)
        self.assertEqual(computer_science_offering.stress_code, "R")
        self.assertEqual(biology_offering.stress_code, "R")
        self.assertEqual(
            biology_offering.source_url,
            "https://ebsu.edu.ng/department-of-applied-biology/",
        )
        self.assertIn("Official Applied Biology curriculum", biology_offering.source_note)

    def test_course_units_above_six_are_supported_for_siwes(self):
        self.client.force_login(self.admin)
        content = (
            "faculty_code,department_code,course_code,course_title,credit_units,stress_code,"
            "programme_code,academic_session,semester,level,offering_active,registration_open,max_students\n"
            "FSC,FSC-CS,CSC 398,Students Industrial Work Experience Scheme,18,AR,"
            "FSC-CS-P01,CURRENT,SECOND,300,true,false,\n"
        )
        response = self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        self.assertEqual(response.status_code, 200)
        self.client.post(reverse("course_csv_import"), {"action": "import"})
        self.assertEqual(Course.objects.get(code="CSC 398").credit_units, 18)
        self.assertEqual(CourseOffering.objects.get(course__code="CSC 398").credit_units, 18)

    def test_missing_current_session_is_reported(self):
        self.session.is_current = False
        self.session.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload()},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "no active current academic session", status_code=400)
        self.assertEqual(Course.objects.count(), 0)

    def test_registration_open_true_is_rejected_from_csv(self):
        self.client.force_login(self.admin)
        content = self.CSV_CONTENT.replace("true,false,", "true,true,")
        response = self.client.post(
            reverse("course_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "registration_open must be false", status_code=400)
        self.assertEqual(Course.objects.count(), 0)


class AcademicSessionCSVImportTests(TestCase):
    CSV_CONTENT = (
        "academic_session,session_start_date,session_end_date,semester,"
        "semester_start_date,semester_end_date,source_url,source_note\n"
        "2026/2027,,,FIRST,,,https://ebsu.edu.ng/2026-2027-post-utme-application-screening/,Candidate session reference; dates not confirmed.\n"
        "2026/2027,,,SECOND,,,https://ebsu.edu.ng/2026-2027-post-utme-application-screening/,Candidate session reference; dates not confirmed.\n"
    )

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="sessioncsvadmin",
            email="sessioncsvadmin@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = User.objects.create_user(
            username="sessioncsvstudent",
            email="sessioncsvstudent@example.test",
            password="StrongTestPassword!2026",
        )

    def upload(self, content=None):
        return SimpleUploadedFile(
            "academic_sessions.csv",
            (content or self.CSV_CONTENT).encode("utf-8"),
            content_type="text/csv",
        )

    def test_non_admin_cannot_access_session_import(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("academic_session_csv_import"))
        self.assertEqual(response.status_code, 403)

    def test_preview_does_not_write_records(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("academic_session_csv_import"),
            {"action": "preview", "csv_file": self.upload()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import preview")
        self.assertEqual(AcademicSession.objects.count(), 0)
        self.assertEqual(Semester.objects.count(), 0)

    def test_import_creates_session_and_first_two_semesters(self):
        self.client.force_login(self.admin)
        content = (
            "academic_session,session_start_date,session_end_date,semester,semester_start_date,semester_end_date\n"
            "2026/2027,,,FIRST,,\n"
            "2026/2027,,,SECOND,,\n"
        )
        self.client.post(
            reverse("academic_session_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        response = self.client.post(
            reverse("academic_session_csv_import"), {"action": "import"}
        )
        self.assertRedirects(response, reverse("academic_list", kwargs={"kind": "sessions"}))
        self.assertEqual(AcademicSession.objects.count(), 1)
        self.assertEqual(Semester.objects.count(), 2)
        self.assertFalse(AcademicSession.objects.get().is_current)
        self.assertFalse(Semester.objects.filter(is_current=True).exists())

    def test_reimport_is_idempotent(self):
        self.client.force_login(self.admin)
        content = (
            "academic_session,session_start_date,session_end_date,semester,semester_start_date,semester_end_date\n"
            "2026/2027,,,FIRST,,\n"
            "2026/2027,,,SECOND,,\n"
        )
        for _ in range(2):
            self.client.post(
                reverse("academic_session_csv_import"),
                {"action": "preview", "csv_file": self.upload(content)},
            )
            self.client.post(
                reverse("academic_session_csv_import"), {"action": "import"}
            )
        self.assertEqual(AcademicSession.objects.count(), 1)
        self.assertEqual(Semester.objects.count(), 2)

    def test_invalid_session_year_range_is_rejected(self):
        self.client.force_login(self.admin)
        content = (
            "academic_session,session_start_date,session_end_date,semester,semester_start_date,semester_end_date\n"
            "2026/2028,,,FIRST,,\n"
        )
        response = self.client.post(
            reverse("academic_session_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "ending year must be one year after", status_code=400)
        self.assertEqual(AcademicSession.objects.count(), 0)

    def test_conflicting_existing_dates_are_not_overwritten(self):
        self.client.force_login(self.admin)
        session = AcademicSession.objects.create(
            name="2026/2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 7, 31),
        )
        content = (
            "academic_session,session_start_date,session_end_date,semester,semester_start_date,semester_end_date\n"
            "2026/2027,2026-10-01,2027-07-31,FIRST,,\n"
        )
        response = self.client.post(
            reverse("academic_session_csv_import"),
            {"action": "preview", "csv_file": self.upload(content)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "conflicts with the existing record", status_code=400)
        session.refresh_from_db()
        self.assertEqual(session.start_date, date(2026, 9, 1))
