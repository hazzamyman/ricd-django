"""
Migration: Simplify OfficerRole and GroupType to 5 clean roles.

Old roles mapped to new:
  PRINCIPAL_OFFICER, PROGRAM_OFFICER, SENIOR_OFFICER → OFFICER
  DIRECTOR, GM → MANAGER
  COUNCIL_USER, COUNCIL_MANAGER → unchanged
  OTHER → READ_ONLY
"""
from django.db import migrations, models


OLD_TO_NEW = {
    'PRINCIPAL_OFFICER': 'OFFICER',
    'PROGRAM_OFFICER': 'OFFICER',
    'SENIOR_OFFICER': 'OFFICER',
    'DIRECTOR': 'MANAGER',
    'GM': 'MANAGER',
    'OTHER': 'READ_ONLY',
}

OLD_GROUP_TO_NEW = {
    'FNC_USER': 'OFFICER',
    'FNC_MANAGER': 'MANAGER',
    'OTHER_TEAM_USER': 'OFFICER',
    'OTHER_TEAM_MANAGER': 'MANAGER',
}


def migrate_roles_forward(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    for old, new in OLD_TO_NEW.items():
        Profile.objects.filter(officer_role=old).update(officer_role=new)

    GroupPermission = apps.get_model('core', 'GroupPermission')
    for old, new in OLD_GROUP_TO_NEW.items():
        GroupPermission.objects.filter(group_type=old).update(group_type=new)


def migrate_roles_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_drop_land_project'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='officer_role',
            field=models.CharField(
                blank=True,
                choices=[
                    ('OFFICER', 'Officer'),
                    ('MANAGER', 'Manager'),
                    ('COUNCIL_USER', 'Council User'),
                    ('COUNCIL_MANAGER', 'Council Manager'),
                    ('READ_ONLY', 'Read Only'),
                ],
                help_text='FNC role for the officer',
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='grouppermission',
            name='group_type',
            field=models.CharField(
                choices=[
                    ('OFFICER', 'Officer'),
                    ('MANAGER', 'Manager'),
                    ('COUNCIL_USER', 'Council User'),
                    ('COUNCIL_MANAGER', 'Council Manager'),
                    ('READ_ONLY', 'Read Only'),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
    ]
