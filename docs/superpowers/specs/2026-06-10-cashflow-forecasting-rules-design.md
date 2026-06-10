# Cashflow forecasting rules — Cash vs Accrual per cashflow method

**Date:** 2026-06-10
**Status:** Design (awaiting user review)
**Pages affected:** `/cashflow` (FY), `/cashflow/monthly/`, Maintenance

---

## Problem

Cashflow has two distinct measures that diverge for Capital Works:

- **Cash to council (payments out)** — milestone `Payment` rows, for *every* project.
- **Accrued / forecast expenditure** — when value is actually delivered:
  - **Capital Grant** projects → tracks the milestone payment (cash and accrual coincide).
  - **Capital Works** projects → accrues progressively through **workstep** completion, timed differently from the milestone cash.

The current cashflow services don't model this cleanly. A prior change made Capital
Works cashflow workstep-only, which dropped the cash/payment view for those projects and
conflated the two measures. We need to (a) separate the two measures behind a **basis
toggle**, (b) classify projects explicitly, and (c) let staff **stipulate the rules** on a
Maintenance page.

## Key decisions (confirmed with user)

1. **Basis toggle** on the cashflow pages: `Cash (payments)` vs `Accrual (expenditure)`.
   Same grid, flip the lens.
2. **Grant accrual = its payments** — so on the Accrual basis, Capital Grants are identical
   to the Cash basis.
3. **Default basis = Accrual.** Because grant-accrual = grant-payment, the Accrual view
   naturally shows *Capital Grants on cash/payments and Capital Works on worksteps* — exactly
   the desired default. The `Cash` toggle then forces Capital Works onto their milestone
   payments too (pure cash-to-council). The toggle therefore only changes how Capital Works
   projects appear.
4. **Explicit classification field** `Project.cashflow_method` (Capital Grant / Capital Works)
   is the single source of truth — no inferring from worksteps.
5. **Editable rules** drive the services (per cashflow method), via a Maintenance page.

---

## Data model

### `Project.cashflow_method` (new field)

- Choices reuse `Work.CashflowMethod`: `MILESTONE` ("Capital Grants (Payment Milestone)") /
  `WORKSTEP` ("Capital Works (WorkStep Progressive)").
- `default = MILESTONE` so **existing projects stay payment-based** (numbers don't move).
- Added to the Project create/edit form (a labelled select with help text).
- File: `apps/core/models/projects_models.py`.

### `CashflowMethodRule` (new model, one row per method)

A small config table the cashflow services consult. File: `apps/core/models/` (new
`cashflow_models.py`, or alongside `SiteSettings`).

| Field | Type / choices | Notes |
|---|---|---|
| `method` | `MILESTONE` / `WORKSTEP` (unique) | mirrors `Work.CashflowMethod` |
| `accrual_source` | `PAYMENT` / `WORKSTEP` | what drives the **accrual** basis |
| `workstep_date` | `FORECAST_COMPLETION` (default) / `FORECAST_START` | which date forecasts the accrual (actuals always use `actual_completion_date`) |
| `cost_basis` | `EFFECTIVE` (default) / `ESTIMATED` | value base for a step: `effective` = actual-or-estimated |
| `notes` | text, blank | free-text guidance shown on the page |

- **Cash source is always payments** — not stored; rendered read-only on the page.
- `workstep_date` / `cost_basis` are only meaningful when `accrual_source = WORKSTEP`.
- Seeded by a data migration:
  - `MILESTONE` (Capital Grant): `accrual_source = PAYMENT`.
  - `WORKSTEP` (Capital Works): `accrual_source = WORKSTEP`, `workstep_date = FORECAST_COMPLETION`,
    `cost_basis = EFFECTIVE`.
- A `get(method)` helper returns the row (creating the seeded default if missing) so the
  services never crash on a missing row.

---

## Cashflow services (`apps/core/services/cashflow.py`)

Both `build_program_cashflow` (FY) and `build_program_monthly_cashflow` gain a
`basis` parameter: `'cash'` | `'accrual'` (default `'accrual'`).

**Classification:** a project is *Capital Works* iff `project.cashflow_method == 'WORKSTEP'`.

**Cash basis** (`basis='cash'`):
- Milestone `Payment` rows for **all** projects (the original payment-only behavior).
- No worksteps. (This restores/repairs the cash view for Capital Works.)

**Accrual basis** (`basis='accrual'`, default):
- For each non-rejected `Payment`, **skip it** if its project is Capital Works
  (`cashflow_method='WORKSTEP'` and that method's `accrual_source='WORKSTEP'`); otherwise
  bucket it as today.
- For Capital Works projects, add the **workstep layer** (`_iter_workstep_cashflow`),
  honoring the `WORKSTEP` rule's `workstep_date` and `cost_basis`:
  - step value = `cost%` × work value, where work value = `work.total_effective_cost`
    (EFFECTIVE, already ×quantity) or `work.estimated_cost × work.quantity` (ESTIMATED).
  - forecast on `workstep_date` (forecast completion or start); released on
    `actual_completion_date`.
  - `_iter_workstep_cashflow` selects worksteps of works whose **project** is Capital Works.
- Split per program via the project's approved BFA ratios (`_split_amount`, unchanged).

**No double counting:** within a basis, a Capital Works project is represented by exactly one
source — payments (cash) or worksteps (accrual), never both.

The monthly note/source copy and the FY page copy are updated to describe the active basis.

---

## Maintenance page

- Route: `maintenance/cashflow-rules/` → `CashflowMethodRulesView` (name `ui:cashflow_rules`),
  class-based, writer/manager-only (mirrors `SiteSettingsView`).
- Renders **one section per method** (Capital Grant, Capital Works): the fixed cash rule
  (read-only: "Milestone payments") and the editable accrual rule (`accrual_source`,
  `workstep_date`, `cost_basis`, `notes`), plus a plain-English explanation of what each basis
  means.
- A single POST saves both rows.
- Linked from the Maintenance landing (`MaintenanceView`) under Administration.

---

## Cashflow page basis toggle

- Both `/cashflow` and `/cashflow/monthly/` get a `Basis: Cash (payments) / Accrual (expenditure)`
  segmented control. Implemented as a GET param `?basis=cash|accrual` (server reload, since the
  numbers differ). Default = `accrual`.
- The views read `basis`, pass it to the service, and reflect the selection in the control.
- Note text explains: *Accrual (default) — expenditure as delivered: Capital Works by workstep,
  Capital Grants by payment. Cash — milestone payments to council for all projects.*

---

## Migrations

1. `Project.cashflow_method` field (default `MILESTONE`).
2. `CashflowMethodRule` model.
3. Data migration seeding the two rule rows.

---

## Testing

- **Model:** `CashflowMethodRule.get()` returns/creates seeded defaults; the two rows seed correctly.
- **Cash basis:** payments only, for both a Capital Grant and a Capital Works project (worksteps
  ignored).
- **Accrual basis:** a Capital Works project's **payments are excluded** and its **worksteps**
  drive forecast (at the configured date) and released (at actual completion); a Capital Grant
  project is **identical across both bases**.
- **Config honored:** switching the `WORKSTEP` rule's `workstep_date` to `FORECAST_START` moves
  the forecast; `cost_basis = ESTIMATED` changes the value.
- **Views:** both cashflow pages render for `?basis=cash` and `?basis=accrual`; Maintenance page
  loads and saves.

---

## Out of scope (YAGNI)

- Per-work (sub-project) basis mixing — classification is per project.
- A "both side-by-side" cell view — the toggle covers it.
- XLSX/CSV basis selection — exports can follow the default (accrual) for now; revisit if needed.
- Auto-syncing `Work.cashflow_method` from `Project.cashflow_method` — the project field drives
  cashflow classification; work-level method continues to drive per-work step scheduling.
