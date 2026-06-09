"""Monthly cashflow service — per-Program x per-calendar-MONTH buckets."""
import pytest
from datetime import date
from decimal import Decimal


@pytest.mark.django_db
def test_forecast_payment_buckets_into_its_month(funding_schedule, project):
    from apps.core.models import Payment
    from apps.core.services.cashflow import build_program_monthly_cashflow

    Payment.objects.create(
        project=project, funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        amount=Decimal('120000'),
        forecast_release_date=date(2026, 4, 15),
        status=Payment.Status.PENDING,
    )

    data = build_program_monthly_cashflow(start='2026-01', months=12)
    key = f"{project.program_id}|2026-04"

    assert key in data['cells']
    assert data['cells'][key]['forecast'] == pytest.approx(120000.0)
    assert data['cells'][key]['released'] is None
    assert any(p['id'] == str(project.program_id) for p in data['programs'])
    # The cell carries the payment for drill-down.
    assert len(data['cells'][key]['payments']) == 1
    assert data['cells'][key]['payments'][0]['kind'] == 'forecast'


@pytest.mark.django_db
def test_released_payment_buckets_into_release_month_only(funding_schedule, project):
    from apps.core.models import Payment
    from apps.core.services.cashflow import build_program_monthly_cashflow

    Payment.objects.create(
        project=project, funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        amount=Decimal('80000'),
        forecast_release_date=date(2026, 3, 1),
        release_date=date(2026, 5, 20),
        status=Payment.Status.RELEASED,
    )

    data = build_program_monthly_cashflow(start='2026-01', months=12)
    released_key = f"{project.program_id}|2026-05"
    forecast_key = f"{project.program_id}|2026-03"

    assert data['cells'][released_key]['released'] == pytest.approx(80000.0)
    # A released payment is actual-only; it must NOT also show as forecast.
    assert forecast_key not in data['cells'] or data['cells'][forecast_key]['forecast'] == pytest.approx(0.0)


@pytest.mark.django_db
def test_payment_outside_window_excluded(funding_schedule, project):
    from apps.core.models import Payment
    from apps.core.services.cashflow import build_program_monthly_cashflow

    Payment.objects.create(
        project=project, funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        amount=Decimal('50000'),
        forecast_release_date=date(2030, 1, 10),
        status=Payment.Status.PENDING,
    )

    data = build_program_monthly_cashflow(start='2026-01', months=12)
    assert f"{project.program_id}|2030-01" not in data['cells']


@pytest.mark.django_db
def test_programmed_project_excluded_from_monthly(project, work_type):
    """Programmed (unapproved, no-payment) projects carry a FY but no payment
    month — they belong on the FY page, not this grid."""
    from apps.core.models import Work
    from apps.core.services.cashflow import build_program_monthly_cashflow

    project.state = project.State.PROGRAMMED
    project.financial_year = '2026-2027'
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=1,
                        estimated_cost=Decimal('250000'), is_notional_cost=False,
                        actual_cost=Decimal('250000'))

    data = build_program_monthly_cashflow(start='2026-01', months=24)
    # No payments at all -> no cells reference this program.
    assert all(not k.startswith(f"{project.program_id}|") for k in data['cells'])


@pytest.mark.django_db
def test_monthly_view_renders(admin_client, funding_schedule, project):
    from django.urls import reverse
    from apps.core.models import Payment

    Payment.objects.create(
        project=project, funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        amount=Decimal('60000'),
        forecast_release_date=date(2026, 2, 1),
        status=Payment.Status.PENDING,
    )
    resp = admin_client.get(reverse('ui:cashflow_monthly'), {'start': '2026-01', 'months': '12'})
    assert resp.status_code == 200
    assert b'Monthly Cashflow' in resp.content
    assert b'monthly-data' in resp.content  # json_script payload present
