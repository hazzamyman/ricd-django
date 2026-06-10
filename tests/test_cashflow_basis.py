"""Cashflow Cash vs Accrual basis + CashflowMethodRule config + Maintenance page."""
import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse


@pytest.mark.django_db
def test_rule_seeds_sensible_defaults():
    from apps.core.models import CashflowMethodRule
    assert CashflowMethodRule.get('MILESTONE').accrual_source == 'PAYMENT'
    assert CashflowMethodRule.get('WORKSTEP').accrual_source == 'WORKSTEP'


@pytest.mark.django_db
def test_basis_toggle_for_capital_works(funding_schedule, project, work_type):
    """A Capital Works project: cash shows its milestone payment; accrual swaps to
    its worksteps and excludes the payment."""
    from apps.core.models import Payment, Work, WorkStep
    from apps.core.services.cashflow import build_program_monthly_cashflow

    project.cashflow_method = 'WORKSTEP'
    project.save()
    # Milestone payment (cash) — Mar 2026.
    Payment.objects.create(project=project, funding_schedule=funding_schedule,
                           payment_type=Payment.PaymentType.FIRST, amount=Decimal('500000'),
                           forecast_release_date=date(2026, 3, 10), status=Payment.Status.PENDING)
    # Workstep accrual — 40% of $1,000,000 = $400,000 forecast May 2026.
    w = Work.objects.create(project=project, work_type=work_type, quantity=1,
                            is_notional_cost=False, actual_cost=Decimal('1000000'),
                            estimated_cost=Decimal('1000000'), cashflow_method='WORKSTEP')
    WorkStep.objects.create(work=w, step_name='Slab', order=1,
                            expected_cost_percentage=Decimal('40'),
                            forecast_completion_date=date(2026, 5, 1), is_active=True)

    pk = project.program_id
    cash = build_program_monthly_cashflow(start='2026-01', months=12, basis='cash')
    accr = build_program_monthly_cashflow(start='2026-01', months=12, basis='accrual')

    # Cash: payment present (Mar), no workstep (May).
    assert cash['cells'][f"{pk}|2026-03"]['forecast'] == pytest.approx(500000.0)
    assert f"{pk}|2026-05" not in cash['cells']
    # Accrual: payment excluded (Mar absent), workstep present (May).
    assert f"{pk}|2026-03" not in accr['cells']
    assert accr['cells'][f"{pk}|2026-05"]['forecast'] == pytest.approx(400000.0)


@pytest.mark.django_db
def test_basis_grant_identical_both_bases(funding_schedule, project):
    """A Capital Grant project looks the same on both bases (accrual = payments)."""
    from apps.core.models import Payment
    from apps.core.services.cashflow import build_program_monthly_cashflow

    # project default cashflow_method == MILESTONE (Capital Grant).
    Payment.objects.create(project=project, funding_schedule=funding_schedule,
                           payment_type=Payment.PaymentType.FIRST, amount=Decimal('300000'),
                           forecast_release_date=date(2026, 4, 1), status=Payment.Status.PENDING)
    pk = project.program_id
    cash = build_program_monthly_cashflow(start='2026-01', months=12, basis='cash')
    accr = build_program_monthly_cashflow(start='2026-01', months=12, basis='accrual')

    assert cash['cells'][f"{pk}|2026-04"]['forecast'] == pytest.approx(300000.0)
    assert accr['cells'][f"{pk}|2026-04"]['forecast'] == pytest.approx(300000.0)


@pytest.mark.django_db
def test_cashflow_rules_maintenance_page(admin_client):
    from apps.core.models import CashflowMethodRule

    resp = admin_client.get(reverse('ui:cashflow_rules'))
    assert resp.status_code == 200
    assert b'Cashflow Forecasting Rules' in resp.content

    resp = admin_client.post(reverse('ui:cashflow_rules'), {
        'MILESTONE_accrual_source': 'PAYMENT', 'MILESTONE_workstep_date': 'FCOMP',
        'MILESTONE_cost_basis': 'EFFECTIVE', 'MILESTONE_notes': '',
        'WORKSTEP_accrual_source': 'WORKSTEP', 'WORKSTEP_workstep_date': 'FSTART',
        'WORKSTEP_cost_basis': 'ESTIMATED', 'WORKSTEP_notes': 'use start date',
    })
    assert resp.status_code in (200, 302)
    works = CashflowMethodRule.get('WORKSTEP')
    assert works.workstep_date == 'FSTART'
    assert works.cost_basis == 'ESTIMATED'
    assert works.notes == 'use start date'


@pytest.mark.django_db
def test_cashflow_pages_render_for_both_bases(admin_client):
    for basis in ('cash', 'accrual'):
        r1 = admin_client.get(reverse('ui:cashflow'), {'basis': basis})
        r2 = admin_client.get(reverse('ui:cashflow_monthly'), {'basis': basis})
        assert r1.status_code == 200
        assert r2.status_code == 200
