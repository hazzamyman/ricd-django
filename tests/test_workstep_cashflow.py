"""Capital Works (WorkStep Progressive) cashflow — driven by workstep value/dates."""
import pytest
from datetime import date
from decimal import Decimal


def _workstep_work(project, work_type):
    from apps.core.models import Work
    # Classification is at the project level now.
    project.cashflow_method = 'WORKSTEP'
    project.save()
    return Work.objects.create(
        project=project, work_type=work_type, quantity=1,
        is_notional_cost=False, actual_cost=Decimal('1000000'),
        estimated_cost=Decimal('1000000'),
        cashflow_method='WORKSTEP',
    )


@pytest.mark.django_db
def test_workstep_monthly_forecast_and_released(funding_schedule, project, work_type):
    from apps.core.models import WorkStep
    from apps.core.services.cashflow import build_program_monthly_cashflow

    w = _workstep_work(project, work_type)
    # Not-yet-completed step (30% of $1,000,000 = $300,000) forecast in Apr 2026.
    WorkStep.objects.create(work=w, step_name='Slab', order=1,
                            expected_cost_percentage=Decimal('30'),
                            forecast_completion_date=date(2026, 4, 15), is_active=True)
    # Completed step (20% = $200,000) actually completed Feb 2026.
    WorkStep.objects.create(work=w, step_name='Frame', order=2,
                            expected_cost_percentage=Decimal('20'),
                            forecast_completion_date=date(2026, 2, 1),
                            actual_completion_date=date(2026, 2, 20), is_active=True)

    data = build_program_monthly_cashflow(start='2026-01', months=12)
    fkey = f"{project.program_id}|2026-04"
    rkey = f"{project.program_id}|2026-02"

    # Forecast lands on the forecast-completion month at the step's value.
    assert data['cells'][fkey]['forecast'] == pytest.approx(300000.0)
    # Completed step is RELEASED on its actual-completion month (and not forecast).
    assert data['cells'][rkey]['released'] == pytest.approx(200000.0)
    assert data['cells'][rkey]['forecast'] == pytest.approx(0.0)
    # Drill-down carries the workstep claim.
    assert any(p['type'].startswith('WorkStep') for p in data['cells'][fkey]['payments'])


@pytest.mark.django_db
def test_workstep_fy_cashflow(funding_schedule, project, work_type):
    from apps.core.models import WorkStep
    from apps.core.services.cashflow import build_program_cashflow

    w = _workstep_work(project, work_type)
    # 50% = $500,000 completed May 2026 -> AU FY 2025-2026.
    WorkStep.objects.create(work=w, step_name='Practical Completion', order=1,
                            expected_cost_percentage=Decimal('50'),
                            actual_completion_date=date(2026, 5, 1), is_active=True)

    data = build_program_cashflow()
    row = next(r for r in data['rows'] if r['program'].pk == project.program_id)
    cell = next(c for c in row['cells'] if c['fy'] == '2025-2026')

    assert cell['released'] == Decimal('500000.00')
    # FY forecast (committed) includes the completed step too.
    assert cell['forecast'] >= Decimal('500000.00')


@pytest.mark.django_db
def test_milestone_work_not_double_counted(funding_schedule, project, work_type):
    """A MILESTONE (Capital Grant) work's steps must NOT feed workstep cashflow."""
    from apps.core.models import Work, WorkStep
    from apps.core.services.cashflow import build_program_monthly_cashflow

    w = Work.objects.create(project=project, work_type=work_type, quantity=1,
                            is_notional_cost=False, actual_cost=Decimal('1000000'),
                            estimated_cost=Decimal('1000000'),
                            cashflow_method='MILESTONE')
    WorkStep.objects.create(work=w, step_name='Slab', order=1,
                            expected_cost_percentage=Decimal('40'),
                            forecast_completion_date=date(2026, 3, 1), is_active=True)

    data = build_program_monthly_cashflow(start='2026-01', months=12)
    assert f"{project.program_id}|2026-03" not in data['cells']
