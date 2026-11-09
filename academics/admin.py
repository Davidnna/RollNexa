from django.contrib import admin

from .models import AcademicSession, Department, Faculty, Programme, Semester


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    readonly_fields = ("is_active",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty", "is_active")
    list_filter = ("faculty", "is_active")
    search_fields = ("code", "name", "faculty__name")
    readonly_fields = ("is_active",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "award", "is_active")
    list_filter = ("department__faculty", "department", "mode", "is_active")
    search_fields = ("code", "name", "department__name")
    readonly_fields = ("is_active",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current", "is_active")
    list_filter = ("is_current", "is_active")
    readonly_fields = ("is_current", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "session", "start_date", "end_date", "is_current", "is_active")
    list_filter = ("session", "name", "is_current", "is_active")
    readonly_fields = ("is_current", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False
