"""Automated notification emails — event trigger + safe placeholder rendering."""
import pytest
from decimal import Decimal


@pytest.mark.django_db
def test_payment_released_creates_notification(funding_schedule, project):
    from apps.core.models import CouncilContact, Payment, SentNotification
    CouncilContact.objects.create(
        council=project.council, role='Contact', name='Recipient',
        email='recipient@example.com', receives_notifications=True,
    )
    # A contact WITHOUT the flag should not receive it.
    CouncilContact.objects.create(
        council=project.council, role='Other', name='No notices',
        email='skip@example.com', receives_notifications=False,
    )

    p = Payment(project=project, funding_schedule=funding_schedule, payment_type='FIRST',
                calculation_type='FIXED', amount=Decimal('100000'), status='RELEASED')
    p.save()  # fires notify_payment_released

    n = SentNotification.objects.filter(event='PAYMENT_RELEASED', project=project).first()
    assert n is not None
    assert 'recipient@example.com' in n.recipients
    assert 'skip@example.com' not in n.recipients
    assert '100,000' in n.body         # {amount} filled
    assert project.name in n.subject   # {project} filled

    # Idempotent: re-saving the released payment does not duplicate.
    count = SentNotification.objects.count()
    p.save()
    assert SentNotification.objects.count() == count


@pytest.mark.django_db
def test_render_leaves_unknown_placeholders_intact():
    from apps.core.services.notifications import render
    assert render('Hi {project} {mystery}', {'project': 'Aurukun'}) == 'Hi Aurukun {mystery}'
