"""
Replace the project-scoped Comment model with a generic ContentType-based
Comment + CommentSettings system.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0002_drop_land_project'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Drop the old project-scoped Comment table
        migrations.DeleteModel(
            name='Comment',
        ),

        # Create the new generic Comment model
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('body', models.TextField()),
                ('visibility', models.CharField(
                    choices=[('INTERNAL', 'Internal (RICD only)'), ('EXTERNAL', 'Visible to Council')],
                    default='INTERNAL',
                    max_length=10,
                )),
                ('is_edited', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ricd_comments',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('content_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='contenttypes.contenttype',
                )),
                ('parent', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='replies',
                    to='core.comment',
                )),
            ],
            options={
                'ordering': ['created_at'],
                'indexes': [
                    models.Index(fields=['content_type', 'object_id', 'parent'], name='core_commen_content_idx'),
                ],
            },
        ),

        # Create CommentSettings toggle table
        migrations.CreateModel(
            name='CommentSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(
                    help_text="Django model name (lowercase), e.g. 'project', 'fundingschedule'",
                    max_length=100,
                    unique=True,
                )),
                ('display_name', models.CharField(help_text='Human-readable page name', max_length=200)),
                ('is_enabled', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Comment Settings',
                'verbose_name_plural': 'Comment Settings',
                'ordering': ['display_name'],
            },
        ),
    ]
