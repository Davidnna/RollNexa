from django.contrib import admin

from .models import (
    AcademicSession,
    Course,
    CourseLecturerAssignment,
    CourseOffering,
    CourseRegistration,
    Department,
    Faculty,
    Programme,
    Semester,
)


class ReadOnlyAcademicAdmin(admin.ModelAdmin):
    """Prevent unlogged academic mutations through Django Administration."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Faculty)
class FacultyAdmin(ReadOnlyAcademicAdmin):
    list_display = ("code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    readonly_fields = ("code", "name", "is_active", "created_at", "updated_at")


@admin.register(Department)
class DepartmentAdmin(ReadOnlyAcademicAdmin):
    list_display = ("code", "name", "faculty", "is_active")
    list_filter = ("faculty", "is_active")
    search_fields = ("code", "name", "faculty__name")
    readonly_fields = ("faculty", "code", "name", "is_active", "created_at", "updated_at")


@admin.register(Programme)
class ProgrammeAdmin(ReadOnlyAcademicAdmin):
    list_display = ("code", "name", "department", "award", "is_active")
    list_filter = ("department__faculty", "department", "mode", "is_active")
    search_fields = ("code", "name", "department__name")
    readonly_fields = (
        "department", "code", "name", "award", "mode", "is_active", "created_at", "updated_at",
    )


@admin.register(AcademicSession)
class AcademicSessionAdmin(ReadOnlyAcademicAdmin):
    list_display = ("name", "start_date", "end_date", "is_current", "is_active")
    list_filter = ("is_current", "is_active")
    readonly_fields = ("name", "start_date", "end_date", "is_current", "is_active", "created_at", "updated_at")


@admin.register(Semester)
class SemesterAdmin(ReadOnlyAcademicAdmin):
    list_display = ("name", "session", "start_date", "end_date", "is_current", "is_active")
    list_filter = ("session", "name", "is_current", "is_active")
    readonly_fields = (
        "session", "name", "start_date", "end_date", "is_current", "is_active", "created_at", "updated_at",
    )


@admin.register(Course)
class CourseAdmin(ReadOnlyAcademicAdmin):
    list_display = ("code", "title", "department", "credit_units", "stress_code", "is_active")
    list_filter = ("is_active", "stress_code", "department")
    search_fields = ("code", "title", "department__name")
    readonly_fields = (
        "department", "code", "title", "credit_units", "stress_code", "is_active", "created_at", "updated_at",
    )


@admin.register(CourseOffering)
class CourseOfferingAdmin(ReadOnlyAcademicAdmin):
    list_display = ("course", "programme", "semester", "level", "registration_open", "is_active")
    list_filter = ("is_active", "registration_open", "level", "semester__session")
    search_fields = ("course__code", "course__title", "programme__name")
    readonly_fields = (
        "course", "programme", "semester", "level", "max_students", "registration_open", "is_active",
        "created_at", "updated_at",
    )


@admin.register(CourseLecturerAssignment)
class CourseLecturerAssignmentAdmin(ReadOnlyAcademicAdmin):
    list_display = (
        "offering", "lecturer", "is_active", "assigned_at", "assigned_by",
        "removed_at", "removed_by",
    )
    list_filter = ("is_active", "offering__semester__session", "offering__programme")
    search_fields = (
        "offering__course__code", "lecturer__user__username",
        "lecturer__user__last_name", "lecturer__institutional_id",
    )
    readonly_fields = (
        "offering", "lecturer", "is_active", "assigned_at", "assigned_by",
        "removed_at", "removed_by", "removal_note",
    )


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(ReadOnlyAcademicAdmin):
    list_display = ("offering", "student", "status", "registered_at", "updated_at")
    list_filter = ("status", "offering__semester__session", "offering__level")
    search_fields = ("student__user__username", "student__user__last_name", "offering__course__code")
    readonly_fields = ("offering", "student", "status", "registered_at", "updated_at")
