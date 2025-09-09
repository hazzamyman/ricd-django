# Generated manually to fix database schema after removing conflicting migrations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ricd', '0015_outputtype_worktype_alter_address_output_type_and_more'),
    ]

    operations = [
        # Add missing fields that should be in the current models
        migrations.AddField(
            model_name='contact',
            name='address',
            field=models.TextField(blank=True, help_text='Physical address', null=True),
        ),
        migrations.AddField(
            model_name='contact',
            name='postal_address',
            field=models.TextField(blank=True, help_text='Postal address (optional)', null=True),
        ),
        migrations.AddField(
            model_name='council',
            name='is_registered_housing_provider',
            field=models.BooleanField(default=False, help_text='Whether or not the Council is a Registered Housing Provider. This affects whether or not we require leases where council is NOT a registered provider.'),
        ),
    ]
