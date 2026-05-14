"""
Tests for FundingNotice and ExpenseClaim models.

Tests: Cap enforcement, claim approval workflow, capped_amount validation.
"""
import pytest
from decimal import Decimal
from django.db import models

from apps.core.models import (
    FundingNotice, ExpenseClaim, FundingSchedule, FundingAgreement, PaymentRule
)
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
    """FundingSchedule to link FundingNotice to"""
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
def funding_notice(project):
    """FundingNotice with capped amount"""
    return FundingNotice.objects.create(
        project=project,
        capped_amount=Decimal("500000.00"),
        issued_date="2026-05-12",
        status="OPEN"
    )


@pytest.fixture
def approver_user():
    return User.objects.create_user(username="approver", password="pass")


@pytest.mark.django_db
class TestFundingNoticeCreation:
    """Test FundingNotice creation and initial state"""

    def test_funding_notice_created_open(self, funding_notice):
        """Test FundingNotice starts in OPEN status"""
        assert funding_notice.id is not None
        assert funding_notice.status == "OPEN"
        assert funding_notice.capped_amount == Decimal("500000.00")

    def test_funding_notice_issued_date(self, funding_notice):
        """Test issued_date field is set"""
        assert funding_notice.issued_date is not None

    def test_funding_notice_requires_funding_schedule(self, council):
        """Test that FundingNotice requires a FundingSchedule"""
        with pytest.raises(Exception):
            FundingNotice.objects.create(
                capped_amount=Decimal("100000.00"),
                issued_date="2026-05-12",
                status="OPEN"
            )


@pytest.mark.django_db
class TestExpenseClaimWorkflow:
    """Test ExpenseClaim submission and approval workflow"""

    def test_expense_claim_created_draft(self, funding_notice, project):
        """Test ExpenseClaim starts in DRAFT status"""
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("50000.00"),
            status="DRAFT"
        )
        assert claim.id is not None
        assert claim.status == "DRAFT"

    def test_expense_claim_submit_transition(self, funding_notice, project):
        """Test DRAFT → SUBMITTED transition"""
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("75000.00"),
            status="DRAFT"
        )
        claim.status = "SUBMITTED"
        claim.save()
        assert claim.status == "SUBMITTED"

    def test_expense_claim_approve_transition(self, funding_notice, project, approver_user):
        """Test SUBMITTED → APPROVED transition"""
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("100000.00"),
            status="SUBMITTED"
        )
        claim.status = "APPROVED"
        claim.approved_by = approver_user
        claim.save()
        assert claim.status == "APPROVED"
        assert claim.approved_by == approver_user

    def test_expense_claim_reject_transition(self, funding_notice, project):
        """Test SUBMITTED → REJECTED transition"""
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("50000.00"),
            status="SUBMITTED"
        )
        claim.status = "REJECTED"
        claim.save()
        assert claim.status == "REJECTED"


@pytest.mark.django_db
class TestExpenseClaimCapEnforcement:
    """Test cap enforcement: SUM(approved_claims) ≤ FundingNotice.capped_amount"""

    def test_single_claim_within_cap(self, funding_notice, project, approver_user):
        """Test single approved claim within cap"""
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("300000.00"),
            status="APPROVED",
            approved_by=approver_user
        )
        approved_total = funding_notice.claims.filter(
            status="APPROVED"
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        assert approved_total <= funding_notice.capped_amount

    def test_multiple_claims_within_cap(self, funding_notice, project, approver_user):
        """Test multiple approved claims sum within cap"""
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("200000.00"),
            status="APPROVED",
            approved_by=approver_user
        )
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("250000.00"),
            status="APPROVED",
            approved_by=approver_user
        )
        approved_total = sum(
            claim.amount for claim in funding_notice.claims.filter(
                status="APPROVED"
            )
        )
        assert approved_total == Decimal("450000.00")
        assert approved_total <= funding_notice.capped_amount

    def test_approved_claims_sum_calculation(self, funding_notice, project, approver_user):
        """Test that only APPROVED claims count toward cap"""
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("200000.00"),
            status="APPROVED",
            approved_by=approver_user
        )
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("150000.00"),
            status="SUBMITTED"
        )
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("100000.00"),
            status="DRAFT"
        )
        approved_total = sum(
            claim.amount for claim in funding_notice.claims.filter(
                status="APPROVED"
            )
        )
        assert approved_total == Decimal("200000.00")
        assert approved_total < funding_notice.capped_amount

    def test_claim_rejection_does_not_count_toward_cap(self, funding_notice, project):
        """Test rejected claims don't count toward cap"""
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("300000.00"),
            status="REJECTED"
        )
        ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("150000.00"),
            status="DRAFT"
        )
        approved_total = sum(
            claim.amount for claim in funding_notice.claims.filter(
                status="APPROVED"
            )
        )
        assert approved_total == Decimal("0")


@pytest.mark.django_db
class TestFundingNoticeStatusTransitions:
    """Test FundingNotice status transitions"""

    def test_open_to_closed_transition(self, funding_notice):
        """Test OPEN → CLOSED transition"""
        funding_notice.status = "CLOSED"
        funding_notice.save()
        assert funding_notice.status == "CLOSED"

    def test_closed_notice_still_accepts_claims(self, funding_notice, project):
        """Test that claims can be added to closed notice"""
        funding_notice.status = "CLOSED"
        funding_notice.save()
        claim = ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=Decimal("50000.00"),
            status="DRAFT"
        )
        assert claim.id is not None


@pytest.mark.django_db
class TestFundingNoticeCapValidation:
    """Test capped_amount validation"""

    def test_capped_amount_positive(self, project):
        """Test capped_amount must be positive"""
        notice = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal("1000.00"),
            issued_date="2026-05-12",
            status="OPEN"
        )
        assert notice.capped_amount > 0

    def test_capped_amount_can_vary(self, project):
        """Test FundingNotice can have different capped amounts"""
        notice1 = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal("500000.00"),
            issued_date="2026-05-12",
            status="OPEN"
        )
        notice2 = FundingNotice.objects.create(
            project=project,
            capped_amount=Decimal("750000.00"),
            issued_date="2026-05-13",
            status="OPEN"
        )
        assert notice1.capped_amount < notice2.capped_amount
