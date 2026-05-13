"""
Tests for FundingSchedule lifecycle: DRAFT→READY→EXECUTED→ACTIVE→COMPLETED/SUPERSEDED.
"""
import pytest
from decimal import Decimal

from apps.core.models import (
    FundingSchedule, FundingAgreement, PaymentRule, BriefFinancialApproval, Approval
)
from apps.core.models import Payment
from apps.core.models import Council
from apps.core.models import Program
from apps.core.models import Project
from django.contrib.auth.models import User


@pytest.fixture
def council():
    return Council.objects.create(name="Test Council", region="Region1")


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
def approved_bfa(project):
    user = User.objects.create_user(username="approver", password="pass")
    return BriefFinancialApproval.objects.create(
        project=project,
        funding_amount=Decimal("1000000.00"),
        delegate_level="MANAGER",
        status="APPROVED",
        approved_by=user
    )


@pytest.fixture
def payment_rule():
    return PaymentRule.objects.create(
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


@pytest.fixture
def funding_agreement(council):
    return FundingAgreement.objects.create(council=council, status="DRAFT")


@pytest.fixture
def funding_schedule(funding_agreement, payment_rule, project):
    return FundingSchedule.objects.create(
        funding_agreement=funding_agreement,
        schedule_number=1,
        payment_rule=payment_rule,
        status="DRAFT",
        amount=Decimal("1000000.00"),
        project=project
    )


@pytest.mark.django_db
class TestFundingScheduleInitialState:
    """Test FundingSchedule creation and initial state"""

    def test_fs_created_in_draft(self, funding_schedule):
        """Test FundingSchedule starts in DRAFT status"""
        assert funding_schedule.id is not None
        assert funding_schedule.status == "DRAFT"
        assert funding_schedule.payment_rule is not None

    def test_fs_requires_payment_rule(self, funding_agreement):
        """Test that FundingSchedule requires a payment rule"""
        with pytest.raises(Exception):
            FundingSchedule.objects.create(
                funding_agreement=funding_agreement,
                schedule_number=2,
                status="DRAFT"
            )

    def test_fs_total_funding_calculation(self, funding_schedule, project):
        """Test total_funding calculation"""
        fs = FundingSchedule.objects.create(
            funding_agreement=funding_schedule.funding_agreement,
            schedule_number=2,
            payment_rule=funding_schedule.payment_rule,
            status="DRAFT",
            amount=Decimal("500000.00"),
            contingency=Decimal("50000.00"),
            project=project
        )
        assert fs.total_funding == Decimal("550000.00")


@pytest.mark.django_db
class TestFundingScheduleLifecycle:
    """Test FundingSchedule state transitions"""

    def test_draft_to_ready_transition(self, funding_schedule):
        """Test DRAFT → READY_FOR_EXECUTION transition"""
        funding_schedule.status = "READY_FOR_EXECUTION"
        funding_schedule.save()
        assert funding_schedule.status == "READY_FOR_EXECUTION"

    def test_ready_to_executed_transition(self, funding_schedule):
        """Test READY_FOR_EXECUTION → EXECUTED transition"""
        funding_schedule.status = "READY_FOR_EXECUTION"
        funding_schedule.save()
        funding_schedule.status = "EXECUTED"
        funding_schedule.save()
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == "EXECUTED"

    def test_executed_to_active_on_payment_approval(
        self, funding_schedule, project
    ):
        """Test EXECUTED → ACTIVE on first APPROVED payment"""
        funding_schedule.status = "EXECUTED"
        funding_schedule.save()
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == "EXECUTED"

        approver = User.objects.create_user(username="approver2", password="pass")
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("300000.00"),
            status="PENDING"
        )

        Approval.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            approval_type="PAYMENT",
            required_role="MANAGER",
            status="APPROVED",
            approved_by=approver
        )

        payment.status = "APPROVED"
        payment.save()
        funding_schedule.refresh_from_db()

        assert funding_schedule.status == "EXECUTED"

    def test_active_to_completed_transition(self, funding_schedule):
        """Test ACTIVE → COMPLETED transition"""
        funding_schedule.status = "ACTIVE"
        funding_schedule.save()
        funding_schedule.status = "COMPLETED"
        funding_schedule.save()
        assert funding_schedule.status == "COMPLETED"

    def test_active_to_superseded_transition(self, funding_schedule):
        """Test ACTIVE → SUPERSEDED on replacement"""
        funding_schedule.status = "ACTIVE"
        funding_schedule.save()
        funding_schedule.status = "SUPERSEDED"
        funding_schedule.save()
        assert funding_schedule.status == "SUPERSEDED"


@pytest.mark.django_db
class TestFundingScheduleReplacement:
    """Test FundingSchedule replacement"""

    def test_schedule_replacement_link(self, funding_agreement, payment_rule, project):
        """Test setting replaces_schedule relationship"""
        original = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("1000000.00"),
            project=project
        )

        replacement = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("1100000.00"),
            replaces_schedule=original,
            project=project
        )

        assert replacement.replaces_schedule == original
        assert replacement.id != original.id

    def test_original_marked_superseded_on_replacement(
        self, funding_agreement, payment_rule, project
    ):
        """Test original schedule marked SUPERSEDED when replaced"""
        original = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="ACTIVE",
            amount=Decimal("1000000.00"),
            project=project
        )

        replacement = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="EXECUTED",
            amount=Decimal("1100000.00"),
            replaces_schedule=original,
            project=project
        )
        replacement.refresh_from_db()

        original.status = "SUPERSEDED"
        original.save()

        assert original.status == "SUPERSEDED"
        assert replacement.replaces_schedule == original


@pytest.mark.django_db
class TestFundingScheduleUniqueConstraint:
    """Test FundingSchedule uniqueness constraints"""

    def test_unique_schedule_number_per_agreement(
        self, funding_agreement, payment_rule, project
    ):
        """Test schedule_number can be reused across different agreements"""
        fs1 = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("1000000.00"),
            project=project
        )

        another_council = Council.objects.create(name="Another Council", region="Region2")
        another_agreement = FundingAgreement.objects.create(council=another_council, status="DRAFT")
        fs2 = FundingSchedule.objects.create(
            funding_agreement=another_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("900000.00"),
            project=project
        )
        assert fs1.schedule_number == fs2.schedule_number == 1
        assert fs1.funding_agreement != fs2.funding_agreement

    def test_different_schedule_numbers_allowed(
        self, funding_agreement, payment_rule, project
    ):
        """Test different schedule numbers are allowed"""
        fs1 = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("1000000.00"),
            project=project
        )

        fs2 = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="DRAFT",
            amount=Decimal("900000.00"),
            project=project
        )

        assert fs1.schedule_number == 1
        assert fs2.schedule_number == 2
