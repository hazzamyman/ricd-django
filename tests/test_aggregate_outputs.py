"""Analytics — Aggregate Outputs service: BFA-driven per-program funding."""
import pytest
from decimal import Decimal
from tests.fixtures import make_bfa


@pytest.mark.django_db
def test_bfa_funding_attributed_to_program_and_category(project, program, work_type):
    from apps.core.models import Work
    from apps.core.services.analytics import build_aggregate_outputs

    work_type.category = 'RESIDENTIAL'
    work_type.save()
    project.state = project.State.FUNDED
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=3,
                        estimated_cost=Decimal('300000'), is_notional_cost=False,
                        actual_cost=Decimal('300000'))
    make_bfa(project, funding_amount=900000, status='APPROVED')

    data = build_aggregate_outputs()
    dw = data['data']['dwellings']

    # The funding program appears as a dynamic column...
    assert any(p['id'] == str(program.pk) for p in dw['programs'])
    assert len(dw['rows']) == 1
    row = dw['rows'][0]
    # ...with the approved BFA funding attributed to it.
    assert row['funding'][str(program.pk)] == pytest.approx(900000.0)
    assert dw['totals']['totalApproved'] == pytest.approx(900000.0)
    # FUNDED state, qty 3 -> funded-not-commenced + funded yield.
    assert row['fundedNotCommenced'] == pytest.approx(3.0)
    assert row['fundedYield'] == pytest.approx(3.0)


@pytest.mark.django_db
def test_program_only_shows_for_categories_it_funds(project, program, work_type):
    """A program column appears only on categories the project has works in."""
    from apps.core.models import Work
    from apps.core.services.analytics import build_aggregate_outputs

    work_type.category = 'LAND_DEV'
    work_type.save()
    project.state = project.State.FUNDED
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=5,
                        estimated_cost=Decimal('100000'), is_notional_cost=False,
                        actual_cost=Decimal('100000'))
    make_bfa(project, funding_amount=500000, status='APPROVED')

    data = build_aggregate_outputs()
    # Funds land (has works there)...
    assert any(p['id'] == str(program.pk) for p in data['data']['land']['programs'])
    # ...but not dwellings (no residential works).
    assert all(p['id'] != str(program.pk) for p in data['data']['dwellings']['programs'])
    assert data['data']['dwellings']['rows'] == []


@pytest.mark.django_db
def test_unapproved_bfa_not_counted(project, program, work_type):
    from apps.core.models import Work
    from apps.core.services.analytics import build_aggregate_outputs

    work_type.category = 'RESIDENTIAL'
    work_type.save()
    project.state = project.State.PROGRAMMED
    project.save()
    Work.objects.create(project=project, work_type=work_type, quantity=2,
                        estimated_cost=Decimal('200000'), is_notional_cost=False,
                        actual_cost=Decimal('200000'))
    make_bfa(project, funding_amount=400000, status='DRAFT')  # not approved

    data = build_aggregate_outputs()
    dw = data['data']['dwellings']
    assert dw['rows'][0]['totalApproved'] == pytest.approx(0.0)
    assert dw['rows'][0]['inPipeline'] == pytest.approx(2.0)  # PROGRAMMED -> in pipeline


@pytest.mark.django_db
def test_analytics_view_renders(admin_client, project, work_type):
    from django.urls import reverse
    from apps.core.models import Work

    work_type.category = 'RESIDENTIAL'
    work_type.save()
    Work.objects.create(project=project, work_type=work_type, quantity=1,
                        estimated_cost=Decimal('100000'), is_notional_cost=False,
                        actual_cost=Decimal('100000'))
    resp = admin_client.get(reverse('ui:aggregate_outputs'))
    assert resp.status_code == 200
    assert b'Aggregate Outputs' in resp.content
    assert b'analytics-data' in resp.content
