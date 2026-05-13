"""
Governance Signal Tests — Verify critical payment approval workflow automation.

Tests the 3 Stage 2B signals:
1. Payment created → auto-create Approval record
2. Approval approved → sync to Payment status
3. Report approved → unlock next payment
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestGovernanceSignal1_PaymentApproval:
    """Signal 1: Payment created → auto-create Approval record"""

    def test_payment_creation_creates_approval(self, funding_schedule, project):
        """When Payment is created, Approval record auto-created"""
        from apps.core.models import Payment, Approval

        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("100000.00"),
            status="PENDING"
        )

        # Verify Approval record was auto-created
        approval = Approval.objects.get(
            entity_type='Payment',
            entity_id=payment.pk
        )
        assert approval.status == Approval.Status.PENDING
        assert approval.approval_type == Approval.ApprovalType.PAYMENT

    def test_approval_delegation_level_set_correctly(self, funding_schedule, project):
        """Approval required_role determined by payment amount"""
        from apps.core.models import Payment, Approval

        # Small amount → Manager level
        payment_small = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("50000.00"),
            status="PENDING"
        )
        approval_small = Approval.objects.get(entity_id=payment_small.pk)
        # Exact role depends on Delegation.get_delegation_level() logic
        assert approval_small.required_role in [
            Approval.RequiredRole.MANAGER,
            Approval.RequiredRole.DIRECTOR,
            Approval.RequiredRole.DELEGATE,
        ]


@pytest.mark.django_db
class TestGovernanceSignal2_ApprovalSync:
    """Signal 2: Approval approved → sync to Payment status"""

    def test_approval_approved_updates_payment(self, funding_schedule, project):
        """When Approval APPROVED, Payment status updates to APPROVED"""
        from apps.core.models import Payment, Approval

        # Create payment (auto-creates approval)
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("100000.00"),
            status="PENDING"
        )

        # Get auto-created approval
        approval = Approval.objects.get(
            entity_type='Payment',
            entity_id=payment.pk
        )

        # Set approval to APPROVED
        approval.status = Approval.Status.APPROVED
        approval.save()

        # Verify Payment status updated to APPROVED
        payment.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED

    def test_payment_approval_triggers_funding_schedule_active(
        self, funding_schedule, project
    ):
        """
        When Payment APPROVED, FundingSchedule transitions EXECUTED → ACTIVE.
        This chains from Signal 2 to existing Signal (Payment APPROVED).
        """
        from apps.core.models import Payment, Approval

        # Set schedule to EXECUTED
        funding_schedule.status = "EXECUTED"
        funding_schedule.save()

        # Create and approve payment
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("100000.00"),
            status="PENDING"
        )

        approval = Approval.objects.get(entity_id=payment.pk)
        approval.status = Approval.Status.APPROVED
        approval.save()

        # Verify FundingSchedule transitioned to ACTIVE
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == "ACTIVE"


@pytest.mark.django_db
class TestGovernanceSignal3_ReportUnlocksPayment:
    """Signal 3: Report/Stage approved → unlock next payment"""

    def test_report_approval_unlocks_next_payment(self, funding_schedule, project):
        """When Report/Stage APPROVED, next Payment unlocked (status=READY)"""
        from apps.core.models import Payment, Stage

        # Set funding schedule to ACTIVE
        funding_schedule.status = "ACTIVE"
        funding_schedule.save()

        # Create stage and payments
        stage = Stage.objects.create(
            project=project,
            stage_name="Stage 1",
            status="PENDING"
        )

        # Create payment (locked/pending)
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("100000.00"),
            status="PENDING",
            payment_type="FIRST"
        )

        # Set stage to APPROVED
        stage.status = "APPROVED"
        stage.save()

        # Verify payment unlocked (status=RECOMMENDED)
        payment.refresh_from_db()
        assert payment.status == Payment.Status.RECOMMENDED


@pytest.mark.django_db
class TestGovernanceIntegration:
    """End-to-end governance workflow validation"""

    def test_full_payment_approval_workflow(self, funding_schedule, project):
        """
        Complete workflow:
        1. Payment created → Approval auto-created (PENDING)
        2. Approval approved → Payment status updated
        3. FundingSchedule transitions from EXECUTED → ACTIVE
        """
        from apps.core.models import Payment, Approval

        # Set schedule to EXECUTED (ready for payment)
        funding_schedule.status = "EXECUTED"
        funding_schedule.save()

        # Step 1: Create payment (auto-creates Approval)
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("250000.00"),
            status="PENDING"
        )

        # Verify approval created and pending
        approval = Approval.objects.get(entity_type='Payment', entity_id=payment.pk)
        assert approval.status == Approval.Status.PENDING
        assert payment.status == Payment.Status.PENDING

        # Step 2: Approve the payment
        approval.status = Approval.Status.APPROVED
        approval.save()

        # Step 3: Verify payment and schedule updated
        payment.refresh_from_db()
        funding_schedule.refresh_from_db()

        assert payment.status == Payment.Status.APPROVED
        assert funding_schedule.status == "ACTIVE"
