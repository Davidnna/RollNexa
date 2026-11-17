from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from core.frontend import frontend_app
from core.views import healthz

admin.site.site_header = "RollNexa Administration"
admin.site.site_title = "RollNexa Admin"
admin.site.index_title = "Platform management"

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include("api.urls")),
    path("admin/", admin.site.urls),
    path("", frontend_app, name="home"),
    path("about/", frontend_app, name="public_about"),
    path("features/", frontend_app, name="public_features"),
    path("how-it-works/", frontend_app, name="public_how_it_works"),
    path("contact/", frontend_app, name="public_contact"),
    path("privacy/", frontend_app, name="public_privacy"),
    path("terms/", frontend_app, name="public_terms"),
    path("login/", frontend_app, name="frontend_login"),
    re_path(r"^app(?:/.*)?$", frontend_app, name="frontend_app"),
    path("accounts/login/", RedirectView.as_view(url="/login/", permanent=False, query_string=True), name="login"),
    path("", include("accounts.urls")),
    path("", include("academics.urls")),
    path("", include("attendance.urls")),
]

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
