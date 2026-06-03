from django.db import migrations

GROUP_NAME = "Standard New Residential Construction"
SCHEDULE_NAME = "Standard 30/60/10"
SITE_ESTABLISHMENT = "Site establishment"
FINAL_STEP = "Final internal clean for handover"

# payment_type, anchor_type, work_step_definition_name, offset_days
RULES = [
    ("FIRST", "PROJECT_START", None, 14),
    ("SECOND", "WORK_STEP", SITE_ESTABLISHMENT, 14),
    ("THIRD", "WORK_STEP", FINAL_STEP, 14),
]


def seed(apps, schema_editor):
    WorkStepGroup = apps.get_model("core", "WorkStepGroup")
    WorkStepDefinition = apps.get_model("core", "WorkStepDefinition")
    Schedule = apps.get_model("core", "PaymentMilestoneSchedule")
    Rule = apps.get_model("core", "PaymentMilestoneRule")

    group = WorkStepGroup.objects.filter(name=GROUP_NAME).first()
    defs = {d.name: d for d in WorkStepDefinition.objects.filter(
        name__in=[SITE_ESTABLISHMENT, FINAL_STEP])}

    schedule, _ = Schedule.objects.get_or_create(
        name=SCHEDULE_NAME,
        defaults={"work_step_group": group, "is_default": True, "is_active": True},
    )
    # Ensure it is the default and (if the group exists) linked to it.
    changed = False
    if not schedule.is_default:
        schedule.is_default = True
        changed = True
    if group and schedule.work_step_group_id is None:
        schedule.work_step_group = group
        changed = True
    if changed:
        schedule.save()

    for payment_type, anchor_type, step_name, offset in RULES:
        step = defs.get(step_name) if step_name else None
        if anchor_type == "WORK_STEP" and step is None:
            # named step not seeded in this DB — fall back to PC so the rule still
            # produces a date rather than silently doing nothing.
            anchor_type = "PROJECT_PC"
        Rule.objects.get_or_create(
            schedule=schedule,
            payment_type=payment_type,
            defaults={
                "anchor_type": anchor_type,
                "work_step_definition": step,
                "offset_days": offset,
            },
        )


def unseed(apps, schema_editor):
    Schedule = apps.get_model("core", "PaymentMilestoneSchedule")
    Schedule.objects.filter(name=SCHEDULE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_remove_payment_forecast_offset_days_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
