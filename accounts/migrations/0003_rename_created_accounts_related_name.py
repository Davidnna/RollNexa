import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_userprofile_academic_assignments")]
    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_rollnexa_accounts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
