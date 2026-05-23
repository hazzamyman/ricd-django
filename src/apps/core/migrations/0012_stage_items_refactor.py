"""
Stage 1/2 report refactor:
- New StageItemDefinition / StageItemGroup / StageItemGroupItem models (template library).
- Project.stage1_item_group + stage2_item_group FKs.
- StageReport gains XOR linkage (funding_schedule | interim_frp | forward_rpf),
  IN_PROGRESS + REJECTED statuses, `item_group` FK.
- StageReportItem rebuilt as cells: (report, group_item) -> typed values + completion flags.
- StageReportAttachment unchanged (still per-item, re-created here to match new item PK).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_id_field_normalisation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. Drop old StageReport child tables (rebuild fresh)                #
        # ------------------------------------------------------------------ #
        migrations.DeleteModel(name='StageReportAttachment'),
        migrations.DeleteModel(name='StageReportItem'),

        # ------------------------------------------------------------------ #
        # 2. Adjust StageReport: new status choices                            #
        # ------------------------------------------------------------------ #
        migrations.AlterField(
            model_name='stagereport',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('IN_PROGRESS', 'In Progress'),
                    ('SUBMITTED', 'Submitted'),
                    ('ENDORSED', 'Endorsed by Council'),
                    ('ASSESSED', 'Assessed by RICD'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                ],
                db_index=True,
                default='DRAFT',
                max_length=20,
            ),
        ),

        # ------------------------------------------------------------------ #
        # 3. New stage-item template models                                    #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='StageItemDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Stage Item Definition',
                'verbose_name_plural': 'Stage Item Definitions',
            },
        ),
        migrations.CreateModel(
            name='StageItemGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('stage_type', models.CharField(
                    choices=[('STAGE1', 'Stage 1'), ('STAGE2', 'Stage 2')],
                    db_index=True,
                    max_length=10,
                )),
                ('name', models.CharField(max_length=255, help_text="e.g. 'Construction', 'Extension', 'Demolition', 'Land'")),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['stage_type', 'name'],
                'unique_together': {('stage_type', 'name')},
                'verbose_name': 'Stage Item Group',
                'verbose_name_plural': 'Stage Item Groups',
            },
        ),
        migrations.CreateModel(
            name='StageItemGroupItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('field_type', models.CharField(
                    choices=[
                        ('DATE', 'Date'),
                        ('DATE_NA', 'Date or N/A'),
                        ('NUMBER', 'Number'),
                        ('CURRENCY', 'Currency'),
                        ('TEXT', 'Text'),
                        ('CHECKBOX', 'Checkbox'),
                        ('YES_NO', 'Yes/No'),
                        ('YES_NO_NA', 'Yes/No/N/A'),
                    ],
                    default='CHECKBOX',
                    max_length=20,
                )),
                ('is_required', models.BooleanField(default=True)),
                ('requires_attachment', models.BooleanField(default=True, help_text='Council must upload at least one document URI')),
                ('help_text', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='core.stageitemgroup',
                )),
                ('item', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='group_memberships',
                    to='core.stageitemdefinition',
                )),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('group', 'order')},
                'verbose_name': 'Stage Item Group Item',
                'verbose_name_plural': 'Stage Item Group Items',
            },
        ),

        # ------------------------------------------------------------------ #
        # 4. Project.stage1_item_group + stage2_item_group                    #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='project',
            name='stage1_item_group',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage1_projects',
                to='core.stageitemgroup',
                help_text="Template group of Stage 1 items for this project's stage report",
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='stage2_item_group',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage2_projects',
                to='core.stageitemgroup',
                help_text="Template group of Stage 2 items for this project's stage report",
            ),
        ),

        # ------------------------------------------------------------------ #
        # 5. StageReport: add interim_frp, forward_rpf, item_group FKs        #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='stagereport',
            name='interim_frp',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage_reports',
                to='core.interimfrpagreement',
                help_text='Interim Forward Remote Capital Program agreement this report is linked to',
            ),
        ),
        migrations.AddField(
            model_name='stagereport',
            name='forward_rpf',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stage_reports',
                to='core.forwardrpfagreement',
                help_text='Forward Remote Capital Program agreement this report is linked to',
            ),
        ),
        migrations.AddField(
            model_name='stagereport',
            name='item_group',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='instances',
                to='core.stageitemgroup',
                help_text='Template group used when this report was opened',
            ),
        ),
        migrations.AddConstraint(
            model_name='stagereport',
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=True))
                    | (models.Q(funding_schedule__isnull=False) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=True))
                    | (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=False) & models.Q(forward_rpf__isnull=True))
                    | (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=False))
                ),
                name='stage_report_agreement_xor',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 6. Recreate StageReportItem (cell-style) and StageReportAttachment  #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='StageReportItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('date_value', models.DateField(blank=True, null=True)),
                ('number_value', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('text_value', models.TextField(blank=True)),
                ('boolean_value', models.BooleanField(blank=True, null=True)),
                ('is_na', models.BooleanField(default=False)),
                ('is_completed', models.BooleanField(default=False, help_text='Convenience flag: derived from value type but explicit for queries')),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='core.stagereport',
                )),
                ('group_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='report_instances',
                    to='core.stageitemgroupitem',
                    help_text='Template item this entry is populated from',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['group_item__order'],
                'unique_together': {('report', 'group_item')},
            },
        ),
        migrations.CreateModel(
            name='StageReportAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('document_uri', models.URLField(blank=True, help_text='Link to attachment in OpenDocs/Google Drive')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='core.stagereportitem',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
