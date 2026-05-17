from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_comment_system'),
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, help_text='Short headline (optional)', max_length=200)),
                ('body', models.TextField()),
                ('visibility', models.CharField(
                    choices=[('INTERNAL', 'Internal (RICD only)'), ('EXTERNAL', 'Visible to Council')],
                    default='INTERNAL', max_length=10,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notices',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NoticeTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='contenttypes.contenttype',
                )),
                ('notice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='targets',
                    to='core.notice',
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='noticetarget',
            constraint=models.UniqueConstraint(
                fields=['notice', 'content_type', 'object_id'],
                name='unique_notice_target',
            ),
        ),
        migrations.AddIndex(
            model_name='noticetarget',
            index=models.Index(fields=['content_type', 'object_id'], name='core_notice_ct_obj_idx'),
        ),
    ]
