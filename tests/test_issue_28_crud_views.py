"""
Tests for issue #28 — CRUD view test suite completeness.

Fills the two gaps not covered by earlier per-issue test files:
  1. Unauthenticated redirect tests for all endpoints that were missing them.
  2. Business-rule rejection tests (BFA missing, PaymentRule immutability).

All entity CRUD operations (200 / create / edit / delete) are covered in:
  test_ui_crud_pages.py, test_funding_agreement_crud.py,
  test_funding_notice_crud.py, test_bfa_crud.py, test_land_crud.py,
  test_issue_15_18_19.py, test_issue_16_17_20.py.
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import (
    Council, Program, Project, FundingSchedule, BriefFinancialApproval,
    Variation, Payment, StageReport, QuarterlyReport,
    PaymentRule, Profile,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council():
    return Council.objects.create(name='Issue28 Council', region='QLD')


@pytest.fixture
def program(council):
    return Program.objects.create(
        name='Issue28 Program',
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('1000000'),
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        name='Issue28 Project', council=council, program=program,
        state=Project.State.PROSPECTIVE, financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(project):
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('200000'),
        contingency=Decimal('0'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
    )


@pytest.fixture
def variation(funding_schedule):
    return Variation.objects.create(
        funding_schedule=funding_schedule,
        variation_option=Variation.VariationOption.OPTION_1_ADD_FS,
        status=Variation.Status.DRAFT,
        description='Issue28 variation',
    )


@pytest.fixture
def payment(project, funding_schedule):
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        payment_type=Payment.PaymentType.FIRST,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        status=Payment.Status.PENDING,
    )


@pytest.fixture
def stage_report(project, funding_schedule):
    return StageReport.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        stage_type=StageReport.StageType.STAGE1,
        status=StageReport.Status.DRAFT,
    )


@pytest.fixture
def quarterly_report(project):
    # QuarterlyReport was refactored to be per-council (not per-project) — see migration 0010
    return QuarterlyReport.objects.create(
        council=project.council,
        year=2025,
        quarter=1,
    )


# ---------------------------------------------------------------------------
# Issue #28 — Unauthenticated redirect tests (the gap)
# Entities covered here are the ones NOT covered in earlier test files.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUnauthenticatedRedirectsFundingSchedules:
    def test_list(self):
        response = Client().get('/funding-schedules/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_create(self):
        response = Client().get('/funding-schedules/create/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_detail(self, funding_schedule):
        response = Client().get(f'/funding-schedules/{funding_schedule.pk}/')
        assert response.status_code == 302

    def test_edit(self, funding_schedule):
        response = Client().get(f'/funding-schedules/{funding_schedule.pk}/edit/')
        assert response.status_code == 302

    def test_delete(self, funding_schedule):
        response = Client().post(f'/funding-schedules/{funding_schedule.pk}/delete/')
        assert response.status_code == 302

    def test_mark_ready(self, funding_schedule):
        response = Client().post(f'/funding-schedules/{funding_schedule.pk}/mark-ready/')
        assert response.status_code == 302

    def test_cancel(self, funding_schedule):
        response = Client().post(f'/funding-schedules/{funding_schedule.pk}/cancel/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestUnauthenticatedRedirectsVariations:
    def test_list(self):
        response = Client().get('/variations/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_create(self):
        response = Client().get('/variations/create/')
        assert response.status_code == 302

    def test_detail(self, variation):
        response = Client().get(f'/variations/{variation.pk}/')
        assert response.status_code == 302

    def test_edit(self, variation):
        response = Client().get(f'/variations/{variation.pk}/edit/')
        assert response.status_code == 302

    def test_delete(self, variation):
        response = Client().post(f'/variations/{variation.pk}/delete/')
        assert response.status_code == 302

    def test_execute(self, variation):
        response = Client().post(f'/variations/{variation.pk}/execute/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestUnauthenticatedRedirectsPayments:
    def test_list(self, project):
        response = Client().get(f'/projects/{project.pk}/payments/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_create(self, project):
        response = Client().get(f'/projects/{project.pk}/payments/create/')
        assert response.status_code == 302

    def test_detail(self, project, payment):
        response = Client().get(f'/projects/{project.pk}/payments/{payment.pk}/')
        assert response.status_code == 302

    def test_edit(self, project, payment):
        response = Client().get(f'/projects/{project.pk}/payments/{payment.pk}/edit/')
        assert response.status_code == 302

    def test_recommend(self, project, payment):
        response = Client().post(f'/projects/{project.pk}/payments/{payment.pk}/recommend/')
        assert response.status_code == 302

    def test_approve(self, project, payment):
        response = Client().post(f'/projects/{project.pk}/payments/{payment.pk}/approve/')
        assert response.status_code == 302

    def test_release(self, project, payment):
        response = Client().post(f'/projects/{project.pk}/payments/{payment.pk}/release/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestUnauthenticatedRedirectsStageReports:
    def test_list(self, project):
        response = Client().get(f'/projects/{project.pk}/stage-reports/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_create(self, project):
        response = Client().get(f'/projects/{project.pk}/stage-reports/create/')
        assert response.status_code == 302

    def test_detail(self, project, stage_report):
        response = Client().get(f'/projects/{project.pk}/stage-reports/{stage_report.pk}/')
        assert response.status_code == 302

    def test_edit(self, project, stage_report):
        response = Client().get(f'/projects/{project.pk}/stage-reports/{stage_report.pk}/edit/')
        assert response.status_code == 302

    def test_endorse(self, project, stage_report):
        response = Client().post(f'/projects/{project.pk}/stage-reports/{stage_report.pk}/endorse/')
        assert response.status_code == 302

    def test_assess(self, project, stage_report):
        response = Client().post(f'/projects/{project.pk}/stage-reports/{stage_report.pk}/assess/')
        assert response.status_code == 302

    def test_approve(self, project, stage_report):
        response = Client().post(f'/projects/{project.pk}/stage-reports/{stage_report.pk}/approve/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestUnauthenticatedRedirectsQuarterlyReports:
    def test_list(self, project):
        response = Client().get(f'/projects/{project.pk}/quarterly-reports/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_create(self, project):
        response = Client().get(f'/projects/{project.pk}/quarterly-reports/create/')
        assert response.status_code == 302

    def test_detail(self, project, quarterly_report):
        response = Client().get(f'/projects/{project.pk}/quarterly-reports/{quarterly_report.pk}/')
        assert response.status_code == 302

    def test_edit(self, project, quarterly_report):
        response = Client().get(f'/projects/{project.pk}/quarterly-reports/{quarterly_report.pk}/edit/')
        assert response.status_code == 302

    def test_delete(self, project, quarterly_report):
        response = Client().post(f'/projects/{project.pk}/quarterly-reports/{quarterly_report.pk}/delete/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Issue #28 — Business rule rejection tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBusinessRuleBFAMissing:
    """FundingSchedule.clean() blocks any new schedule when no approved BFA exists.

    Order of checks in clean():
      1. payment_rule required for non-DRAFT  (bypassed here by using DRAFT)
      2. approved BFA required for all new records  (the check we're testing)
    """

    def test_no_bfa_raises_on_full_clean(self, project):
        from django.core.exceptions import ValidationError
        # DRAFT bypasses the payment_rule guard so we reach the BFA check.
        fs = FundingSchedule(
            project=project,
            amount=Decimal('100000'),
            contingency=Decimal('0'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.DRAFT,
        )
        with pytest.raises(ValidationError, match='BriefFinancialApproval'):
            fs.full_clean()

    def test_approved_bfa_allows_full_clean(self, project):
        from tests.fixtures import make_bfa
        make_bfa(project, Decimal('500000'), status=BriefFinancialApproval.Status.APPROVED)
        fs = FundingSchedule(
            project=project,
            amount=Decimal('100000'),
            contingency=Decimal('0'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.DRAFT,
        )
        fs.full_clean()  # must not raise

    def test_pending_bfa_is_not_sufficient(self, project):
        """A BFA in PENDING (not APPROVED) does not satisfy the pre-condition."""
        from django.core.exceptions import ValidationError
        from tests.fixtures import make_bfa
        make_bfa(project, Decimal('500000'), status=BriefFinancialApproval.Status.PENDING)
        fs = FundingSchedule(
            project=project,
            amount=Decimal('100000'),
            contingency=Decimal('0'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.DRAFT,
        )
        with pytest.raises(ValidationError, match='BriefFinancialApproval'):
            fs.full_clean()


@pytest.mark.django_db
class TestBusinessRulePaymentRuleImmutability:
    """PaymentRule raises if modified after being linked to a FundingSchedule."""

    def test_unlinked_rule_can_be_updated(self):
        rule = PaymentRule.objects.create(
            name='Editable Rule',
            rule_type=PaymentRule.RuleType.SPLIT,
            config_json={'milestones': [
                {'name': 'S1', 'trigger': 'report', 'percentage': 60},
                {'name': 'S2', 'trigger': 'complete', 'percentage': 40},
            ]},
            version=1,
        )
        rule.name = 'Renamed'
        rule.save()
        rule.refresh_from_db()
        assert rule.name == 'Renamed'

    def test_linked_rule_cannot_be_updated(self, project):
        from django.core.exceptions import ValidationError
        rule = PaymentRule.objects.create(
            name='Locked Rule',
            rule_type=PaymentRule.RuleType.SPLIT,
            config_json={'milestones': [
                {'name': 'S1', 'trigger': 'report', 'percentage': 60},
                {'name': 'S2', 'trigger': 'complete', 'percentage': 40},
            ]},
            version=1,
        )
        FundingSchedule.objects.create(
            project=project,
            payment_rule=rule,
            amount=Decimal('100000'),
            contingency=Decimal('0'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
        )
        # Immutability is enforced in clean(), so full_clean() must raise.
        rule.name = 'Should not save'
        with pytest.raises(ValidationError, match='immutable'):
            rule.full_clean()

    # NOTE: test_payment_rule_has_no_edit_url removed — PR 1 added CRUD endpoints
    # for PaymentRule with is_locked guard. The edit URL exists; immutability is
    # enforced in PaymentRule.clean() while the rule is referenced by a schedule.


@pytest.mark.django_db
class TestBusinessRuleWorkFundingXOR:
    """WorkFunding must target project OR work — not both, not neither."""

    def test_both_raises(self, project, funding_schedule):
        from django.core.exceptions import ValidationError
        from apps.core.models import WorkFunding, WorkType, Work
        wt = WorkType.objects.create(name='RoadXOR')
        work = Work.objects.create(project=project, work_type=wt)
        wf = WorkFunding(
            funding_schedule=funding_schedule, project=project,
            work=work, amount=Decimal('1000'),
        )
        with pytest.raises(ValidationError):
            wf.full_clean()

    def test_neither_raises(self, funding_schedule):
        from django.core.exceptions import ValidationError
        from apps.core.models import WorkFunding
        wf = WorkFunding(funding_schedule=funding_schedule, amount=Decimal('1000'))
        with pytest.raises(ValidationError):
            wf.full_clean()
