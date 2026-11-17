import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Faculty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True, validators=[django.core.validators.RegexValidator(message="Use 2–20 letters, numbers, dots, underscores, slashes or hyphens.", regex="^[A-Za-z0-9][A-Za-z0-9._/-]{1,19}$")])),
                ("name", models.CharField(max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "faculties"},
        ),
        migrations.CreateModel(
            name="AcademicSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=9, unique=True, validators=[django.core.validators.RegexValidator(message="Enter the academic session in the format YYYY/YYYY, e.g. 2025/2026.", regex=r"^\d{4}/\d{4}$")])),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(db_index=True, default=False)),
            ],
            options={"ordering": ["-name"], "verbose_name": "academic session", "verbose_name_plural": "academic sessions"},
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, validators=[django.core.validators.RegexValidator(message="Use 2–20 letters, numbers, dots, underscores, slashes or hyphens.", regex="^[A-Za-z0-9][A-Za-z0-9._/-]{1,19}$")])),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("faculty", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="departments", to="academics.faculty")),
            ],
            options={"ordering": ["faculty__name", "name"]},
        ),
        migrations.CreateModel(
            name="Programme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, validators=[django.core.validators.RegexValidator(message="Use 2–20 letters, numbers, dots, underscores, slashes or hyphens.", regex="^[A-Za-z0-9][A-Za-z0-9._/-]{1,19}$")])),
                ("name", models.CharField(max_length=180)),
                ("award", models.CharField(default="B.Sc.", help_text="For example: B.Sc., B.A., B.Eng., B.Ed.", max_length=40)),
                ("duration_years", models.PositiveSmallIntegerField(default=4, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(8)])),
                ("mode", models.CharField(choices=[("full_time", "Full-time"), ("part_time", "Part-time")], default="full_time", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programmes", to="academics.department")),
            ],
            options={"ordering": ["department__name", "name"]},
        ),
        migrations.CreateModel(
            name="Semester",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(choices=[("first", "First semester"), ("second", "Second semester"), ("summer", "Summer semester")], max_length=12)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(db_index=True, default=False)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="semesters", to="academics.academicsession")),
            ],
            options={"ordering": ["-session__name", "name"]},
        ),
        migrations.AddConstraint(model_name="department", constraint=models.UniqueConstraint(fields=("faculty", "code"), name="uniq_department_code_per_faculty")),
        migrations.AddConstraint(model_name="department", constraint=models.UniqueConstraint(fields=("faculty", "name"), name="uniq_department_name_per_faculty")),
        migrations.AddConstraint(model_name="programme", constraint=models.UniqueConstraint(fields=("department", "code"), name="uniq_programme_code_per_department")),
        migrations.AddConstraint(model_name="programme", constraint=models.UniqueConstraint(fields=("department", "name"), name="uniq_programme_name_per_department")),
        migrations.AddConstraint(model_name="academicsession", constraint=models.UniqueConstraint(condition=Q(is_current=True), fields=("is_current",), name="one_current_academic_session")),
        migrations.AddConstraint(model_name="semester", constraint=models.UniqueConstraint(fields=("session", "name"), name="uniq_semester_name_per_session")),
        migrations.AddConstraint(model_name="semester", constraint=models.UniqueConstraint(condition=Q(is_current=True), fields=("is_current",), name="one_current_semester")),
    ]
