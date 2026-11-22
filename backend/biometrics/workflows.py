from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from attendance.models import AttendanceVerification
from core.audit import record_audit_event

from .models import BiometricConsent, BiometricConsentEvent, FaceEnrollment
from .services import MODEL_VERSION, build_enrollment_template, encrypt_template


@transaction.atomic
def update_biometric_consent(*, student, action, policy_version):
    expected_version = getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.1")
    if action not in {BiometricConsentEvent.ACTION_GRANTED, BiometricConsentEvent.ACTION_WITHDRAWN}:
        raise ValidationError("Choose whether to grant or withdraw biometric consent.")
    if action == BiometricConsentEvent.ACTION_GRANTED and policy_version != expected_version:
        raise ValidationError("The biometric consent notice has changed. Review the current notice before continuing.")

    student = UserProfile.objects.select_for_update().get(pk=student.pk)
    consent = BiometricConsent.objects.select_for_update().filter(student=student).first()
    if consent and consent.status == action and (
        action == BiometricConsentEvent.ACTION_WITHDRAWN or consent.policy_version == expected_version
    ):
        return consent
    moment = timezone.now()
    if consent is None:
        consent = BiometricConsent(student=student, policy_version=expected_version)

    event_policy_version = expected_version
    if action == BiometricConsentEvent.ACTION_GRANTED:
        consent.policy_version = expected_version
        consent.status = BiometricConsent.STATUS_GRANTED
        consent.granted_at = moment
        consent.withdrawn_at = None
    else:
        event_policy_version = consent.policy_version
        consent.status = BiometricConsent.STATUS_WITHDRAWN
        consent.withdrawn_at = moment
        FaceEnrollment.objects.filter(student=student).delete()
        AttendanceVerification.objects.filter(
            student=student,
            status=AttendanceVerification.STATUS_QR_VERIFIED,
        ).update(status=AttendanceVerification.STATUS_EXPIRED, updated_at=moment)

    consent.full_clean()
    consent.save()
    BiometricConsentEvent.objects.create(
        student=student,
        action=action,
        policy_version=event_policy_version,
        occurred_at=moment,
    )
    record_audit_event(
        actor=student.user,
        event_type=f"biometrics.consent_{action}",
        object_type="user_profile",
        object_id=student.pk,
        summary=(
            "A student granted biometric consent."
            if action == BiometricConsentEvent.ACTION_GRANTED
            else "A student withdrew biometric consent."
        ),
        metadata={"policy_version": event_policy_version},
    )
    return consent


@transaction.atomic
def create_or_replace_face_enrollment(*, student, frames):
    student = UserProfile.objects.select_for_update().get(pk=student.pk)
    consent = BiometricConsent.objects.select_for_update().filter(
        student=student,
        status=BiometricConsent.STATUS_GRANTED,
        policy_version=getattr(settings, "BIOMETRIC_CONSENT_POLICY_VERSION", "1.1"),
    ).first()
    if not consent:
        raise ValidationError("Grant current biometric consent before enrolling your face.")

    template = build_enrollment_template(frames)
    encrypted_template = encrypt_template(template)
    enrollment, _ = FaceEnrollment.objects.update_or_create(
        student=student,
        defaults={
            "encrypted_template": encrypted_template,
            "encryption_key_version": getattr(settings, "BIOMETRIC_ENCRYPTION_KEY_VERSION", "v1"),
            "model_version": MODEL_VERSION,
            "template_version": 1,
            "sample_count": len(frames),
            "is_active": True,
            "enrolled_at": timezone.now(),
            "last_verified_at": None,
        },
    )
    enrollment.full_clean()
    enrollment.save()
    record_audit_event(
        actor=student.user,
        event_type="biometrics.enrollment_created",
        object_type="user_profile",
        object_id=student.pk,
        summary="A student completed facial enrolment.",
        metadata={"model_version": MODEL_VERSION, "sample_count": len(frames)},
    )
    return enrollment
