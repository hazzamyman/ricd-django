# First Nations Capital — Enhancement Backlog

Source: review of `docs/FirstNationsCapital.md` (the FNC operating manual)
against the RICDapp codebase as of 2026-05-25. Items here are gaps between
what the manual describes and what the system models / supports today.

**Status legend**

- 🎯 **NEXT** — agreed next priority
- 🔵 **Planned** — agreed as a future build, not yet scheduled
- ⚪ **Candidate** — captured for consideration; needs business input
- 🔗 **External-only** — stays as a URL / manual link; the system stores a
  reference but does not integrate

**Sizing**

- **XS** — < 1 hour (one form field, one signal, one migration)
- **S** — half day (one new model + minimal UI)
- **M** — full day (new model + UI + signals + tests)
- **L** — multi-day (model + workflow + UI + automation + reports + tests)
- **XL** — > 1 week (multiple inter-locking models, significant UX work)

---

## TIER 1 — Daily / weekly operational workflows

These are workflows that happen multiple times per week and are currently
invisible to the system (people are doing them via email, spreadsheets,
SharePoint).

### 🔵 1.1 GPEV payment request workflow

**Manual:** First / Second / Last Payment sections (pages 10–12 and 16).

**What's needed:** Track the 5-stage email workflow that happens between
`Payment.APPROVED` and `Payment.RELEASED`:

1. Relevant team compiles all docs + reconciles
2. Email to Principal Business Support Officer (PBSO)
3. PBSO prepares GPEV draft email + liaises with Finance for coding
4. Manager endorses
5. Director approves and sends email to BPAS
6. BPAS submits the GPEV → SAP doc number returned
7. RCTI saved + sent to Council CEO/CFO

**Model sketch:** `PaymentRequest(payment, stage, performed_by, performed_at,
notes, supporting_documents_uri)`. Stage transitions follow the chain above
with role gating. Surface a "Who's holding this up?" panel on Payment detail.

**Size:** L. Touches Payment workflow, RBAC roles, email templates, audit log.

**Dependency:** None hard; integrates cleanly with existing Approval model.

### 🔵 1.2 Breach of Contract tracking + escalation

**Manual:** Breach of Contract / Failure to comply (page 27). 19 named breach
types with citations.

**What's needed:** Capture breach events linked to a Council and/or FS:

- `BreachType` lookup (19 known + custom)
- `Breach(council, funding_schedule, breach_type, breach_sentence,
  identified_date, due_date_for_response, status, escalation_level)`
- `BreachAction(breach, level, performed_by, performed_at,
  action_type=email/phone, summary, due_by)`
- Auto-suggest escalation when `due_by` passes with status still OPEN.
- Generate notice letters from templates when escalating to formal Notice.

**Size:** L. New domain area; needs RBAC integration + notification triggers.

### 🔵 1.3 End of Month Reconciliation export view

**Manual:** End of Month Reporting (page 16).

**What's needed:** A `/reports/eom/` view that exports the 4 EOM tabs matching
the SharePoint sheet format:

- **Contracted / Not yet in Construction** — FSes with EXECUTED status and no
  child Project in COMMENCED/UC state.
- **Forecast Commencements** — pipeline projects with expected start in current
  / forward FY.
- **In Construction** — projects in COMMENCED/UC state.
- **Forecast Completions** — projects with `forecast_practical_completion_date`
  in current / forward FY.

Each row needs address, RICD rep, risk status, comments. Yellow-highlight cells
that changed since last EOM (track snapshots).

**Size:** M. Mostly view + export logic; no new models if we add an `eom_notes`
field per Project.

### 🔵 1.4 Construction Creation List export

**Manual:** Construction Creation List / Property Registration (page 17).

**What's needed:** Monthly export listing forecast handovers in the next 5
months, by suburb/LGA, with Reside PLC, RICD rep, RPD, comments. Highlight
differences from previous month's submission.

**Size:** S. View + CSV/Excel export. Project.handover_date already exists.

### 🔵 1.5 Letter to Council as a tracked artefact

**Manual:** Draft Letter sections (pages 8 + 11). "DDG wants to send ALL
letters out for new funding schedules" (March 2026 onward).

**What's needed:** `CouncilLetter(funding_schedule, type, recipient,
mincor_ref, status=draft/endorsed/sent, signed_by, sent_date, document_uri)`.
Status workflow draft → manager endorsed → director endorsed → DDG signed →
sent.

**Size:** M. New model + endorsement workflow + integration with the FS
execution chain.

### 🔵 1.6 Reminder email workflow for reports

**Manual:** Performance Management → Quarterly Report (page 24).

**What's needed:** Scheduled task that fires:

- 1 week before quarter end → reminder email to CEO + Works Manager +
  Project Officer
- Due-date passed → overdue email to Council, CC Manager + officers
- Every 2 weeks while overdue → escalation up the chain (Manager → Director →
  ED → GM)

Track which reminders have been sent + responses. Stop the cycle when the
report is submitted.

**Size:** L. Needs a scheduled task runner (Celery beat or `django-q`), email
templates, escalation logic, audit trail. Same pattern reusable for breaches.

---

## TIER 2 — Strategic / contract management

### 🎯 2.1 Contract Management Report per FS + Council — NEXT PRIORITY

**Manual:** "For Discussion" section on page 18 explicitly asks how to
document contract management. "Performance Management" + "Financial
Management" sections describe the inputs.

**What's needed:** Two views generating "where is this contract at" reports:

- **Per Funding Schedule:** payments made (status + dates + SAP refs),
  expenditure to date (council-reported via QR vs amount paid via Payment),
  unspent funds calculation, discrepancies flagged, meeting log (kick-off,
  Stage 1 CM, close-out), risk register entries, breach history.
- **Per Council:** roll-up across all active FSes; total committed, total
  paid, total unspent, list of overdue obligations.

**Model implications:**

- New `ContractMeeting(funding_schedule, type=kickoff/stage1_cm/close_out,
  date, attendees, notes_uri)` — overlaps with item 3.1 below; build once.
- The report itself can be a view + PDF export, no new persistent model
  needed. All inputs already exist in the database (Payment, QR, breach,
  meeting).

**Size:** M for views + L if we add PDF export + autosave-on-quarter-end.

**Dependencies:** Easier if 2.4 (QR content fields) and 1.2 (breach tracking)
are done first, since the CM report aggregates them. But can ship a "v1"
that just surfaces what's available today.

### 🔵 2.2 Strategic Capital Plan (SCP)

**Manual:** Strategic Capital Plan Process (page 5–6) — 60+ lines of detail.

**What's needed:** Where projects come from before they're "Prospective".

- `StrategicCapitalPlan(council, version, status=draft/endorsed/superseded,
  endorsed_date, vision, housing_needs_summary, document_uri)`
- `SCPProject(scp, name, type, indicative_cost, year_index_in_pipeline,
  priority, rationale)` — the 10-year pipeline items
- Annual review cycle: when 12 months pass since endorsement, prompt to
  review.
- Promote SCPProject → Project (creates a PROSPECTIVE Project, links back to
  SCP for traceability)

**Size:** L. New domain area. UX needs an "SCP editor" page.

### 🔵 2.3 Lease model

**Manual:** Multiple references — Item 7 of FS, Stage 3 clause, RILIPO
request to draft lease, "Failure to Grant Leases" breach (item 16 of breach
table).

**What's needed:** Track the 40-year leases from Council to State for Social
Housing:

- `Lease(council, funding_schedule, lease_type=40year/holding,
  lots/parcels=[...], term_years, granted_date, executed_date, expiry_date,
  document_uri, status, council_is_registered_housing_provider)`
- Field on `FundingSchedule.lease_clause_type` =
  `RegisteredHousingProvider` | `40YearLease` (Item 7 of FS quality check).
- RILIPO assignment + drafting workflow (request when Stage 2 payment
  released).

**Size:** M.

### 🔵 2.4 Quarterly Report content expansion

**Manual:** Quarterly Report (one off) section (page 23) + breach categories.

**What's needed:** Expand `QuarterlyReport` model with the fields the Funding
Agreement actually requires:

- `pct_works_completed: Decimal`
- `total_expenditure_to_date: Decimal`
- `unspent_funding: Decimal`
- `adverse_matters: Text`
- `council_contribution: Decimal` + `other_party_contribution: Decimal`
- `total_employed: Int`
- `local_indigenous_employed: Int`
- `indigenous_businesses_engaged: Int`
- New child models: `QuarterlyReportExpenditureItem(qr, description, amount)`
  for the itemised expenditure statement
- Attachments: bank statements, photographs (already supported via
  `QuarterlyReportAttachment`)

**Size:** M. Mostly migrations + form expansion.

---

## TIER 3 — Meetings + relationship tracking

### 🔵 3.1 Meetings module (Kick-off / CM / Close-out)

**Manual:** Contract Management Meetings (pages 18–19).

**What's needed:** A single `Meeting` model with type discriminator covering:

- Kick-off (`[Council] RCPFA FS#N KO`) — start of new FS
- Stage 1 CM meeting — after Stage 1 reported complete
- Close-out / Lessons Learned (`[Council] RCPFA FS#N LL` + `CO`) — end of FS
- TWG (Technical Working Group) — periodic
- Site visit — Stage target/sunset aligned, see 3.2 below

Fields: `funding_schedule (nullable for TWG), type, date, attendees,
agenda_summary, minutes_uri, notes`. Surface meeting log on FS detail.

**Size:** S–M. Co-dependency with 2.1.

### 🔵 3.2 Site visit tracking

**Manual:** Site Visits and Progress Verification (page 28).

**What's needed:** Either reuse the Meeting model with type=site_visit, or a
dedicated `SiteVisit(project, council, planned_date, actual_date, attendees,
observations, photos_uri, follow_up_actions, linked_stage)`.

Auto-suggest one before each Stage target date.

**Size:** S.

### 🔵 3.3 Risk Register

**Manual:** Risk Management table (pages 17–18) + naming convention
`[Council] RCPFA FS#N RR`.

**What's needed:** `RiskRegisterEntry(funding_schedule, risk_event, cause,
impact, likelihood, control, owner, status, last_reviewed)`. Surface as a
tab on FS detail. Templated entries from the 8 generic risk events in the
manual.

**Size:** S.

---

## TIER 4 — Reference data + form completeness

### 🔵 4.1 Human Rights Assessment artefact

**Manual:** Financial Approval (page 7). Naming convention `[Council] HRA`.

**What's needed:** Add `human_rights_assessment_uri` field to `BFA` (or
`BFAItem`). Track that one exists when the brief is endorsed.

**Size:** XS.

### 🔵 4.2 Council bank account storage

**Manual:** First Payment (page 10) — "FNC should confirm with the CEO or
CFO of Council what their bank account details are".

**What's needed:** `CouncilBankAccount(council, bsb, account_number,
account_name, last_confirmed_date, confirmed_by, is_active)`. Reference on
Payment when releasing.

**Size:** S. Sensitive data — needs RBAC restriction.

### 🔵 4.3 Council contribution amount (Item 6 of FS)

**Manual:** Funding Schedule QA checklist Item 6 (page 31).

**What's needed:** Add `FundingSchedule.council_contribution_amount` field
(default 0) for the rare cases when council contributes own funds.

**Size:** XS.

### 🔵 4.4 Lease clause type on FS (Item 7 of FS)

**Manual:** FS QA checklist Item 7 (page 31). Field selects between
"Registered Housing Provider" clause vs "40-year lease" clause.

**What's needed:** `FundingSchedule.lease_clause_type` choice field. Will
become required when 2.3 (Lease model) lands.

**Size:** XS.

### 🔵 4.5 Indicative costings population

**Manual:** Indicative Costs section (page 7) lists categories but values
are blank in the manual.

**What's needed:** Once team confirms 2024/25 values, populate `NotionalCost`
rows (model already exists) for:

- Land lot development
- Dwelling (per bedrooms)
- Extension
- Demolish existing property

**Size:** XS (data only).

### 🔵 4.6 FS / RCPFA / Letter Quality Assurance checklists

**Manual:** Annexure 1 / 2 / 3 (pages 29–32). Multi-question checklists run
when drafting.

**What's needed:** Implement these as in-app checklists with auto-pass where
possible (e.g. "Is FS number unique for this council?" can be data-checked).
Surface a "QA score" before allowing the FS to move past DRAFT.

**Size:** M.

---

## TIER 5 — External / integration boundaries (decided: ALWAYS EXTERNAL)

🔗 The following stay as **URL / reference fields only**. The system stores a
reference (URL, ID, document path) but does not call out to these systems:

- **Reside PLC** — `Address.residence_plc_ref` already exists; no API
  integration.
- **BEIIS** — used externally to find Lot/Plan/Title references; we store
  the result on Address.
- **eEnquiries (Titles Queensland)** — used externally for title docs; we
  store the title reference.
- **OpenDocs Content Manager** — `document_uri` URL field everywhere; no API.
- **SharePoint** — same; URLs only.
- **Master Data spreadsheet** — system is replacing this; no migration
  needed beyond seeded suburbs / electorates / lookup data.
- **OGM MINCOR** — email-driven; `mincor_reference` is text only.
- **MyTravel / Shifts / Leave Calendar** — out of scope; user/staff
  lifecycle is HR not project delivery.
- **Power BI reports (CSM007, ALL013)** — useful external data sources for
  housing register / overcrowding; not integrated.
- **ABS monthly Building Approval data** — separate workflow; if useful,
  build an export view (like 1.3 / 1.4) but don't integrate the submission.
- **HSData / Tenancy Team** request emails — manual workflow.

---

## Cross-cutting workflow patterns observed

A few patterns repeat across many Tier 1/2 items — building these as shared
infrastructure once would unlock multiple features:

### A. Email-driven workflow tracker

GPEV requests (1.1), breach escalation (1.2), reminder emails (1.6),
endorsement chains (Brief, FS, Letter to council) all share the same shape:
**multi-stage approval with role gating + audit trail + email artefacts**.
The existing `Approval` + `WorkflowAction` models already capture some of
this; a generic `ApprovalChain(steps[], current_step, status)` infra would
slot in.

**Size:** L for the infra, S each to plug a workflow in afterwards.

### B. Document attachments with naming conventions

The manual specifies naming patterns for many artefacts
(`YYYYMMDD_Document-name`, `[Council] RCPFA FS#N XX`). A generic
`Attachment(content_object, type, document_uri, name, generated_filename)`
with auto-generation of the expected filename from a template would enforce
the convention everywhere.

**Size:** M.

### C. Recurring task / scheduled job runner

Quarterly Report reminders (1.6), annual SCP review (2.2), monthly EOM (1.3)
and Construction Creation List (1.4) all need scheduled triggers. Need a job
runner — either Celery + beat, or `django-q`, or `django-apscheduler`.

**Size:** S to bring in + configure; reusable everywhere.

---

## Suggested sequencing for upcoming sessions

When the team is ready, suggested order:

1. **2.1 Contract Management Report (🎯 NEXT)** — biggest single user-facing
   win, lots of existing data to surface. Optional pre-requisites: light QR
   field expansion (subset of 2.4) and the meetings model (3.1) — but can
   ship a "v1" that surfaces only what's already in the DB today.
2. **1.5 Letter to Council** — closes the funding-execution loop.
3. **1.1 GPEV payment request** — closes the payment-release loop, AND
   provides the test case for the generic Approval Chain infra (Pattern A).
4. **1.2 Breach tracking + 1.6 Reminder workflow** — both share the
   scheduled task runner (Pattern C) and email infra.
5. **2.4 QR content + 2.3 Lease + 4.x form completeness** — domain model
   polish.
6. **2.2 SCP** — strategic planning. Largest piece.
7. **3.x meetings / site visits / risk register** — relationship / contract
   management depth.

Items in Tier 4 are mostly XS/S and can be slotted in opportunistically as
they come up during related work.

---

## Already shipped (for reference)

These items came up during the manual review and ARE already in the system:

- ✅ Council, Program, Project, FundingAgreement (1:1 per council),
  FundingSchedule, BFA (multi-project + co-funding + document_uri + MINCOR
  ref), PaymentRule + Milestones, Payment + PaymentAllocation (locked
  per-program snapshots), Variation + VariationDeed + VariationItem
- ✅ Report models: StageReport (per-FS), QuarterlyReport (per-council),
  MonthlyTracker (basic)
- ✅ Approval + Delegation (matches the financial delegation thresholds
  table in the manual)
- ✅ AuditLog + WorkflowAction (signal-driven event capture)
- ✅ Practical Completion + Handover dates (per-Work with Project/Address
  aggregates, bulk-set, sunset-breach warning)
- ✅ Cashflow forecast (per-Program × per-FY matrix, locked actuals,
  on-the-fly forecasts)
- ✅ Suburb / StateElectorate / FederalElectorate / QhigiRegion with 53
  seeded QLD suburbs
- ✅ Comments + Notices (generic content type system)
- ✅ Defects (per-project)
- ✅ Address + Suburb + Electorate lookups
- ✅ Project state lifecycle (PROSPECTIVE → PROGRAMMED → FUNDED → COMMENCED
  → UNDER_CONSTRUCTION → COMPLETED)
- ✅ FundingSchedule state lifecycle (DRAFT → READY_FOR_EXECUTION → EXECUTED
  → ACTIVE → COMPLETED / SUPERSEDED / CANCELLED)
- ✅ WorkStep / WorkStepGroup / NotionalCost (Capital Works cashflow path)
- ✅ Popup "+ Add" pattern for lookups (Suburb on Address form, WorkType on
  Work form)
