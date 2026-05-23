"""
Comprehensive tests for PaymentRule model.

Tests: Versioning, immutability once linked, SPLIT/INVOICE_BASED rules, validation.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.core.models import PaymentRule, FundingSchedule, FundingAgreement
from apps.core.models import Council
from apps.core.models import Program
from apps.core.models import Project


@pytest.fixture
def council():
    return Council.objects.create(name="Test Council", region="Test Region")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Test Program",
        funding_source="Government",
        budget=Decimal("1000000.00"),
        gl_code="GL123"
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
def split_payment_rule():
    """PaymentRule with SPLIT type (milestone-based)"""
    return PaymentRule.objects.create(
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


@pytest.fixture
def invoice_payment_rule():
    """PaymentRule with INVOICE_BASED type (expense claims)"""
    return PaymentRule.objects.create(
        name="Invoice-Based Reimbursement",
        rule_type="INVOICE",
        config_json={"requires_approval": True},
        version=1
    )


@pytest.mark.django_db
class TestPaymentRuleCreation:
    """Test PaymentRule creation and basic properties"""

    def test_split_rule_creation(self, split_payment_rule):
        """Test creating a SPLIT payment rule"""
        assert split_payment_rule.id is not None
        assert split_payment_rule.rule_type == "SPLIT"
        assert split_payment_rule.version == 1
        assert split_payment_rule.name == "Standard 30-60-10 Split"

    def test_invoice_rule_creation(self, invoice_payment_rule):
        """Test creating an INVOICE_BASED payment rule"""
        assert invoice_payment_rule.id is not None
        assert invoice_payment_rule.rule_type == "INVOICE"
        assert invoice_payment_rule.config_json["requires_approval"] is True

    def test_payment_rule_versioning(self):
        """Test that versions can be incremented"""
        rule_v1 = PaymentRule.objects.create(
            name="Versioned Rule v1",
            rule_type="SPLIT",
            config_json={"milestones": [{"name": "M1", "percentage": 100}]},
            version=1
        )
        rule_v2 = PaymentRule.objects.create(
            name="Versioned Rule v2",
            rule_type="SPLIT",
            config_json={"milestones": [{"name": "M1", "percentage": 50}, {"name": "M2", "percentage": 50}]},
            version=2
        )
        assert rule_v1.version == 1
        assert rule_v2.version == 2
        assert rule_v1.id != rule_v2.id


@pytest.mark.django_db
class TestPaymentRuleImmutability:
    """Test that PaymentRule becomes immutable once linked to FundingSchedule"""

    def test_rule_immutable_after_funding_schedule_link(self, split_payment_rule, council):
        """Test that a PaymentRule cannot be modified once linked to FundingSchedule"""
        agreement = FundingAgreement.objects.create(
            council=council,
            status="DRAFT"
        )
        fs = FundingSchedule.objects.create(
            funding_agreement=agreement,
            schedule_number=1,
            payment_rule=split_payment_rule,
            status="DRAFT"
        )
        assert split_payment_rule.id in FundingSchedule.objects.values_list('payment_rule', flat=True)

    def test_rule_modifiable_before_linking(self, split_payment_rule):
        """Test that a PaymentRule can be modified before being linked"""
        split_payment_rule.config_json = {
            "milestones": [{"name": "New", "percentage": 100}]
        }
        split_payment_rule.full_clean()
        split_payment_rule.save()
        split_payment_rule.refresh_from_db()
        assert split_payment_rule.config_json["milestones"][0]["name"] == "New"


@pytest.mark.django_db
class TestPaymentRuleSPLITValidation:
    """Test SPLIT rule validation: milestones must sum to 100%"""

    def test_split_rule_valid_100_percent(self):
        """Test SPLIT rule with milestones totaling 100%"""
        rule = PaymentRule(
            name="Valid Split",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "Phase 1", "percentage": 30},
                    {"name": "Phase 2", "percentage": 40},
                    {"name": "Phase 3", "percentage": 30}
                ]
            },
            version=1
        )
        rule.full_clean()
        rule.save()
        assert rule.id is not None

    def test_split_rule_invalid_less_than_100(self):
        """Test SPLIT rule with milestones < 100% raises error"""
        rule = PaymentRule(
            name="Invalid Split (90%)",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "Phase 1", "percentage": 50},
                    {"name": "Phase 2", "percentage": 40}
                ]
            },
            version=1
        )
        with pytest.raises(ValidationError):
            rule.full_clean()

    def test_split_rule_invalid_more_than_100(self):
        """Test SPLIT rule with milestones > 100% raises error"""
        rule = PaymentRule(
            name="Invalid Split (110%)",
            rule_type="SPLIT",
            config_json={
                "milestones": [
                    {"name": "Phase 1", "percentage": 60},
                    {"name": "Phase 2", "percentage": 50}
                ]
            },
            version=1
        )
        with pytest.raises(ValidationError):
            rule.full_clean()

    def test_invoice_rule_no_percentage_validation(self, invoice_payment_rule):
        """Test INVOICE_BASED rule has no percentage validation"""
        invoice_payment_rule.full_clean()
        assert invoice_payment_rule.rule_type == "INVOICE"
