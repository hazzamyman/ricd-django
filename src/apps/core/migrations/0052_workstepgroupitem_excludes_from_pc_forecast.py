from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_delegateposition'),
    ]

    operations = [
        migrations.AddField(
            model_name='workstepgroupitem',
            name='excludes_from_pc_forecast',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'When checked, this step does not participate in the sequential date chain '
                    'and is excluded from Practical Completion date forecasting. '
                    'Use for parallel or standalone activities (e.g. inspections, admin) that '
                    'happen independently of the main construction sequence.'
                ),
            ),
        ),
    ]
