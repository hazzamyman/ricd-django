"""
PR 3: Stage reports move from per-Project to per-FundingSchedule.

Schema changes:
  * FundingSchedule gains `start_date`, `stage1_item_group`, `stage2_item_group`
  * StageReport.project becomes nullable (SET_NULL); old (project, stage_type)
    unique constraint is dropped
  * Three conditional UniqueConstraints added: one per agreement linkage so a
    FS / Interim / Forward can have at most one Stage 1 and one Stage 2 report.

Data backfill:
  * For each FundingSchedule, copy stage1/2_item_group from its first linked
    Project if any of those projects already have one set. Idempotent.
"""
import django.db.models.deletion
from django.db import migrations, models


def backfill_item_groups_from_projects(apps, schema_editor):
    FS = apps.get_model('core', 'FundingSchedule')
    Project = apps.get_model('core', 'Project')
    for fs in FS.objects.all():
        p1 = Project.objects.filter(
            funding_schedule=fs, stage1_item_group__isnull=False
        ).first()
        if p1 and fs.stage1_item_group_id is None:
            fs.stage1_item_group_id = p1.stage1_item_group_id
        p2 = Project.objects.filter(
            funding_schedule=fs, stage2_item_group__isnull=False
        ).first()
        if p2 and fs.stage2_item_group_id is None:
            fs.stage2_item_group_id = p2.stage2_item_group_id
        anchor = Project.objects.filter(funding_schedule=fs).first()
        if anchor:
            for field in ('start_date', 'stage1_target_date', 'stage1_sunset_date',
                          'stage2_target_date', 'stage2_sunset_date'):
                if getattr(fs, field) is None and getattr(anchor, field) is not None:
                    setattr(fs, field, getattr(anchor, field))
        fs.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_pr2_worktype_bedroom_range'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='stagereport',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='fundingschedule',
            name='start_date',
            field=models.DateField(
                blank=True, null=True,
                help_text='Project start (cascaded to child projects on save)',
            ),
        ),
        migrations.AddField(
            model_name='fundingschedule',
            name='stage1_item_group',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage1_funding_schedules',
                to='core.stageitemgroup',
                help_text="Template group of Stage 1 items for the report covering this schedule's projects",
            ),
        ),
        migrations.AddField(
            model_name='fundingschedule',
            name='stage2_item_group',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage2_funding_schedules',
                to='core.stageitemgroup',
                help_text="Template group of Stage 2 items for the report covering this schedule's projects",
            ),
        ),
        migrations.AlterField(
            model_name='stagereport',
            name='project',
            field=models.ForeignKey(
                blank=True, db_index=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage_reports',
                to='core.project',
                help_text='Primary project (informational; the report covers all child projects of the linked FS)',
            ),
        ),
        migrations.AddConstraint(
            model_name='stagereport',
            constraint=models.UniqueConstraint(
                condition=models.Q(funding_schedule__isnull=False),
                fields=('funding_schedule', 'stage_type'),
                name='stage_report_unique_per_fs_stage',
            ),
        ),
        migrations.AddConstraint(
            model_name='stagereport',
            constraint=models.UniqueConstraint(
                condition=models.Q(interim_frp__isnull=False),
                fields=('interim_frp', 'stage_type'),
                name='stage_report_unique_per_interim_stage',
            ),
        ),
        migrations.AddConstraint(
            model_name='stagereport',
            constraint=models.UniqueConstraint(
                condition=models.Q(forward_rpf__isnull=False),
                fields=('forward_rpf', 'stage_type'),
                name='stage_report_unique_per_forward_stage',
            ),
        ),
        migrations.RunPython(backfill_item_groups_from_projects, reverse_code=noop_reverse),
    ]
