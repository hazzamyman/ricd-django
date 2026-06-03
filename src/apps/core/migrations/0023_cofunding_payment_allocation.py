# Generated 2026-05-25; hand-edited to preserve data.
#
# Order:
#   1. Add the new PaymentAllocation model + table
#   2. Add BFAItem.program FK + alter ordering
#   3. RunPython: backfill BFAItem.program from project.program AND create
#      PaymentAllocation rows for every existing RELEASED Payment using
#      current BFAItem ratios (snapshot-on-migration, then lock forever).
#   4. Apply new unique constraints (after backfill is done so they hold).

import django.db.models.deletion
from django.db import migrations, models


def backfill_program_and_allocations(apps, schema_editor):
    from decimal import Decimal

    BFAItem = apps.get_model('core', 'BriefFinancialApprovalItem')
    Payment = apps.get_model('core', 'Payment')
    PaymentAllocation = apps.get_model('core', 'PaymentAllocation')

    # 1) Default BFAItem.program to project.program for existing rows
    for item in BFAItem.objects.filter(program__isnull=True).select_related('project'):
        if item.project_id and item.project.program_id:
            item.program_id = item.project.program_id
            item.save(update_fields=['program'])

    # 2) Snapshot PaymentAllocation rows for already-RELEASED payments using
    #    current BFAItem ratios.
    for p in Payment.objects.filter(status='RELEASED'):
        if PaymentAllocation.objects.filter(payment=p).exists():
            continue
        if not p.project_id:
            continue
        amount = p.amount or Decimal('0')
        if amount <= 0:
            continue

        project = p.project
        items = BFAItem.objects.filter(
            project_id=p.project_id, bfa__status='APPROVED',
        )
        totals = {}
        grand = Decimal('0')
        for item in items:
            t = (item.funding_amount or Decimal('0')) + (item.contingency_amount or Decimal('0'))
            if t <= 0:
                continue
            prog_id = item.program_id or project.program_id
            if prog_id is None:
                continue
            totals[prog_id] = totals.get(prog_id, Decimal('0')) + t
            grand += t

        if grand == 0:
            if project.program_id:
                PaymentAllocation.objects.create(
                    payment=p, program_id=project.program_id,
                    amount=amount, ratio=Decimal('1.000000'),
                )
            continue

        ordered = sorted(totals.items(), key=lambda kv: -kv[1])
        running = Decimal('0')
        for i, (prog_id, total) in enumerate(ordered):
            ratio = (total / grand).quantize(Decimal('0.000001'))
            if i == len(ordered) - 1:
                share = (amount - running).quantize(Decimal('0.01'))
            else:
                share = (amount * ratio).quantize(Decimal('0.01'))
                running += share
            PaymentAllocation.objects.create(
                payment=p, program_id=prog_id, amount=share, ratio=ratio,
            )


def reverse_backfill(apps, schema_editor):
    PaymentAllocation = apps.get_model('core', 'PaymentAllocation')
    BFAItem = apps.get_model('core', 'BriefFinancialApprovalItem')
    PaymentAllocation.objects.all().delete()
    BFAItem.objects.update(program=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_move_cost_centre_to_program"),
    ]

    operations = [
        # --- Step 1: create PaymentAllocation table ---
        migrations.CreateModel(
            name="PaymentAllocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True,
                        serialize=False, verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "ratio",
                    models.DecimalField(
                        decimal_places=6,
                        help_text="Fraction of payment.amount attributed to this program (0..1).",
                        max_digits=7,
                    ),
                ),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["payment_id", "program__name"]},
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="payment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="allocations",
                to="core.payment",
            ),
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="program",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_allocations",
                to="core.program",
            ),
        ),

        # --- Step 2: add BFAItem.program FK + drop old unique constraint ---
        migrations.AlterModelOptions(
            name="brieffinancialapprovalitem",
            options={"ordering": ["project__name", "program__name"]},
        ),
        migrations.RemoveConstraint(
            model_name="brieffinancialapprovalitem",
            name="bfa_item_unique_project",
        ),
        migrations.AddField(
            model_name="brieffinancialapprovalitem",
            name="program",
            field=models.ForeignKey(
                blank=True,
                help_text="Funding program this row draws from. Defaults to project.program in save(); set explicitly when capturing co-funding from a different program.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bfa_items",
                to="core.program",
            ),
        ),

        # --- Step 3: backfill data BEFORE adding the new constraints ---
        migrations.RunPython(backfill_program_and_allocations, reverse_backfill),

        # --- Step 4: enforce new uniqueness constraints ---
        migrations.AddConstraint(
            model_name="brieffinancialapprovalitem",
            constraint=models.UniqueConstraint(
                fields=("bfa", "project", "program"),
                name="bfa_item_unique_project_program",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymentallocation",
            constraint=models.UniqueConstraint(
                fields=("payment", "program"),
                name="payment_allocation_unique_program",
            ),
        ),
    ]
