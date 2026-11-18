from django.urls import path

from . import attendance_views, views, workspace_views
from biometrics import views as biometric_views

urlpatterns = [
    path("csrf/", views.CsrfTokenView.as_view(), name="api_csrf"),
    path("auth/session/", views.SessionView.as_view(), name="api_session"),
    path("auth/login/", views.LoginView.as_view(), name="api_login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api_logout"),
    path("auth/password-change/", views.PasswordChangeView.as_view(), name="api_password_change"),
    path("dashboard/summary/", views.DashboardSummaryView.as_view(), name="api_dashboard_summary"),
    path("attendance/sessions/<int:session_id>/qr/", attendance_views.AttendanceQRView.as_view(), name="api_attendance_qr"),
    path("attendance/verify-qr/", attendance_views.VerifyAttendanceQRView.as_view(), name="api_attendance_verify_qr"),
    path("attendance/verifications/<uuid:verification_id>/", attendance_views.AttendanceVerificationStatusView.as_view(), name="api_attendance_verification_status"),
    path("attendance/sessions/<int:session_id>/manual-records/", attendance_views.ManualAttendanceRecordsView.as_view(), name="api_attendance_manual_records"),
    path("biometrics/status/", biometric_views.BiometricStatusView.as_view(), name="api_biometrics_status"),
    path("biometrics/consent/", biometric_views.BiometricConsentView.as_view(), name="api_biometrics_consent"),
    path("biometrics/enrolment/", biometric_views.FaceEnrollmentView.as_view(), name="api_biometrics_enrolment"),
    path("biometrics/face-preview/", biometric_views.FacePreviewView.as_view(), name="api_biometrics_face_preview"),
    path("biometrics/verifications/<uuid:verification_id>/challenge/", biometric_views.FaceChallengeView.as_view(), name="api_biometrics_challenge"),
    path("biometrics/verifications/<uuid:verification_id>/verify/", biometric_views.FaceVerificationView.as_view(), name="api_biometrics_verify"),
    path("workspace/profile/", workspace_views.ProfileView.as_view(), name="api_workspace_profile"),
    path("workspace/reports/", workspace_views.ReportsView.as_view(), name="api_workspace_reports"),
    path("workspace/registration-control/", workspace_views.CourseRegistrationControlView.as_view(), name="api_workspace_registration_control"),
    path("workspace/assignment-options/", workspace_views.AssignmentOptionsView.as_view(), name="api_workspace_assignment_options"),
    path("workspace/assignments/bulk/", workspace_views.BulkTeachingAssignmentView.as_view(), name="api_workspace_bulk_assignments"),
    path("workspace/<str:resource>/", workspace_views.WorkspaceCollectionView.as_view(), name="api_workspace_collection"),
    path("workspace/<str:resource>/<int:pk>/", workspace_views.WorkspaceDetailView.as_view(), name="api_workspace_detail"),
    path("workspace/<str:resource>/<int:pk>/<str:action>/", workspace_views.WorkspaceActionView.as_view(), name="api_workspace_action"),
]
