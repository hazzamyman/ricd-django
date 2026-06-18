"""Phase 2: the daily send_due_notifications command + master on/off switch."""
import pytest
from datetime import date, timedelta
from django.core.management import call_command


@pytest.mark.django_db
def test_stage_target_reminder_is_sent_and_idempotent(project):
    from apps.core.models import CouncilContact, SentNotification
    CouncilContact.objects.create(
        council=project.council, role='C', name='Recipient',
        email='r@example.com', receives_notifications=True)
    project.stage1_target_date = date.today() + timedelta(days=30)
    project.state = project.State.COMMENCED
    project.save()

    call_command('send_due_notifications')

    n = SentNotification.objects.filter(event='STAGE_TARGET_DUE', project=project).first()
    assert n is not None
    assert project.name in n.body
    assert 'r@example.com' in n.recipients

    # Running again does not re-send.
    count = SentNotification.objects.count()
    call_command('send_due_notifications')
    assert SentNotification.objects.count() == count


@pytest.mark.django_db
def test_master_switch_off_blocks_everything(project):
    from apps.core.models import CouncilContact, SentNotification, SiteSettings
    s = SiteSettings.get()
    s.notifications_enabled = False
    s.save()
    CouncilContact.objects.create(
        council=project.council, role='C', name='Recipient',
        email='r@example.com', receives_notifications=True)
    project.stage1_target_date = date.today() + timedelta(days=1)
    project.state = project.State.COMMENCED
    project.save()

    call_command('send_due_notifications')
    assert not SentNotification.objects.filter(event='STAGE_TARGET_DUE').exists()
