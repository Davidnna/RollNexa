from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "AttendIQ Administration"
admin.site.site_title = "AttendIQ Admin"
admin.site.index_title = "Platform management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("", include("accounts.urls")),
]

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
