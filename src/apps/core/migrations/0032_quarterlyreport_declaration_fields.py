from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_project_quarterly_report_item_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='quarterlyreport',
            name='declaration_officer_name',
            field=models.CharField(
                blank=True, max_length=255,
                help_text="Full name of the duly authorised officer signing off the report.",
            ),
        ),
        migrations.AddField(
            model_name='quarterlyreport',
            name='declaration_officer_position',
            field=models.CharField(
                blank=True, max_length=255,
                help_text="Position/title of the authorised officer.",
            ),
        ),
        migrations.AddField(
            model_name='quarterlyreport',
            name='declaration_date',
            field=models.DateField(
                blank=True, null=True,
                help_text="Date the authorised officer certified the report.",
            ),
        ),
    ]
