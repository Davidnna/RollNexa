from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from biometrics.models import FaceEnrollment
from biometrics.services import (
    BiometricServiceError,
    biometric_encryption_key_status,
    decrypt_template,
)


class Command(BaseCommand):
    help = (
        "Verify that the configured biometric encryption key can decrypt every "
        "stored facial template without displaying template data."
    )

    def handle(self, *args, **options):
        if biometric_encryption_key_status() != "valid":
            raise CommandError(
                "The configured biometric encryption key is missing or invalid. "
                "No stored templates were checked."
            )

        expected_key_version = getattr(
            settings,
            "BIOMETRIC_ENCRYPTION_KEY_VERSION",
            "v1",
        )
        checked = 0
        failed = 0
        version_mismatches = 0

        templates = FaceEnrollment.objects.only(
            "encrypted_template",
            "encryption_key_version",
        ).iterator(chunk_size=100)

        for enrollment in templates:
            checked += 1
            if enrollment.encryption_key_version != expected_key_version:
                version_mismatches += 1
                continue

            try:
                embedding = decrypt_template(enrollment.encrypted_template)
                del embedding
            except BiometricServiceError:
                failed += 1

        if failed or version_mismatches:
            raise CommandError(
                "Biometric restore verification failed: "
                f"{failed} template(s) could not be decrypted and "
                f"{version_mismatches} template(s) use a different key version. "
                "No biometric feature data was displayed."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Biometric restore verification passed: "
                f"{checked} stored template(s) decrypted successfully. "
                "No biometric feature data was displayed."
            )
        )
