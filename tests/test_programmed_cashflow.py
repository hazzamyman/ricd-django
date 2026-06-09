"""Cashflow forward demand — programmed (not-yet-approved) projects layer."""
import pytest
from decimal import Decimal


@pytest.mark.django_db
def test_programmed_project_in_forward_demand(project, work_type):
    from apps.core.models import Work
    from apps.core.services.cashflow import build_program_cashflow
    # `project` fixture has a program but NO approved BFA and no payments.
    project.state = project.State.PROGRAMMED
    project.financial_year = '2030-2031'
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=1,
                        estimated_cost=Decimal('250000'), is_notional_cost=False,
                        actual_cost=Decimal('250000'))

    data = build_program_cashflow()
    fd = {f['fy']: f for f in data['forward_demand']}

    assert any(pp['project'].pk == project.pk for pp in data['programmed_projects'])
    assert fd['2030-2031']['programmed'] == Decimal('250000.00')
    assert fd['2030-2031']['total_need'] == Decimal('250000.00')   # no committed forecast


@pytest.mark.django_db
def test_approved_project_not_counted_as_programmed(funding_schedule, project, work_type):
    from apps.core.models import Work
    from apps.core.services.cashflow import build_program_cashflow
    # The funding_schedule fixture creates an APPROVED BFA for `project` -> committed.
    project.state = project.State.PROGRAMMED
    project.financial_year = '2031-2032'
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=1,
                        estimated_cost=Decimal('250000'), is_notional_cost=False,
                        actual_cost=Decimal('250000'))

    data = build_program_cashflow()
    assert not any(pp['project'].pk == project.pk for pp in data['programmed_projects'])
