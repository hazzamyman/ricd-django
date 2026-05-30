# Schema + data migration:
#   - WorkStepGroup.work_type (FK) -> work_types (M2M to WorkType)
#   - StageItemGroup.work_types (M2M, additive)
# The FK is dropped only AFTER existing rows have been copied into the M2M.

from django.db import migrations, models


def forwards_backfill(apps, schema_editor):
    """Copy each WorkStepGroup.work_type into work_types.add(work_type)."""
    WorkStepGroup = apps.get_model("core", "WorkStepGroup")
    for g in WorkStepGroup.objects.all():
        if g.work_type_id:
            g.work_types.add(g.work_type_id)


def backwards_noop(apps, schema_editor):
    # Reverse cannot reconstruct a single FK from a multi-valued M2M unambiguously.
    # Treat as a one-way move; pick the first M2M row when rolling back manually.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0027_mvp_phase_b_qr_content_expansion"),
    ]

    operations = [
        # 1.  Add the new M2M field. Use a placeholder related_name to avoid
        #     clashing with the existing FK's related_name ('step_groups').
        migrations.AddField(
            model_name="workstepgroup",
            name="work_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Work types this group applies to — many-to-many so one group can serve all residential types that share a workflow.",
                related_name="step_groups_m2m_tmp",
                to="core.worktype",
            ),
        ),
        # 2.  Add StageItemGroup.work_types (no clash, additive).
        migrations.AddField(
            model_name="stageitemgroup",
            name="work_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Optional — work types this group typically applies to. Drives the picker filter on the Funding Schedule form.",
                related_name="stage_item_groups",
                to="core.worktype",
            ),
        ),
        # 3.  Copy existing single FK rows into the new M2M.
        migrations.RunPython(forwards_backfill, backwards_noop),
        # 4.  Drop the old single-valued FK.
        migrations.RemoveField(
            model_name="workstepgroup",
            name="work_type",
        ),
        # 5.  Rename the M2M's reverse accessor to its final name.
        migrations.AlterField(
            model_name="workstepgroup",
            name="work_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Work types this group applies to — many-to-many so one group can serve all residential types that share a workflow.",
                related_name="step_groups",
                to="core.worktype",
            ),
        ),
        # 6.  Cosmetic — new ordering / help_text on the model.
        migrations.AlterModelOptions(
            name="workstepgroup",
            options={
                "ordering": ["name"],
                "verbose_name": "Work Step Group",
                "verbose_name_plural": "Work Step Groups",
            },
        ),
        migrations.AlterField(
            model_name="workstepgroup",
            name="name",
            field=models.CharField(
                help_text="e.g. 'Standard New Residential Construction', 'Land Subdivision'",
                max_length=200,
            ),
        ),
    ]
