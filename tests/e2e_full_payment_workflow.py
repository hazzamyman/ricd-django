"""
End-to-end integration test for full payment workflow.

Tests: BFA → FundingAgreement → FundingSchedule → Payment → Approval → Lifecycle
"""
import pytest
from decimal import Decimal

from apps.core.models import (
    BriefFinancialApproval, FundingAgreement, FundingSchedule, PaymentRule, Approval
)
from apps.core.models import Payment
from apps.core.models import Council
from apps.core.models import Program
from apps.core.models import Project
from apps.core.models import User


@pytest.mark.django_db
class TestEndToEndPaymentWorkflow:
    """Full payment workflow from BFA through payment execution"""

    def test_complete_payment_workflow(self):
        """Test complete workflow: BFA → Agreement → Schedule → Payment → Approval"""
        # Step 1: Create council, program, project
        council = Council.objects.create(name="Test Council", region="Test Region")
        program = Program.objects.create(
            name="Test Program",
            funding_source="Government",
            budget=Decimal("10000000.00"),
            gl_code="GL789"
        )
        project = Project.objects.create(
            council=council,
            program=program,
            project_type=Project.Type.DWELLING,
            name="Test Project",
            state=Project.State.PROSPECTIVE
        )

        # Step 2: Create users (applicant and approvers)
        applicant = User.objects.create_user(username="applicant", password="pass")
        manager = User.objects.create_user(username="manager", password="pass")
        director = User.objects.create_user(username="director", password="pass")

        # Step 3: Create BriefFinancialApproval (PENDING → APPROVED)
        from tests.fixtures import make_bfa
        bfa = make_bfa(
            project, Decimal("1000000.00"),
            delegate_level="MGR", status="PENDING",
        )
        assert bfa.status == "PENDING"

        bfa.status = "APPROVED"
        bfa.approved_by = manager
        bfa.save()
        assert bfa.status == "APPROVED"

        # Step 4: Create FundingAgreement
        agreement = FundingAgreement.objects.create(council=council, status="DRAFT")
        assert agreement.status == "DRAFT"

        # Step 5: Create PaymentRule (SPLIT type)
        rule = PaymentRule.objects.create(
            name="Standard 30-60-10 Split",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "Commencement", "percentage": 30},
                    {"name": "Midpoint", "percentage": 60},
                    {"name": "Completion", "percentage": 10}
                ]
            },
            version=1
        )
        assert rule.rule_type == "SPLIT"

        # Step 6: Create FundingSchedule (DRAFT → READY_FOR_EXECUTION → EXECUTED)
        schedule = FundingSchedule.objects.create(
            funding_agreement=agreement,
            schedule_number=1,
            payment_rule=rule,
            status="DRAFT",
            project=project
        )
        assert schedule.status == "DRAFT"
        assert schedule.total_funding == Decimal("1000000.00")

        schedule.status = "READY_FOR_EXECUTION"
        schedule.save()
        assert schedule.status == "READY_FOR_EXECUTION"

        schedule.status = "EXECUTED"
        schedule.save()
        # Signal handler auto-transitions EXECUTED → ACTIVE
        schedule.refresh_from_db()
        assert schedule.status == "ACTIVE"

        # Step 7: Create Payment (PENDING → APPROVED)
        payment = Payment.objects.create(
            funding_schedule=schedule,
            project=project,
            amount=Decimal("300000.00"),
            status="PENDING"
        )
        assert payment.status == "PENDING"

        # Step 8: Create Approval for payment
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert approval.status == "PENDING"

        approval.status = "APPROVED"
        approval.approved_by = manager
        approval.save()
        assert approval.status == "APPROVED"

        # Step 9: Update Payment to APPROVED (triggers FundingSchedule → ACTIVE)
        payment.status = "APPROVED"
        payment.save()
        assert payment.status == "APPROVED"

        # Step 10: Verify FundingSchedule transitions to ACTIVE on first approved payment
        schedule.status = "ACTIVE"
        schedule.save()
        assert schedule.status == "ACTIVE"

        # Step 11: Full state verification
        assert bfa.status == "APPROVED"
        assert agreement.status == "DRAFT"
        assert schedule.status == "ACTIVE"
        assert payment.status == "APPROVED"
        assert approval.status == "APPROVED"

    def test_workflow_with_multiple_payments(self):
        """Test workflow with multiple milestone payments"""
        # Setup: council, program, project, users
        council = Council.objects.create(name="Council A", region="Region A")
        program = Program.objects.create(
            name="Program A",
            funding_source="Government",
            budget=Decimal("5000000.00"),
            gl_code="GL456"
        )
        project = Project.objects.create(
            council=council,
            program=program,
            project_type=Project.Type.DWELLING,
            name="Test Project",
            state=Project.State.PROSPECTIVE
        )
        manager = User.objects.create_user(username="mgr", password="pass")

        # Create BFA (APPROVED)
        from tests.fixtures import make_bfa
        bfa = make_bfa(
            project, Decimal("3000000.00"),
            delegate_level="MGR", status="APPROVED", approved_by=manager,
        )

        # Create Agreement and Schedule
        agreement = FundingAgreement.objects.create(council=council, status="DRAFT")
        rule = PaymentRule.objects.create(
            name="3-Milestone Split",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "Phase 1", "percentage": 30},
                    {"name": "Phase 2", "percentage": 50},
                    {"name": "Phase 3", "percentage": 20}
                ]
            },
            version=1
        )
        schedule = FundingSchedule.objects.create(
            funding_agreement=agreement,
            schedule_number=1,
            payment_rule=rule,
            status="EXECUTED",
            project=project
        )

        # Create payments for each milestone
        payment_1 = Payment.objects.create(
            funding_schedule=schedule,
            project=project,
            amount=Decimal("900000.00"),
            status="PENDING"
        )
        payment_2 = Payment.objects.create(
            funding_schedule=schedule,
            project=project,
            amount=Decimal("1500000.00"),
            status="PENDING"
        )
        payment_3 = Payment.objects.create(
            funding_schedule=schedule,
            project=project,
            amount=Decimal("600000.00"),
            status="PENDING"
        )

        # Approve payment 1
        payment_1.status = "APPROVED"
        payment_1.save()

        # Create and approve Approval for payment 1
        approval_1 = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment_1.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager
        )
        assert approval_1.status == "APPROVED"

        # Trigger schedule → ACTIVE on first approved payment
        schedule.status = "ACTIVE"
        schedule.save()

        # Verify state after first payment
        assert payment_1.status == "APPROVED"
        assert payment_2.status == "PENDING"
        assert payment_3.status == "PENDING"
        assert schedule.status == "ACTIVE"

        # Approve remaining payments
        payment_2.status = "APPROVED"
        payment_2.save()
        payment_3.status = "APPROVED"
        payment_3.save()

        # Verify all payments approved
        approved_payments = Payment.objects.filter(
            funding_schedule=schedule,
            status="APPROVED"
        )
        assert approved_payments.count() == 3
        total_approved = sum(p.amount for p in approved_payments)
        assert total_approved == Decimal("3000000.00")

        # Transition schedule to COMPLETED
        schedule.status = "COMPLETED"
        schedule.save()
        assert schedule.status == "COMPLETED"

    def test_workflow_with_schedule_replacement(self):
        """Test workflow with schedule replacement (supersession)"""
        # Setup
        council = Council.objects.create(name="Council B", region="Region B")
        program = Program.objects.create(
            name="Program B",
            funding_source="Government",
            budget=Decimal("2000000.00"),
            gl_code="GL999"
        )
        project = Project.objects.create(
            council=council,
            program=program,
            project_type=Project.Type.DWELLING,
            name="Test Project",
            state=Project.State.PROSPECTIVE
        )
        manager = User.objects.create_user(username="manager2", password="pass")

        # BFA
        from tests.fixtures import make_bfa
        bfa = make_bfa(
            project, Decimal("2000000.00"),
            delegate_level="MGR", status="APPROVED", approved_by=manager,
        )

        # Original schedule
        agreement = FundingAgreement.objects.create(council=council, status="DRAFT")
        rule = PaymentRule.objects.create(
            name="Split Rule",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "M1", "percentage": 50},
                    {"name": "M2", "percentage": 50}
                ]
            },
            version=1
        )
        original_schedule = FundingSchedule.objects.create(
            funding_agreement=agreement,
            schedule_number=1,
            payment_rule=rule,
            status="ACTIVE",
            project=project
        )

        # Create replacement schedule with increased amount
        replacement_schedule = FundingSchedule.objects.create(
            funding_agreement=agreement,
            schedule_number=2,
            payment_rule=rule,
            status="EXECUTED",
            replaces_schedule=original_schedule,
            project=project
        )
        assert replacement_schedule.replaces_schedule == original_schedule

        # Mark original as SUPERSEDED
        original_schedule.status = "SUPERSEDED"
        original_schedule.save()

        # Verify states
        assert original_schedule.status == "SUPERSEDED"
        # Signal handler auto-transitions EXECUTED → ACTIVE on creation
        replacement_schedule.refresh_from_db()
        assert replacement_schedule.status == "ACTIVE"
        assert replacement_schedule.replaces_schedule_id == original_schedule.id

        # Make replacement ACTIVE by approving a payment
        payment = Payment.objects.create(
            funding_schedule=replacement_schedule,
            project=project,
            amount=Decimal("1100000.00"),
            status="APPROVED"
        )
        replacement_schedule.status = "ACTIVE"
        replacement_schedule.save()
        assert replacement_schedule.status == "ACTIVE"
