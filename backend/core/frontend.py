from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.cache import never_cache


@never_cache
def frontend_app(request, path=None):
    index_path = settings.BASE_DIR / "static" / "frontend" / "index.html"
    if not index_path.is_file():
        return HttpResponseNotFound(
            "The RollNexa frontend has not been built. "
            "Run the frontend build before serving this route."
        )

    response = HttpResponse(index_path.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
