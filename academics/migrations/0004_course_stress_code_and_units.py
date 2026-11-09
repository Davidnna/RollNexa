from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0003_course_catalogue_and_offerings"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="course",
            name="course_credit_units_between_1_6",
        ),
        migrations.AlterField(
            model_name="course",
            name="credit_units",
            field=models.PositiveSmallIntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(30)],
                help_text="Enter the approved course unit value (1–30).",
            ),
        ),
        migrations.AddField(
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
                help_text="Optional curriculum classification, retained as published by the institution.",
                max_length=2,
            ),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.CheckConstraint(
                condition=Q(credit_units__gte=1) & Q(credit_units__lte=30),
                name="course_credit_units_between_1_30",
            ),
        ),
    ]
