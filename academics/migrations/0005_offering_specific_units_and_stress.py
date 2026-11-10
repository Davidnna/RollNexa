from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Q


def copy_course_defaults_to_offerings(apps, schema_editor):
    CourseOffering = apps.get_model("academics", "CourseOffering")
    for offering in CourseOffering.objects.select_related("course").iterator():
        offering.credit_units = offering.course.credit_units
        offering.stress_code = offering.course.stress_code or ""
        offering.save(update_fields=["credit_units", "stress_code"])


def reverse_copy(apps, schema_editor):
    # The original Course fields remain in place as catalogue defaults.
    # There is no safe reverse operation because different offerings may now differ.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0004_course_stress_code_and_units"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseoffering",
            name="credit_units",
            field=models.PositiveSmallIntegerField(
                default=2,
                validators=[MinValueValidator(1), MaxValueValidator(30)],
                help_text="Approved credit units for this programme-specific offering (1–30).",
            ),
        ),
        migrations.AddField(
            model_name="courseoffering",
            name="stress_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("C", "Core (C)"),
                    ("R", "Required (R)"),
                    ("E", "Elective (E)"),
                    ("G", "General (G)"),
                    ("AR", "As published: AR"),
                ],
                default="",
                help_text="Programme-specific curriculum classification, if published.",
                max_length=2,
            ),
        ),
        migrations.RunPython(copy_course_defaults_to_offerings, reverse_copy),
        migrations.AddConstraint(
            model_name="courseoffering",
            constraint=models.CheckConstraint(
                condition=Q(credit_units__gte=1) & Q(credit_units__lte=30),
                name="offering_credit_units_between_1_30",
            ),
        ),
    ]
