from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "offering", "title", "starts_at", "ends_at", "status", "created_by")
    list_filter = ("status", "offering__semester__session", "offering__semester")
    search_fields = ("offering__course__code", "offering__course__title", "title", "created_by__username")
    readonly_fields = ("offering", "title", "starts_at", "ends_at", "status", "created_by", "activated_at", "activated_by", "closed_at", "closed_by", "cancelled_at", "cancelled_by", "notes", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "qr_verified_at", "face_verified_at", "recorded_at")
    list_filter = ("session__status", "session__offering__semester__session")
    search_fields = ("student__user__username", "student__user__first_name", "student__user__last_name", "session__offering__course__code")
    readonly_fields = ("session", "student", "qr_verified_at", "face_verified_at", "recorded_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
