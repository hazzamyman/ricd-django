# DelegatePosition: maintenance-managed delegation positions replace the
# hardcoded BriefFinancialApproval.DelegateLevel choices.

from django.db import migrations, models
import django.db.models.deletion


# Old hardcoded delegate_level value -> seeded position title.
_LEVEL_TO_TITLE = {
    'MGR': 'Manager',
    'DIR': 'Director',
    'GM': 'General Manager',
}

# Seed rows: (title, max_approval_amount, order). None amount == unlimited.
# Amounts are sensible starting points — edit them in Maintenance.
_SEED = [
    ('Manager', 250000, 1),
    ('Director', 1000000, 2),
    ('General Manager', None, 3),
]


def seed_and_map(apps, schema_editor):
    DelegatePosition = apps.get_model('core', 'DelegatePosition')
    BriefFinancialApproval = apps.get_model('core', 'BriefFinancialApproval')

    title_to_obj = {}
    for title, amount, order in _SEED:
        obj, _ = DelegatePosition.objects.get_or_create(
            title=title, defaults={'max_approval_amount': amount, 'order': order},
        )
        title_to_obj[title] = obj

    for bfa in BriefFinancialApproval.objects.all():
        title = _LEVEL_TO_TITLE.get(bfa.delegate_level)
        if title and title in title_to_obj:
            bfa.delegate_position = title_to_obj[title]
            bfa.save(update_fields=['delegate_position'])


def unmap(apps, schema_editor):
    # delegate_level is removed on forward, so there's nothing to restore.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_cashflowmethodrule"),
    ]

    operations = [
        migrations.CreateModel(
            name="DelegatePosition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True,
                        serialize=False, verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100, unique=True)),
                (
                    "max_approval_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True,
                        help_text="Maximum amount this position may approve. Leave blank for unlimited.",
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, help_text="Display order (low to high)."),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Delegate position",
                "ordering": ["order", "title"],
            },
        ),
        migrations.AddField(
            model_name="brieffinancialapproval",
            name="delegate_position",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approvals", to="core.delegateposition",
                help_text="Delegation position approving this. Managed in Maintenance → Delegate Positions.",
            ),
        ),
        migrations.RunPython(seed_and_map, unmap),
        migrations.RemoveField(
            model_name="brieffinancialapproval",
            name="delegate_level",
        ),
    ]
