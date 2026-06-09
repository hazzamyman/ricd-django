from django.db import models


class EmailTemplate(models.Model):
    """Editable template for an automated-notification event.

    Wording is edited in Maintenance. Placeholders are curated `{name}` tokens
    filled from the event context (see apps.core.services.notifications). Unknown
    tokens are left intact rather than erroring.
    """
    class Event(models.TextChoices):
        # Event-driven (Phase 1 — fire from signals immediately)
        PAYMENT_RELEASED = 'PAYMENT_RELEASED', 'Payment released'
        AGREEMENT_SIGNED = 'AGREEMENT_SIGNED', 'Funding agreement signed'
        REPORT_APPROVED = 'REPORT_APPROVED', 'Report approved'
        REPORT_REJECTED = 'REPORT_REJECTED', 'Report rejected / returned'
        PROJECT_COMPLETED = 'PROJECT_COMPLETED', 'Project completed'
        # Time-based (Phase 2 — templates exist now; a daily job will send them)
        MONTHLY_TRACKER_OVERDUE = 'MONTHLY_TRACKER_OVERDUE', 'Monthly tracker overdue'
        QUARTERLY_REPORT_OVERDUE = 'QUARTERLY_REPORT_OVERDUE', 'Quarterly report overdue'
        STAGE_TARGET_DUE = 'STAGE_TARGET_DUE', 'Stage target date approaching'
        STAGE_SUNSET_DUE = 'STAGE_SUNSET_DUE', 'Stage sunset date approaching'

    event = models.CharField(max_length=40, choices=Event.choices, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(
        default=True, help_text="Uncheck to stop this notification being sent."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event']
        verbose_name = 'Email Template'

    def __str__(self):
        return self.get_event_display()


class SentNotification(models.Model):
    """Audit log of automated emails. Also provides idempotency: a (event,
    object) is only sent once, keyed on `dedupe_key`."""
    event = models.CharField(max_length=40, db_index=True)
    dedupe_key = models.CharField(max_length=255, db_index=True)
    council = models.ForeignKey('Council', null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey('Project', null=True, blank=True, on_delete=models.SET_NULL)
    recipients = models.TextField(blank=True, help_text="Comma-separated recipient emails")
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Sent Notification'

    def __str__(self):
        return f"{self.event} → {self.recipients or '(no recipients)'} ({self.sent_at:%Y-%m-%d %H:%M})"
