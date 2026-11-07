from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "institutional_id", "must_change_password", "created_at")
    list_filter = ("role", "must_change_password")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "institutional_id")
    readonly_fields = (
        "user", "role", "institutional_id", "phone_number",
        "must_change_password", "created_by", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
