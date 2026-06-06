# RICD Domain Model — Gap Analysis (current state)

**Refreshed:** 2026-06-06
**Reference spec:** `docs/RICD_domain_model.md`
**Scope:** `src/apps/core/models/*` (the consolidated `core` models layer)

> **Note:** This supersedes the 2026-04-27 version, which predated the layer
> refactor and the Phase-1/2 build-out. Most entities that the old version
> listed as "missing" now exist. This document reflects the model as built.

---

## Summary

The domain model is **substantially complete** and in several areas exceeds the
spec (reporting and stages are richer than the single `Report`/`ProjectStage`
entities the spec describes). All spec entities are present. The remaining
differences are a handful of deliberate structural/naming choices plus two small
items closed on 2026-06-06 (see "Recently closed").

---

## Entity coverage

| Spec entity | Implemented as | Status |
|-------------|----------------|--------|
| Council | `Council` | ✅ |
| FundingAgreement | `FundingAgreement` | ✅ legal umbrella, split from schedule |
| PaymentRule | `PaymentRule` (+ `PaymentRuleMilestone`) | ✅ versioned; `clean()` immutability |
| FundingSchedule | `FundingSchedule` | ✅ agreement link, schedule_number, payment_rule, replaces_schedule, lifecycle |
| VariationDeed | `Variation` | ✅ (status DRAFT/SENT/EXECUTED) |
| VariationItem | `VariationItem` | ✅ option types as `OPTION_1..9`/`OTHER` (QGDS deed numbering) |
| Program | `Program` | ✅ (+ per-FY `ProgramBudget`) |
| Project | `Project` | ✅ `type` LAND/DWELLING, parent-land self-ref, state machine |
| Address | `Address` | ✅ (richer than spec) |
| Work | `Work` | ✅ + `cashflow_method`, `step_group`, `actual_start_date` |
| WorkType | `WorkType` | ✅ + `short_code`, notional costs |
| Allocation | `WorkFunding` | ✅ **project-XOR-work `CheckConstraint`** + cost_centre/gl_code/tax_code |
| Payment | `Payment` | ✅ (see divergences) |
| FundingNotice | `FundingNotice` | ✅ capped_amount, remaining/expended props |
| ExpenseClaim | `ExpenseClaim` | ✅ **cap enforced in `clean()`** |
| BriefFinancialApproval | `BriefFinancialApproval` (+ items) | ✅ + per-program split, contingency |
| Approval | `Approval` | ✅ generic (entity_type/entity_id/approval_type/required_role) |
| Report | `MonthlyTracker`, `QuarterlyReport`, `StageReport` | ✅ split into 3 purpose-built models |
| ProjectStage | `Stage` (+ `StageReport`/`StageItemGroup`) | ⚠️ thin `Stage`; richer workflow elsewhere |
| WorkflowAction | `WorkflowAction` | ✅ generic immutable event log |
| AuditLog | `AuditLog` | ✅ auto-written by signals for financial models |
| PaymentAllocation | `PaymentAllocation` | ✅ (extra) per-program snapshot locked at release |
| WorkStep* (cashflow) | `WorkStepDefinition/Group/GroupItem`, `WorkStep` | ✅ rolling forecast |
| PaymentMilestoneSchedule/Rule | same | ✅ (extra) configurable payment timing |

---

## Remaining divergences from the spec

### 1. Payment ↔ Allocation linkage (partially addressed)
- **Spec:** `Payment.allocation_id → Allocation(→ Project XOR Work)`.
- **Built:** `Payment → project + funding_schedule`. As of 2026-06-06 an optional
  `Payment.work` FK exists for "trace this payment to its dwelling". Program-level
  traceability is via `PaymentAllocation` (snapshotted at release).
- **Residual gap:** no FK to the `WorkFunding` allocation row itself; payment isn't
  tied to a specific allocation line, only (optionally) to a Work.

### 2. FundingNotice / ExpenseClaim pathway is separate from Payment & Cashflow
- Notice disbursements are `ExpenseClaim` rows, not `Payment` rows, so they don't
  appear in the program × FY cashflow matrix.
- As of 2026-06-06 the cashflow page shows a **Notice / Expense-Claim pathway**
  summary panel so the stream is acknowledged, but it is not bucketed by FY.

### 3. `Stage` thinner than spec `ProjectStage`
- `Stage` has name/dates/status only — no `stage_type`, planned-vs-actual split,
  or `sequence_order` UNIQUE per project. The real stage-gate workflow is carried
  by `StageReport` (STAGE1/STAGE2, DRAFT→SUBMITTED→ASSESSED→APPROVED) and
  `StageItemGroup` checklists, plus `WorkStepGroupItem.stage_gate`.

### 4. Naming: Variation options
- `VariationItem.option` uses `OPTION_1..OPTION_9`/`OTHER` (matching the QGDS deed
  "Option N" structure) rather than the spec's `ADD_/REMOVE_/REPLACE_/VARY_*`
  enum names. Semantics are equivalent; the replace→supersede effect is handled
  via `VariationFundingSchedule` + signals.

---

## Recently closed (2026-06-06)

- **Payment `RECONCILED` status** added (spec lifecycle `RELEASED → RECONCILED`),
  with a `reconciled_date` stamp and a "Reconcile" action on released payments.
- **`Payment.work`** optional FK so a payment can be traced to the specific
  dwelling/lot it funds (form constrains choices to the project's works).
- **Cashflow notice-pathway panel** added (item 2 above).

---

## Business rules — implementation status

| Rule | Status |
|------|--------|
| BFA APPROVED before FundingSchedule creation | Enforced in model `clean()` |
| PaymentRule immutable once linked | Enforced in `PaymentRule.clean()` |
| ExpenseClaim `SUM(approved) ≤ capped_amount` | Enforced in `ExpenseClaim.clean()` |
| Allocation project XOR work | DB `CheckConstraint` + `clean()` |
| FundingSchedule → ACTIVE on first APPROVED payment | Signal (`apps/core/signals.py`) |
| FundingSchedule → SUPERSEDED on REPLACE variation | Signal/business-rules trigger |
| Stage 1/2 APPROVED → unlock next payment | Signal on report/stage approval |
| WorkflowAction + AuditLog on state changes | Signals (broad post_save/pre_save) |

> **Caveat:** rules in `.clean()` run via ModelForms/admin, but bulk writes and
> `save(update_fields=...)` paths can bypass `clean()`. Acceptable for current use;
> worth promoting the most critical ones to DB constraints or `save()` guards later.

---

## Suggested follow-ups (non-blocking)

1. Optional `Payment.allocation` FK (to `WorkFunding`) to fully close divergence #1.
2. Squash migrations `0037–0040` (forecast-anchor churn) into one.
3. Consolidate the 17 live `src/templates/*` files into `apps/ui/templates/` and
   drop `src/templates` from `TEMPLATES['DIRS']`.
4. Promote key `clean()` rules to `save()`/DB constraints for non-form write paths.
