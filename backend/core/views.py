from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def healthz(request):
    """Liveness endpoint: confirms the web process is responding."""
    return HttpResponse("ok", content_type="text/plain", status=200)


@never_cache
@require_GET
def readyz(request):
    """Readiness endpoint: confirms the database and required model assets are available."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        from biometrics.services import biometric_models_available

        if not biometric_models_available():
            return HttpResponse("not ready", content_type="text/plain", status=503)
    except (DatabaseError, OSError):
        return HttpResponse("not ready", content_type="text/plain", status=503)
    return HttpResponse("ready", content_type="text/plain", status=200)


def error_403(request, exception=None):
    return render(request, "accounts/access_denied.html", status=403)


def error_404(request, exception):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
