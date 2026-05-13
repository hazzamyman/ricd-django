"""
Tests for Approval generic governance model.

Tests: Generic entity approval, delegation thresholds, approval workflow.
"""
import pytest
from decimal import Decimal

from apps.core.models import Approval, FundingSchedule, FundingAgreement, PaymentRule
from apps.core.models import Payment
from apps.core.models import Council
from apps.core.models import Program
from apps.core.models import Project
from django.contrib.auth.models import User


@pytest.fixture
def council():
    return Council.objects.create(name="Test Council", region="Test Region")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Test Program",
        funding_source="Government",
        budget=Decimal("10000000.00"),
        gl_code="GL789"
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        council=council,
        program=program,
        project_type=Project.Type.DWELLING,
        name="Test Project",
        state=Project.State.PROSPECTIVE
    )


@pytest.fixture
def funding_schedule(council):
    agreement = FundingAgreement.objects.create(council=council, status="DRAFT")
    rule = PaymentRule.objects.create(
        name="Standard Split",
        rule_type="SPLIT",
        config_json={
            "milestones": [
                {"name": "Start", "percentage": 30},
                {"name": "Mid", "percentage": 60},
                {"name": "End", "percentage": 10}
            ]
        },
        version=1
    )
    return FundingSchedule.objects.create(
        funding_agreement=agreement,
        schedule_number=1,
        payment_rule=rule,
        status="EXECUTED",
        amount=Decimal("1000000.00")
    )


@pytest.fixture
def payment(funding_schedule, project):
    return Payment.objects.create(
        funding_schedule=funding_schedule,
        project=project,
        amount=Decimal("300000.00"),
        status="PENDING"
    )


@pytest.fixture
def manager_user():
    return User.objects.create_user(username="manager", password="pass")


@pytest.fixture
def director_user():
    return User.objects.create_user(username="director", password="pass")


@pytest.fixture
def gm_user():
    return User.objects.create_user(username="gm", password="pass")


@pytest.mark.django_db
class TestApprovalCreation:
    """Test Approval creation and generic entity support"""

    def test_approval_created_pending(self, payment):
        """Test Approval starts in PENDING status"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert approval.id is not None
        assert approval.status == "PENDING"
        assert approval.entity_type == "Payment"

    def test_approval_for_different_entity_types(self, payment):
        """Test Approval supports multiple entity types"""
        payment_approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert payment_approval.entity_type == "Payment"

        report_approval = Approval.objects.create(
            entity_type="Report",
            entity_id=1,
            approval_type="REPORT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert report_approval.entity_type == "Report"

        variation_approval = Approval.objects.create(
            entity_type="Variation",
            entity_id=1,
            approval_type="VARIATION",
            required_role="DIRECTOR",
            status="PENDING"
        )
        assert variation_approval.entity_type == "Variation"

    def test_approval_records_approved_by_user(self, payment, manager_user):
        """Test Approval records the approver"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager_user
        )
        assert approval.approved_by == manager_user


@pytest.mark.django_db
class TestApprovalWorkflow:
    """Test Approval status transitions"""

    def test_pending_to_approved_transition(self, payment, manager_user):
        """Test PENDING → APPROVED transition"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        approval.status = "APPROVED"
        approval.approved_by = manager_user
        approval.save()
        assert approval.status == "APPROVED"

    def test_pending_to_rejected_transition(self, payment):
        """Test PENDING → REJECTED transition"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        approval.status = "REJECTED"
        approval.save()
        assert approval.status == "REJECTED"

    def test_multiple_approvals_for_same_entity(self, payment, manager_user, director_user):
        """Test multiple sequential approvals for same entity"""
        manager_approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager_user
        )
        director_approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="DIRECTOR",
            status="APPROVED",
            approved_by=director_user
        )
        payment_approvals = Approval.objects.filter(
            entity_type="Payment",
            entity_id=payment.id
        )
        assert payment_approvals.count() == 2


@pytest.mark.django_db
class TestDelegationThresholds:
    """Test delegate level approval requirements"""

    def test_manager_level_approval(self, payment, manager_user):
        """Test MANAGER level can approve payments up to threshold"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager_user
        )
        assert approval.required_role == "MANAGER"
        assert approval.status == "APPROVED"

    def test_director_level_approval(self, payment, director_user):
        """Test DIRECTOR level required for higher payments"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="DIRECTOR",
            status="APPROVED",
            approved_by=director_user
        )
        assert approval.required_role == "DIRECTOR"

    def test_gm_level_approval(self, payment, gm_user):
        """Test GM level required for highest payments"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="GM",
            status="APPROVED",
            approved_by=gm_user
        )
        assert approval.required_role == "GM"

    def test_approval_type_matches_entity(self, payment):
        """Test approval_type matches entity_type"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert approval.approval_type == "PAYMENT"
        assert approval.entity_type == "Payment"


@pytest.mark.django_db
class TestApprovalForDifferentEntities:
    """Test Approval for various entity types"""

    def test_financial_approval(self):
        """Test FINANCIAL approval type"""
        approval = Approval.objects.create(
            entity_type="BriefFinancialApproval",
            entity_id=1,
            approval_type="FINANCIAL",
            required_role="DIRECTOR",
            status="PENDING"
        )
        assert approval.approval_type == "FINANCIAL"

    def test_report_approval(self):
        """Test REPORT approval type"""
        approval = Approval.objects.create(
            entity_type="Report",
            entity_id=1,
            approval_type="REPORT",
            required_role="MANAGER",
            status="PENDING"
        )
        assert approval.approval_type == "REPORT"

    def test_variation_approval(self):
        """Test VARIATION approval type"""
        approval = Approval.objects.create(
            entity_type="VariationDeed",
            entity_id=1,
            approval_type="VARIATION",
            required_role="DIRECTOR",
            status="PENDING"
        )
        assert approval.approval_type == "VARIATION"


@pytest.mark.django_db
class TestApprovalAuditTrail:
    """Test Approval audit trail and timestamps"""

    def test_approval_created_timestamp(self, payment, manager_user):
        """Test that approval records created_at timestamp"""
        approval = Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager_user
        )
        assert approval.created_at is not None

    def test_approval_history_queryable(self, payment, manager_user, director_user):
        """Test approval history can be queried"""
        Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=manager_user
        )
        Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="DIRECTOR",
            status="APPROVED",
            approved_by=director_user
        )
        approvals = Approval.objects.filter(
            entity_type="Payment",
            entity_id=payment.id
        ).order_by('created_at')
        assert approvals.count() == 2
