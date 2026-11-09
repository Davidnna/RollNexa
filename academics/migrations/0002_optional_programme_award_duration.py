from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("academics", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="programme",
            name="award",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional. For example: B.Sc., B.A., B.Eng. Leave blank if not confirmed.",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="programme",
            name="duration_years",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Optional. Leave blank if the official duration has not been confirmed.",
                null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(8)],
            ),
        ),
    ]
