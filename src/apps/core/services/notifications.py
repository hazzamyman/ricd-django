"""Automated notification emails.

Curated `{placeholder}` tokens are rendered with str.format_map and a safe dict
(unknown tokens are left intact). Recipients are the council contacts flagged
`receives_notifications`. Every send is logged to SentNotification, which also
provides idempotency via a per-event dedupe key.

In dev the email backend is the console backend (settings), so nothing is sent
externally — the SentNotification log is the source of truth and the demo view.
"""
import datetime
from decimal import Decimal


# Placeholders offered per event — shown as help text in Maintenance.
EVENT_PLACEHOLDERS = {
    'PAYMENT_RELEASED': ['{project}', '{council}', '{program}', '{amount}',
                         '{payment_type}', '{works}', '{addresses}', '{date}'],
    'AGREEMENT_SIGNED': ['{council}', '{agreement}', '{execution_date}', '{date}'],
    'REPORT_APPROVED': ['{project}', '{council}', '{report_type}', '{date}'],
    'REPORT_REJECTED': ['{project}', '{council}', '{report_type}', '{date}'],
    'PROJECT_COMPLETED': ['{project}', '{council}', '{program}', '{works}', '{addresses}', '{date}'],
    'MONTHLY_TRACKER_OVERDUE': ['{council}', '{period}', '{due_date}', '{date}'],
    'QUARTERLY_REPORT_OVERDUE': ['{council}', '{period}', '{due_date}', '{date}'],
    'STAGE_TARGET_DUE': ['{project}', '{council}', '{stage}', '{due_date}', '{days}', '{date}'],
    'STAGE_SUNSET_DUE': ['{project}', '{council}', '{stage}', '{due_date}', '{days}', '{date}'],
}


def _today():
    return datetime.date.today().strftime('%d %b %Y')


class _SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'  # leave unknown placeholders untouched


def render(text, context):
    try:
        return (text or '').format_map(_SafeDict(context or {}))
    except Exception:
        return text or ''


def project_context(project):
    """Common placeholders derived from a project."""
    if project is None:
        return {'date': _today()}
    works = list(project.works.select_related('work_type', 'address').all())
    addresses = list(project.addresses.all()) if hasattr(project, 'addresses') else []
    return {
        'project': project.name,
        'council': project.council.name if project.council_id else '',
        'program': project.program.name if project.program_id else '',
        'financial_year': getattr(project, 'financial_year', '') or '',
        'works': '; '.join(str(w) for w in works) or '—',
        'addresses': '; '.join(str(a) for a in addresses) or '—',
        'date': _today(),
    }


def _recipients_for_council(council):
    if council is None:
        return []
    return list(
        council.contacts.filter(receives_notifications=True)
        .exclude(email='').values_list('email', flat=True)
    )


def _from_email(s):
    from django.conf import settings
    return (s.notifications_from_email or '').strip() \
        or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ricd.qld.gov.au')


def _smtp_connection(s):
    """Build an SMTP connection from the saved SiteSettings, or None for LOG mode."""
    from apps.core.models import SiteSettings
    if s.email_send_mode != SiteSettings.EmailSendMode.SMTP or not s.email_host:
        return None
    from django.core.mail import get_connection
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=s.email_host, port=s.email_port,
        username=s.email_host_user or None, password=s.email_host_password or None,
        use_tls=s.email_use_tls, use_ssl=s.email_use_ssl, fail_silently=False,
    )


def _deliver(subject, body, recipients, s):
    """Send when in SMTP mode; in LOG mode do nothing (the SentNotification IS the
    record). Returns (success, error)."""
    if not recipients:
        return True, ''
    conn = _smtp_connection(s)
    if conn is None:
        return True, ''  # LOG mode — not sent
    try:
        from django.core.mail import EmailMessage
        EmailMessage(subject, body, _from_email(s), recipients, connection=conn).send()
        return True, ''
    except Exception as e:  # never let a mail failure break the triggering save
        return False, str(e)


def send_event_email(event, *, council=None, project=None, context=None, dedupe_key=None):
    """Render + (maybe) send + log the email for `event`. Idempotent on dedupe_key.

    Returns the SentNotification, or None when notifications are disabled / there's
    no active template / it was already sent."""
    from apps.core.models import EmailTemplate, SentNotification, SiteSettings

    s = SiteSettings.get()
    if not s.notifications_enabled:
        return None  # master switch off
    tmpl = EmailTemplate.objects.filter(event=event, is_active=True).first()
    if not tmpl:
        return None
    key = dedupe_key or event
    if SentNotification.objects.filter(dedupe_key=key).exists():
        return None  # already sent

    ctx = context or {}
    ctx.setdefault('date', _today())
    subject = render(tmpl.subject, ctx)
    body = render(tmpl.body, ctx)
    recipients = _recipients_for_council(council)

    success, error = _deliver(subject, body, recipients, s)

    return SentNotification.objects.create(
        event=event, dedupe_key=key,
        council=council, project=project,
        recipients=', '.join(recipients), subject=subject, body=body,
        success=success, error=error,
    )


def send_test_email(to_email):
    """Send a one-off test email using the saved config. Returns (ok, message)."""
    from apps.core.models import SiteSettings
    s = SiteSettings.get()
    if not to_email:
        return False, 'No email address on your user account to send the test to.'
    subject = 'RICD — test notification email'
    body = ('This is a test email from the RICD application to confirm the email '
            'configuration is working.\n\nIf you received this, sending is set up correctly.')
    conn = _smtp_connection(s)
    if conn is None:
        return True, ('Email mode is "Log only" — no email was actually sent. '
                      'Switch to SMTP mode and set a host to send for real.')
    try:
        from django.core.mail import EmailMessage
        EmailMessage(subject, body, _from_email(s), [to_email], connection=conn).send()
        return True, f'Test email sent to {to_email}.'
    except Exception as e:
        return False, f'Send failed: {e}'


def money(value):
    return f"${(value or Decimal('0')):,.2f}"
