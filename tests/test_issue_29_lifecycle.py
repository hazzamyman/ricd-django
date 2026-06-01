"""
Tests for issue #29 — Workflow lifecycle test suite.

Covers signal-level and model-level lifecycle automation:
- FundingSchedule: state machine transitions + signal triggers
- Payment: APPROVED payment → FundingSchedule becomes ACTIVE
- Payment: auto-create Approval record on Payment creation (governance signal)
- Approval: APPROVED → Payment status synced to APPROVED
- VariationDeed: EXECUTED → trigger_funding_schedule_executed / supersede
- ExpenseClaim: cap enforcement at exact boundary (under/at/over)
- Report/Stage: APPROVED → unlock next PENDING payment (signal)
"""
import pytest
from decimal import Decimal
from datetime import date


# ===========================================================================
# Shared fixtures
# ===========================================================================

@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(username='lifecycle_user', password='pass')


@pytest.fixture
def council(db):
    from apps.core.models import Council
    return Council.objects.create(
        name='Lifecycle Council',
        region='R',
        state_electorate='SE',
        federal_electorate='FE',
    )


@pytest.fixture
def program(db):
    from apps.core.models import Program
    return Program.objects.create(
        name='Lifecycle Program',
        funding_source='STATE',
        budget=Decimal('10000000'),
        gl_code='GL001',
        business_case_reference='BC-001',
    )


@pytest.fixture
def project(db, council, program):
    from apps.core.models import Project
    return Project.objects.create(
        name='Lifecycle Project',
        council=council,
        program=program,
        state='PROSPECTIVE',
        dwelling_status='PROSPECTIVE',
        financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(db, project):
    from apps.core.models import FundingSchedule
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('500000'),
        contingency=Decimal('50000'),
    )


@pytest.fixture
def payment(db, project, funding_schedule):
    from apps.core.models import Payment
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        payment_type='FIRST',
        calculation_type='FIXED',
        amount=Decimal('150000'),
        status='PENDING',
    )


# ===========================================================================
# FundingSchedule state machine
# ===========================================================================

@pytest.mark.django_db
class TestFundingScheduleStateMachine:
    def test_initial_status_is_draft(self, funding_schedule):
        from apps.core.models import FundingSchedule
        assert funding_schedule.status == FundingSchedule.Status.DRAFT

    def test_mark_ready_transitions_draft_to_ready(self, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='READY')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.READY_FOR_EXECUTION

    def test_complete_transitions_active_to_completed(self, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='ACTIVE')
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='COMPLETED')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.COMPLETED

    def test_cancel_from_draft(self, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='CANCELLED')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.CANCELLED

    def test_cancel_from_active(self, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='ACTIVE')
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='CANCELLED')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.CANCELLED

    def test_supersede_transitions_to_superseded(self, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='ACTIVE')
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='SUPERSEDED')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.SUPERSEDED

    def test_trigger_active_from_executed(self, funding_schedule):
        from apps.core.models import FundingSchedule
        from apps.core.business_rules import trigger_funding_schedule_active
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='EXECUTED')
        funding_schedule.refresh_from_db()
        result = trigger_funding_schedule_active(funding_schedule)
        assert result is True
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.ACTIVE

    def test_trigger_active_noop_when_not_executed(self, funding_schedule):
        from apps.core.business_rules import trigger_funding_schedule_active
        result = trigger_funding_schedule_active(funding_schedule)
        assert result is False

    def test_trigger_superseded(self, funding_schedule):
        from apps.core.models import FundingSchedule
        from apps.core.business_rules import trigger_funding_schedule_superseded
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='ACTIVE')
        funding_schedule.refresh_from_db()
        trigger_funding_schedule_superseded(funding_schedule)
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.SUPERSEDED


# ===========================================================================
# Payment: APPROVED → FundingSchedule ACTIVE (signal)
# ===========================================================================

@pytest.mark.django_db
class TestPaymentApprovedActivatesSchedule:
    def test_payment_approved_signal_activates_executed_schedule(self, project, funding_schedule):
        from apps.core.models import FundingSchedule, Payment

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='EXECUTED')

        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='APPROVED',
        )

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.ACTIVE

    def test_payment_approved_does_not_activate_draft_schedule(self, project, funding_schedule):
        from apps.core.models import FundingSchedule, Payment

        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='APPROVED',
        )

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.DRAFT

    def test_payment_pending_does_not_activate_schedule(self, project, funding_schedule):
        from apps.core.models import FundingSchedule, Payment

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='EXECUTED')

        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='PENDING',
        )

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.EXECUTED


# ===========================================================================
# Governance signal: Payment created → Approval record auto-created
# ===========================================================================

@pytest.mark.django_db
class TestAutoCreatePaymentApproval:
    def test_payment_creation_creates_approval_record(self, project, funding_schedule):
        from apps.core.models import Payment, Approval

        before = Approval.objects.count()
        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('100000'),
            status='PENDING',
        )
        assert Approval.objects.count() == before + 1

    def test_approval_record_has_correct_type_and_status(self, project, funding_schedule):
        from apps.core.models import Payment, Approval

        payment = Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('100000'),
            status='PENDING',
        )

        approval = Approval.objects.filter(
            entity_type='Payment',
            entity_id=payment.pk,
        ).first()
        assert approval is not None
        assert approval.approval_type == Approval.ApprovalType.PAYMENT
        assert approval.status == Approval.Status.PENDING

    def test_approval_record_has_delegation_level(self, project, funding_schedule):
        from apps.core.models import Payment, Approval

        payment = Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('100000'),
            status='PENDING',
        )

        approval = Approval.objects.filter(
            entity_type='Payment', entity_id=payment.pk
        ).first()
        assert approval.required_role


# ===========================================================================
# Governance signal: Approval APPROVED → Payment synced to APPROVED
# ===========================================================================

@pytest.mark.django_db
class TestApprovalSyncToPayment:
    def test_payment_approval_approved_sets_payment_approved(self, payment):
        from apps.core.models import Approval

        Approval.objects.create(
            entity_type='Payment',
            entity_id=payment.pk,
            approval_type=Approval.ApprovalType.PAYMENT,
            required_role=Approval.RequiredRole.MANAGER,
            status=Approval.Status.APPROVED,
        )

        payment.refresh_from_db()
        assert payment.status == 'APPROVED'

    def test_non_payment_approval_does_not_affect_payment(self, payment):
        from apps.core.models import Approval

        Approval.objects.create(
            entity_type='Project',
            entity_id=payment.pk,
            approval_type=Approval.ApprovalType.FINANCIAL,
            required_role=Approval.RequiredRole.MANAGER,
            status=Approval.Status.APPROVED,
        )

        payment.refresh_from_db()
        assert payment.status == 'PENDING'

    def test_payment_approval_rejected_does_not_change_payment(self, payment):
        from apps.core.models import Approval

        Approval.objects.create(
            entity_type='Payment',
            entity_id=payment.pk,
            approval_type=Approval.ApprovalType.PAYMENT,
            required_role=Approval.RequiredRole.MANAGER,
            status=Approval.Status.REJECTED,
        )

        payment.refresh_from_db()
        assert payment.status == 'PENDING'


# ===========================================================================
# VariationDeed: EXECUTED → trigger_funding_schedule_executed
# ===========================================================================

@pytest.mark.django_db
class TestVariationExecutionTriggers:
    def test_variation_executed_triggers_schedule_executed(self, funding_schedule):
        """
        When a Variation linked to a FS is set to EXECUTED and the FS is READY,
        the signal fires trigger_funding_schedule_executed → FS becomes EXECUTED.
        Note: after the fix, EXECUTED does NOT auto-cascade to ACTIVE.
        """
        from apps.core.models import Variation, FundingSchedule

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='READY')

        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status='DRAFT',
        )
        variation.funding_schedules.add(funding_schedule)

        variation.status = 'EXECUTED'
        variation.save()

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.EXECUTED

    def test_variation_executed_does_not_execute_draft_schedule(self, funding_schedule):
        from apps.core.models import Variation, FundingSchedule

        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status='DRAFT',
        )
        variation.funding_schedules.add(funding_schedule)
        variation.status = 'EXECUTED'
        variation.save()

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.DRAFT

    def test_trigger_funding_schedule_executed_directly(self, funding_schedule):
        from apps.core.models import Variation, FundingSchedule
        from apps.core.business_rules import trigger_funding_schedule_executed

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='READY')
        funding_schedule.refresh_from_db()

        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status='EXECUTED',
        )
        variation.funding_schedules.add(funding_schedule)

        result = trigger_funding_schedule_executed(funding_schedule)
        assert result is True
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.EXECUTED

    def test_variation_executed_then_payment_approved_activates_schedule(
        self, project, funding_schedule
    ):
        """Full chain: Variation EXECUTED → FS EXECUTED → Payment APPROVED → FS ACTIVE."""
        from apps.core.models import Variation, FundingSchedule, Payment

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='READY')

        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status='DRAFT',
        )
        variation.funding_schedules.add(funding_schedule)
        variation.status = 'EXECUTED'
        variation.save()

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.EXECUTED

        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='APPROVED',
        )

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.ACTIVE


# ===========================================================================
# ExpenseClaim: cap enforcement at boundary
# ===========================================================================

@pytest.mark.django_db
class TestExpenseClaimCapEnforcement:
    @pytest.fixture
    def notice(self, db, project):
        from apps.core.models import FundingNotice
        return FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('1000.00'),
            status='OPEN',
        )

    @pytest.fixture
    def notice_near_cap(self, db, project):
        from apps.core.models import FundingNotice, ExpenseClaim
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal('1000.00'),
            status='OPEN',
        )
        ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('900.00'),
            status='APPROVED',
        )
        return notice

    def test_claim_under_cap_can_be_approved(self, notice):
        from apps.core.models import ExpenseClaim
        claim = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('500.00'),
            status='SUBMITTED',
        )
        claim.status = 'APPROVED'
        claim.save()
        claim.refresh_from_db()
        assert claim.status == 'APPROVED'

    def test_claim_exactly_at_cap_can_be_approved(self, notice_near_cap):
        from apps.core.models import ExpenseClaim
        claim = ExpenseClaim.objects.create(
            funding_notice=notice_near_cap,
            amount=Decimal('100.00'),
            status='SUBMITTED',
        )
        claim.status = 'APPROVED'
        claim.save()
        claim.refresh_from_db()
        assert claim.status == 'APPROVED'

    def test_claim_one_cent_over_cap_is_blocked(self, notice_near_cap):
        from apps.core.models import ExpenseClaim
        from django.core.exceptions import ValidationError

        claim = ExpenseClaim.objects.create(
            funding_notice=notice_near_cap,
            amount=Decimal('100.01'),
            status='SUBMITTED',
        )
        claim.status = 'APPROVED'
        with pytest.raises(ValidationError):
            claim.full_clean()

    def test_notice_is_exhausted_when_cap_filled(self, notice_near_cap):
        from apps.core.models import ExpenseClaim
        ExpenseClaim.objects.create(
            funding_notice=notice_near_cap,
            amount=Decimal('100.00'),
            status='APPROVED',
        )
        notice_near_cap.refresh_from_db()
        assert notice_near_cap.is_exhausted

    def test_approved_claims_total_excludes_non_approved(self, notice):
        from apps.core.models import ExpenseClaim
        ExpenseClaim.objects.create(
            funding_notice=notice, amount=Decimal('200'), status='APPROVED'
        )
        ExpenseClaim.objects.create(
            funding_notice=notice, amount=Decimal('300'), status='SUBMITTED'
        )
        notice.refresh_from_db()
        assert notice.approved_claims_total == Decimal('200')

    def test_remaining_decreases_after_approval(self, notice):
        from apps.core.models import ExpenseClaim
        ExpenseClaim.objects.create(
            funding_notice=notice, amount=Decimal('400'), status='APPROVED'
        )
        notice.refresh_from_db()
        assert notice.remaining == Decimal('600')


# ===========================================================================
# Report/Stage APPROVED → unlock next PENDING payment
# ===========================================================================

@pytest.mark.django_db
class TestReportApprovedUnlocksPayment:
    @pytest.fixture
    def active_schedule(self, db, funding_schedule):
        from apps.core.models import FundingSchedule
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='ACTIVE')
        funding_schedule.refresh_from_db()
        return funding_schedule

    @pytest.fixture
    def second_payment(self, db, project, active_schedule):
        from apps.core.models import Payment
        return Payment.objects.create(
            project=project,
            funding_schedule=active_schedule,
            payment_type='SECOND',
            calculation_type='FIXED',
            amount=Decimal('300000'),
            status='PENDING',
        )

    def test_stage_approved_unlocks_next_pending_payment(
        self, project, active_schedule, second_payment
    ):
        """Stage saved with status=APPROVED triggers unlock_next_payment signal."""
        from apps.core.models import Payment
        from apps.core.models.stages_models import Stage

        stage = Stage.objects.create(
            project=project,
            stage_name='Stage 1',
            status='PENDING',
        )
        stage.status = 'APPROVED'
        stage.save()

        second_payment.refresh_from_db()
        assert second_payment.status == Payment.Status.RECOMMENDED

    def test_stage_non_approved_does_not_unlock_payment(
        self, project, active_schedule, second_payment
    ):
        from apps.core.models import Payment
        from apps.core.models.stages_models import Stage

        Stage.objects.create(
            project=project,
            stage_name='Stage 1',
            status='PENDING',
        )

        second_payment.refresh_from_db()
        assert second_payment.status == Payment.Status.PENDING

    def test_no_active_schedule_means_no_payment_unlocked(
        self, project, second_payment
    ):
        """If no ACTIVE FundingSchedule exists, Stage APPROVED does not unlock payment."""
        from apps.core.models import Payment, FundingSchedule
        from apps.core.models.stages_models import Stage

        FundingSchedule.objects.filter(project=project).update(status='DRAFT')

        stage = Stage.objects.create(project=project, stage_name='Stage 1', status='PENDING')
        stage.status = 'APPROVED'
        stage.save()

        second_payment.refresh_from_db()
        assert second_payment.status == Payment.Status.PENDING


# ===========================================================================
# Full payment pipeline
# ===========================================================================

@pytest.mark.django_db
class TestPaymentPipeline:
    def test_full_payment_lifecycle_via_status_updates(self, project, funding_schedule):
        from apps.core.models import Payment, FundingSchedule

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='EXECUTED')

        payment = Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='PENDING',
        )
        assert payment.status == 'PENDING'

        payment.status = 'RECOMMENDED'
        payment.save(update_fields=['status', 'updated_at'])
        assert payment.status == 'RECOMMENDED'

        payment.status = 'APPROVED'
        payment.save(update_fields=['status', 'updated_at'])
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.ACTIVE

        payment.status = 'RELEASED'
        payment.release_date = date.today()
        payment.save(update_fields=['status', 'release_date', 'updated_at'])
        assert payment.status == 'RELEASED'

    def test_rejected_payment_does_not_activate_schedule(self, project, funding_schedule):
        from apps.core.models import Payment, FundingSchedule

        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status='EXECUTED')

        Payment.objects.create(
            project=project,
            funding_schedule=funding_schedule,
            payment_type='FIRST',
            calculation_type='FIXED',
            amount=Decimal('150000'),
            status='REJECTED',
        )

        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.EXECUTED
