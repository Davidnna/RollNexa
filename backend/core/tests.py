from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from .audit import record_audit_event
from .middleware import BiometricRequestSizeLimitMiddleware, RollNexaSecurityHeadersMiddleware
from .models import AuditEvent

User = get_user_model()


class AuditEventTests(TestCase):
    def test_audit_event_preserves_actor_and_safe_metadata(self):
        actor = User.objects.create_user(username="audit-user", password="StrongTestPassword!2026")
        event = record_audit_event(
            actor=actor,
            event_type="account.created",
            object_type="user",
            object_id=42,
            summary="A student account was created.",
            metadata={"role": "student"},
        )
        self.assertEqual(event.actor, actor)
        self.assertEqual(event.actor_username, "audit-user")
        self.assertEqual(event.object_id, "42")
        self.assertEqual(event.metadata, {"role": "student"})

    def test_sensitive_metadata_keys_are_removed(self):
        event = record_audit_event(
            actor=None,
            event_type="biometrics.test",
            object_type="test",
            summary="Sensitive fields are excluded.",
            metadata={
                "role": "student",
                "password": "must-not-be-stored",
                "image_frame": "must-not-be-stored",
                "template_version": 1,
            },
        )
        self.assertEqual(event.metadata, {"role": "student"})

    def test_audit_events_cannot_be_updated(self):
        event = AuditEvent.objects.create(
            event_type="test.event",
            object_type="test",
            summary="Original summary",
        )
        event.summary = "Changed summary"
        with self.assertRaises(ValueError):
            event.save()
        with self.assertRaises(ValueError):
            event.delete()


class RequestHardeningMiddlewareTests(TestCase):
    def test_oversized_biometric_upload_is_rejected_before_parsing(self):
        factory = RequestFactory()
        request = factory.post(
            "/api/v1/biometrics/enrolment/",
            data="",
            content_type="multipart/form-data",
        )
        request.META["CONTENT_LENGTH"] = str(9 * 1024 * 1024)
        response = BiometricRequestSizeLimitMiddleware(lambda _request: None)(request)
        self.assertEqual(response.status_code, 413)

    @override_settings(DEBUG=False)
    def test_react_routes_receive_security_headers(self):
        factory = RequestFactory()
        request = factory.get("/app/biometrics")
        response = RollNexaSecurityHeadersMiddleware(lambda _request: HttpResponse("ok"))(request)
        self.assertIn("camera=(self)", response["Permissions-Policy"])
        self.assertIn("script-src 'self'", response["Content-Security-Policy"])

    def test_admin_route_is_not_given_react_csp(self):
        factory = RequestFactory()
        request = factory.get("/admin/")
        response = RollNexaSecurityHeadersMiddleware(lambda _request: HttpResponse("ok"))(request)
        self.assertNotIn("Content-Security-Policy", response)

class ReadinessEndpointTests(TestCase):
    @override_settings(BIOMETRIC_MODEL_DIR="/tmp/rollnexa-test-models")
    def test_readyz_requires_database_and_model_assets(self):
        from unittest.mock import patch

        from django.test import Client

        with patch("biometrics.services.biometric_models_available", return_value=True):
            response = Client().get("/readyz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ready")

    def test_healthz_remains_a_liveness_endpoint(self):
        from django.test import Client

        response = Client().get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_REDIRECT_EXEMPT=[r"^healthz$", r"^readyz$"],
        SECURE_HSTS_SECONDS=31536000,
    )
    def test_health_endpoint_is_exempt_from_redirect_and_https_responses_receive_hsts(self):
        from django.test import Client

        client = Client()
        http_response = client.get("/healthz")
        self.assertEqual(http_response.status_code, 200)
        https_response = client.get("/healthz", secure=True)
        self.assertIn("max-age=31536000", https_response["Strict-Transport-Security"])
