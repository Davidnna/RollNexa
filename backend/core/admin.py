from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "actor_username", "object_type", "object_id", "summary")
    list_filter = ("event_type", "object_type", "created_at")
    search_fields = ("actor_username", "event_type", "object_type", "object_id", "summary")
    readonly_fields = (
        "actor",
        "actor_username",
        "event_type",
        "object_type",
        "object_id",
        "summary",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
