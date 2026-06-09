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


def send_event_email(event, *, council=None, project=None, context=None, dedupe_key=None):
    """Render + send (and log) the email for `event`. Idempotent on dedupe_key.

    Returns the SentNotification, or None when there's no active template / it was
    already sent."""
    from django.conf import settings
    from apps.core.models import EmailTemplate, SentNotification, SiteSettings

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

    from_email = (SiteSettings.get().notifications_from_email or '').strip() \
        or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ricd.qld.gov.au')

    success, error = True, ''
    if recipients:
        try:
            from django.core.mail import send_mail
            send_mail(subject, body, from_email, recipients, fail_silently=False)
        except Exception as e:  # don't let a mail failure break the triggering save
            success, error = False, str(e)

    return SentNotification.objects.create(
        event=event, dedupe_key=key,
        council=council, project=project,
        recipients=', '.join(recipients), subject=subject, body=body,
        success=success, error=error,
    )


def money(value):
    return f"${(value or Decimal('0')):,.2f}"
