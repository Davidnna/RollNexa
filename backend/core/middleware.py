from django.http import JsonResponse


MAX_BIOMETRIC_REQUEST_BYTES = 8 * 1024 * 1024
FRONTEND_PATHS = {
    "/",
    "/about/",
    "/features/",
    "/how-it-works/",
    "/contact/",
    "/privacy/",
    "/terms/",
    "/login/",
    "/app",
}


class BiometricRequestSizeLimitMiddleware:
    """Reject oversized biometric multipart requests before Django parses uploads."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/v1/biometrics/") and request.method == "POST":
            content_length = request.META.get("CONTENT_LENGTH", "")
            if content_length:
                try:
                    request_size = int(content_length)
                except (TypeError, ValueError):
                    return JsonResponse({"detail": "The upload size could not be verified."}, status=400)
                if request_size < 0 or request_size > MAX_BIOMETRIC_REQUEST_BYTES:
                    return JsonResponse(
                        {"detail": "The biometric upload is too large. Capture the images again at a lower resolution."},
                        status=413,
                    )
        return self.get_response(request)


class RollNexaSecurityHeadersMiddleware:
    """Apply browser permissions and a restrictive policy to the React application."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not response.has_header("Permissions-Policy"):
            response["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        if request.path in FRONTEND_PATHS or request.path.startswith("/app/"):
            if not response.has_header("Content-Security-Policy"):
                response["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "base-uri 'self'; "
                    "object-src 'none'; "
                    "frame-ancestors 'none'; "
                    "form-action 'self'; "
                    "script-src 'self'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' data: https://fonts.gstatic.com; "
                    "img-src 'self' data: blob:; "
                    "media-src 'self' blob:; "
                    "connect-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com"
                )
        return response
