"""Seed catalogues + templates derived directly from the user's RCPFA spec.

What this migration creates (idempotent via get_or_create):

  WorkStepDefinitions   ~35 named monthly-tracker date columns
                        (Design Tender, Slab, Framing, Lockup, etc.)

  WorkStepGroup         "Standard New Residential Construction"
                        — orders the ~35 definitions, marks each as a
                          monthly-tracker column. (Not linked to any
                          WorkType yet; user assigns via M2M after running.)

  StageItemDefinitions  All unique items needed across Stage 1/2 for both
                        Construction and Land projects.

  StageItemGroups       4 groups:
                          - "Stage 1 — Construction"
                          - "Stage 1 — Land"
                          - "Stage 2 — Construction"
                          - "Stage 2 — Land"
                        Each populated with its items in order. work_types
                        M2M left empty — user assigns once their WorkType
                        catalogue stabilises (one click in the UI per group).

Re-running this migration is safe — every create uses get_or_create.
"""
from django.db import migrations


# ---------------------------------------------------------------------------
# Monthly Tracker date columns (WorkStepDefinitions)
# ---------------------------------------------------------------------------
MONTHLY_TRACKER_STEPS = [
    "Design Tender",
    "Design Award",
    "Construction Tender",
    "Construction Award",
    "Ergon new connection application submitted",
    "Site establishment",
    "Earthworks / Slab",
    "Underground services",
    "Termite prevention",
    "Sub-floor framing or concrete",
    "Wall frames or masonry block walls",
    "Roof framing & battens",
    "Roof sheeting, fascia & gutter",
    "Soffit linings & roof gables",
    "Plumbing & electrical rough-in",
    "Internal wall & ceiling linings",
    "External door & window install",
    "External decks, stairs & balustrade",
    "Waterproofing",
    "Internal floor coverings",
    "Carpentry 2nd fix",
    "Wet area wall linings",
    "Joinery install",
    "Internal painting",
    "External painting",
    "Electrical fit-off",
    "Plumbing fit-off",
    "Carpentry 3rd fix",
    "Fencing & gates",
    "Clothesline",
    "Driveway & paths",
    "Shed",
    "Site clean",
    "Final internal clean for handover",
    "Ergon connection",
]

# Stage gate hints
STAGE1_GATE_STEP = "Construction Award"
STAGE2_GATE_STEP = "Final internal clean for handover"


# Stage 1 — Construction (the Council must do)
STAGE1_CONSTRUCTION = [
    "Keep detailed expenditure records; provide Quarterly Reports within 14 days of quarter-end.",
    "Prepare and obtain State approval of the Land description (Item 5) + Works description (Item 6) + Annexures 1 & 2.",
    "Ensure native title and cultural heritage matters are addressed.",
    "Obtain development approval (or exemption via Department of Housing and Public Works) if required.",
    "Obtain tenure to the Land (if not already held).",
    "Have the Land surveyed (if not already surveyed).",
    "Where Land is to be subdivided: prepare plan of subdivision and provide to the State.",
    "Sign and return the Leases to the State after receipt.",
    "Have the Works designed consistent with the department's Design and Construction Standards for Remote Housing; obtain State approval.",
    "Obtain structural certification of the design.",
    "Invite tenders for the Works (unless Works are being carried out by Council).",
    "Appoint appropriately licensed contractors, or nominate qualified Council employees, to deliver the Works.",
    "Ensure any nominated Council employees have requisite skills, qualifications, licences and experience.",
    "Obtain building approval; ensure all statutory requirements are met by Council and contractors.",
    "Where Works include new infrastructure (roads, pathways, utilities, comms): obtain approvals and engage licensed contractors.",
    "Provide the Stage 1 Report to the State within 14 days of completing these steps.",
]

# Stage 1 — Land
STAGE1_LAND = [
    "Keep detailed expenditure records; provide Quarterly Reports within 14 days of quarter-end.",
    "Prepare and obtain State approval of the Land description (Item 5) + Works description (Item 6) + Annexures 1 & 2.",
    "Ensure native title and cultural heritage matters are addressed.",
    "Obtain tenure to the Land (if not already held).",
    "Have the Land surveyed (if not already surveyed).",
    "Where Land is to be subdivided: prepare plan of subdivision and provide to the State.",
    "Provide a copy of the Development Application for Reconfiguration of Lots.",
    "Sign and return the Leases to the State after receipt.",
    "Appoint a Civil Engineer (RPEQ) to complete Preliminary Operational Work Design — provide Schematic Design, Detailed Design, and Design Certificate.",
    "Have the Works designed consistent with the department's Design and Construction Standards; obtain State approval.",
    "Obtain structural certification of the design.",
    "Obtain development approval (or exemption via Department of Housing and Public Works) if required.",
    "Invite tenders for the Works (unless Works are being carried out by Council).",
    "Appoint appropriately licensed contractors, or nominate qualified Council employees, to deliver the Works.",
    "Ensure any nominated Council employees have requisite skills, qualifications, licences and experience.",
    "Obtain building approval; ensure all statutory requirements are met by Council and contractors.",
    "Where Works include new infrastructure (roads, pathways, utilities, comms): obtain approvals and engage licensed contractors.",
    "Provide the Stage 1 Report to the State within 14 days of completing these steps.",
]

# Stage 2 — Construction / Extension
STAGE2_CONSTRUCTION = [
    "Within one month of Stage 2 Funding release: prepare and provide a detailed Schedule of Works covering Site preparation, Base/slab, Framing, Lock-up, Fixing, and Completion.",
    "Have the remaining Works carried out.",
    "Provide the Quarterly Reports within 14 days of quarter-end.",
    "Provide the Monthly Tracker Reports within 14 days of month-end.",
    "Ensure Practical Completion is achieved; notify the State within 7 days of achievement.",
    "Comply with reasonable handover requirements (warranties, as-constructed drawings, joint inspection — Annexure 4 checklist).",
    "Provide the Stage 2 Report to the State within 14 days of completing these steps.",
]

# Stage 2 — Land
STAGE2_LAND = [
    "Have the remaining Works carried out.",
    "Provide the Quarterly Reports within 14 days of quarter-end.",
    "Provide the Monthly Tracker Reports within 14 days of month-end.",
    "Ensure Practical Completion is achieved; notify the State within 7 days of achievement.",
    "Comply with reasonable handover requirements (warranties, as-constructed drawings, joint inspection — Annexure 4 checklist).",
    "Provide the Stage 2 Report to the State within 14 days of completing these steps.",
]


def _seed(apps, schema_editor):
    WorkStepDefinition = apps.get_model("core", "WorkStepDefinition")
    WorkStepGroup = apps.get_model("core", "WorkStepGroup")
    WorkStepGroupItem = apps.get_model("core", "WorkStepGroupItem")
    StageItemDefinition = apps.get_model("core", "StageItemDefinition")
    StageItemGroup = apps.get_model("core", "StageItemGroup")
    StageItemGroupItem = apps.get_model("core", "StageItemGroupItem")

    # --- Monthly Tracker WorkStepDefinitions -------------------------------
    step_by_name = {}
    for name in MONTHLY_TRACKER_STEPS:
        obj, _ = WorkStepDefinition.objects.get_or_create(
            name=name, defaults={"description": "", "is_active": True}
        )
        step_by_name[name] = obj

    # --- WorkStepGroup: Standard New Residential Construction --------------
    group, created = WorkStepGroup.objects.get_or_create(
        name="Standard New Residential Construction",
        defaults={
            "description": (
                "Default Monthly Tracker template covering design tender through "
                "to handover for new residential builds. Link this group to the "
                "Work Types it applies to (House, Duplex, Townhouse, Unit, etc.) "
                "via the work_types M2M."
            ),
            "is_active": True,
        },
    )
    if created or not group.items.exists():
        n = len(MONTHLY_TRACKER_STEPS)
        share_pct = round(100 / n, 2)
        used = round(share_pct * (n - 1), 2)
        last_share = round(100 - used, 2)
        for idx, name in enumerate(MONTHLY_TRACKER_STEPS, start=1):
            stage_gate = ""
            if name == STAGE1_GATE_STEP:
                stage_gate = "STAGE1"
            elif name == STAGE2_GATE_STEP:
                stage_gate = "STAGE2"
            cost_pct = last_share if idx == n else share_pct
            WorkStepGroupItem.objects.get_or_create(
                group=group, order=idx,
                defaults={
                    "step": step_by_name[name],
                    "cost_percentage": cost_pct,
                    "expected_duration_days": 7,
                    "stage_gate": stage_gate,
                    "is_monthly_tracker_column": True,
                },
            )

    # --- StageItemDefinitions ----------------------------------------------
    def def_for(text):
        obj, _ = StageItemDefinition.objects.get_or_create(
            name=text, defaults={"description": "", "is_active": True}
        )
        return obj

    # --- StageItemGroups ----------------------------------------------------
    seed_groups = [
        ("STAGE1", "Stage 1 — Construction", STAGE1_CONSTRUCTION),
        ("STAGE1", "Stage 1 — Land",         STAGE1_LAND),
        ("STAGE2", "Stage 2 — Construction", STAGE2_CONSTRUCTION),
        ("STAGE2", "Stage 2 — Land",         STAGE2_LAND),
    ]
    for stage_type, name, item_texts in seed_groups:
        g, created = StageItemGroup.objects.get_or_create(
            stage_type=stage_type, name=name,
            defaults={"description": "", "is_active": True},
        )
        if created or not g.items.exists():
            for order_idx, text in enumerate(item_texts, start=1):
                defn = def_for(text)
                StageItemGroupItem.objects.get_or_create(
                    group=g, order=order_idx,
                    defaults={
                        "item": defn,
                        "field_type": "DATE",
                        "is_required": True,
                        "requires_attachment": False,
                        "help_text": "",
                    },
                )


def _unseed(apps, schema_editor):
    """Reverse seed — delete by names so we don't kill user-created rows."""
    WorkStepDefinition = apps.get_model("core", "WorkStepDefinition")
    WorkStepGroup = apps.get_model("core", "WorkStepGroup")
    StageItemDefinition = apps.get_model("core", "StageItemDefinition")
    StageItemGroup = apps.get_model("core", "StageItemGroup")

    WorkStepGroup.objects.filter(name="Standard New Residential Construction").delete()
    WorkStepDefinition.objects.filter(name__in=MONTHLY_TRACKER_STEPS).delete()

    for nm in (
        "Stage 1 — Construction", "Stage 1 — Land",
        "Stage 2 — Construction", "Stage 2 — Land",
    ):
        StageItemGroup.objects.filter(name=nm).delete()
    all_texts = set(STAGE1_CONSTRUCTION) | set(STAGE1_LAND) | set(STAGE2_CONSTRUCTION) | set(STAGE2_LAND)
    StageItemDefinition.objects.filter(name__in=all_texts).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_workstep_m2m_and_stage_worktypes"),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
