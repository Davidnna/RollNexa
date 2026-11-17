from django.urls import path

from . import views, workspace_views

urlpatterns = [
    path("csrf/", views.CsrfTokenView.as_view(), name="api_csrf"),
    path("auth/session/", views.SessionView.as_view(), name="api_session"),
    path("auth/login/", views.LoginView.as_view(), name="api_login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api_logout"),
    path("auth/password-change/", views.PasswordChangeView.as_view(), name="api_password_change"),
    path("dashboard/summary/", views.DashboardSummaryView.as_view(), name="api_dashboard_summary"),
    path("workspace/profile/", workspace_views.ProfileView.as_view(), name="api_workspace_profile"),
    path("workspace/reports/", workspace_views.ReportsView.as_view(), name="api_workspace_reports"),
    path("workspace/<str:resource>/", workspace_views.WorkspaceCollectionView.as_view(), name="api_workspace_collection"),
    path("workspace/<str:resource>/<int:pk>/", workspace_views.WorkspaceDetailView.as_view(), name="api_workspace_detail"),
    path("workspace/<str:resource>/<int:pk>/<str:action>/", workspace_views.WorkspaceActionView.as_view(), name="api_workspace_action"),
]
