import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("academics", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="department",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="staff_profiles", to="academics.department"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="programme",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="student_profiles", to="academics.programme"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="current_level",
            field=models.CharField(blank=True, choices=[("100", "100 level"), ("200", "200 level"), ("300", "300 level"), ("400", "400 level"), ("500", "500 level"), ("600", "600 level"), ("700", "700 level")], max_length=3),
        ),
    ]
