"""QBUILD (State-builder) delivery: BFA required, but no Council funding schedule —
payments are made directly against the project."""
import pytest
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError


def _approve_bfa(project, amount=Decimal('200000')):
    from apps.core.models import BriefFinancialApproval, BriefFinancialApprovalItem
    bfa = BriefFinancialApproval.objects.create(
        status=BriefFinancialApproval.Status.APPROVED)
    BriefFinancialApprovalItem.objects.create(
        bfa=bfa, project=project, program_id=project.program_id,
        funding_amount=amount, contingency_amount=Decimal('0'))
    return bfa


@pytest.mark.django_db
def test_qbuild_direct_payment_allowed_without_schedule(project):
    from apps.core.models import Payment
    project.qbuild_delivered = True
    project.save()
    _approve_bfa(project)

    p = Payment(project=project, funding_schedule=None, payment_type='FIRST',
                calculation_type='FIXED', amount=Decimal('150000'),
                forecast_release_date=date(2027, 9, 1), status='PENDING')
    p.clean()   # no funding schedule, but QBUILD + BFA → allowed
    p.save()
    assert p.pk is not None
    assert p.funding_schedule_id is None


@pytest.mark.django_db
def test_non_qbuild_payment_requires_schedule(project):
    from apps.core.models import Payment
    _approve_bfa(project)   # BFA present, but project is NOT QBUILD-delivered
    p = Payment(project=project, funding_schedule=None, payment_type='FIRST',
                calculation_type='FIXED', amount=Decimal('1000'), status='PENDING')
    with pytest.raises(ValidationError) as exc:
        p.clean()
    assert any('schedule' in m.lower() for m in exc.value.messages)
