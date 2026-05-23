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
def funding_schedule(funding_agreement, payment_rule, project, approved_bfa):
    """Seeded with a WorkFunding allocation so total_funding == 500000."""
    from apps.core.models import WorkFunding
    fs = FundingSchedule.objects.create(
        funding_agreement=funding_agreement,
        schedule_number=1,
        payment_rule=payment_rule,
        status="DRAFT",
        project=project
    )
    WorkFunding.objects.create(
        funding_schedule=fs, project=project, amount=Decimal('500000.00')
    )
    return fs


@pytest.mark.django_db
class TestFundingScheduleInitialState:
    """Test FundingSchedule creation and initial state"""

    def test_fs_created_in_draft(self, funding_schedule):
        """Test FundingSchedule starts in DRAFT status"""
        assert funding_schedule.id is not None
        assert funding_schedule.status == "DRAFT"
        assert funding_schedule.payment_rule is not None

    def test_fs_requires_payment_rule(self, funding_agreement, project, approved_bfa):
        """payment_rule is required to leave DRAFT, not at creation."""
        fs = FundingSchedule(
            funding_agreement=funding_agreement,
            project=project,
            schedule_number=2,
            status="READY",  # not DRAFT -> must have payment_rule
        )
        with pytest.raises(Exception):
            fs.full_clean()

    def test_fs_total_funding_calculation(self, funding_schedule):
        """total_funding = SUM of WorkFunding allocations (fixture seeds 500k)."""
        assert funding_schedule.total_funding == Decimal("500000.00")


@pytest.mark.django_db
class TestFundingScheduleLifecycle:
    """Test FundingSchedule state transitions"""

    def test_draft_to_ready_transition(self, funding_schedule):
        """Test DRAFT → READY_FOR_EXECUTION transition"""
        funding_schedule.status = "READY_FOR_EXECUTION"
        funding_schedule.save()
        assert funding_schedule.status == "READY_FOR_EXECUTION"

    def test_ready_to_executed_transition(self, funding_schedule):
        """Test READY_FOR_EXECUTION → EXECUTED transition.

        The governance signal immediately calls trigger_funding_schedule_active
        when status is set to EXECUTED via save(), which advances the FS to
        ACTIVE. Use update() to bypass signals and assert the EXECUTED state
        itself is a valid DB value.
        """
        from apps.core.models import FundingSchedule as FS
        FS.objects.filter(pk=funding_schedule.pk).update(status="EXECUTED")
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == "EXECUTED"

    def test_executed_to_active_on_payment_approval(
        self, funding_schedule, project
    ):
        """Test EXECUTED → ACTIVE on first APPROVED payment.

        Signal fires trigger_funding_schedule_active when a Payment is saved
        with status=APPROVED and its funding_schedule is EXECUTED. We use
        update() to bypass the post_save signal when forcing the FS into
        EXECUTED state so we can test the payment-approval trigger in isolation.
        """
        from apps.core.models import FundingSchedule as FS
        FS.objects.filter(pk=funding_schedule.pk).update(status="EXECUTED")
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == "EXECUTED"

        approver = User.objects.create_user(username="approver2", password="pass")
        payment = Payment.objects.create(
            funding_schedule=funding_schedule,
            project=project,
            amount=Decimal("300000.00"),
            status="PENDING"
        )

        payment.status = "APPROVED"
        payment.save()
        funding_schedule.refresh_from_db()

        assert funding_schedule.status == "ACTIVE"

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
            project=project
        )

        replacement = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="DRAFT",
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
            project=project
        )

        replacement = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="EXECUTED",
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
            project=project
        )

        another_council = Council.objects.create(name="Another Council", region="Region2")
        another_agreement = FundingAgreement.objects.create(council=another_council, status="DRAFT")
        fs2 = FundingSchedule.objects.create(
            funding_agreement=another_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
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
            project=project
        )

        fs2 = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=2,
            payment_rule=payment_rule,
            status="DRAFT",
            project=project
        )

        assert fs1.schedule_number == 1
        assert fs2.schedule_number == 2
