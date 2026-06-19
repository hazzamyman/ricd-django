"""
Comprehensive tests for BriefFinancialApproval model.

Tests: Pre-condition enforcement, approval status transitions, delegate levels.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.models import (
    BriefFinancialApproval, FundingSchedule, FundingAgreement, PaymentRule,
    DelegatePosition,
)
from apps.core.models import Council, Program, Project
from django.contrib.auth.models import User
from tests.fixtures import make_bfa


@pytest.fixture
def council():
    return Council.objects.create(name="Test Council", region="Test Region")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Test Program",
        funding_source="Government",
        budget=Decimal("5000000.00"),
        gl_code="GL456",
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        council=council,
        program=program,
        project_type=Project.Type.DWELLING,
        name="Test Project",
        state=Project.State.PROSPECTIVE,
    )


@pytest.fixture
def approver_user():
    return User.objects.create_user(
        username="approver",
        email="approver@test.local",
        password="testpass",
    )


@pytest.fixture
def manager_position():
    # 'Manager' is seeded by migration 0051 — reuse it rather than duplicate.
    return DelegatePosition.objects.get_or_create(
        title="Manager", defaults={'max_approval_amount': Decimal("250000.00"), 'order': 1})[0]


@pytest.fixture
def director_position():
    return DelegatePosition.objects.get_or_create(
        title="Director", defaults={'max_approval_amount': Decimal("1000000.00"), 'order': 2})[0]


@pytest.fixture
def approved_bfa(project, approver_user, manager_position):
    return make_bfa(
        project, Decimal("500000.00"),
        delegate_position=manager_position,
        status="APPROVED",
        approved_by=approver_user,
        mincor_reference="MINCOR-2026-001",
    )


@pytest.fixture
def pending_bfa(project, director_position):
    return make_bfa(
        project, Decimal("750000.00"),
        delegate_position=director_position,
        status="PENDING",
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
                {"name": "End", "percentage": 10},
            ]
        },
        version=1,
    )


@pytest.fixture
def funding_agreement(council):
    return FundingAgreement.objects.create(council=council, status="DRAFT")


@pytest.mark.django_db
class TestBriefFinancialApprovalCreation:
    def test_create_pending_bfa(self, pending_bfa):
        assert pending_bfa.id is not None
        assert pending_bfa.status == "PENDING"
        assert pending_bfa.funding_amount == Decimal("750000.00")
        assert pending_bfa.delegate_position.title == "Director"
        assert pending_bfa.approved_by is None

    def test_create_approved_bfa(self, project, approver_user, manager_position):
        bfa = make_bfa(
            project, Decimal("500000.00"),
            delegate_position=manager_position,
            status="APPROVED",
            approved_by=approver_user,
            mincor_reference="MINCOR-2026-001",
        )
        bfa.approved_at = timezone.now()
        bfa.save()
        assert bfa.id is not None
        assert bfa.status == "APPROVED"
        assert bfa.approved_by == approver_user
        assert bfa.approved_at is not None

    def test_rejected_bfa(self, project):
        rejection = make_bfa(
            project, Decimal("600000.00"),
            status="REJECTED",
        )
        assert rejection.status == "REJECTED"


@pytest.mark.django_db
class TestBriefFinancialApprovalPreCondition:
    """APPROVED BFA item required for a project before its FundingSchedule can be created."""

    def test_fs_creation_with_approved_bfa(
        self, project, approved_bfa, funding_agreement, payment_rule
    ):
        fs = FundingSchedule.objects.create(
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
        )
        assert fs.id is not None

    def test_fs_fails_without_bfa(self, council, funding_agreement, payment_rule):
        project_no_bfa = Project.objects.create(
            council=council,
            program=Program.objects.create(
                name="Other Program",
                funding_source="Other",
                budget=Decimal("1000000.00"),
            ),
            project_type=Project.Type.DWELLING,
            name="No BFA Project",
            state=Project.State.PROSPECTIVE,
        )
        fs = FundingSchedule(
            project=project_no_bfa,
            funding_agreement=funding_agreement,
            schedule_number=1,
            payment_rule=payment_rule,
            status="DRAFT",
        )
        with pytest.raises((ValidationError, ValueError)):
            fs.full_clean()


@pytest.mark.django_db
class TestBriefFinancialApprovalDelegatePositions:
    def test_manager_position(self, project, approver_user, manager_position):
        bfa = make_bfa(
            project, Decimal("200000.00"),
            delegate_position=manager_position,
            status="APPROVED", approved_by=approver_user,
        )
        assert bfa.delegate_position == manager_position
        assert bfa.delegate_position.title == "Manager"

    def test_director_position(self, project, approver_user, director_position):
        bfa = make_bfa(
            project, Decimal("600000.00"),
            delegate_position=director_position,
            status="APPROVED", approved_by=approver_user,
        )
        assert bfa.delegate_position.title == "Director"

    def test_position_cleared_on_delete(self, project, approver_user, manager_position):
        bfa = make_bfa(
            project, Decimal("200000.00"),
            delegate_position=manager_position,
            status="APPROVED", approved_by=approver_user,
        )
        manager_position.delete()
        bfa.refresh_from_db()
        assert bfa.delegate_position is None
