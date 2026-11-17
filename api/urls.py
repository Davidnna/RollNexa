from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CsrfTokenView.as_view(), name="api_csrf"),
    path("auth/session/", views.SessionView.as_view(), name="api_session"),
    path("auth/login/", views.LoginView.as_view(), name="api_login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api_logout"),
    path("auth/password-change/", views.PasswordChangeView.as_view(), name="api_password_change"),
    path("dashboard/summary/", views.DashboardSummaryView.as_view(), name="api_dashboard_summary"),
]
