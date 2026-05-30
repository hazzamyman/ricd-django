# Claude Design — Prompt Pack for RICDapp

Use each section below as a standalone prompt when asking **Claude Design** (or any visual-spec AI) to design a polished version of the listed page. Each prompt is self-contained: it states the page purpose, the audience, the data available, the actions, the existing style tokens, and the empty/error/loading states.

Paste the entire section starting at `## Prompt` for the page you want.

---

## Global style tokens (paste at top of every prompt)

```
RICDapp uses a "Stripe meets Atlassian" palette — deep teal brand over a slate-neutral
base. Generous whitespace, subtle borders, WCAG-AA contrast. Use these CSS tokens
that are already wired in base.html:

  --bg:        #f6f8fa     (page background)
  --panel:     #ffffff     (cards)
  --panel-alt: #f8fafc     (table head, soft surfaces)
  --line:      #e5e7eb     (default border)
  --line-2:    #d1d5db     (input border, hover)
  --line-soft: #eef1f4     (divider)
  --ink:       #0f172a     (primary text)
  --ink-2:     #1f2937
  --muted:     #64748b     (secondary text)
  --muted-2:   #94a3b8
  --brand:     #0f5d6b     (deep teal — primary buttons, active nav)
  --brand-700: #0a4955     (hover)
  --brand-50:  #e6f1f3     (subtle brand background)

  status families — each has bg/fg/bd variants:
  --st-grey   slate    (Draft / Inactive / Prospective)
  --st-amber  goldenrod(Programmed / Pending / Warning / Sunset risk)
  --st-blue   indigo   (Funded / Submitted / Recommended / Approved / UnderConstr)
  --st-green  emerald  (Active / Released / Completed / On Track)
  --st-red    crimson  (Rejected / Cancelled / Overdue / Money-negative)

Reusable classes already defined in base.html:
  .kpi                          — tile with .label and .value
  .pill .grey/.amber/.blue/.green/.red
  .state-badge .state-<lower>
  .sec-h                        — section header (h2 + side action)
  .pg-head                      — page header with h1 + .meta + .actions
  .money-neg                    — applied automatically by {{ x|money }} filter

Typography: Inter (UI), JetBrains Mono (codes/SAP refs). Page padding 18-24px.
Card radius 8px, button radius 6px. Sidebar is 220px fixed left.
Framework: Django templates + Bootstrap 5.3 + vanilla JS. No React, no Tailwind.
```

---

## Prompt 1 — Project Detail Page

### Audience
RICD FNC staff (officers, managers) and Council users. FNC sees full data; Council sees only their own council's projects.

### Page purpose
The Project Detail page is the operational hub for a single project. From here a user must be able to:
1. **Understand at a glance**: what state is this project in, who's leading it, what's the funding picture, when does PC happen, is anything at risk.
2. **Drill into Works/Addresses** to manage the physical asset list.
3. **Review Funding** — which BFA approved how much, which Funding Schedule covers it, how much has been released to council.
4. **Review Payments** released against the schedule with their statuses and SAP refs.
5. **Review Reports** (Stage 1/2, Quarterly, Monthly Tracker).
6. **Set or anchor the rolling forecast** for handover/PC via the project-level bulk-set form (applies to all child Works).
7. **See and post Comments** (internal + council-visible).

### Tab layout (already in code)
1. **Overview**  — KPIs + project details + funding split + Set Dates form (this is the most-viewed tab)
2. **Addresses & Works** — list of addresses, list of works, links to per-work detail (the rolling forecast schedule)
3. **Funding** — BFAs and Funding Schedules covering this project
4. **Payments** — payment timeline + per-payment status
5. **Reports** — Stage reports + Quarterly + Monthly Tracker entries
6. **Documents** — external links to OpenDocs / Shared Drive / Sharepoint
7. **Comments** — threaded internal + external comments

### Available data (Project model + relations)
- `project.name`, `project.state` (PROS/PROG/FUND/COMM/UC/COMP), `project.project_type` (DWELLING / LAND)
- `project.council`, `project.program` (with cost_centre, gl_code)
- `project.financial_year` (FY commenced, e.g. "2025-2026"), `project.financial_year_completed`
- `project.sap_ion` (SAP Internal Order Number)
- `project.cli_no`, `project.initial_caa_date` *(advanced/hidden by default — toggle in form)*
- `project.start_date`, `project.stage1_target_date`, `project.stage2_target_date`, `project.stage2_sunset_date`
- `project.forecast_practical_completion_date`, `project.practical_completion_date` (aggregates from child works)
- `project.forecast_handover_date`, `project.handover_date` (aggregates)
- `project.pc_breaches_sunset` — boolean, true if forecast PC > Stage 2 Sunset + 30 days
- `project.effective_lead_officer` — User (falls back to council.lead_officer)
- `project.principal_officer`, `project.senior_officer` (RICD staff)
- `project.bfa_program_ratios()` — dict `{program_id: Decimal_ratio}` for cofunding
- `project.works.all()`, `project.addresses.all()`, `project.funding_schedules.all()`, `project.payments.all()`
- `project.contracts.all()`, `project.financial_approvals` (BFAs that include this project)
- `project.land_pre_conditions.all()` — **LAND projects only**: list of `LandPreCondition` with `.category` (Native Title / Environmental / DA / Survey), `.status` (RED / AMB / GRN), `.native_title_type` (ILUA / 24JAA / 24KAA / Extinguished), `.completed_date`, `.notes`

### Required design treatments
- **Page header**: project name as h1; meta strip with state-badge, Council link, Program link, FY, Lead Officer (with "(council default)" hint if inherited), Completion date if set
- **KPI row (top of Overview tab)**: 4–5 tiles
  - Approved (BFA) total — sum from BFAItems
  - Released to date (sum of PaymentAllocations)
  - Drawdown % (released / approved * 100)
  - Forecast PC date (with sunset-risk badge if applicable)
  - Stage state badge (large)
- **Date timeline visualization**: horizontal bar/timeline showing Start → Stage 1 Target → Stage 1 Sunset → Stage 2 Target → Stage 2 Sunset → PC (forecast) → Handover (forecast). Mark actual dates in green, forecasts muted, sunset risk amber/red.
- **"Set Dates" panel**: 5-column form (Actual Start, Forecast PC, Actual PC, Forecast Handover, Actual Handover). Setting Actual Start anchors the rolling forecast — make this prominent. Single "Apply to all works" button.
- **Funding split block**: if cofunded across multiple programs, show a stacked bar with each program's slice (color-coded), cost centre + GL listed below each
- **Out-of-sync warning**: if `project.dates_in_sync` is False, an amber callout linking back to the Funding Schedule for "edit FS dates (cascades to project)"
- **Quick actions**: Edit, Delete, Add Work, Add Address, Open Stage 1 Report, Open Stage 2 Report, Open Quarterly Report

### Empty / loading / error states
- New project with no Works yet: empty state on Works tab with "Add your first Work" CTA + link to bulk-add via address creation
- No Funding yet: Funding tab shows "No BFA approved. Once a BFA is approved, allocations appear here." plus a "Request BFA" CTA
- Failed save on Set Dates: inline error per field, success toast otherwise

### Prompt
> Design a polished Project Detail page for RICDapp using the style tokens above. The page has 7 tabs (Overview, Addresses & Works, Funding, Payments, Reports, Documents, Comments). Make the Overview tab visually impressive — it's the most-viewed page in the app. Emphasise: project state badge, KPI tiles for Approved/Released/Drawdown/Forecast PC, a horizontal date timeline (Start → Stage 1 → Stage 2 → PC → Handover) with actuals in green and forecasts muted, sunset-risk warning when forecast PC > Stage 2 Sunset + 30 days. Include a "Set Dates" form that lets the user bulk-set Actual Start (anchors rolling forecast), Forecast/Actual PC, Forecast/Actual Handover for all child Works — making "Actual Start" the prominent primary input. Show the cofunding split when a project draws from multiple programs (e.g., 60% from CHIP, 40% from RCAP) as a stacked bar with program name + cost centre + GL beneath each segment. Keep the tab strip Stripe-clean (underlined active tab, no boxy borders). Layout: 220px fixed sidebar, 56px navbar at top, content area uses 18-24px padding.

---

## Prompt 2 — Works & Addresses Page (project sub-page)

### Audience
Construction-team users + RICD officers. This is where day-to-day Work tracking happens.

### Page purpose
Browse and manage the works and addresses belonging to a project. From here:
1. List every Address with its lot/plan/street and the works attached
2. List every Work with its type, bedrooms, quantity, estimated cost, status, **and the rolling forecast schedule**
3. Drill into a Work detail (which has the editable per-step grid built last)
4. Bulk-add multiple works at once when seeding a project
5. See sunset-risk badges on works whose forecast PC pushes past Stage 2 sunset + 30 days

### Available data
- `address.suburb_link` (FK to Suburb with state_electorate_link / federal_electorate_link / qhigi_region), `address.street`, `address.lot`, `address.plan`
- `address.livable_housing_level` (Silver / Gold / Platinum — Livable Housing Design guideline)
- `address.usage_type` (Public Housing / Affordable / Community / Mixed Use)
- `address.lease_status` (Not Required / Pending / Executed) + `address.lease_executed_date`
- *Advanced/collapsed:* `address.floor_number`, `address.land_status` (Available / Acquired / Crown / Transfer Pending)
- *Advanced/collapsed:* `address.floor_material`, `address.frame_material`, `address.wall_material`, `address.roof_material`, `address.car_accommodation` (free text — recorded as-built)
- *Advanced/collapsed:* `address.bathrooms_count`, `address.kitchens_count`, `address.living_rooms_count`
- `work.work_type` (FK), `work.work_type_other`, `work.bedrooms`, `work.quantity`
- `work.estimated_cost`, `work.actual_cost`, `work.forecast_final_cost`, `work.costs_finalised`
- `work.total_estimated_cost`, `work.cost_source`
- `work.contractor` (FK to Contractor — name, trade type)
- `work.floor_area` (m²), `work.drawing_no`, `work.notes`
- `work.status` (PENDING / IN_PROGRESS / COMPLETED)
- `work.cashflow_method` (Capital Grants milestone vs WorkStep progressive)
- `work.step_group` — link to the template (via the M2M group we built)
- `work.actual_start_date`, `work.forecast_practical_completion_date`, `work.practical_completion_date`
- `work.forecast_handover_date`, `work.handover_date`
- `work.pc_breaches_sunset` — boolean
- `work.steps.all()` — ordered list of WorkStep with forecast + actual dates per step

### Required design treatments
- **Two columns or two stacked sections**: Addresses (left/top), Works (right/bottom). Each gets its own card.
- **Addresses table**: street + lot/plan, suburb, electorates as soft pills, work count badge, Livable Housing level badge (Silver/Gold/Platinum → grey/amber/blue pill), lease-status lock icon (green when Executed)
- **Works table**: address, type + bedrooms, quantity, status, contractor name (muted), total estimated cost (right-aligned, `$X,XXX.00`), forecast PC (muted) or actual PC (green), sunset-risk pill if applicable
- **Per-work row click**: opens Work Detail with the rolling-forecast grid
- **Bulk add**: a "+ Add bulk works" action that opens a modal/inline form with address picker + work type picker + bedrooms + quantity + cost; can add 5-10 works in one go
- **Status filter chips**: at the top — All / Pending / In Progress / Completed
- **Search**: by street / lot / work type
- **CSV export** button

### Empty / loading states
- No addresses: "Add the first address" CTA with explanation that addresses come from the Suburbs lookup (or use + Add Suburb popup)
- No works: similar — "Add the first work" with a quick-add modal

### Prompt
> Design a Works & Addresses page for an RICD project. The page has two main sections: Addresses (cards or table) and Works (table). Each Address shows street/lot/plan + suburb + electorate pills, a Livable Housing Design badge (Silver/Gold/Platinum — show as a tiny coloured pill: grey/amber/blue), and a lease-status lock icon (green padlock when lease is Executed, grey outline when Pending, hidden when Not Required). Each Work row shows the address, work type + bedrooms, quantity, contractor (muted), status pill, total estimated cost (formatted `$1,234,567.00`), forecast PC (muted) or actual PC (green), and a "Sunset risk" amber pill if forecast PC exceeds Stage 2 sunset + 30 days. Add status filter chips (All/Pending/In Progress/Completed), a search box, and CSV export. Include a "+ Bulk add works" modal that lets the user pick an address, work type, bedrooms, quantity, and cost — adding 5-10 works in one shot. Clicking a work row opens the Work Detail page (see Prompt 7). Use the existing style tokens.

---

## Prompt 3 — Reporting Dashboard

### Audience
Mixed — FNC officers monitor portfolio-wide; Council managers see their council; both need quick "where do I need to act" surface.

### Page purpose
A single landing page at `/reports/` that surfaces:
1. **What's overdue** — reports past due (Quarterly, Monthly Tracker, Stage)
2. **Portfolio health** — counts in each Project.State, total $ approved / released / remaining
3. **Recent activity** — last 10 actions (audit log style)
4. **Quick links** to all the reports — Monthly Progress, EOM Reconciliation, Construction Creation List, Cashflow, plus per-council Quarterly + per-project Stage

### Available data
- `QuarterlyReport.objects.filter(...).is_overdue` — date > due_date + 14 days
- `MonthlyTracker.objects.filter(status='DRAFT', ...)` per council
- `StageReport.objects.filter(status='SUBMITTED')`
- Project state counts: `Project.objects.values('state').annotate(c=Count('id'))`
- Sum aggregates from BFAItem, PaymentAllocation
- AuditLog rows from `apps.core.models.AuditLog`

### Required design treatments
- **Hero stat row** (4 KPIs):
  - Approved (portfolio) — sum
  - Released (portfolio) — sum
  - Drawdown % overall
  - Active funding schedules count
- **"Action needed" panel** (red-tinged): list of overdue reports with click-through
- **"Pipeline" panel**: 6 mini-tiles, one per Project.State, with count + percentage bar
- **"Reports library"**: card grid linking to:
  - Monthly Progress Report (per council selector)
  - End-of-Month Reconciliation (with month picker)
  - Construction Creation List (with council filter)
  - Quarterly Reports (per council selector)
  - Stage Reports (per project selector)
  - Cashflow by Month / by Program (new — Prompt 4 below)
- **Recent activity stream**: 10 most recent AuditLog entries with user, timestamp, action, entity, click-through

### Empty / loading states
- New install: most KPIs read 0; show onboarding hints
- No overdue: green "On track" panel instead of red action panel

### Prompt
> Design a Reports landing page that surfaces what needs attention now and provides quick access to every report. Layout: a hero row of 4 KPIs (Approved $, Released $, Drawdown %, Active FS count). Below that, a two-column grid: left column is an "Action Needed" panel (red-tinged) listing overdue Quarterly/Monthly Tracker/Stage reports with one-click navigation; right column is a "Project Pipeline" panel showing 6 mini-tiles (one per state: Prospective/Programmed/Funded/Commenced/Under Construction/Completed) with count and a thin progress bar. Below that, a "Reports Library" card grid (3 columns) linking to: Monthly Progress, End-of-Month Reconciliation, Construction Creation List, Quarterly, Stage, and Cashflow. Bottom: a recent-activity feed (10 entries with user avatar, timestamp, action verb, entity link). Money displayed as `$1,234,567.00` (negatives in red). Use style tokens.

---

## Prompt 4 — Cashflow Report (by Month, by Program with Cost Centre)

### Audience
Finance team + RICD program managers. This is the primary monthly forecasting & reconciliation tool.

### Page purpose
A flexible cashflow report showing forecast vs actual payments aggregated by month and program. Used at month-end for finance reconciliation and quarterly board updates. Must display Cost Centre and GL code per program so accounting can match the totals to SAP.

### Available data
- `Payment.objects.filter(...)` with `forecast_release_date`, `release_date`, `calculated_amount`, `status` (PENDING/RECOMMENDED/APPROVED/RELEASED/REJECTED)
- `PaymentAllocation.objects.filter(...)` — per-program split with `program.cost_centre`, `program.gl_code`, `ratio`
- `Project.program` (FK), `program.name`, `program.cost_centre`, `program.gl_code`, `program.funding_source`
- Date range: FY (July-June) or custom

### Required design treatments
- **Filter bar at top**:
  - Date range (Financial Year picker default; custom range option)
  - Council (multi-select with "All")
  - Program (multi-select with "All")
  - Status (forecast only / actual only / both)
- **Pivot grid (default)**:
  - Rows = programs (with cost centre + GL listed as second-line muted)
  - Columns = months (Jul … Jun)
  - Cells = sum of allocations for that program × month (forecast in muted, actual in bold). Cell colour amber if forecast > actual.
  - Row totals (rightmost column) and column totals (bottom row)
  - Click a cell → drilldown to list of payments
- **Alternate view (tabs)**:
  - "By month" — flat list of months × totals
  - "By program" — flat list of programs × totals with cost centre + GL
- **Export buttons**: CSV (sums + drilldown rows) + XLSX (pivot preserved)
- **Cost-centre badge format**: small inline pill like `CC 8100` next to program name
- **GL code**: muted secondary line — `GL 51200` style

### Required computations
- For each (month, program): `sum(PaymentAllocation.amount where payment.release_date.month=M, payment.status=RELEASED)` for actual; same with `forecast_release_date` and `status=APPROVED|RECOMMENDED` for forecast.
- Row total = sum across months
- Column total = sum across programs

### Empty / loading states
- No payments in range: friendly empty state "No payments scheduled or released between [from] and [to]"
- All forecast no actuals: amber banner "FY just started — actuals will populate as payments release"

### Prompt
> Design a Cashflow Report page for RICDapp Finance staff. The default view is a pivot grid: rows are Programs (each row shows program name + a small `CC <costcentre>` pill + GL code as muted secondary line), columns are months across a financial year (Jul–Jun by default). Each cell shows a forecast figure (muted) and an actual figure (bold, in `$1,234,567.00` format with negatives red); cells where forecast > actual get an amber tint. Rightmost column is the row total; bottom row is the month total. Above the grid: filter bar with Financial Year picker, multi-select Council, multi-select Program, status toggle (forecast/actual/both). Right side of filter bar: CSV + XLSX export buttons. Provide two alternate views as tabs: "By Month" (flat: each month with totals) and "By Program" (flat: each program with totals + cost centre + GL). Clicking any cell opens a drilldown panel listing the individual payments. The design should feel like a Stripe revenue report — dense but legible, lots of whitespace around the table. Use the existing style tokens.

---

## Prompt 5 — End-of-Month Reconciliation (Polish)

### Audience
Finance team. Used once a month at month-end to reconcile released payments against SAP/Finance system.

### Page purpose
The page already exists at `/reports/eom-reconciliation/`. It lists all PaymentAllocations released in a given month, grouped by Program with subtotals and by Council with totals. Has a CSV export. The current implementation is functional but visually plain — needs design polish.

### Current data shown (already implemented)
- Month picker (defaults to current month)
- Per-program group:
  - Program name + Cost Centre + GL
  - Table of payments (release date, council, project, FS#, type, amount, ratio, SAP ref, tax invoice ref)
  - Subtotal
- Per-council totals (separate card)
- Grand total
- CSV export

### Required design treatments
- **Sticky header** with the month label + grand total + Export CSV button (always visible while scrolling)
- **Per-program cards** with the program name as the prominent card header and `CC <cc>` `GL <gl>` as a soft secondary line
- **Payment rows**: SAP ref in monospace font (JetBrains Mono) so codes line up
- **Per-council summary**: small bar chart visualization showing each council's share
- **Drill-through**: clicking a payment row opens the Payment Detail page

### Prompt
> Design a polished End-of-Month Reconciliation page. The page is a one-month snapshot of every released PaymentAllocation, grouped by Program. At the top: sticky header with month name (e.g., "May 2026") as h1, grand total in large `$X,XXX,XXX.00` (negatives red), and an "Export CSV" button. Per-program card: program name + soft secondary line showing `CC 8100 · GL 51200`. Inside each card: a dense table with columns Release Date, Council, Project, FS#, Type, Amount (right-aligned, money formatted), Ratio (4dp decimal), SAP Ref (JetBrains Mono font), Tax Invoice Ref (Mono). Below the per-program cards: a Per-Council Summary card with a horizontal bar chart showing each council's share of the month's total. Allow month switching via a date input in the header. Click any payment row → opens Payment Detail. The whole feel should be Finance-precise: alignment, monospace for codes, clear hierarchy.

---

## Prompt 6 — Council Detail / Dashboard

### Audience
RICD officers focused on a single council, and Council Manager users browsing their own council.

### Page purpose
A 360° view of a council. Already implemented with KPIs (project count, contacts), financial summary, reporting health, project pipeline, active funding schedules. Needs design polish.

### Available data (already in context)
- `fin_summary` — dict with approved_funding, approved_contingency, approved_grand, committed_via_fs, released_total, council_reported_unspent, unspent_reported_at, drawdown_pct, remaining
- `reporting_health` — dict with qr_overdue_count, qr_overdue list, qr_upcoming list, latest_qr
- `active_fs_summary` — list of {fs, released, drawdown_pct, forecast_pc}
- `pipeline_counts` — list of {state, label, count}
- `council.region`, electorate FK + legacy text fallback, lead_officer FK

### Required design treatments
- **Hero**: council name + region + electorate badges + lead-officer chip with avatar
- **Map snippet** (optional): if council has a lat/lng, show a small QLD map with a pin
- **Financial summary**: 4 KPI tiles + sparkline of monthly released funds
- **Pipeline**: hexagonal/circular badges arranged in a flow (Prospective → Programmed → Funded → Commenced → Under Construction → Completed) with counts on each
- **Active FS table**: sortable, with progress bars per FS
- **Recent reports**: timeline of monthly + quarterly + stage submissions
- **Contacts panel**: card list with avatar + name + role + email + phone, "+ Add Contact" button

### Prompt
> Design a Council Detail page that feels like a Salesforce Account page or a Stripe Customer page — comprehensive but scannable. Hero: council name as h1, region as h3 muted, soft badges for State Electorate, Federal Electorate, RHP status, and a chip showing the Lead Officer (with avatar initials, name, and a small "(council default)" muted hint when individual projects inherit this officer). Below: 4 KPI tiles (Approved BFA $, Released $, Drawdown %, Remaining $) with a subtle sparkline of the last 6 months under the Released tile. Then a Pipeline strip: 6 chevron-style badges flowing left→right (Prospective → Programmed → Funded → Commenced → Under Construction → Completed) with counts and percentage of total. Two-column section: left = Reporting Health (overdue Quarterly Reports as red list, upcoming as muted list, latest QR with status pill); right = Active Funding Schedules table (FS#, projects, amount, released, drawdown progress bar, forecast PC date). Contacts panel sidebar: cards with name/role/email/phone, "+ Add Contact" CTA. Recent reports timeline at the bottom (Monthly · Quarterly · Stage submissions, last 10).

---

---

## Prompt 7 — Work Item Detail (Rolling Forecast Schedule)

### Audience
Construction-team users + RICD officers. This is the day-to-day tracking page for a single Work item — where dates get entered and the forecast rolls forward.

### Page purpose
Show the full detail of one Work item and provide an inline-editable rolling-forecast schedule. From here:
1. See all Work metadata (type, bedrooms, quantity, costs, contractor, status)
2. Set/change the Actual Start Date to anchor the rolling forecast cascade
3. Set a target Forecast Handover Date (triggers backward scheduling when no actual start is set yet)
4. See per-step forecast start/complete dates auto-calculated from the anchor
5. Enter actual completion dates per step (downstream forecasts roll forward automatically)
6. Toggle steps as Active/Inactive
7. Sync steps from the assigned WorkStepGroup template

### Available data
- `work.work_type`, `work.work_type_other`, `work.bedrooms`, `work.quantity`
- `work.estimated_cost`, `work.actual_cost`, `work.forecast_final_cost`, `work.costs_finalised`
- `work.contractor` (FK), `work.floor_area`, `work.drawing_no`, `work.notes`
- `work.status`, `work.cashflow_method`, `work.step_group`
- `work.actual_start_date` — the forecast anchor (forward scheduling from here)
- `work.forecast_handover_date` — target handover (backward scheduling when no actual start set)
- `work.forecast_practical_completion_date` — computed from the STAGE2-gated step's forecast completion
- `work.practical_completion_date`, `work.handover_date` — actuals
- `work.pc_breaches_sunset` — boolean sunset-risk flag
- `work.steps.all()` — list of WorkStep: `order`, `step_name`, `expected_duration_days`, `expected_cost_percentage`, `forecast_start_date`, `forecast_completion_date`, `actual_completion_date`, `is_active`, `group_item.stage_gate` (STAGE1 / STAGE2)
- `anchor_form` — Django form with `actual_start_date` + `forecast_handover_date`
- `step_formset` — inline formset: one row per step, editable `actual_completion_date` + `is_active`

### Scheduling logic (already implemented)
- **Forward scheduling**: when `actual_start_date` is set, step dates cascade forward; each completed step's `actual_completion_date` becomes the next step's start
- **Backward scheduling**: when only `forecast_handover_date` is set (no actual start), step dates cascade backward from the target — the page should surface this mode clearly so the user understands they're in planning mode
- One save submits both the anchor form and the step formset together

### Required design treatments
- **Work header card**: type + bedrooms + quantity as h2; status badge; costs row (Estimated / Forecast Final / Actual, the latter in green when costs_finalised); contractor chip (if set); floor area + drawing no as small meta; notes in a collapsible
- **Anchor card**: two inputs side-by-side — "Actual Start Date" (bold, primary — anchors forward scheduling) and "Forecast Handover Date" (secondary — triggers backward scheduling if no actual start). A third read-only cell shows "Computed PC date" (bold if set; amber sunset-risk badge if applicable). Add a mode indicator: "Forward schedule (from actual start)" vs "Backward schedule (from target handover)" vs "No anchor set"
- **Steps grid**: compact table — #, Step Name (+ "Done" green badge if actual_complete), Duration (days), Cost %, Stage Gate (Stage 1 / Stage 2 badges), Forecast Start (muted), Forecast Complete (muted), Actual Complete (date input), Active? (checkbox). Rows for inactive steps are greyed. STAGE2 row gets a subtle highlight (it defines PC date).
- **Save All** button pinned to the bottom of the steps card + one at the top
- **Sync steps** button: recreates steps from the group template (shown only if step_group is set)

### Empty / loading states
- No steps yet + step_group assigned: "Use 'Sync steps from group' above to create them"
- No steps yet + no step_group: "Assign a step group via Edit first"
- cashflow_method ≠ WORKSTEP: steps section hidden entirely (not applicable for milestone-based works)

### Prompt
> Design a Work Item Detail page for RICDapp. The page has two zones: (1) a metadata header card showing the work type + bedrooms + quantity, a status badge, a costs row (Estimated / Forecast Final / Actual side-by-side, green tick when costs_finalised), contractor chip, floor area + drawing no, and a collapsible notes section; (2) a rolling-forecast schedule section (only shown when cashflow_method = WORKSTEP). The schedule section opens with an "Anchor" card: a prominent "Actual Start Date" input (this anchors forward scheduling — make it the dominant visual element), a secondary "Forecast Handover Date" input (used when no actual start — triggers backward scheduling), and a read-only "Computed PC date" field with an amber "Sunset risk" badge when the forecast PC breaches Stage 2 sunset + 30 days. Show a small mode pill: "Forward schedule ↓" (teal) when actual start is set, "Backward schedule ↑" (amber) when only handover is set, "No anchor" (grey) otherwise. Below the anchor card: a compact steps table with columns: #, Step Name (add a green "Done" chip when actual_complete is set), Duration (days), Cost %, Stage Gate (Stage 1 / Stage 2 coloured badges), Forecast Start (muted), Forecast Complete (muted), Actual Complete (date input field), Active? (checkbox). Highlight the STAGE2 row with a faint teal left border — it defines Practical Completion. Inactive step rows are greyed. Two "Save All" buttons — one at the top right of the steps card, one at the bottom. The whole page uses the existing style tokens (sidebar 220px, navbar 56px).

---

## Prompt 8 — Land Project Detail

### Audience
RICD land officers managing pre-construction land development projects. These projects have a different lifecycle from dwelling construction — they're mostly about approvals, tenure, and infrastructure design before a single house can be built.

### Page purpose
A Land project detail page that surfaces:
1. The four **pre-condition traffic-light flags** (Native Title, Environmental Assessment, DA, Survey) as the most prominent visual element — these gate whether construction can proceed
2. Land parcel details (LandTenure links, lot/plan numbers, tenure type, native title status at parcel level)
3. Infrastructure readiness (water, electricity, sewerage assessments)
4. Links to Development Applications and parent/child project relationships
5. Works (infrastructure works such as civil construction, OPW, subdivision) that have WorkStep schedules using the same rolling-forecast system as dwelling works

### Available data
- `project.land_pre_conditions.all()` — 4 flags, one per category:
  - **Native Title**: status (RED/AMB/GRN) + native_title_type (ILUA / Statutory 24JAA / Statutory 24KAA / Extinguished) + completed_date + notes
  - **Environmental Assessment**: status + completed_date + notes
  - **Development Application**: status + completed_date + notes
  - **Survey**: status + completed_date + notes
- `project.land_parcels.all()` — LandTenure: lot_number, plan_number, tenure_type (Crown/Freehold/Leasehold), native_title_status (parcel-level), cultural_heritage_status
- `project.development_application` (FK to DevelopmentApplication: type, reference, status, lodged_date, decision_date)
- `project.infra_water_assessment`, `project.infra_electricity_assessment`, `project.infra_sewerage_assessment`
- `project.parent_land_project` (FK back to another Project for subdivision parent)
- `project.child_dwellings.all()` — linked dwelling projects built on this land
- `project.works.all()` — infrastructure works (same Work model, cashflow_method = WORKSTEP with land-specific WorkStepGroups)

### Traffic-light status meaning
- 🔴 **Red** — not started / not addressed
- 🟡 **Amber** — in progress / outstanding issues
- 🟢 **Green** — addressed / no issues / cleared

### Required design treatments
- **Pre-Conditions panel** (hero, top of page): 4 coloured tiles in a 2×2 or 4-across row. Each tile:
  - Title (e.g. "Native Title")
  - Large coloured circle/badge for traffic light (red/amber/green — use Bootstrap `danger/warning/success`)
  - Sub-label: NT pathway (ILUA / 24JAA / 24KAA / Extinguished) for the NT tile; blank for others
  - Completed date (green tick + date if set)
  - Notes truncated to 1 line
  - "Edit" pencil icon (FNC only) in top-right of each tile → links to the pre-conditions edit page
- **Land Parcels table**: lot/plan, tenure type, native title parcel status, cultural heritage status — compact, with status pills
- **Infrastructure readiness** (3 short paragraphs with labels): Water, Electricity, Sewerage
- **DA card** (if set): application type, reference, status pill, lodged date, decision date, link to decision notice
- **Child dwellings** (if any): mini-table of linked dwelling projects
- **Works section**: same as Prompt 2 — but these works are infrastructure/civil, not residential. Reuse the same works table pattern.
- **"All green?" summary**: if all 4 pre-condition flags are GREEN, show a prominent "✅ Ready for construction" banner across the top of the pre-conditions panel

### Empty / loading states
- Pre-conditions not recorded yet (all unsaved): show all 4 tiles as RED with "Not recorded" label and a prominent "Record pre-conditions" CTA button
- No land parcels linked: "Link land parcels via the Land Tenure section"

### Prompt
> Design a Land Project Detail page for RICDapp. The visual hero of the page is a 4-tile Pre-Conditions panel showing the traffic-light status of: Native Title, Environmental Assessment, Development Application (DA), and Survey. Each tile has a large coloured circle (red/amber/green using Bootstrap danger/warning/success), the category name, a sub-label (for Native Title: show the pathway — ILUA / Statutory 24JAA / Statutory 24KAA / Extinguished), a completed date with green tick if set, and up to one line of notes. If all 4 tiles are Green, replace the panel header with a "✅ All pre-conditions met — ready for construction" teal banner. Below the pre-conditions: a Land Parcels table (lot/plan, tenure type, native title status, cultural heritage status — using the status pill classes). An Infrastructure card showing Water / Electricity / Sewerage readiness assessments as labelled text blocks. A Development Application card (type, reference, status, dates, link to decision notice). A Child Dwellings mini-table (linked dwelling projects with their state and forecast PC). A Works section (same compact table as Prompt 2 — infrastructure/civil works for this land project). The page uses the existing sidebar/navbar layout and style tokens. FNC users see an "Edit pre-conditions" button; Council users see read-only tiles.

---

## Tips for using these prompts

1. **Paste the global style tokens block first**, then paste the section you want.
2. Ask for the design as **either**:
   - "Static HTML/CSS using the tokens above" (most directly usable)
   - "Figma-style component breakdown" (better for design review)
   - "Annotated wireframe with state variants" (good for empty/loading/error states)
3. **Specify framework**: this app uses Django templates + Bootstrap 5.3 + vanilla JS. No React/Vue. Tell Claude Design "no React, no Tailwind — use Bootstrap classes plus the tokens".
4. **Specify mobile breakpoint**: 991.98px (Bootstrap lg). Below that, the 220px sidebar collapses to an icon-toggled drawer.
5. **For each design that comes back**, the integration cost is just dropping the HTML into the right template file under `src/apps/ui/templates/` and threading the right context vars from the existing view.
6. **Advanced/collapsed fields**: the Address and Project forms use a `<details>` collapsible for optional fields (construction materials, room counts, CLI number, CAA date). The collapsed section auto-opens if it contains a validation error.

## Recommended order

1. Project Detail (Prompt 1) — highest visibility, most-used page
2. Work Item Detail (Prompt 7) — the rolling forecast page users interact with daily
3. Land Project Detail (Prompt 8) — new pattern; the pre-condition tiles are the flagship new UI element
4. Cashflow Report (Prompt 4) — net-new functionality, finance team will demo this
5. Council Detail (Prompt 6) — polish on existing
6. Works & Addresses (Prompt 2) — wire the new forecast grid into a nicer container
7. Reporting Dashboard (Prompt 3) — landing-page polish
8. EOM Reconciliation (Prompt 5) — final polish, the dataset is already correct
