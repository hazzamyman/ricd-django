"""
End-to-end integration tests for the complete RICD payment workflow.

Issue #30 — Two tracks:
  * Schedule track: BFA → FundingAgreement → PaymentRule → FundingSchedule →
                    Payments → StageReports → COMPLETED
  * Notice track:   FundingNotice → ExpenseClaim (cap enforcement) → CLOSED

Tests use real models, signals, and business rules — no mocking.
"""
import pytest
from decimal import Decimal
from datetime import date

from django.core.exceptions import ValidationError

from apps.core.models import (
    Approval,
    BriefFinancialApproval,
    Council,
    ExpenseClaim,
    FundingAgreement,
    FundingNotice,
    FundingSchedule,
    Payment,
    PaymentRule,
    Program,
    Project,
    StageReport,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_council(name='E2E Council', region='QLD'):
    return Council.objects.create(name=name, region=region)


def _make_program(name='E2E Program'):
    return Program.objects.create(
        name=name,
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('10000000'),
    )


def _make_project(council, program, name='E2E Project'):
    return Project.objects.create(
        name=name,
        council=council,
        program=program,
        state=Project.State.FUNDED,
        financial_year='2025-2026',
    )


def _make_payment_rule(name='Standard Split'):
    return PaymentRule.objects.create(
        name=name,
        rule_type='SPLIT',
        config_json={'percentages': [30, 60, 10]},
        version=1,
    )


def _make_funding_schedule(project, agreement=None, rule=None, amount=Decimal('300000')):
    """Create a FundingSchedule in EXECUTED status (ready for first payment)."""
    if rule is None:
        rule = _make_payment_rule()
    return FundingSchedule.objects.create(
        project=project,
        funding_agreement=agreement,
        payment_rule=rule,
        amount=amount,
        contingency=Decimal('0'),
        total_funding=amount,
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
        status=FundingSchedule.Status.EXECUTED,
    )


def _make_payment(project, schedule, amount, ptype=Payment.PaymentType.FIRST):
    """Create a Payment and return it with its auto-created Approval."""
    payment = Payment.objects.create(
        project=project,
        funding_schedule=schedule,
        payment_type=ptype,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
        amount=amount,
        status=Payment.Status.PENDING,
    )
    approval = Approval.objects.filter(
        entity_type='Payment',
        entity_id=payment.pk,
    ).first()
    return payment, approval


# ===========================================================================
# Schedule Track
# ===========================================================================

@pytest.mark.django_db
class TestScheduleTrack:
    """
    Full lifecycle from BFA approval through three milestone payments to
    FundingSchedule COMPLETED.
    """

    def test_bfa_pending_to_approved(self):
        council = _make_council()
        program = _make_program()
        project = _make_project(council, program)

        bfa = BriefFinancialApproval.objects.create(
            project=project,
            funding_amount=Decimal('300000'),
            delegate_level=BriefFinancialApproval.DelegateLevel.MANAGER,
            status=BriefFinancialApproval.Status.PENDING,
        )
        assert bfa.status == BriefFinancialApproval.Status.PENDING

        bfa.status = BriefFinancialApproval.Status.APPROVED
        bfa.save()
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.APPROVED

    def test_funding_schedule_draft_to_executed(self):
        council = _make_council()
        project = _make_project(council, _make_program())
        agreement = FundingAgreement.objects.create(
            council=council,
            name='E2E Agreement',
            status=FundingAgreement.Status.ACTIVE,
        )
        rule = _make_payment_rule()

        fs = FundingSchedule.objects.create(
            project=project,
            funding_agreement=agreement,
            payment_rule=rule,
            amount=Decimal('300000'),
            contingency=Decimal('0'),
            total_funding=Decimal('300000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.DRAFT,
        )
        assert fs.status == FundingSchedule.Status.DRAFT

        fs.status = FundingSchedule.Status.READY_FOR_EXECUTION
        fs.save()
        fs.refresh_from_db()
        assert fs.status == FundingSchedule.Status.READY_FOR_EXECUTION

        fs.status = FundingSchedule.Status.EXECUTED
        fs.save()
        fs.refresh_from_db()
        assert fs.status == FundingSchedule.Status.EXECUTED

    def test_payment_created_auto_generates_approval(self):
        council = _make_council()
        project = _make_project(council, _make_program())
        schedule = _make_funding_schedule(project)

        payment, approval = _make_payment(project, schedule, Decimal('90000'))

        assert approval is not None, "Approval should be auto-created on Payment creation"
        assert approval.entity_type == 'Payment'
        assert approval.entity_id == payment.pk
        assert approval.status == Approval.Status.PENDING

    def test_approval_approved_triggers_payment_approved(self):
        council = _make_council()
        project = _make_project(council, _make_program())
        schedule = _make_funding_schedule(project)

        payment, approval = _make_payment(project, schedule, Decimal('90000'))

        assert approval is not None
        approval.status = Approval.Status.APPROVED
        approval.save()

        payment.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED

    def test_payment_approved_activates_executed_schedule(self):
        council = _make_council()
        project = _make_project(council, _make_program())
        schedule = _make_funding_schedule(project)  # status=EXECUTED

        assert schedule.status == FundingSchedule.Status.EXECUTED

        payment, approval = _make_payment(project, schedule, Decimal('90000'))
        approval.status = Approval.Status.APPROVED
        approval.save()

        schedule.refresh_from_db()
        assert schedule.status == FundingSchedule.Status.ACTIVE

    def test_full_bfa_to_completion(self):
        """
        Complete lifecycle:
          BFA APPROVED → FS EXECUTED → 3 payments released → FS COMPLETED
        """
        council = _make_council()
        program = _make_program()
        project = _make_project(council, program)

        # BFA
        bfa = BriefFinancialApproval.objects.create(
            project=project,
            funding_amount=Decimal('300000'),
            delegate_level=BriefFinancialApproval.DelegateLevel.MANAGER,
            status=BriefFinancialApproval.Status.APPROVED,
        )
        assert bfa.status == BriefFinancialApproval.Status.APPROVED

        # Agreement
        agreement = FundingAgreement.objects.create(
            council=council,
            name='Completion Agreement',
            status=FundingAgreement.Status.ACTIVE,
            execution_date=date(2025, 1, 15),
        )

        # Schedule (DRAFT → READY → EXECUTED)
        rule = _make_payment_rule()
        schedule = FundingSchedule.objects.create(
            project=project,
            funding_agreement=agreement,
            payment_rule=rule,
            amount=Decimal('300000'),
            contingency=Decimal('0'),
            total_funding=Decimal('300000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.DRAFT,
        )
        schedule.status = FundingSchedule.Status.READY_FOR_EXECUTION
        schedule.save()
        schedule.status = FundingSchedule.Status.EXECUTED
        schedule.save()
        schedule.refresh_from_db()
        assert schedule.status == FundingSchedule.Status.EXECUTED

        # --- Payment 1: FIRST (30%) ---
        pmt1, appr1 = _make_payment(project, schedule, Decimal('90000'), Payment.PaymentType.FIRST)
        assert appr1 is not None
        appr1.status = Approval.Status.APPROVED
        appr1.save()

        pmt1.refresh_from_db()
        assert pmt1.status == Payment.Status.APPROVED

        schedule.refresh_from_db()
        assert schedule.status == FundingSchedule.Status.ACTIVE

        pmt1.status = Payment.Status.RELEASED
        pmt1.release_date = date(2025, 3, 1)
        pmt1.save()
        pmt1.refresh_from_db()
        assert pmt1.status == Payment.Status.RELEASED

        # --- Stage 1 Report ---
        sr1 = StageReport.objects.create(
            project=project,
            funding_schedule=schedule,
            stage_type=StageReport.StageType.STAGE1,
            status=StageReport.Status.DRAFT,
        )
        sr1.status = StageReport.Status.SUBMITTED
        sr1.save()
        sr1.status = StageReport.Status.ENDORSED
        sr1.save()
        sr1.status = StageReport.Status.ASSESSED
        sr1.save()
        sr1.status = StageReport.Status.APPROVED
        sr1.save()
        sr1.refresh_from_db()
        assert sr1.status == StageReport.Status.APPROVED

        # --- Payment 2: SECOND (60%) ---
        pmt2, appr2 = _make_payment(project, schedule, Decimal('180000'), Payment.PaymentType.SECOND)
        assert appr2 is not None
        appr2.status = Approval.Status.APPROVED
        appr2.save()

        pmt2.refresh_from_db()
        assert pmt2.status == Payment.Status.APPROVED

        pmt2.status = Payment.Status.RELEASED
        pmt2.release_date = date(2025, 9, 1)
        pmt2.save()

        # --- Stage 2 Report ---
        sr2 = StageReport.objects.create(
            project=project,
            funding_schedule=schedule,
            stage_type=StageReport.StageType.STAGE2,
            status=StageReport.Status.DRAFT,
        )
        sr2.status = StageReport.Status.APPROVED
        sr2.save()
        sr2.refresh_from_db()
        assert sr2.status == StageReport.Status.APPROVED

        # --- Payment 3: THIRD (10%) ---
        pmt3, appr3 = _make_payment(project, schedule, Decimal('30000'), Payment.PaymentType.THIRD)
        assert appr3 is not None
        appr3.status = Approval.Status.APPROVED
        appr3.save()

        pmt3.refresh_from_db()
        assert pmt3.status == Payment.Status.APPROVED

        pmt3.status = Payment.Status.RELEASED
        pmt3.release_date = date(2025, 12, 1)
        pmt3.save()

        # --- FS → COMPLETED ---
        schedule.status = FundingSchedule.Status.COMPLETED
        schedule.save()
        schedule.refresh_from_db()
        assert schedule.status == FundingSchedule.Status.COMPLETED

        # Final tally
        released = Payment.objects.filter(
            funding_schedule=schedule,
            status=Payment.Status.RELEASED,
        )
        assert released.count() == 3
        assert sum(p.amount for p in released) == Decimal('300000')

    def test_variation_supersedes_schedule(self):
        """A replacement schedule marks the original as SUPERSEDED."""
        council = _make_council()
        project = _make_project(council, _make_program())
        agreement = FundingAgreement.objects.create(
            council=council,
            name='Variation Agreement',
            status=FundingAgreement.Status.ACTIVE,
        )

        original = _make_funding_schedule(project, agreement=agreement, amount=Decimal('200000'))
        assert original.status == FundingSchedule.Status.EXECUTED

        # Approve first payment → original becomes ACTIVE
        pmt, appr = _make_payment(project, original, Decimal('60000'), Payment.PaymentType.FIRST)
        appr.status = Approval.Status.APPROVED
        appr.save()
        original.refresh_from_db()
        assert original.status == FundingSchedule.Status.ACTIVE

        # Create replacement schedule
        rule = _make_payment_rule('Replacement Rule')
        replacement = FundingSchedule.objects.create(
            project=project,
            funding_agreement=agreement,
            payment_rule=rule,
            amount=Decimal('250000'),
            contingency=Decimal('0'),
            total_funding=Decimal('250000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD,
            status=FundingSchedule.Status.EXECUTED,
            replaces_schedule=original,
        )
        assert replacement.replaces_schedule_id == original.pk

        # Supersede the original
        original.status = FundingSchedule.Status.SUPERSEDED
        original.save()
        original.refresh_from_db()
        assert original.status == FundingSchedule.Status.SUPERSEDED

        # Replacement can be activated by its own payment
        pmt2, appr2 = _make_payment(project, replacement, Decimal('75000'), Payment.PaymentType.FIRST)
        appr2.status = Approval.Status.APPROVED
        appr2.save()
        replacement.refresh_from_db()
        assert replacement.status == FundingSchedule.Status.ACTIVE


# ===========================================================================
# Notice Track
# ===========================================================================

@pytest.mark.django_db
class TestNoticeTrack:
    """FundingNotice + ExpenseClaim cap enforcement lifecycle."""

    def _setup(self, suffix=''):
        council = _make_council(f'Notice Council{suffix}')
        program = _make_program(f'Notice Program{suffix}')
        project = _make_project(council, program, f'Notice Project{suffix}')
        return project

    def test_funding_notice_open_to_closed(self):
        project = self._setup()
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('50000'),
            issued_date=date(2025, 3, 1),
            status=FundingNotice.Status.OPEN,
        )
        assert notice.status == FundingNotice.Status.OPEN

        # Approve a claim within cap
        claim = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('30000'),
            date_submitted=date(2025, 4, 1),
            status=ExpenseClaim.Status.DRAFT,
        )
        claim.status = ExpenseClaim.Status.SUBMITTED
        claim.save()
        claim.status = ExpenseClaim.Status.APPROVED
        claim.full_clean()
        claim.save()
        claim.refresh_from_db()
        assert claim.status == ExpenseClaim.Status.APPROVED

        # Close the notice
        notice.status = FundingNotice.Status.CLOSED
        notice.save()
        notice.refresh_from_db()
        assert notice.status == FundingNotice.Status.CLOSED

    def test_expense_claim_cap_enforcement(self):
        """A claim that would exceed the capped amount raises ValidationError."""
        project = self._setup('Cap')
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('50000'),
            issued_date=date(2025, 3, 1),
            status=FundingNotice.Status.OPEN,
        )

        # First claim approved within cap
        ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('40000'),
            date_submitted=date(2025, 4, 1),
            status=ExpenseClaim.Status.APPROVED,
        )

        # Second claim would push total to 60k > cap of 50k
        claim2 = ExpenseClaim(
            funding_notice=notice,
            amount=Decimal('20000'),
            date_submitted=date(2025, 5, 1),
            status=ExpenseClaim.Status.SUBMITTED,
        )
        with pytest.raises(ValidationError, match='exceed notice cap'):
            claim2.full_clean()

    def test_expense_claim_draft_skips_cap_check(self):
        """DRAFT claims bypass the cap check."""
        project = self._setup('Draft')
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('10000'),
            issued_date=date(2025, 3, 1),
            status=FundingNotice.Status.OPEN,
        )

        claim = ExpenseClaim(
            funding_notice=notice,
            amount=Decimal('999999'),
            date_submitted=date(2025, 4, 1),
            status=ExpenseClaim.Status.DRAFT,
        )
        claim.full_clean()  # must not raise

    def test_multiple_approved_claims_accumulate_against_cap(self):
        """The cap check sums all existing APPROVED claims."""
        project = self._setup('Multi')
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('100000'),
            issued_date=date(2025, 3, 1),
            status=FundingNotice.Status.OPEN,
        )

        # Three claims that together hit the cap exactly
        for amount in [Decimal('30000'), Decimal('40000'), Decimal('30000')]:
            ExpenseClaim.objects.create(
                funding_notice=notice,
                amount=amount,
                date_submitted=date(2025, 4, 1),
                status=ExpenseClaim.Status.APPROVED,
            )

        # Any further non-DRAFT claim must fail
        overflow = ExpenseClaim(
            funding_notice=notice,
            amount=Decimal('1'),
            date_submitted=date(2025, 5, 1),
            status=ExpenseClaim.Status.SUBMITTED,
        )
        with pytest.raises(ValidationError, match='exceed notice cap'):
            overflow.full_clean()
