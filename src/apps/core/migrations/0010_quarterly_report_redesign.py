"""
QuarterlyReport redesign: per-council + year + quarter, 4-state status,
configurable items grid (rows = Works, columns = items).

Drops old per-project QR tables and recreates as per-council with
QuarterlyReportItemGroup / QuarterlyReportItem (kept config-driven structure)
and QuarterlyReportEntry (now (report, work, item) cells).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_monthly_tracker_redesign'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. Drop old per-project quarterly tables                            #
        # ------------------------------------------------------------------ #
        migrations.DeleteModel(name='QuarterlyReportAttachment'),
        migrations.DeleteModel(name='QuarterlyReportEntry'),
        migrations.DeleteModel(name='QuarterlyReport'),
        migrations.DeleteModel(name='QuarterlyReportItem'),
        migrations.DeleteModel(name='QuarterlyReportItemGroup'),

        # ------------------------------------------------------------------ #
        # 2. Recreate item-group and item config tables                       #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='QuarterlyReportItemGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['order', 'name']},
        ),
        migrations.CreateModel(
            name='QuarterlyReportItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
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
                    default='TEXT',
                    max_length=20,
                )),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_required', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('help_text', models.CharField(blank=True, max_length=255)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='core.quarterlyreportitemgroup',
                )),
            ],
            options={'ordering': ['order']},
        ),

        # ------------------------------------------------------------------ #
        # 3. QuarterlyReport (per council + year + quarter)                   #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='QuarterlyReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('year', models.PositiveSmallIntegerField(db_index=True)),
                ('quarter', models.PositiveSmallIntegerField(db_index=True, help_text='1-4')),
                ('status', models.CharField(
                    choices=[
                        ('DRAFT', 'Draft'),
                        ('IN_PROGRESS', 'In Progress'),
                        ('SUBMITTED', 'Submitted by Council'),
                        ('APPROVED', 'Approved'),
                    ],
                    db_index=True,
                    default='DRAFT',
                    max_length=20,
                )),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('council', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quarterly_reports',
                    to='core.council',
                )),
                ('submitted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='submitted_quarterly_reports',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('approved_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_quarterly_reports',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-year', '-quarter'],
                'unique_together': {('council', 'year', 'quarter')},
            },
        ),

        # ------------------------------------------------------------------ #
        # 4. QuarterlyReportEntry (grid cells)                                #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='QuarterlyReportEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('date_value', models.DateField(blank=True, null=True)),
                ('number_value', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('text_value', models.TextField(blank=True)),
                ('boolean_value', models.BooleanField(blank=True, null=True)),
                ('is_na', models.BooleanField(default=False, help_text='Mark cell as N/A when item supports it')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='entries',
                    to='core.quarterlyreport',
                )),
                ('work', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quarterly_entries',
                    to='core.work',
                )),
                ('item', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.quarterlyreportitem',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'unique_together': {('report', 'work', 'item')}},
        ),

        # ------------------------------------------------------------------ #
        # 5. QuarterlyReportAttachment                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='QuarterlyReportAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('document_uri', models.URLField(blank=True, help_text='Link to attachment in OpenDocs/Google Drive')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='core.quarterlyreport',
                )),
                ('work', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quarterly_attachments',
                    to='core.work',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
