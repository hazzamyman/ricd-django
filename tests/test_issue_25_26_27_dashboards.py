"""
Tests for dashboard issues:
  #25 — Financial traceability view (/dashboard/traceability/)
  #26 — Project status board (/dashboard/projects/)
  #27 — Cashflow forecast (/dashboard/cashflow/)
"""
import json
import pytest
from datetime import date
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import (
    Council, Program, Project, FundingSchedule, FundingAgreement,
    Payment, WorkFunding, Profile,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council():
    return Council.objects.create(name='Dash Council', region='QLD')


@pytest.fixture
def program(council):
    return Program.objects.create(
        name='Dash Program',
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('5000000'),
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        name='Dash Project', council=council, program=program,
        state=Project.State.FUNDED, financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(project):
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('300000'),
        contingency=Decimal('0'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
        status=FundingSchedule.Status.ACTIVE,
    )


@pytest.fixture
def funding_agreement(council, funding_schedule):
    fa = FundingAgreement.objects.create(
        council=council,
        name='Dash Agreement',
        status=FundingAgreement.Status.ACTIVE,
        execution_date=date(2025, 1, 15),
    )
    funding_schedule.funding_agreement = fa
    funding_schedule.save()
    return fa


@pytest.fixture
def released_payment(project, funding_schedule):
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        amount=Decimal('180000'),
        status=Payment.Status.RELEASED,
        release_date=date(2025, 3, 10),
    )


@pytest.fixture
def approved_payment(project, funding_schedule):
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.SECOND,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        amount=Decimal('120000'),
        status=Payment.Status.APPROVED,
        release_date=date(2025, 9, 1),
    )


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='dash_officer', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.OFFICER)
    client.force_login(user)
    return client, user


# ===========================================================================
# Issue #27 — Cashflow forecast
# ===========================================================================

@pytest.mark.django_db
class TestCashflowView:
    def test_get_returns_200(self, auth_client):
        client, _ = auth_client
        response = client.get('/cashflow/')
        assert response.status_code == 200

    def test_requires_login(self):
        response = Client().get('/cashflow/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_shows_released_payment_amount(self, auth_client, released_payment):
        client, _ = auth_client
        response = client.get('/cashflow/')
        assert response.status_code == 200
        assert b'180' in response.content

    def test_chart_data_in_context(self, auth_client, released_payment, approved_payment):
        client, _ = auth_client
        response = client.get('/cashflow/')
        ctx = response.context
        labels = json.loads(ctx['chart_labels'])
        planned = json.loads(ctx['chart_planned'])
        actual = json.loads(ctx['chart_actual'])
        assert isinstance(labels, list)
        assert isinstance(planned, list)
        assert isinstance(actual, list)
        assert len(labels) == len(planned) == len(actual)

    def test_filter_by_program(self, auth_client, released_payment, program):
        client, _ = auth_client
        response = client.get(f'/cashflow/?program={program.pk}')
        assert response.status_code == 200
        assert b'180' in response.content

    def test_filter_by_council(self, auth_client, released_payment, council):
        client, _ = auth_client
        response = client.get(f'/cashflow/?council={council.pk}')
        assert response.status_code == 200

    def test_filter_excludes_other_council(self, auth_client, released_payment):
        client, _ = auth_client
        other = Council.objects.create(name='Other Council CF', region='NSW')
        response = client.get(f'/cashflow/?council={other.pk}')
        assert response.status_code == 200
        # released_payment is $180k for Dash Council — should not appear
        ctx = response.context
        assert ctx['total_forecast'] == 0 or ctx['total_released'] == 0

    def test_total_released_excludes_approved(self, auth_client, released_payment, approved_payment):
        client, _ = auth_client
        response = client.get('/cashflow/')
        ctx = response.context
        assert ctx['total_released'] == Decimal('180000')
        assert ctx['total_forecast'] == Decimal('300000')

    def test_approved_payment_in_planned_bucket(self, auth_client, approved_payment):
        client, _ = auth_client
        response = client.get('/cashflow/')
        ctx = response.context
        planned = json.loads(ctx['chart_planned'])
        assert sum(planned) == 120000  # only the APPROVED payment

    def test_by_program_includes_drawdown(self, auth_client, released_payment, program):
        client, _ = auth_client
        response = client.get('/cashflow/')
        ctx = response.context
        prog_row = next((r for r in ctx['by_program'] if r['program'] == program), None)
        assert prog_row is not None
        assert prog_row['drawdown_percent'] > 0


# ===========================================================================
# Issue #26 — Project status board
# ===========================================================================

@pytest.mark.django_db
class TestProjectsBoardView:
    def test_get_returns_200(self, auth_client):
        client, _ = auth_client
        response = client.get('/dashboard/projects/')
        assert response.status_code == 200

    def test_requires_login(self):
        response = Client().get('/dashboard/projects/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_project_appears_in_correct_column(self, auth_client, project):
        client, _ = auth_client
        response = client.get('/dashboard/projects/')
        ctx = response.context
        funded_col = next(c for c in ctx['columns'] if c['state'] == Project.State.FUNDED)
        names = [card['project'].name for card in funded_col['projects']]
        assert project.name in names

    def test_all_six_columns_present(self, auth_client):
        client, _ = auth_client
        response = client.get('/dashboard/projects/')
        ctx = response.context
        states = [c['state'] for c in ctx['columns']]
        expected = [
            Project.State.PROSPECTIVE, Project.State.PROGRAMMED, Project.State.FUNDED,
            Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION, Project.State.COMPLETED,
        ]
        for s in expected:
            assert s in states
        assert len(states) == 6

    def test_filter_by_program(self, auth_client, project, program):
        client, _ = auth_client
        response = client.get(f'/dashboard/projects/?program={program.pk}')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['total_projects'] >= 1

    def test_filter_by_council_excludes_others(self, auth_client, project):
        client, _ = auth_client
        other = Council.objects.create(name='Other Board Council', region='NSW')
        response = client.get(f'/dashboard/projects/?council={other.pk}')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['total_projects'] == 0

    def test_filter_by_financial_year(self, auth_client, project):
        client, _ = auth_client
        response = client.get('/dashboard/projects/?financial_year=2025-2026')
        ctx = response.context
        assert ctx['total_projects'] >= 1

    def test_card_has_total_funding(self, auth_client, project, funding_schedule):
        client, _ = auth_client
        response = client.get('/dashboard/projects/')
        ctx = response.context
        funded_col = next(c for c in ctx['columns'] if c['state'] == Project.State.FUNDED)
        card = next((c for c in funded_col['projects'] if c['project'] == project), None)
        assert card is not None
        assert card['total_funding'] == Decimal('300000')

    def test_overdue_card_flagged(self, auth_client, council, program):
        client, _ = auth_client
        Project.objects.create(
            name='Overdue Board Project', council=council, program=program,
            state=Project.State.COMMENCED,
            financial_year='2024-2025',
            completion_date=date(2020, 1, 1),
        )
        response = client.get('/dashboard/projects/')
        ctx = response.context
        commenced_col = next(c for c in ctx['columns'] if c['state'] == Project.State.COMMENCED)
        overdue_cards = [c for c in commenced_col['projects'] if c['overdue']]
        assert len(overdue_cards) >= 1

    def test_project_with_no_completion_date_not_overdue(self, auth_client, project):
        client, _ = auth_client
        response = client.get('/dashboard/projects/')
        ctx = response.context
        funded_col = next(c for c in ctx['columns'] if c['state'] == Project.State.FUNDED)
        card = next((c for c in funded_col['projects'] if c['project'] == project), None)
        assert card is not None
        assert card['days_left'] is None
        assert card['overdue'] is False


# ===========================================================================
# Issue #25 — Financial traceability
# ===========================================================================

@pytest.mark.django_db
class TestTraceabilityView:
    def test_get_no_council_returns_200(self, auth_client):
        client, _ = auth_client
        response = client.get('/dashboard/traceability/')
        assert response.status_code == 200

    def test_requires_login(self):
        response = Client().get('/dashboard/traceability/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_council_picker_shown_without_param(self, auth_client, council):
        client, _ = auth_client
        response = client.get('/dashboard/traceability/')
        assert council.name.encode() in response.content

    def test_agreement_shown_for_council(self, auth_client, council, funding_agreement):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        assert response.status_code == 200
        assert b'Dash Agreement' in response.content

    def test_schedule_shown_under_agreement(self, auth_client, council, funding_agreement, funding_schedule):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        assert len(ctx['chain']) == 1
        assert len(ctx['chain'][0]['schedules']) == 1

    def test_payments_shown_in_chain(self, auth_client, council, funding_agreement, released_payment):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        srow = ctx['chain'][0]['schedules'][0]
        assert len(srow['payments']) == 1
        assert srow['payments'][0].amount == Decimal('180000')

    def test_pct_expended_calculated(self, auth_client, council, funding_agreement, released_payment):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        srow = ctx['chain'][0]['schedules'][0]
        # 180000 / 300000 = 60%
        assert srow['pct_expended'] == 60.0

    def test_grand_totals_aggregated(self, auth_client, council, funding_agreement, released_payment):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        assert ctx['grand_total'] == Decimal('300000')
        assert ctx['grand_paid'] == Decimal('180000')
        assert ctx['grand_remaining'] == Decimal('120000')
        assert ctx['grand_pct'] == 60.0

    def test_no_agreements_shows_empty_state(self, auth_client):
        client, _ = auth_client
        empty = Council.objects.create(name='Empty Council', region='VIC')
        response = client.get(f'/dashboard/traceability/?council={empty.pk}')
        assert response.status_code == 200
        assert b'No funding agreements' in response.content

    def test_allocations_shown_in_chain(self, auth_client, council, funding_agreement, funding_schedule, project):
        client, _ = auth_client
        WorkFunding.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            cost_centre='316001',
            amount=Decimal('300000'),
        )
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        srow = ctx['chain'][0]['schedules'][0]
        assert len(srow['allocations']) == 1
        assert srow['allocations'][0].cost_centre == '316001'

    def test_running_totals_at_agreement_level(self, auth_client, council, funding_agreement,
                                                released_payment, approved_payment):
        client, _ = auth_client
        response = client.get(f'/dashboard/traceability/?council={council.pk}')
        ctx = response.context
        agreement_row = ctx['chain'][0]
        assert agreement_row['total'] == Decimal('300000')
        # only RELEASED counts as paid
        assert agreement_row['paid'] == Decimal('180000')
        assert agreement_row['pct_expended'] == 60.0
