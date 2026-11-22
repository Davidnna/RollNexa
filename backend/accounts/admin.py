from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered

from .models import UserProfile

User = get_user_model()


class ReadOnlyUserAdmin(UserAdmin):
    """Keep Django Administration diagnostic-only; account changes use audited workflows."""

    exclude = ("password",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


try:
    admin.site.unregister(User)
except NotRegistered:
    pass
admin.site.register(User, ReadOnlyUserAdmin)

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "department",
        "programme",
        "current_level",
        "institutional_id",
        "must_change_password",
        "created_at",
    )
    list_filter = ("role", "must_change_password")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "institutional_id",
    )
    readonly_fields = (
        "user",
        "role",
        "institutional_id",
        "phone_number",
        "department",
        "programme",
        "current_level",
        "must_change_password",
        "created_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
