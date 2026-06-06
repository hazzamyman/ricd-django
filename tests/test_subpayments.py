"""Per-project sub-payment generation + funding-sufficiency check."""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError


@pytest.fixture
def split_rule():
    from apps.core.models import PaymentRule, PaymentRuleMilestone
    rule = PaymentRule.objects.create(name='Test 30/60/10', rule_type=PaymentRule.RuleType.SPLIT)
    PaymentRuleMilestone.objects.create(rule=rule, order=1, name='First', percentage=Decimal('30'))
    PaymentRuleMilestone.objects.create(rule=rule, order=2, name='Second', percentage=Decimal('60'))
    PaymentRuleMilestone.objects.create(rule=rule, order=3, name='Third', percentage=Decimal('10'))
    return rule


@pytest.mark.django_db
def test_generate_instalments_splits_by_allocation(funding_schedule, split_rule):
    from apps.core.models import Payment
    fs = funding_schedule
    fs.payment_rule = split_rule
    fs.save()

    created, total = fs.generate_project_instalments()

    assert created == 3
    assert total == Decimal('500000.00')
    by_type = {p.payment_type: p.amount for p in Payment.objects.filter(funding_schedule=fs)}
    assert by_type['FIRST'] == Decimal('150000.00')
    assert by_type['SECOND'] == Decimal('300000.00')
    assert by_type['THIRD'] == Decimal('50000.00')
    # all sub-payments follow the milestone schedule for dates
    assert all(p.forecast_anchor == Payment.ForecastAnchor.SCHEDULED
               for p in Payment.objects.filter(funding_schedule=fs))


@pytest.mark.django_db
def test_generate_is_idempotent(funding_schedule, split_rule):
    fs = funding_schedule
    fs.payment_rule = split_rule
    fs.save()
    fs.generate_project_instalments()
    created_again, _ = fs.generate_project_instalments()
    assert created_again == 0


@pytest.mark.django_db
def test_funding_sufficiency_excludes_contingency(funding_schedule):
    # Fixture: BFA funding 500k (+50k contingency), allocated 500k.
    fs = funding_schedule
    assert fs.has_approved_bfa() is True
    assert fs.approved_bfa_funding_only_for_children == Decimal('500000.00')
    assert fs.total_allocated() == Decimal('500000.00')
    assert fs.funding_shortfall() == Decimal('0.00')
    assert fs.is_funding_sufficient() is True


@pytest.mark.django_db
def test_overallocation_beyond_funding_is_blocked(funding_schedule, project):
    from apps.core.models import WorkFunding
    # Existing allocation already equals BFA funding (500k). One more dollar would
    # dip into contingency — funding-only rule blocks it.
    wf = WorkFunding(funding_schedule=funding_schedule, project=project, amount=Decimal('1.00'))
    with pytest.raises(ValidationError):
        wf.clean()
