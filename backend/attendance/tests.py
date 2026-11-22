import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
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
from .models import AttendanceRecord, AttendanceSession, AttendanceVerification
from core.models import AuditEvent
from .services import (
    activate_attendance_session,
    complete_attendance_verification,
    cancel_attendance_session,
    close_attendance_session,
    create_attendance_session,
    issue_attendance_qr_token,
    record_verified_attendance,
    record_manual_attendance_exception,
    verify_attendance_qr,
)

User = get_user_model()


class AttendanceManagementTests(TestCase):
    def test_manual_attendance_reason_choices_match_database_constraint(self):
        constraint = next(
            item
            for item in AttendanceRecord._meta.constraints
            if item.name == "att_record_method_valid"
        )
        manual_branch = constraint.condition.children[1]
        constraint_values = dict(manual_branch.children)["manual_reason__in"]
        choice_values = {
            value for value, _label in AttendanceRecord.MANUAL_REASON_CHOICES
        }

        self.assertEqual(set(constraint_values), choice_values)

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

    def test_qr_only_verification_cannot_record_attendance(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        with self.assertRaises(ValidationError):
            record_verified_attendance(verification_id=verification.pk)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_failed_face_verification_cannot_record_attendance(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        verification.status = AttendanceVerification.STATUS_FAILED
        verification.save(update_fields=["status", "updated_at"])
        with self.assertRaises(ValidationError):
            record_verified_attendance(verification_id=verification.pk)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_facial_verification_must_follow_qr_verification(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        with self.assertRaises(ValidationError):
            complete_attendance_verification(
                verification_id=verification.pk,
                verified_at=verification.qr_verified_at - timedelta(seconds=1),
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_attendance_is_recorded_after_both_checks_succeed(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        record = complete_attendance_verification(verification_id=verification.pk)
        verification.refresh_from_db()
        self.assertEqual(record.session, session)
        self.assertEqual(record.student, self.student)
        self.assertEqual(verification.status, AttendanceVerification.STATUS_COMPLETED)
        self.assertEqual(AttendanceRecord.objects.count(), 1)

    def test_duplicate_attendance_for_same_student_and_session_is_rejected(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        complete_attendance_verification(verification_id=verification.pk)
        with self.assertRaises(ValidationError):
            record_verified_attendance(verification_id=verification.pk)
        self.assertEqual(AttendanceRecord.objects.filter(session=session, student=self.student).count(), 1)

    def test_attendance_cannot_be_recorded_when_all_lecturer_assignments_are_revoked(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        self.assignment.is_active = False
        self.assignment.removed_at = timezone.now()
        self.assignment.removed_by = self.admin
        self.assignment.save(update_fields=["is_active", "removed_at", "removed_by"])
        with self.assertRaises(ValidationError):
            complete_attendance_verification(verification_id=verification.pk)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_student_profile_must_still_match_the_registered_offering(self):
        session = self._active_session()
        verification = self._pending_verification(session)
        other_programme = Programme.objects.create(
            department=self.programme.department,
            code="BSC-IT",
            name="Information Technology",
        )
        self.student.programme = other_programme
        self.student.save(update_fields=["programme"])
        with self.assertRaises(ValidationError):
            complete_attendance_verification(verification_id=verification.pk)
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
        session = self._active_session()
        qr_verified_at = timezone.now()
        verification = AttendanceVerification.objects.create(
            session=session,
            student=other_student,
            qr_token_fingerprint="f" * 64,
            qr_verified_at=qr_verified_at,
            expires_at=session.ends_at,
            status=AttendanceVerification.STATUS_QR_VERIFIED,
        )
        with self.assertRaises(ValidationError):
            complete_attendance_verification(verification_id=verification.pk)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def _active_session(self):
        session = self.create_session()
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        return session

    def _issued_qr(self, session):
        return issue_attendance_qr_token(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
        )

    def _pending_verification(self, session, student=None):
        issued = self._issued_qr(session)
        verification, _ = verify_attendance_qr(
            token=issued["token"],
            student_profile=student or self.student,
        )
        return verification

    def test_assigned_lecturer_can_issue_short_lived_qr_token(self):
        session = self._active_session()
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("api_attendance_qr", kwargs={"session_id": session.pk}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["token"])
        self.assertGreater(payload["ttlSeconds"], 0)
        self.assertEqual(payload["session"]["id"], session.pk)

    def test_scheduled_session_cannot_issue_qr_token(self):
        session = self.create_session()
        self.client.force_login(self.lecturer_user)
        response = self.client.get(reverse("api_attendance_qr", kwargs={"session_id": session.pk}))
        self.assertEqual(response.status_code, 400)

    def test_student_cannot_issue_lecturer_qr_token(self):
        session = self._active_session()
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("api_attendance_qr", kwargs={"session_id": session.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unassigned_lecturer_cannot_issue_qr_token(self):
        session = self._active_session()
        other_user = User.objects.create_user(
            username="unassigned_qr_lecturer",
            email="unassigned_qr_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        other_user.profile.role = UserProfile.ROLE_LECTURER
        other_user.profile.save()
        self.client.force_login(other_user)
        response = self.client.get(reverse("api_attendance_qr", kwargs={"session_id": session.pk}))
        self.assertEqual(response.status_code, 404)

    def test_valid_qr_scan_creates_pending_verification_not_attendance(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        verification = AttendanceVerification.objects.get(pk=response.json()["verificationId"])
        self.assertEqual(verification.session, session)
        self.assertEqual(verification.student, self.student)
        self.assertEqual(verification.status, AttendanceVerification.STATUS_QR_VERIFIED)
        self.assertEqual(len(verification.qr_token_fingerprint), 64)
        self.assertNotEqual(verification.qr_token_fingerprint, issued["token"])
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_repeated_qr_scan_reuses_active_pending_verification(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.client.force_login(self.student_user)
        url = reverse("api_attendance_verify_qr")
        body = json.dumps({"token": issued["token"]})
        first = self.client.post(url, data=body, content_type="application/json")
        second = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["verificationId"], second.json()["verificationId"])
        self.assertEqual(AttendanceVerification.objects.filter(
            session=session,
            student=self.student,
            status=AttendanceVerification.STATUS_QR_VERIFIED,
        ).count(), 1)

    def test_unregistered_student_cannot_verify_qr_code(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        other_user = User.objects.create_user(
            username="unregistered_qr_student",
            email="unregistered_qr_student@example.test",
            password="StrongTestPassword!2026",
        )
        other_student = other_user.profile
        other_student.programme = self.programme
        other_student.current_level = "300"
        other_student.save()
        self.client.force_login(other_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceVerification.objects.count(), 0)

    def test_lecturer_cannot_submit_student_qr_verification(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.client.force_login(self.lecturer_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_tampered_qr_token_is_rejected(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"] + "tampered"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceVerification.objects.count(), 0)

    def test_qr_token_is_rejected_after_session_is_closed(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        close_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=timezone.now(),
        )
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceVerification.objects.count(), 0)

    def test_revoked_issuer_assignment_invalidates_qr_token(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.assignment.is_active = False
        self.assignment.removed_at = timezone.now()
        self.assignment.removed_by = self.admin
        self.assignment.save(update_fields=["is_active", "removed_at", "removed_by"])
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("api_attendance_verify_qr"),
            data=json.dumps({"token": issued["token"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceVerification.objects.count(), 0)

    def test_expired_pending_verification_can_be_replaced_by_new_scan(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        first, reused = verify_attendance_qr(token=issued["token"], student_profile=self.student)
        self.assertFalse(reused)
        expired_at = first.qr_verified_at + timedelta(seconds=1)
        first.expires_at = expired_at
        first.save(update_fields=["expires_at", "updated_at"])
        second, reused = verify_attendance_qr(
            token=issued["token"],
            student_profile=self.student,
            at=expired_at + timedelta(seconds=1),
        )
        self.assertFalse(reused)
        self.assertNotEqual(first.pk, second.pk)
        first.refresh_from_db()
        self.assertEqual(first.status, AttendanceVerification.STATUS_EXPIRED)

    def test_closing_session_expires_pending_qr_verifications(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        verification, _ = verify_attendance_qr(token=issued["token"], student_profile=self.student)
        close_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=timezone.now(),
        )
        verification.refresh_from_db()
        self.assertEqual(verification.status, AttendanceVerification.STATUS_EXPIRED)

    def test_student_can_only_read_their_own_verification_status(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        verification, _ = verify_attendance_qr(token=issued["token"], student_profile=self.student)
        other_user = User.objects.create_user(
            username="other_qr_student",
            email="other_qr_student@example.test",
            password="StrongTestPassword!2026",
        )
        other_user.profile.programme = self.programme
        other_user.profile.current_level = "300"
        other_user.profile.save()
        self.client.force_login(other_user)
        response = self.client.get(reverse(
            "api_attendance_verification_status",
            kwargs={"verification_id": verification.pk},
        ))
        self.assertEqual(response.status_code, 404)

    def test_attendance_verification_expires_no_later_than_session_end(self):
        session = self.create_session(
            starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(seconds=30),
        )
        activate_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=timezone.now(),
        )
        issued = self._issued_qr(session)
        verification, _ = verify_attendance_qr(token=issued["token"], student_profile=self.student)
        self.assertLessEqual(verification.expires_at, session.ends_at)


    def test_signed_qr_token_expires_after_its_validity_window(self):
        session = self._active_session()
        issued = self._issued_qr(session)
        self.client.force_login(self.student_user)
        with patch(
            "attendance.services.signing.loads",
            side_effect=signing.SignatureExpired("expired"),
        ):
            response = self.client.post(
                reverse("api_attendance_verify_qr"),
                data=json.dumps({"token": issued["token"]}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceVerification.objects.count(), 0)


    def test_lecturer_can_record_manual_attendance_exception_for_registered_student(self):
        session = self._active_session()
        record = record_manual_attendance_exception(
            session_id=session.pk,
            student_id=self.student.pk,
            lecturer_profile=self.lecturer,
            reason=AttendanceRecord.MANUAL_REASON_CONSENT_WITHDRAWN,
        )
        self.assertEqual(record.recording_method, AttendanceRecord.METHOD_MANUAL_EXCEPTION)
        self.assertIsNone(record.qr_verified_at)
        self.assertIsNone(record.face_verified_at)
        self.assertEqual(record.recorded_by, self.lecturer_user)
        self.assertEqual(AttendanceRecord.objects.filter(session=session, student=self.student).count(), 1)
        self.assertTrue(AuditEvent.objects.filter(
            event_type="attendance.recorded_manual_exception",
            object_type="attendance_record",
            object_id=str(record.pk),
        ).exists())

    def test_manual_attendance_exception_requires_assigned_lecturer(self):
        session = self._active_session()
        other_user = User.objects.create_user(
            username="manual_other_lecturer",
            email="manual_other_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        other_user.profile.role = UserProfile.ROLE_LECTURER
        other_user.profile.save(update_fields=["role", "updated_at"])
        with self.assertRaises(ValidationError):
            record_manual_attendance_exception(
                session_id=session.pk,
                student_id=self.student.pk,
                lecturer_profile=other_user.profile,
                reason=AttendanceRecord.MANUAL_REASON_CAMERA_UNAVAILABLE,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_manual_attendance_other_reason_requires_notes(self):
        session = self._active_session()
        with self.assertRaises(ValidationError):
            record_manual_attendance_exception(
                session_id=session.pk,
                student_id=self.student.pk,
                lecturer_profile=self.lecturer,
                reason=AttendanceRecord.MANUAL_REASON_OTHER,
            )
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_manual_attendance_exception_cannot_be_recorded_after_session_closes(self):
        session = self._active_session()
        close_attendance_session(
            session_id=session.pk,
            lecturer_profile=self.lecturer,
            at=self.now + timedelta(minutes=1),
        )
        with self.assertRaises(ValidationError):
            record_manual_attendance_exception(
                session_id=session.pk,
                student_id=self.student.pk,
                lecturer_profile=self.lecturer,
                reason=AttendanceRecord.MANUAL_REASON_TECHNICAL_ISSUE,
                recorded_at=self.now + timedelta(minutes=2),
            )

    def test_manual_attendance_api_is_lecturer_scoped_and_returns_audit_records(self):
        session = self._active_session()
        self.client.force_login(self.lecturer_user)
        create_response = self.client.post(
            reverse("api_attendance_manual_records", kwargs={"session_id": session.pk}),
            data=json.dumps({
                "studentId": self.student.pk,
                "reason": AttendanceRecord.MANUAL_REASON_CAMERA_UNAVAILABLE,
                "notes": "Student camera permission was unavailable.",
            }),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        list_response = self.client.get(
            reverse("api_attendance_manual_records", kwargs={"session_id": session.pk})
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["alreadyRecordedStudentIds"], [self.student.pk])
        self.assertEqual(len(list_response.json()["manualRecords"]), 1)

    def test_student_cannot_create_manual_attendance_exception(self):
        session = self._active_session()
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("api_attendance_manual_records", kwargs={"session_id": session.pk}),
            data=json.dumps({"studentId": self.student.pk, "reason": "camera_unavailable"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AttendanceRecord.objects.count(), 0)
