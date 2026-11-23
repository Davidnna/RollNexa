from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0007_lecturer_assignment_audit_history"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="courselecturerassignment",
            options={
                "ordering": [
                    "-assigned_at",
                    "lecturer__user__last_name",
                    "lecturer__user__first_name",
                ],
            },
        ),
        migrations.AlterField(
            model_name="course",
            name="credit_units",
            field=models.PositiveSmallIntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(30)],
                help_text=(
                    "Catalogue default only; the approved units for each "
                    "programme are stored on CourseOffering (1–30)."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="course",
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
                help_text=(
                    "Catalogue default only; programme-specific classification "
                    "is stored on CourseOffering."
                ),
                max_length=2,
            ),
        ),
    ]
