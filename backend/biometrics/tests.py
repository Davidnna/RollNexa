from datetime import timedelta
from io import StringIO

import numpy as np
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

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
from attendance.models import AttendanceRecord, AttendanceVerification
from core.models import AuditEvent
from attendance.services import (
    activate_attendance_session,
    create_attendance_session,
    issue_attendance_qr_token,
    verify_attendance_qr,
)

from .models import (
    BiometricChallenge,
    BiometricConsent,
    BiometricConsentEvent,
    BiometricVerificationAttempt,
    FaceEnrollment,
)
from .services import (
    BiometricServiceError,
    biometric_encryption_key_status,
    decrypt_template,
    encrypt_template,
)
from .workflows import create_or_replace_face_enrollment, update_biometric_consent

User = get_user_model()
TEST_FERNET_KEY = Fernet.generate_key().decode("ascii")


@override_settings(
    BIOMETRIC_ENCRYPTION_KEY=TEST_FERNET_KEY,
    BIOMETRIC_ENCRYPTION_KEY_VERSION="test-v1",
    BIOMETRIC_CONSENT_POLICY_VERSION="1.0",
    BIOMETRIC_FACE_MATCH_THRESHOLD=0.363,
    BIOMETRIC_MODEL_DIR="/tmp/rollnexa-test-models",
)
class BiometricWorkflowTests(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)
        self.admin = User.objects.create_superuser(
            username="biometric_admin",
            email="biometric_admin@example.test",
            password="StrongTestPassword!2026",
        )
        faculty = Faculty.objects.create(code="ENG", name="Faculty of Engineering")
        department = Department.objects.create(faculty=faculty, code="SWE", name="Software Engineering")
        self.programme = Programme.objects.create(
            department=department,
            code="BSC-SWE",
            name="Software Engineering",
        )
        academic_session = AcademicSession.objects.create(name="2025/2026", is_current=True)
        semester = Semester.objects.create(session=academic_session, name=Semester.FIRST, is_current=True)
        course = Course.objects.create(
            department=department,
            code="SWE401",
            title="Software Project",
            credit_units=3,
        )
        self.offering = CourseOffering.objects.create(
            course=course,
            programme=self.programme,
            semester=semester,
            level="400",
            registration_open=True,
        )

        lecturer_user = User.objects.create_user(
            username="biometric_lecturer",
            email="biometric_lecturer@example.test",
            password="StrongTestPassword!2026",
        )
        self.lecturer = lecturer_user.profile
        self.lecturer.role = UserProfile.ROLE_LECTURER
        self.lecturer.department = department
        self.lecturer.save()
        self.assignment = CourseLecturerAssignment.objects.create(
            offering=self.offering,
            lecturer=self.lecturer,
            assigned_by=self.admin,
        )
        self.lecturer_user = lecturer_user

        student_user = User.objects.create_user(
            username="biometric_student",
            email="biometric_student@example.test",
            password="StrongTestPassword!2026",
        )
        self.student = student_user.profile
        self.student.programme = self.programme
        self.student.current_level = "400"
        self.student.save()
        self.student_user = student_user
        CourseRegistration.objects.create(
            offering=self.offering,
            student=self.student,
            status=CourseRegistration.STATUS_REGISTERED,
        )
        self.session = create_attendance_session(
            offering_id=self.offering.pk,
            created_by=self.lecturer_user,
            title="Biometric test session",
            starts_at=self.now - timedelta(minutes=5),
            ends_at=self.now + timedelta(minutes=45),
        )
        activate_attendance_session(
            session_id=self.session.pk,
            lecturer_profile=self.lecturer,
            at=self.now,
        )
        self.client = APIClient()

    def grant_consent(self):
        return update_biometric_consent(
            student=self.student,
            action=BiometricConsentEvent.ACTION_GRANTED,
            policy_version="1.0",
        )

    def create_enrollment(self):
        self.grant_consent()
        enrollment = FaceEnrollment(
            student=self.student,
            encrypted_template=b"test-encrypted-template",
            encryption_key_version="test-v1",
            model_version="test-model",
            sample_count=3,
        )
        enrollment.full_clean()
        enrollment.save()
        return enrollment

    def create_pending_verification(self):
        issued = issue_attendance_qr_token(
            session_id=self.session.pk,
            lecturer_profile=self.lecturer,
        )
        verification, _ = verify_attendance_qr(
            token=issued["token"],
            student_profile=self.student,
        )
        return verification

    def test_restore_command_verifies_encrypted_templates_without_outputting_embeddings(self):
        self.grant_consent()
        enrollment = FaceEnrollment(
            student=self.student,
            encrypted_template=encrypt_template(np.ones(128, dtype=np.float32)),
            encryption_key_version="test-v1",
            model_version="test-model",
            sample_count=3,
        )
        enrollment.full_clean()
        enrollment.save()

        output = StringIO()
        call_command("verify_biometric_restore", stdout=output)

        self.assertIn("1 stored template(s) decrypted successfully", output.getvalue())
        self.assertNotIn("embedding", output.getvalue().lower())

    def test_restore_command_rejects_a_different_encryption_key(self):
        self.grant_consent()
        enrollment = FaceEnrollment(
            student=self.student,
            encrypted_template=encrypt_template(np.ones(128, dtype=np.float32)),
            encryption_key_version="test-v1",
            model_version="test-model",
            sample_count=3,
        )
        enrollment.full_clean()
        enrollment.save()

        with override_settings(BIOMETRIC_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii")):
            with self.assertRaises(CommandError):
                call_command("verify_biometric_restore", stdout=StringIO())

    def test_restore_command_rejects_an_unavailable_key_version(self):
        self.grant_consent()
        enrollment = FaceEnrollment(
            student=self.student,
            encrypted_template=encrypt_template(np.ones(128, dtype=np.float32)),
            encryption_key_version="old-key-version",
            model_version="test-model",
            sample_count=3,
        )
        enrollment.full_clean()
        enrollment.save()

        with self.assertRaises(CommandError):
            call_command("verify_biometric_restore", stdout=StringIO())

    def test_student_can_grant_biometric_consent_and_event_is_audited(self):
        consent = self.grant_consent()
        self.assertEqual(consent.status, BiometricConsent.STATUS_GRANTED)
        self.assertEqual(consent.policy_version, "1.0")
        self.assertEqual(
            BiometricConsentEvent.objects.filter(
                student=self.student,
                action=BiometricConsentEvent.ACTION_GRANTED,
            ).count(),
            1,
        )
        self.assertTrue(AuditEvent.objects.filter(
            event_type="biometrics.consent_granted",
            object_type="user_profile",
            object_id=str(self.student.pk),
        ).exists())

    def test_consent_requires_the_current_policy_version(self):
        with self.assertRaises(ValidationError):
            update_biometric_consent(
                student=self.student,
                action=BiometricConsentEvent.ACTION_GRANTED,
                policy_version="outdated",
            )
        self.assertFalse(BiometricConsent.objects.filter(student=self.student).exists())

    def test_student_can_withdraw_consent_after_policy_version_changes(self):
        self.grant_consent()
        with override_settings(BIOMETRIC_CONSENT_POLICY_VERSION="2.0"):
            consent = update_biometric_consent(
                student=self.student,
                action=BiometricConsentEvent.ACTION_WITHDRAWN,
                policy_version="2.0",
            )
        self.assertEqual(consent.status, BiometricConsent.STATUS_WITHDRAWN)
        withdrawal_event = BiometricConsentEvent.objects.filter(
            student=self.student,
            action=BiometricConsentEvent.ACTION_WITHDRAWN,
        ).get()
        self.assertEqual(withdrawal_event.policy_version, "1.0")

    def test_withdrawing_consent_deletes_template_and_expires_pending_qr_attempt(self):
        self.create_enrollment()
        verification = self.create_pending_verification()
        consent = update_biometric_consent(
            student=self.student,
            action=BiometricConsentEvent.ACTION_WITHDRAWN,
            policy_version="1.0",
        )
        verification.refresh_from_db()
        self.assertEqual(consent.status, BiometricConsent.STATUS_WITHDRAWN)
        self.assertFalse(FaceEnrollment.objects.filter(student=self.student).exists())
        self.assertEqual(verification.status, AttendanceVerification.STATUS_EXPIRED)
        self.assertEqual(
            BiometricConsentEvent.objects.filter(student=self.student).count(),
            2,
        )

    def test_enrolment_replaces_template_only_after_current_consent(self):
        self.grant_consent()
        with patch("biometrics.workflows.build_enrollment_template", return_value=np.ones(128, dtype=np.float32)), patch(
            "biometrics.workflows.encrypt_template", return_value=b"encrypted-vector"
        ):
            enrollment = create_or_replace_face_enrollment(
                student=self.student,
                frames=[object(), object(), object()],
            )
        self.assertEqual(enrollment.encrypted_template, b"encrypted-vector")
        self.assertEqual(enrollment.encryption_key_version, "test-v1")
        self.assertEqual(enrollment.sample_count, 3)

    def test_enrolment_without_consent_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_or_replace_face_enrollment(student=self.student, frames=[])
        self.assertFalse(FaceEnrollment.objects.filter(student=self.student).exists())

    def test_student_consent_api_requires_acknowledgement(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(
            reverse("api_biometrics_consent"),
            {"action": "granted", "policyVersion": "1.0", "acknowledged": False},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BiometricConsent.objects.filter(student=self.student).exists())

    def test_student_can_read_biometric_status(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(reverse("api_biometrics_status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["consentStatus"], "not_given")
        self.assertFalse(response.data["isEnrolled"])
        self.assertEqual(response.data["encryptionStatus"], "valid")
        self.assertTrue(response.data["encryptionConfigured"])

    @override_settings(BIOMETRIC_ENCRYPTION_KEY="")
    def test_biometric_key_status_reports_missing_key(self):
        self.assertEqual(biometric_encryption_key_status(), "missing")

    @override_settings(BIOMETRIC_ENCRYPTION_KEY="not-a-fernet-key")
    def test_biometric_key_status_reports_invalid_key(self):
        self.assertEqual(biometric_encryption_key_status(), "invalid")

    @override_settings(BIOMETRIC_ENCRYPTION_KEY="")
    def test_student_status_api_reports_missing_encryption_key(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(reverse("api_biometrics_status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["encryptionStatus"], "missing")
        self.assertFalse(response.data["encryptionConfigured"])

    @override_settings(BIOMETRIC_ENCRYPTION_KEY="not-a-fernet-key")
    def test_student_status_api_reports_invalid_encryption_key_without_exposing_it(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(reverse("api_biometrics_status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["encryptionStatus"], "invalid")
        self.assertFalse(response.data["encryptionConfigured"])
        self.assertNotIn("not-a-fernet-key", str(response.data))

    @override_settings(BIOMETRIC_ENCRYPTION_KEY="not-a-fernet-key")
    def test_enrolment_api_rejects_invalid_key_before_face_processing(self):
        self.grant_consent()
        self.client.force_authenticate(user=self.student_user)
        frames = [
            SimpleUploadedFile(
                f"frame-{index}.jpg",
                b"placeholder",
                content_type="image/jpeg",
            )
            for index in range(1, 4)
        ]
        with patch("biometrics.views.create_or_replace_face_enrollment") as create_enrollment:
            response = self.client.post(
                reverse("api_biometrics_enrolment"),
                {"frames": frames},
                format="multipart",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "encryption_key_invalid")
        create_enrollment.assert_not_called()

    @override_settings(BIOMETRIC_ENCRYPTION_KEY=f"  {TEST_FERNET_KEY}\n")
    def test_biometric_key_status_accepts_surrounding_whitespace(self):
        self.assertEqual(biometric_encryption_key_status(), "valid")
        vector = np.ones(128, dtype=np.float32)
        encrypted = encrypt_template(vector)
        decrypted = decrypt_template(encrypted)
        self.assertEqual(decrypted.shape, (128,))

    def test_non_student_cannot_access_biometric_status(self):
        self.client.force_authenticate(user=self.lecturer_user)
        response = self.client.get(reverse("api_biometrics_status"))
        self.assertEqual(response.status_code, 403)

    @patch("biometrics.views.biometric_models_available", return_value=True)
    @patch(
        "biometrics.views.inspect_face_frame",
        return_value={
            "status": "face_ready",
            "ready": True,
            "faceCount": 1,
            "message": "Face detected. Hold this position.",
            "boundingBox": {"x": 0.3, "y": 0.1, "width": 0.4, "height": 0.7},
            "poseRatio": 0.5,
        },
    )
    def test_student_can_receive_live_face_preview_after_granting_consent(self, _inspect_face, _models_available):
        self.grant_consent()
        self.client.force_authenticate(user=self.student_user)
        frame = SimpleUploadedFile("preview.jpg", b"preview-frame", content_type="image/jpeg")
        response = self.client.post(
            reverse("api_biometrics_face_preview"),
            {"frame": frame},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertEqual(response.data["faceCount"], 1)
        self.assertAlmostEqual(response.data["poseRatio"], 0.5)

    @patch("biometrics.views.inspect_face_frame")
    def test_live_face_preview_requires_current_biometric_consent(self, inspect_face):
        self.client.force_authenticate(user=self.student_user)
        frame = SimpleUploadedFile("preview.jpg", b"preview-frame", content_type="image/jpeg")
        response = self.client.post(
            reverse("api_biometrics_face_preview"),
            {"frame": frame},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)
        inspect_face.assert_not_called()

    def test_non_student_cannot_use_live_face_preview(self):
        self.client.force_authenticate(user=self.lecturer_user)
        frame = SimpleUploadedFile("preview.jpg", b"preview-frame", content_type="image/jpeg")
        response = self.client.post(
            reverse("api_biometrics_face_preview"),
            {"frame": frame},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    @patch("biometrics.views.biometric_models_available", return_value=True)
    def test_student_can_request_randomised_face_challenge_after_qr_verification(self, _models_available):
        self.create_enrollment()
        verification = self.create_pending_verification()
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(
            reverse("api_biometrics_challenge", kwargs={"verification_id": verification.pk}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(response.data["direction"], {"turn_left", "turn_right"})
        self.assertTrue(BiometricChallenge.objects.filter(pk=response.data["challengeId"]).exists())

    @patch("biometrics.views.biometric_models_available", return_value=True)
    @patch("biometrics.views.verify_face_challenge", return_value={"liveness_passed": True, "model_version": "test-model"})
    def test_face_verification_api_records_attendance_only_after_server_verifier_succeeds(self, _verify_face, _models_available):
        self.create_enrollment()
        verification = self.create_pending_verification()
        self.client.force_authenticate(user=self.student_user)
        challenge_response = self.client.post(
            reverse("api_biometrics_challenge", kwargs={"verification_id": verification.pk}),
            {},
            format="json",
        )
        challenge_id = challenge_response.data["challengeId"]
        baseline = SimpleUploadedFile("baseline.jpg", b"baseline-frame", content_type="image/jpeg")
        challenged = SimpleUploadedFile("challenge.jpg", b"challenge-frame", content_type="image/jpeg")
        response = self.client.post(
            reverse("api_biometrics_verify", kwargs={"verification_id": verification.pk}),
            {
                "challengeId": challenge_id,
                "baselineFrame": baseline,
                "challengeFrame": challenged,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        record = AttendanceRecord.objects.get()
        self.assertEqual(record.recording_method, AttendanceRecord.METHOD_DUAL_VERIFIED)
        verification.refresh_from_db()
        self.assertEqual(verification.status, AttendanceVerification.STATUS_COMPLETED)
        self.assertEqual(BiometricVerificationAttempt.objects.get().result, BiometricVerificationAttempt.RESULT_PASSED)

    def test_client_cannot_complete_face_verification_with_a_success_boolean(self):
        verification = self.create_pending_verification()
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(
            reverse("api_biometrics_verify", kwargs={"verification_id": verification.pk}),
            {"faceVerified": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceRecord.objects.count(), 0)


    @patch("biometrics.views.biometric_models_available", return_value=True)
    @patch("biometrics.views.verify_face_challenge", side_effect=BiometricServiceError("liveness_failed", "Head movement was not detected."))
    def test_three_failed_liveness_challenges_close_the_verification_attempt(self, _verify_face, _models_available):
        self.create_enrollment()
        verification = self.create_pending_verification()
        self.client.force_authenticate(user=self.student_user)
        for attempt_number in range(1, 4):
            challenge_response = self.client.post(
                reverse("api_biometrics_challenge", kwargs={"verification_id": verification.pk}),
                {},
                format="json",
            )
            baseline = SimpleUploadedFile("baseline.jpg", b"baseline-frame", content_type="image/jpeg")
            challenged = SimpleUploadedFile("challenge.jpg", b"challenge-frame", content_type="image/jpeg")
            response = self.client.post(
                reverse("api_biometrics_verify", kwargs={"verification_id": verification.pk}),
                {
                    "challengeId": challenge_response.data["challengeId"],
                    "baselineFrame": baseline,
                    "challengeFrame": challenged,
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["attemptsRemaining"], max(0, 3 - attempt_number))
        verification.refresh_from_db()
        self.assertEqual(verification.status, AttendanceVerification.STATUS_FAILED)
        self.assertEqual(AttendanceRecord.objects.count(), 0)
        self.assertEqual(BiometricVerificationAttempt.objects.filter(result="failed").count(), 3)


class BiometricProcessingUnitTests(TestCase):
    def test_live_face_inspection_returns_position_and_pose_feedback(self):
        from .services import inspect_face_frame

        class FakeDetector:
            def setInputSize(self, size):
                self.input_size = size

            def detect(self, image):
                face = np.array(
                    [[230, 70, 180, 220, 285, 150, 355, 150, 320, 185, 292, 235, 348, 235, 0.96]],
                    dtype=np.float32,
                )
                return 1, face

        image = np.zeros((360, 640, 3), dtype=np.uint8)
        with patch("biometrics.services._decode_image", return_value=image), patch(
            "biometrics.services._load_models", return_value=(FakeDetector(), object())
        ):
            result = inspect_face_frame(object())

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "face_ready")
        self.assertEqual(result["faceCount"], 1)
        self.assertAlmostEqual(result["poseRatio"], 0.5)
        self.assertAlmostEqual(result["boundingBox"]["width"], 180 / 640)

    def test_live_face_inspection_returns_guidance_when_no_face_is_detected(self):
        from .services import inspect_face_frame

        class FakeDetector:
            def setInputSize(self, size):
                self.input_size = size

            def detect(self, image):
                return 1, None

        image = np.zeros((360, 640, 3), dtype=np.uint8)
        with patch("biometrics.services._decode_image", return_value=image), patch(
            "biometrics.services._load_models", return_value=(FakeDetector(), object())
        ):
            result = inspect_face_frame(object())

        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "no_face")
        self.assertEqual(result["faceCount"], 0)

    def test_enrolment_requires_neutral_left_and_right_pose_samples(self):
        from .services import FaceSample, build_enrollment_template

        vector = np.ones(128, dtype=np.float32)
        samples = [
            FaceSample(vector, 0.50),
            FaceSample(vector, 0.36),
            FaceSample(vector, 0.64),
        ]
        with patch("biometrics.services._extract_face_sample", side_effect=samples):
            template = build_enrollment_template([object(), object(), object()])
        self.assertEqual(template.shape, (128,))
        self.assertAlmostEqual(float(np.linalg.norm(template)), 1.0, places=5)

    def test_enrolment_rejects_inconsistent_face_embeddings(self):
        from .services import BiometricServiceError, FaceSample, build_enrollment_template

        first = np.zeros(128, dtype=np.float32)
        first[0] = 1.0
        second = np.zeros(128, dtype=np.float32)
        second[1] = 1.0
        samples = [FaceSample(first, 0.50), FaceSample(second, 0.36), FaceSample(first, 0.64)]
        with patch("biometrics.services._extract_face_sample", side_effect=samples):
            with self.assertRaises(BiometricServiceError) as context:
                build_enrollment_template([object(), object(), object()])
        self.assertEqual(context.exception.code, "enrollment_identity_inconsistent")

    def test_left_head_turn_challenge_requires_leftward_pose_change(self):
        from .services import FaceSample, verify_face_challenge

        vector = np.ones(128, dtype=np.float32)
        samples = [FaceSample(vector, 0.50), FaceSample(vector, 0.35)]
        with patch("biometrics.services._extract_face_sample", side_effect=samples), patch(
            "biometrics.services.decrypt_template", return_value=vector
        ):
            result = verify_face_challenge(
                baseline_frame=object(),
                challenge_frame=object(),
                encrypted_template=b"encrypted",
                direction="turn_left",
            )
        self.assertTrue(result["liveness_passed"])


    def test_jpeg_dimensions_are_checked_before_image_decode(self):
        from .services import BiometricServiceError, _decode_image

        height = 2000
        width = 2200
        jpeg_header = (
            b"\xff\xd8\xff\xc0\x00\x11\x08"
            + height.to_bytes(2, "big")
            + width.to_bytes(2, "big")
            + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        )
        upload = SimpleUploadedFile("large.jpg", jpeg_header, content_type="image/jpeg")
        with patch("biometrics.services.cv2.imdecode", side_effect=AssertionError("decode must not run")):
            with self.assertRaises(BiometricServiceError) as context:
                _decode_image(upload)
        self.assertEqual(context.exception.code, "image_resolution_high")

    def test_non_jpeg_camera_payload_is_rejected(self):
        from .services import BiometricServiceError, _decode_image

        upload = SimpleUploadedFile("image.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        with self.assertRaises(BiometricServiceError) as context:
            _decode_image(upload)
        self.assertEqual(context.exception.code, "image_invalid")

    @override_settings(BIOMETRIC_FACE_DETECTION_THRESHOLD=1.5)
    def test_invalid_detection_threshold_fails_closed(self):
        from .services import BiometricServiceUnavailable, _face_detection_threshold

        with self.assertRaises(BiometricServiceUnavailable) as context:
            _face_detection_threshold()
        self.assertEqual(context.exception.code, "face_detection_configuration_invalid")

    def test_wrong_head_turn_direction_fails_liveness_check(self):
        from .services import BiometricServiceError, FaceSample, verify_face_challenge

        vector = np.ones(128, dtype=np.float32)
        samples = [FaceSample(vector, 0.50), FaceSample(vector, 0.65)]
        with patch("biometrics.services._extract_face_sample", side_effect=samples), patch(
            "biometrics.services.decrypt_template", return_value=vector
        ):
            with self.assertRaises(BiometricServiceError) as context:
                verify_face_challenge(
                    baseline_frame=object(),
                    challenge_frame=object(),
                    encrypted_template=b"encrypted",
                    direction="turn_left",
                )
        self.assertEqual(context.exception.code, "liveness_failed")
