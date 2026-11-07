from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="registration/login.html",
        redirect_authenticated_user=True,
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("accounts/password-change/", views.AttendIQPasswordChangeView.as_view(), name="password_change"),
    path("accounts/password-change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html",
    ), name="password_change_done"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/lecturer/", views.lecturer_dashboard, name="lecturer_dashboard"),
    path("management/users/", views.user_list, name="user_list"),
    path("management/users/create/", views.user_create, name="user_create"),
    path("management/users/created/", views.user_created, name="user_created"),
    path("management/users/<int:user_id>/toggle-status/", views.toggle_account_status, name="toggle_account_status"),
    path("setup/initial-admin/", views.initial_admin_setup, name="initial_admin_setup"),
]
