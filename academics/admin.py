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


from .models import Course, CourseLecturerAssignment, CourseOffering, CourseRegistration


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "department", "credit_units", "stress_code", "is_active")
    list_filter = ("is_active", "stress_code", "department")
    search_fields = ("code", "title", "department__name")
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course", "programme", "semester", "level", "registration_open", "is_active")
    list_filter = ("is_active", "registration_open", "level", "semester__session")
    search_fields = ("course__code", "course__title", "programme__name")
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseLecturerAssignment)
class CourseLecturerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("offering", "lecturer", "assigned_at")
    search_fields = ("offering__course__code", "lecturer__user__username", "lecturer__user__last_name")
    readonly_fields = ("assigned_at",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ("offering", "student", "status", "registered_at", "updated_at")
    list_filter = ("status", "offering__semester__session", "offering__level")
    search_fields = ("student__user__username", "student__user__last_name", "offering__course__code")
    readonly_fields = ("registered_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False
