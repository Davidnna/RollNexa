from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from academics.models import (
    AcademicSession,
    Course,
    CourseLecturerAssignment,
    CourseOffering,
    CourseRegistration,
    Department,
    Faculty,
    Programme,
    Semester,
)

from .forms import AttendanceSessionForm
from .models import AttendanceRecord, AttendanceSession
from .services import (
    activate_attendance_session,
    cancel_attendance_session,
    close_attendance_session,
    create_attendance_session,
    record_verified_attendance,
)

User = get_user_model()


class AttendanceManagementTests(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)
        self.admin = User.objects.create_superuser(
            username="attendance_admin",
            email="attendance_admin@example.test",
            password="StrongTestPassword!2026",
        )
        faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        department = Department.objects.create(
            faculty=faculty, code="CSC", name="Computer Science"
        )
        self.programme = Programme.objects.create(
            department=department, code="BSC-CS", name="Computer Science"
        )
        academic_session = AcademicSession.objects.create(
            name="2025/2026", is_current=True
        )
        semester = Semester.objects.create(
            session=academic_session, name=Semester.FIRST, is_current=True
        )
        course = Course.objects.create(
            department=department,
            code="CSC301",
            title="Data Structures",
            credit_units=3,
        )
        self.offering = CourseOffering.objects.create(
            course=course,
            programme=self.programme,
            semester=semester,
            level="300",
            registration_open=True,
        )

        self.lecturer_user = User.objects.create_user(
            username="attendance_lecturer",
            email="attendance_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        self.lecturer = self.lecturer_user.profile
        self.lecturer.role = UserProfile.ROLE_LECTURER
        self.lecturer.department = department
        self.lecturer.save()
        self.assignment = CourseLecturerAssignment.objects.create(
            offering=self.offering,
            lecturer=self.lecturer,
            assigned_by=self.admin,
        )

        self.student_user = User.objects.create_user(
            username="attendance_student",
            email="attendance_student@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = self.student_user.profile
        self.student.programme = self.programme
        self.student.current_level = "300"
        self.student.save()
        CourseRegistration.objects.create(
            offering=self.offering,
            student=self.student,
            status=CourseRegistration.STATUS_REGISTERED,
        )

    def create_session(self, starts_at=None, ends_at=None, title="Lecture 1"):
        return create_attendance_session(
            offering_id=self.offering.pk,
            created_by=self.lecturer_user,
            title=title,
            starts_at=starts_at or self.now - timedelta(minutes=10),
            ends_at=ends_at or self.now + timedelta(minutes=50),
        )

    def test_lecturer_can_open_attendance_session_list(self):
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("lecturer_attendance_sessions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance sessions")

    def test_student_cannot_open_attendance_session_management(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("lecturer_attendance_sessions"))
        self.assertEqual(response.status_code, 403)

    def test_lecturer_can_schedule_session_for_assigned_offering(self):
        self.client.force_login(self.lecturer_user)
        response = self.client.post(reverse("attendance_session_create"), {
            "offering": str(self.offering.pk),
            "title": "Monday lecture",
            "starts_at": timezone.localtime(self.now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M"),
            "ends_at": timezone.localtime(self.now + timedelta(minutes=55)).strftime("%Y-%m-%dT%H:%M"),
            "notes": "Week 1 lecture",
        })
        self.assertEqual(response.status_code, 302)
        session = AttendanceSession.objects.get(title="Monday lecture")
        self.assertEqual(session.created_by, self.lecturer_user)
        self.assertEqual(session.status, AttendanceSession.STATUS_SCHEDULED)

    def test_lecturer_can_open_a_session_detail_page(self):
        session = self.create_session()
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("attendance_session_detail", kwargs={"pk": session.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SESSION DETAILS")
        self.assertContains(response, self.student_user.username)

    def test_different_lecturer_cannot_open_an_unassigned_session(self):
        session = self.create_session()
        other_user = User.objects.create_user(
            username="other_lecturer",
            email="other_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        other_user.profile.role = UserProfile.ROLE_LECTURER
        other_user.profile.save()
        self.client.force_login(other_user)
        response = self.client.get(reverse("attendance_session_detail", kwargs={"pk": session.pk}))
        self.assertEqual(response.status_code, 404)

    def test_form_excludes_offerings_not_assigned_to_lecturer(self):
        unassigned_user = User.objects.create_user(
            username="unassigned_lecturer",
            email="unassigned_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        unassigned_profile = unassigned_user.profile
        unassigned_profile.role = UserProfile.ROLE_LECTURER
        unassigned_profile.save()
        form = AttendanceSessionForm(
            lecturer_profile=unassigned_profile,
            created_by=unassigned_user,
        )
        self.assertFalse(form.fields["offering"].queryset.filter(pk=self.offering.pk).exists())

    def test_overlapping_sessions_for_same_offering_are_rejected(self):
        self.create_session()
        with self.assertRaises(ValidationError):
            self.create_session(
                starts_at=self.now,
                ends_at=self.now + timedelta(minutes=60),
                title="Overlapping session",
            )

    def test_cancelled_session_does_not_block_a_replacement_session(self):
        first = self.create_session()
        cancelled = cancel_attendance_session(
            session_id=first.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        self.assertEqual(cancelled.cancelled_by, self.lecturer_user)
        replacement = self.create_session(title="Replacement")
        self.assertEqual(replacement.status, AttendanceSession.STATUS_SCHEDULED)

    def test_lecturer_can_activate_session_within_its_time_window(self):
        session = self.create_session()
        activated = activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        self.assertEqual(activated.status, AttendanceSession.STATUS_ACTIVE)
        self.assertEqual(activated.activated_at, self.now)
        self.assertEqual(activated.activated_by, self.lecturer_user)

    def test_session_cannot_be_activated_before_its_start_time(self):
        session = self.create_session(
            starts_at=self.now + timedelta(minutes=10),
            ends_at=self.now + timedelta(minutes=60),
        )
        with self.assertRaises(ValidationError):
            activate_attendance_session(
                session_id=session.pk,
                lecturer_profile=self.lecturer,
                at=self.now,
            )

    def test_session_cannot_be_activated_after_its_end_time(self):
        session = self.create_session(
            starts_at=self.now - timedelta(minutes=60),
            ends_at=self.now - timedelta(minutes=1),
        )
        with self.assertRaises(ValidationError):
            activate_attendance_session(
                session_id=session.pk,
                lecturer_profile=self.lecturer,
                at=self.now,
            )

    def test_lecturer_can_close_an_active_session(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        closed = close_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now + timedelta(minutes=5),
        )
        self.assertEqual(closed.status, AttendanceSession.STATUS_CLOSED)
        self.assertEqual(closed.closed_at, self.now + timedelta(minutes=5))
        self.assertEqual(closed.closed_by, self.lecturer_user)

    def test_session_cannot_be_closed_before_its_activation_time(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            close_attendance_session(
                session_id=session.pk,
                lecturer_profile=self.lecturer,
                at=self.now - timedelta(seconds=1),
            )

    def test_only_scheduled_sessions_can_be_cancelled(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            cancel_attendance_session(
                session_id=session.pk,
                lecturer_profile=self.lecturer,
                at=self.now + timedelta(minutes=1),
            )

    def test_lecturer_cannot_manage_session_after_assignment_is_revoked(self):
        session = self.create_session()
        self.assignment.is_active = False
        self.assignment.removed_at = self.now
        self.assignment.removed_by = self.admin
        self.assignment.save(update_fields=["is_active", "removed_at", "removed_by"])
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("attendance_session_detail", kwargs={"pk": session.pk}))
        self.assertEqual(response.status_code, 404)

    def test_both_verification_timestamps_are_required_to_record_attendance(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=self.student,
                qr_verified_at=self.now,
                face_verified_at=None,
                qr_verified=True,
                face_verified=True,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_attendance_is_rejected_when_either_verifier_fails(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=self.student,
                qr_verified_at=self.now - timedelta(seconds=3),
                face_verified_at=self.now - timedelta(seconds=1),
                qr_verified=True,
                face_verified=False,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_facial_verification_must_follow_qr_verification(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=self.student,
                qr_verified_at=self.now - timedelta(seconds=1),
                face_verified_at=self.now - timedelta(seconds=3),
                qr_verified=True,
                face_verified=True,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_attendance_is_recorded_after_both_checks_succeed(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        record = record_verified_attendance(
            session_id=session.pk,
            student_profile=self.student,
            qr_verified_at=self.now - timedelta(seconds=3),
            face_verified_at=self.now - timedelta(seconds=1),
            qr_verified=True,
            face_verified=True,
            recorded_at=self.now,
        )
        self.assertEqual(record.session, session)
        self.assertEqual(record.student, self.student)
        self.assertEqual(AttendanceRecord.objects.count(), 1)

    def test_duplicate_attendance_for_same_student_and_session_is_rejected(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        kwargs = {
            "session_id": session.pk,
            "student_profile": self.student,
            "qr_verified_at": self.now - timedelta(seconds=3),
            "face_verified_at": self.now - timedelta(seconds=1),
            "qr_verified": True,
            "face_verified": True,
            "recorded_at": self.now,
        }
        record_verified_attendance(**kwargs)
        with self.assertRaises(ValidationError):
            record_verified_attendance(**kwargs)
        self.assertEqual(AttendanceRecord.objects.count(), 1)

    def test_attendance_cannot_be_recorded_when_all_lecturer_assignments_are_revoked(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        self.assignment.is_active = False
        self.assignment.removed_at = self.now
        self.assignment.removed_by = self.admin
        self.assignment.save(update_fields=["is_active", "removed_at", "removed_by"])
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=self.student,
                qr_verified_at=self.now - timedelta(seconds=3),
                face_verified_at=self.now - timedelta(seconds=1),
                qr_verified=True,
                face_verified=True,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_student_profile_must_still_match_the_registered_offering(self):
        other_programme = Programme.objects.create(
            department=self.programme.department,
            code="BSC-IT",
            name="Information Technology",
        )
        self.student.programme = other_programme
        self.student.save(update_fields=["programme"])
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=self.student,
                qr_verified_at=self.now - timedelta(seconds=3),
                face_verified_at=self.now - timedelta(seconds=1),
                qr_verified=True,
                face_verified=True,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_unregistered_student_cannot_be_marked_present(self):
        other_user = User.objects.create_user(
            username="unregistered_student",
            email="unregistered_student@example.test",
            password="StrongTestPassword!2026",
        )
        other_student = other_user.profile
        other_student.programme = self.programme
        other_student.current_level = "300"
        other_student.save()
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        with self.assertRaises(ValidationError):
            record_verified_attendance(
                session_id=session.pk,
                student_profile=other_student,
                qr_verified_at=self.now - timedelta(seconds=3),
                face_verified_at=self.now - timedelta(seconds=1),
                qr_verified=True,
                face_verified=True,
                recorded_at=self.now,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)
