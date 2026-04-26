"""
Email utilities for FNC system.

Future Implementation Notes:
---------------------------
To enable email functionality:

1. Configure email settings in settings.py:
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   EMAIL_HOST = 'smtp.office365.com'  # For M365 integration
   EMAIL_PORT = 587
   EMAIL_USE_TLS = True
   EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
   EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

2. Consider using django-celery-email for async email sending:
   CELERY_EMAIL_BACKEND = 'django_celery_email.backends.CeleryEmailBackend'

3. For M365 OAuth2 integration:
   - Use Microsoft Graph API
   - Register app in Azure AD
   - Use msal library for authentication
"""

from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta


def send_overdue_report_reminder(project, report_type, recipients):
    """
    Send reminder for overdue reports.

    Args:
        project: Project instance
        report_type: 'monthly', 'quarterly', 'stage1', or 'stage2'
        recipients: List of email addresses

    Returns:
        bool: True if email sent successfully (or stub returns True)

    TODO: Implement actual email sending
    TODO: Add HTML template for rich email content
    TODO: Add unsubscribe link for recipients
    """
    subject = f"Overdue {report_type.title()} Report - {project.name}"
    message = f"""
    Dear Council,

    This is a reminder that the {report_type} report for project "{project.name}"
    is overdue. Please submit the report as soon as possible.

    Project: {project.name}
    Council: {project.council.name}
    Program: {project.program.name}

    Please log in to the FNC system to submit your report.

    Kind regards,
    FNC System
    """

    # Stub implementation - replace with actual email sending
    # send_mail(
    #     subject=subject,
    #     message=message,
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=recipients,
    #     fail_silently=False,
    # )

    print(f"[STUB] Email sent to {recipients}: {subject}")
    return True


def send_report_submitted_notification(report, recipients):
    """
    Notify FNC users that a report has been submitted for assessment.

    Args:
        report: MonthlyTracker, QuarterlyReport, or StageReport instance
        recipients: List of FNC user email addresses

    TODO: Implement
    """
    subject = f"Report Submitted - {report}"
    print(f"[STUB] Email sent to {recipients}: {subject}")
    return True


def send_report_endorsed_notification(report, recipients):
    """
    Notify FNC users that a report has been endorsed by Council Manager.

    Args:
        report: Report instance
        recipients: List of FNC user email addresses

    TODO: Implement
    """
    subject = f"Report Endorsed - {report}"
    print(f"[STUB] Email sent to {recipients}: {subject}")
    return True


def send_report_approved_notification(report, recipients):
    """
    Notify Council users that a report has been approved by FNC Manager.

    Args:
        report: StageReport instance
        recipients: List of Council user email addresses

    TODO: Implement
    """
    subject = f"Report Approved - {report}"
    print(f"[STUB] Email sent to {recipients}: {subject}")
    return True


def send_payment_released_notification(payment, recipients):
    """
    Notify Council users that a payment has been released.

    Args:
        payment: Payment instance
        recipients: List of Council user email addresses

    TODO: Implement
    """
    subject = f"Payment Released - {payment.project.name}"
    message = f"""
    Dear Council,

    A payment has been released for project "{payment.project.name}".

    Payment Details:
    - Amount: ${payment.amount}
    - Type: {payment.get_payment_type_display()}
    - Reference: {payment.reference}
    - Release Date: {payment.release_date}

    Kind regards,
    FNC System
    """

    print(f"[STUB] Email sent to {recipients}: {subject}")
    return True


def get_overdue_reports(days=14):
    """
    Get reports that are overdue beyond the specified days.

    Args:
        days: Number of days after due date to consider overdue

    Returns:
        dict: Dictionary of overdue reports by type

    TODO: Implement actual query logic
    TODO: Run as scheduled task (Celery beat or cron)
    """
    from apps.reports.models import MonthlyTracker, QuarterlyReport, StageReport

    cutoff_date = timezone.now() - timedelta(days=days)

    # TODO: Implement actual queries
    # monthly = MonthlyTracker.objects.filter(
    #     submitted_at__isnull=True,
    #     created_at__lt=cutoff_date
    # )
    # quarterly = QuarterlyReport.objects.filter(...)
    # stage_reports = StageReport.objects.filter(...)

    return {
        'monthly': [],
        'quarterly': [],
        'stage1': [],
        'stage2': []
    }


def send_warranty_expiry_reminder(days_before=30, recipients=None):
    """
    Send reminders for projects with warranty or defects liability expiring soon.

    Args:
        days_before: Days before expiry to send reminder
        recipients: List of email addresses. If None, gets FNC users.

    Returns:
        dict: Summary of emails sent

    TODO: Implement actual email sending
    TODO: Run as scheduled task (Celery beat or cron)
    """
    from apps.projects.models import Project
    from django.contrib.auth import get_user_model

    User = get_user_model()

    today = timezone.now().date()
    reminder_date = today + timedelta(days=days_before)

    # Find projects with warranty expiring
    warranty_expiring = Project.objects.filter(
        warranty_end_date__lte=reminder_date,
        warranty_end_date__gte=today,
        state=Project.State.COMPLETED
    )

    # Find projects with defects liability expiring
    from apps.defects.models import Defect
    defects_expiring = Defect.objects.filter(
        defects_liability_expiry__lte=reminder_date,
        defects_liability_expiry__gte=today,
        rectified_date__isnull=False
    )

    # Get recipients if not provided
    if not recipients:
        ricd_users = User.objects.filter(
            groups__name__startswith='FNC'
        ).values_list('email', flat=True)
        recipients = list(ricd_users)

    subject = f"Warranty/Defects Liability Expiry Reminder"
    message = f"""
    Dear FNC Team,

    The following projects have warranty or defects liability periods expiring soon:

    WARRANTY EXPIRY:
    {chr(10).join([f"- {p.name} ({p.council.name}) - {p.warranty_end_date}" for p in warranty_expiring]) or "None"}

    DEFECTS LIABILITY EXPIRY:
    {chr(10).join([f"- {d.project.name} ({d.work}) - {d.defects_liability_expiry}" for d in defects_expiring]) or "None"}

    Please follow up with Councils as appropriate.

    Kind regards,
    FNC System
    """

    print(f"[STUB] Email sent to {recipients}: {subject}")
    print(f"  - Warranty expiring: {warranty_expiring.count()}")
    print(f"  - Defects liability expiring: {defects_expiring.count()}")

    return {
        'warranty_expiring': warranty_expiring.count(),
        'defects_expiring': defects_expiring.count(),
        'recipients': recipients
    }


def send_completion_followup_reminder(project, days_after_completion=90):
    """
    Send follow-up reminder after project completion to check on defects.

    Args:
        project: Project instance
        days_after_completion: Days after completion to send reminder

    TODO: Implement
    """
    subject = f"Project Completion Follow-up - {project.name}"
    message = f"""
    Dear FNC Team,

    Project "{project.name}" was completed on {project.completion_date}.

    Please ensure:
    - Defects have been addressed
    - Handover checklist is complete
    - Council is satisfied with completion

    Kind regards,
    FNC System
    """

    print(f"[STUB] Email sent for {project.name}: {subject}")
