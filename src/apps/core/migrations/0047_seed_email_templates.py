from django.db import migrations

# event, subject, body  (placeholders are {tokens})
TEMPLATES = [
    ("PAYMENT_RELEASED",
     "Payment released — {project}",
     "Dear {council},\n\n"
     "A {payment_type} of {amount} has been released for project \"{project}\" "
     "({program}).\n\n"
     "Works: {works}\n\n"
     "Released on {date}.\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("AGREEMENT_SIGNED",
     "Funding agreement signed — {council}",
     "Dear {council},\n\n"
     "The funding agreement \"{agreement}\" has been executed"
     " (execution date {execution_date}).\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("REPORT_APPROVED",
     "{report_type} approved — {project}",
     "Dear {council},\n\n"
     "Your {report_type} for project \"{project}\" has been approved on {date}.\n\n"
     "Thank you.\n\nRegards,\nFirst Nations Capital (RICD)"),

    ("REPORT_REJECTED",
     "{report_type} returned — {project}",
     "Dear {council},\n\n"
     "Your {report_type} for project \"{project}\" has been returned for revision "
     "on {date}. Please review the comments and resubmit.\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("PROJECT_COMPLETED",
     "Project completed — {project}",
     "Dear {council},\n\n"
     "Project \"{project}\" ({program}) has been marked complete on {date}.\n\n"
     "Works: {works}\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("MONTHLY_TRACKER_OVERDUE",
     "Monthly tracker overdue — {council}",
     "Dear {council},\n\n"
     "The Monthly Tracker for {period} is overdue (was due {due_date}). "
     "Please submit it as soon as possible.\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("QUARTERLY_REPORT_OVERDUE",
     "Quarterly report overdue — {council}",
     "Dear {council},\n\n"
     "The Quarterly Report for {period} is overdue (was due {due_date}). "
     "Please submit it as soon as possible.\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("STAGE_TARGET_DUE",
     "{stage} target approaching — {project}",
     "Dear {council},\n\n"
     "The {stage} target date for project \"{project}\" is {due_date} "
     "({days} away).\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),

    ("STAGE_SUNSET_DUE",
     "{stage} sunset approaching — {project}",
     "Dear {council},\n\n"
     "The {stage} sunset date for project \"{project}\" is {due_date} "
     "({days} away). Funding may lapse if the milestone is not met.\n\n"
     "Regards,\nFirst Nations Capital (RICD)"),
]


def seed(apps, schema_editor):
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    for event, subject, body in TEMPLATES:
        EmailTemplate.objects.get_or_create(
            event=event, defaults={"subject": subject, "body": body, "is_active": True}
        )


def unseed(apps, schema_editor):
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    EmailTemplate.objects.filter(event__in=[t[0] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0046_emailtemplate_councilcontact_receives_notifications_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
