from django.contrib import admin

from .models import (
    BiometricChallenge,
    BiometricConsent,
    BiometricConsentEvent,
    BiometricVerificationAttempt,
    FaceEnrollment,
)


@admin.register(BiometricConsent)
class BiometricConsentAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "policy_version", "granted_at", "withdrawn_at")
    list_filter = ("status", "policy_version")
    search_fields = ("student__user__username", "student__institutional_id")
    readonly_fields = ("student", "status", "policy_version", "granted_at", "withdrawn_at", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BiometricConsentEvent)
class BiometricConsentEventAdmin(admin.ModelAdmin):
    list_display = ("student", "action", "policy_version", "occurred_at")
    list_filter = ("action", "policy_version")
    search_fields = ("student__user__username", "student__institutional_id")
    readonly_fields = ("student", "action", "policy_version", "occurred_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FaceEnrollment)
class FaceEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "is_active", "model_version", "sample_count", "enrolled_at", "last_verified_at")
    list_filter = ("is_active", "model_version")
    search_fields = ("student__user__username", "student__institutional_id")
    exclude = ("encrypted_template",)
    readonly_fields = ("student", "encryption_key_version", "model_version", "template_version", "sample_count", "enrolled_at", "last_verified_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BiometricChallenge)
class BiometricChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "direction", "created_at", "expires_at", "consumed_at")
    list_filter = ("direction",)
    search_fields = ("student__user__username",)
    readonly_fields = ("id", "verification", "student", "direction", "expires_at", "consumed_at", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BiometricVerificationAttempt)
class BiometricVerificationAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "result", "failure_code", "liveness_passed", "model_version", "occurred_at")
    list_filter = ("result", "liveness_passed", "model_version")
    search_fields = ("student__user__username",)
    readonly_fields = ("verification", "student", "challenge", "result", "failure_code", "liveness_passed", "model_version", "occurred_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
