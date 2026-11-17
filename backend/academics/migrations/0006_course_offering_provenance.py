from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0005_offering_specific_units_and_stress"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseoffering",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="Optional source URL for this programme-specific curriculum entry.",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="courseoffering",
            name="source_note",
            field=models.TextField(
                blank=True,
                help_text="Optional provenance or verification note for this offering.",
            ),
        ),
    ]
