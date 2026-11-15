from django.urls import path

from . import views

urlpatterns = [
    path("lecturer/attendance/", views.lecturer_attendance_sessions, name="lecturer_attendance_sessions"),
    path("lecturer/attendance/create/", views.attendance_session_create, name="attendance_session_create"),
    path("lecturer/attendance/<int:pk>/", views.attendance_session_detail, name="attendance_session_detail"),
    path("lecturer/attendance/<int:pk>/activate/", views.attendance_session_activate, name="attendance_session_activate"),
    path("lecturer/attendance/<int:pk>/close/", views.attendance_session_close, name="attendance_session_close"),
    path("lecturer/attendance/<int:pk>/cancel/", views.attendance_session_cancel, name="attendance_session_cancel"),
]
