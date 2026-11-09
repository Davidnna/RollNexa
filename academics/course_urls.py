from django.urls import path
from . import course_views as views
from . import course_import_views as import_views

urlpatterns = [
    path("management/courses/", views.course_management, name="course_management"),
    path("management/courses/import/", import_views.course_csv_import, name="course_csv_import"),
    path("management/courses/import/template/", import_views.course_csv_template, name="course_csv_template"),
    path("management/courses/catalogue/", views.course_catalogue, name="course_catalogue"),
    path("management/courses/catalogue/create/", views.course_create, name="course_create"),
    path("management/courses/catalogue/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("management/courses/catalogue/<int:pk>/toggle/", views.course_toggle, name="course_toggle"),
    path("management/courses/offerings/", views.offering_list, name="offering_list"),
    path("management/courses/offerings/create/", views.offering_create, name="offering_create"),
    path("management/courses/offerings/<int:pk>/", views.offering_detail, name="offering_detail"),
    path("management/courses/offerings/<int:pk>/edit/", views.offering_edit, name="offering_edit"),
    path("management/courses/offerings/<int:pk>/toggle/", views.offering_toggle, name="offering_toggle"),
    path("management/courses/offerings/<int:pk>/assign-lecturer/", views.offering_assign_lecturer, name="offering_assign_lecturer"),
    path("management/courses/offerings/<int:pk>/lecturers/<int:assignment_id>/remove/", views.offering_remove_lecturer, name="offering_remove_lecturer"),
    path("management/courses/offerings/<int:pk>/registrations/", views.offering_registrations, name="offering_registrations"),
    path("student/courses/", views.student_course_list, name="student_course_list"),
    path("student/courses/<int:pk>/register/", views.student_course_register, name="student_course_register"),
    path("student/courses/<int:pk>/withdraw/", views.student_course_withdraw, name="student_course_withdraw"),
    path("lecturer/courses/", views.lecturer_course_list, name="lecturer_course_list"),
    path("lecturer/courses/<int:pk>/", views.lecturer_course_roster, name="lecturer_course_roster"),
]
