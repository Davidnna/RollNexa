from django.urls import path
from . import views

urlpatterns = [
    path("management/academic/", views.academic_overview, name="academic_overview"),
    path("management/academic/<str:kind>/", views.academic_list, name="academic_list"),
    path("management/academic/<str:kind>/create/", views.academic_create, name="academic_create"),
    path("management/academic/<str:kind>/<int:pk>/edit/", views.academic_edit, name="academic_edit"),
    path("management/academic/<str:kind>/<int:pk>/toggle/", views.academic_toggle, name="academic_toggle"),
    path("management/academic/sessions/<int:pk>/set-current/", views.set_current_session, name="set_current_session"),
    path("management/academic/semesters/<int:pk>/set-current/", views.set_current_semester, name="set_current_semester"),
]
