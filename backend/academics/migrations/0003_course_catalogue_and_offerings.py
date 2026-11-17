import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0002_optional_programme_award_duration"),
        ("accounts", "0003_rename_created_accounts_related_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, validators=[django.core.validators.RegexValidator(message="Use 2–20 letters, numbers, spaces, dots, underscores, slashes or hyphens.", regex="^[A-Za-z0-9][A-Za-z0-9 ._/-]{1,19}$")])),
                ("title", models.CharField(max_length=180)),
                ("credit_units", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(6)], help_text="Enter the approved course unit value (1–6).")),
                ("description", models.TextField(blank=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="courses", to="academics.department")),
            ],
            options={"ordering": ["department__name", "code"]},
        ),
        migrations.CreateModel(
            name="CourseOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("level", models.CharField(choices=[("100", "100 level"), ("200", "200 level"), ("300", "300 level"), ("400", "400 level"), ("500", "500 level"), ("600", "600 level"), ("700", "700 level")], max_length=3)),
                ("registration_open", models.BooleanField(default=False, help_text="Students can register only while this offering is active and registration is open.")),
                ("max_students", models.PositiveIntegerField(blank=True, help_text="Optional enrolment limit. Leave blank for no configured limit.", null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ("notes", models.TextField(blank=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="offerings", to="academics.course")),
                ("programme", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="course_offerings", to="academics.programme")),
                ("semester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="course_offerings", to="academics.semester")),
            ],
            options={"ordering": ["-semester__session__name", "semester__name", "level", "course__code"]},
        ),
        migrations.CreateModel(
            name="CourseLecturerAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("lecturer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="course_lecturer_assignments", to="accounts.userprofile")),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lecturer_assignments", to="academics.courseoffering")),
            ],
            options={"ordering": ["lecturer__user__last_name", "lecturer__user__first_name"]},
        ),
        migrations.CreateModel(
            name="CourseRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("registered", "Registered"), ("withdrawn", "Withdrawn")], db_index=True, default="registered", max_length=12)),
                ("registered_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registrations", to="academics.courseoffering")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="course_registrations", to="accounts.userprofile")),
            ],
            options={"ordering": ["student__user__last_name", "student__user__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.UniqueConstraint(fields=("department", "code"), name="uniq_course_code_per_department"),
        ),
        migrations.AddConstraint(
            model_name="courseoffering",
            constraint=models.UniqueConstraint(fields=("course", "programme", "semester", "level"), name="uniq_course_offering_programme_term_level"),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.CheckConstraint(condition=Q(credit_units__gte=1) & Q(credit_units__lte=6), name="course_credit_units_between_1_6"),
        ),
        migrations.AddConstraint(
            model_name="courseoffering",
            constraint=models.CheckConstraint(condition=Q(max_students__isnull=True) | Q(max_students__gte=1), name="course_offering_capacity_positive"),
        ),
        migrations.AddConstraint(
            model_name="courselecturerassignment",
            constraint=models.UniqueConstraint(fields=("offering", "lecturer"), name="uniq_lecturer_per_course_offering"),
        ),
        migrations.AddConstraint(
            model_name="courseregistration",
            constraint=models.UniqueConstraint(fields=("offering", "student"), name="uniq_student_course_registration"),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["code"], name="course_code_idx"),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["title"], name="course_title_idx"),
        ),
        migrations.AddIndex(
            model_name="courseoffering",
            index=models.Index(fields=["programme", "level", "is_active"], name="offering_programme_level_idx"),
        ),
        migrations.AddIndex(
            model_name="courseoffering",
            index=models.Index(fields=["semester", "is_active"], name="offering_semester_active_idx"),
        ),
        migrations.AddIndex(
            model_name="courseregistration",
            index=models.Index(fields=["student", "status"], name="course_reg_student_status_idx"),
        ),
    ]
