"""
Phase 4: MonthlyTracker redesign — per-council, per-month.

Replaces:
  - MonthlyTrackerItemGroup, MonthlyTrackerItem, MonthlyTrackerEntry (config-driven approach)
  - MonthlyTracker (was per-FundingSchedule)

Adds:
  - CouncilTrackerConfig (singleton per council)
  - MonthlyTracker (per council + year + month)
  - MonthlyTrackerWorkEntry (per tracker + WorkStep cell)
  - WorkStepGroupItem.is_monthly_tracker_column flag
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_remove_worksteptemplate_work_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. Remove old MonthlyTracker related tables                         #
        # ------------------------------------------------------------------ #
        migrations.DeleteModel(name='MonthlyTrackerEntry'),
        migrations.DeleteModel(name='MonthlyTrackerItem'),
        migrations.DeleteModel(name='MonthlyTrackerItemGroup'),
        migrations.DeleteModel(name='MonthlyTracker'),

        # ------------------------------------------------------------------ #
        # 2. Add is_monthly_tracker_column to WorkStepGroupItem               #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='workstepgroupitem',
            name='is_monthly_tracker_column',
            field=models.BooleanField(
                default=False,
                help_text='Show this step as a column in the monthly tracker grid',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 3. CouncilTrackerConfig                                              #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='CouncilTrackerConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('council_submission_enabled', models.BooleanField(
                    default=False,
                    help_text='Allow council users to submit their monthly tracker',
                )),
                ('submission_due_day', models.PositiveSmallIntegerField(
                    default=8,
                    help_text='Day of the following month by which the council must submit (default 8)',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('council', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tracker_config',
                    to='core.council',
                )),
            ],
        ),

        # ------------------------------------------------------------------ #
        # 4. MonthlyTracker (new -- per council + year + month)               #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='MonthlyTracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(db_index=True)),
                ('month', models.PositiveSmallIntegerField(db_index=True, help_text='1–12')),
                ('status', models.CharField(
                    choices=[
                        ('DRAFT', 'Draft'),
                        ('SUBMITTED', 'Submitted by Council'),
                        ('REVIEWED', 'Reviewed by RICD'),
                    ],
                    db_index=True,
                    default='DRAFT',
                    max_length=20,
                )),
                ('notes', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('council', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='monthly_trackers',
                    to='core.council',
                )),
                ('submitted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='submitted_monthly_trackers',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_monthly_trackers',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-year', '-month'],
                'unique_together': {('council', 'year', 'month')},
            },
        ),

        # ------------------------------------------------------------------ #
        # 5. MonthlyTrackerWorkEntry                                           #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='MonthlyTrackerWorkEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actual_completion_date', models.DateField(
                    blank=True,
                    null=True,
                    help_text='Set when council ticks the checkbox; cleared when unticked',
                )),
                ('forecast_completion_date', models.DateField(
                    blank=True,
                    null=True,
                    help_text="Council's forecast if the step is not yet complete",
                )),
                ('notes', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tracker', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='work_entries',
                    to='core.monthlytracker',
                )),
                ('work_step', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tracker_entries',
                    to='core.workstep',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('tracker', 'work_step')},
            },
        ),
    ]
