from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_add_work_address_project_land_precondition_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='quarterly_report_item_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                help_text="Template group of Quarterly Report items for this project's quarterly reports",
                to='core.quarterlyreportitemgroup',
            ),
        ),
    ]
