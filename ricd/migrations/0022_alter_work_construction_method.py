# Generated manually to fix construction_method field mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ricd', '0021_constructionmethod_alter_address_construction_method_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='construction_method',
            field=models.ForeignKey(
                'ConstructionMethod',
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                help_text="Construction method used for this work"
            ),
        ),
    ]