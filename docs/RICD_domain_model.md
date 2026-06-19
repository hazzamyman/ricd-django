# RICD Django App — Project Reference Document

**Remote Indigenous Capital Delivery (RICD) System**
**Queensland Government — Capital Works Funding Management**
**Last updated: 2026-04-26 (session end ~12:05 AEST)**

> This document consolidates the full domain modelling session for the RICD Django + PostgreSQL application. It represents the **final, authoritative state** of the data model as of the last successful session. Use this as your starting point for continued iteration.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Design Principles](#2-core-design-principles)
3. [Entity Table — Final Model](#3-entity-table--final-model)
4. [Relationships](#4-relationships)
5. [Key Constraints & Business Rules](#5-key-constraints--business-rules)
6. [Lifecycle State Machines](#6-lifecycle-state-machines)
7. [Payment Process Rules (Critical)](#7-payment-process-rules-critical)
8. [PaymentRule Config Examples](#8-paymentrule-config-examples)
9. [VariationItem Option Type Rules](#9-variationitem-option-type-rules)
10. [End-to-End Process Flow](#10-end-to-end-process-flow)
11. [Session History — Design Decision Log](#11-session-history--design-decision-log)
12. [Remaining Work / Next Steps](#12-remaining-work--next-steps)

---

## 1. Project Overview

The RICD system manages the full lifecycle of government-funded housing and infrastructure capital works across remote Indigenous communities in Queensland. It covers:

- **Funding agreements** between the Queensland Government and Indigenous Councils
- **Funding schedules** detailing funded projects and works packages
- **Variation deeds** (legal instruments) for activating and amending schedules
- **Payments** tied to milestones or invoice-based rules
- **Funding notices** as a separate, capped funding pathway (no schedule required)
- **Approvals** and **workflow governance** supporting financial delegation rules
- **Reporting** (monthly, quarterly, stage-based) that gates payment releases
- **Audit logging** for full financial traceability and compliance

**Tech stack:** Django + PostgreSQL
**Document storage:** External URLs only (Google Drive / future OpenDocs). No binary storage in the system.

---

## 2. Core Design Principles

1. **Full financial traceability** — Every monetary flow must be traceable end-to-end:
   `FundingAgreement → FundingSchedule / FundingNotice → Allocation → Payment`

2. **No document storage** — Only `document_uri` URL fields (Google Drive or OpenDocs links). No blobs, no internal file management.

3. **Structured fields over JSON** — All known variation option types use dedicated columns. `config_json` is reserved exclusively for `option_type = OTHER`.

4. **Versioned, immutable PaymentRules** — Once a `PaymentRule` is linked to a `FundingSchedule`, it cannot be altered. New versions create new rows.

5. **Approval is a separate system from workflow logging** — `Approval` records govern decision authority. `WorkflowAction` is an immutable event history log only.

6. **Avoid over-engineered abstraction** — No generic polymorphic approval frameworks beyond what is specified here.

7. **All state changes must be auditable** — Every transition generates both a `WorkflowAction` (business event) and an `AuditLog` (data-level change record).

8. **FundingAgreement is a legal umbrella only** — It does not contain project-level funding or monetary breakdowns. That lives in `FundingSchedule`.

---

## 3. Entity Table — Final Model

> **Status:** This is the final agreed entity model as of 2026-04-26T12:05 AEST.

### Council
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `name` | varchar, UNIQUE |
| `region` | varchar |
| `is_registered_housing_provider` | boolean |

---

### FundingAgreement
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `council_id` | FK → Council |
| `execution_date` | date |
| `status` | enum: `DRAFT`, `ACTIVE`, `CEASED` |
| `document_uri` | URL (Google Drive / OpenDocs) |

---

### PaymentRule *(versioned, immutable once used)*
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `name` | varchar |
| `rule_type` | enum: `SPLIT`, `INVOICE_BASED` |
| `config_json` | JSON (see §8 for structure) |
| `version` | int ≥ 1 |

**Rules:**
- `SPLIT` = milestone-percentage driven payments
- `INVOICE_BASED` = invoice/expense-claim driven with approval rules
- No financial caps or project-specific values in `config_json`
- Once referenced by a `FundingSchedule`, the record is immutable

---

### FundingSchedule
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `funding_agreement_id` | FK → FundingAgreement |
| `schedule_number` | int |
| `payment_rule_id` | FK → PaymentRule (**NOT NULL**) |
| `status` | enum: `DRAFT`, `READY_FOR_EXECUTION`, `EXECUTED`, `ACTIVE`, `COMPLETED`, `SUPERSEDED` |
| `total_amount` | Decimal (derived from sum of Allocations) |
| `replaces_schedule_id` | FK → FundingSchedule (self, nullable) |

**Unique constraint:** `(funding_agreement_id, schedule_number)`

---

### VariationDeed
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `funding_agreement_id` | FK → FundingAgreement |
| `funding_schedule_id` | FK → FundingSchedule (optional target) |
| `variation_type` | enum: `INITIAL`, `AMENDMENT` |
| `status` | enum: `DRAFT`, `SENT`, `EXECUTED` |
| `executed_by_id` | FK → User (required when EXECUTED) |
| `executed_at` | timestamp (required when EXECUTED) |
| `document_uri` | URL |

---

### VariationItem
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `variation_deed_id` | FK → VariationDeed (**required**) |
| `sequence_number` | varchar (e.g. "a", "b", "c") |
| `option_type` | enum (see §9) |
| `affected_funding_schedule_id` | FK → FundingSchedule (nullable) |
| `replacement_funding_schedule_id` | FK → FundingSchedule (nullable, REPLACE only) |
| `config_json` | JSON (**only** when `option_type = OTHER`) |
| `effective_date` | date (nullable) |
| `description` | text |

---

### Program
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `name` | varchar |
| `funding_source` | varchar |
| `budget` | Decimal |
| `gl_code` | varchar |
| `business_case_ref` | varchar |

---

### Project
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `council_id` | FK → Council |
| `program_id` | FK → Program |
| `type` | enum: `LAND`, `DWELLING` |
| `parent_land_project_id` | FK → Project (self-ref, nullable — DWELLING only) |
| `status` | enum: `PROSPECTIVE`, `PROGRAMMED`, `FUNDED`, `COMMENCED`, `UNDER_CONSTRUCTION`, `COMPLETED` |
| `start_date` | date |
| `completion_date` | date |

**Rules:**
- `type = DWELLING` may reference a `parent_land_project_id` where that project has `type = LAND`
- `type = LAND` must have `parent_land_project_id = NULL`

---

### Address
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `address_line` | text (placeholders like "TBA Lot 1" allowed) |
| `suburb` | varchar |
| `state` | varchar |
| `postcode` | varchar |

---

### Work
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `project_id` | FK → Project (**required**) |
| `address_id` | FK → Address (optional) |
| `work_type_id` | FK → WorkType |
| `quantity` | Decimal |
| `estimated_cost` | Decimal |
| `status` | enum: `PLANNED`, `IN_PROGRESS`, `COMPLETED` |

---

### WorkType
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `category` | varchar |
| `description` | text |

---

### Allocation
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `funding_schedule_id` | FK → FundingSchedule |
| `project_id` | FK → Project (nullable) |
| `work_id` | FK → Work (nullable) |
| `amount` | Decimal |
| `cost_centre` | varchar |
| `gl_code` | varchar |
| `tax_code` | varchar |

**DB CHECK constraint:** `(project_id IS NOT NULL AND work_id IS NULL) OR (project_id IS NULL AND work_id IS NOT NULL)` — exactly one of `project_id` or `work_id` must be set.

---

### Payment
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `allocation_id` | FK → Allocation |
| `funding_schedule_id` | FK → FundingSchedule (**required**) |
| `funding_notice_id` | FK → FundingNotice (nullable) |
| `payment_source_type` | enum: `SCHEDULE`, `NOTICE` |
| `percentage` | Decimal |
| `amount` | Decimal |
| `release_date` | date |
| `reference` | text |
| `status` | enum: `PENDING`, `APPROVED`, `RELEASED`, `RECONCILED` |

**Rules:**
- Must always reference `funding_schedule_id`; optionally also `funding_notice_id` for traceability
- `APPROVED` requires an `Approval` record based on delegation thresholds
- First payment reaching `APPROVED` → triggers `FundingSchedule.status = ACTIVE`

---

### FundingNotice
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `project_id` | FK → Project (**required**) |
| `capped_amount` | Decimal ≥ 0 |
| `issued_date` | date |
| `status` | enum: `OPEN`, `CLOSED` |

**Rules:**
- Multiple `FundingNotice` records per project are allowed
- The cap is project-specific (NOT stored in `PaymentRule`)
- **Unique:** `(project_id, issued_date)`

---

### ExpenseClaim
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `funding_notice_id` | FK → FundingNotice |
| `amount` | Decimal |
| `date_submitted` | date |
| `status` | enum: `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED` |
| `approved_by_id` | FK → User (required when APPROVED) |
| `approved_date` | date (required when APPROVED) |

**Cap rule:** `SUM(amount WHERE status = APPROVED) ≤ FundingNotice.capped_amount` — enforced before approval.

---

### BriefFinancialApproval *(pre-condition for funding creation)*
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `project_id` | FK → Project |
| `funding_amount` | Decimal |
| `delegate_position_id` | FK → DelegatePosition (maintenance-managed; title + max approval amount) |
| `approval_status` | enum: `PENDING`, `APPROVED`, `REJECTED` |
| `approved_by_id` | FK → User |
| `approved_at` | timestamp |
| `mincor_reference` | varchar |
| `comments` | text |

**Rule:** A `FundingSchedule` cannot be created unless an `APPROVED` `BriefFinancialApproval` exists for the associated project.

---

### Approval *(unified governance approval system)*
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `entity_type` | varchar (must match a real table name) |
| `entity_id` | int (must exist in that table) |
| `approval_type` | enum: `FINANCIAL`, `CONTRACT`, `PAYMENT`, `REPORT`, `VARIATION` |
| `required_role` | enum: `MANAGER`, `DIRECTOR`, `GM`, `DELEGATE` |
| `approved_by_id` | FK → User |
| `approved_at` | timestamp |
| `status` | enum: `PENDING`, `APPROVED`, `REJECTED` |
| `comments` | text |

**Required for:** FundingSchedule approval, Payment release, Report approval, Variation execution.

---

### Report
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `project_id` | FK → Project |
| `funding_schedule_id` | FK → FundingSchedule (optional) |
| `type` | enum: `MONTHLY`, `QUARTERLY`, `STAGE1`, `STAGE2` |
| `state` | enum: `DRAFT`, `SUBMITTED`, `ASSESSED`, `APPROVED`, `REJECTED` |
| `submitted_by_id` | FK → User |
| `assessed_by_id` | FK → User (optional) |
| `approved_by_id` | FK → User (optional) |
| `submitted_date` | date |
| `approved_date` | date (optional) |
| `due_date` | date |

**Rules:**
- Stage 1 `APPROVED` → unlocks interim (second) payment
- Stage 2 `APPROVED` → unlocks final payment

---

### ProjectStage
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `project_id` | FK → Project |
| `stage_type` | varchar (configurable per project type) |
| `status` | enum: `PENDING`, `IN_PROGRESS`, `COMPLETED` |
| `planned_start` | date |
| `planned_end` | date |
| `actual_start` | date (optional) |
| `actual_end` | date (optional) |
| `sequence_order` | int (UNIQUE per project) |

---

### WorkflowAction *(immutable event log — NOT a decision authority)*
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `entity_type` | varchar |
| `entity_id` | int |
| `action_type` | enum: `CREATE`, `UPDATE`, `APPROVE`, `REJECT`, `RELEASE_PAYMENT`, `EXECUTE_VARIATION` |
| `performed_by_id` | FK → User |
| `performed_at` | timestamp |
| `metadata_json` | JSON (free-form: rationale, external ticket IDs, etc.) |

---

### AuditLog *(low-level immutable change log)*
| Field | Type / Notes |
|-------|-------------|
| `id` | PK |
| `user_id` | FK → User |
| `timestamp` | timestamp |
| `entity_type` | varchar |
| `entity_id` | int |
| `action` | varchar |
| `before_json` | JSON |
| `after_json` | JSON |

**Covers:** All financial-related tables: FundingAgreement, FundingSchedule, VariationDeed, VariationItem, Allocation, Payment, FundingNotice, ExpenseClaim, Report, ProjectStage, Approval, BriefFinancialApproval.

---

## 4. Relationships

- **Council** → has many → FundingAgreement, Project, FundingNotice
- **FundingAgreement** → belongs to → Council; has many → FundingSchedule, VariationDeed
- **FundingSchedule** → belongs to → FundingAgreement; references → PaymentRule (required); may replace → another FundingSchedule (`replaces_schedule_id`); has many → Allocation, Payment, Report, VariationDeed (as target)
- **VariationDeed** → links FundingAgreement ↔ FundingSchedule; has many → VariationItem
- **VariationItem** → belongs to → VariationDeed; optional FK to old/new FundingSchedule per option type
- **Program** → has many → Project
- **Project** → belongs to → Council, Program; optional self-ref `parent_land_project_id` (DWELLING only); has many → Work, Allocation, Report, ProjectStage, FundingNotice, BriefFinancialApproval
- **Work** → belongs to → Project (required); optional → Address
- **Allocation** → belongs to → FundingSchedule; references exactly one of Project OR Work (DB CHECK)
- **Payment** → belongs to → Allocation; must reference FundingSchedule (required); optionally references FundingNotice
- **FundingNotice** → belongs to → Project (required); has many → ExpenseClaim
- **ExpenseClaim** → belongs to → FundingNotice
- **BriefFinancialApproval** → belongs to → Project; must be APPROVED before FundingSchedule creation
- **Approval** → generic sign-off entity for FundingSchedule, Payment, Report, VariationDeed
- **Report** → belongs to → Project; optional link to FundingSchedule
- **ProjectStage** → belongs to → Project; ordered by `sequence_order`
- **WorkflowAction** → logs every high-level operation on any entity
- **AuditLog** → immutable change log across all financial/governance tables

---

## 5. Key Constraints & Business Rules

| Entity | Constraint / Rule |
|--------|-------------------|
| **Council** | `name` UNIQUE |
| **FundingAgreement** | Cannot move to `ACTIVE` without an APPROVED BriefFinancialApproval on at least one project |
| **FundingSchedule** | UNIQUE(`funding_agreement_id`, `schedule_number`); `payment_rule_id` NOT NULL |
| **FundingSchedule** | `EXECUTED` only when a linked VariationDeed with `status = EXECUTED` exists AND at least one VariationItem of type `ADD_FUNDING_SCHEDULE` or `REPLACE_FUNDING_SCHEDULE` targets the schedule |
| **FundingSchedule** | `ACTIVE` automatically set on the first Payment whose status becomes `APPROVED` |
| **FundingSchedule** | `SUPERSEDED` set when a `REPLACE_FUNDING_SCHEDULE` VariationItem creates a new schedule referencing the old via `replaces_schedule_id` |
| **VariationDeed** | When `EXECUTED`: `executed_by_id` and `executed_at` are required |
| **VariationItem** | `config_json` allowed ONLY when `option_type = OTHER` (see §9 for full column rules) |
| **Project** | `type = DWELLING` may set `parent_land_project_id` → must reference a `type = LAND` project; `type = LAND` must have `parent_land_project_id = NULL` |
| **Work** | `project_id` NOT NULL; `address_id` optional |
| **Allocation** | DB CHECK: exactly one of `project_id` or `work_id` must be non-NULL |
| **PaymentRule** | `version ≥ 1`; immutable once referenced by any FundingSchedule |
| **Payment** | `funding_schedule_id` required; `funding_notice_id` optional; at least one must provide traceability |
| **Payment** | APPROVAL required before status can move to `RELEASED` |
| **FundingNotice** | `capped_amount ≥ 0`; UNIQUE(`project_id`, `issued_date`) |
| **ExpenseClaim** | `SUM(approved claims) ≤ FundingNotice.capped_amount` — enforced before approval |
| **ExpenseClaim** | When `APPROVED`: `approved_by_id` and `approved_date` are required |
| **Approval** | `entity_type` must match a real table; `entity_id` must exist in that table |
| **BriefFinancialApproval** | Must be `APPROVED` before any FundingSchedule can be created for the project |
| **Report** | Stage 1 APPROVED → permits second payment release; Stage 2 APPROVED → permits final payment |
| **ProjectStage** | `sequence_order` UNIQUE per `project_id` |
| **WorkflowAction** | Every state transition on any entity must generate a WorkflowAction record |
| **AuditLog** | Insert/Update/Delete on all financial tables creates an immutable log entry |

---

## 6. Lifecycle State Machines

### FundingSchedule
```
DRAFT → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED
                                                  ↘ SUPERSEDED
```
- `DRAFT → READY_FOR_EXECUTION`: Triggered by FINANCIAL Approval
- `READY_FOR_EXECUTION → EXECUTED`: Triggered by VariationDeed execution (with ADD or REPLACE item)
- `EXECUTED → ACTIVE`: Triggered by first APPROVED Payment
- `ACTIVE → SUPERSEDED`: Triggered by REPLACE_FUNDING_SCHEDULE VariationItem

### VariationDeed
```
DRAFT → SENT → EXECUTED
```

### Payment
```
PENDING → APPROVED → RELEASED → RECONCILED
```
- Approval required before `RELEASED`

### Report
```
DRAFT → SUBMITTED → ASSESSED → APPROVED
                             ↘ REJECTED
```

### FundingAgreement
```
DRAFT → ACTIVE → CEASED
```

### Project
```
PROSPECTIVE → PROGRAMMED → FUNDED → COMMENCED → UNDER_CONSTRUCTION → COMPLETED
```

### Work
```
PLANNED → IN_PROGRESS → COMPLETED
```

### ExpenseClaim
```
DRAFT → SUBMITTED → APPROVED
                  ↘ REJECTED
```

### FundingNotice
```
OPEN → CLOSED
```

### ProjectStage
```
PENDING → IN_PROGRESS → COMPLETED
```

---

## 7. Payment Process Rules (Critical)

| Payment # | Pre-condition |
|-----------|--------------|
| **First payment** | FundingSchedule must be `EXECUTED`; BriefFinancialApproval must be `APPROVED` |
| **Second payment** | Stage 1 Report must be `APPROVED` |
| **Final payment** | Stage 2 Report must be `APPROVED` |

**All payments:** Require an `Approval` record of type `PAYMENT` (delegation threshold checked against PaymentRule).

---

## 8. PaymentRule Config Examples

### SPLIT (milestone-percentage based)
```json
{
  "milestones": [
    { "name": "Commencement", "percentage": 30 },
    { "name": "Midpoint", "percentage": 60 },
    { "name": "Completion", "percentage": 10 }
  ]
}
```

### INVOICE_BASED (expense-claim driven)
```json
{
  "requires_approval": true
}
```

**Critical rules:**
- No financial caps in `config_json` (caps live on `FundingNotice.capped_amount`)
- No project-specific values
- Only defines *how* payments are calculated/released

---

## 9. VariationItem Option Type Rules

| `option_type` | `affected_schedule_id` | `replacement_schedule_id` | `config_json` |
|--------------|------------------------|---------------------------|---------------|
| `ADD_FUNDING_SCHEDULE` | NULL | NULL | NOT ALLOWED |
| `REMOVE_FUNDING_SCHEDULE` | **required** | NULL | NOT ALLOWED |
| `REPLACE_FUNDING_SCHEDULE` | **required** | **required** | NOT ALLOWED |
| `VARY_FUNDING_AMOUNT` | optional | NULL | NOT ALLOWED |
| `VARY_SCOPE_OF_WORKS` | optional | NULL | NOT ALLOWED |
| `VARY_LAND` | optional | NULL | NOT ALLOWED |
| `VARY_REPORTING` | optional | NULL | NOT ALLOWED |
| `OTHER` | optional | NULL | **required** |

**Effects:**
- `REPLACE_FUNDING_SCHEDULE`: Old schedule → `SUPERSEDED`; new schedule `replaces_schedule_id` = old schedule ID
- `REMOVE_FUNDING_SCHEDULE`: Affected schedule → `SUPERSEDED` (treated as terminated)
- `VARY_*` options: Modify attributes tracked via `config_json` on the VariationItem and audit logs; do not create new schedules

---

## 10. End-to-End Process Flow

### Step 1 — Financial Planning
1. Create **BriefFinancialApproval** for the project → obtain `APPROVED` status
2. Create **FundingAgreement** (Council link, execution date, document URI)

### Step 2 — Schedule Creation
1. Submit a **FundingSchedule** in `DRAFT`; must reference an approved **PaymentRule**
2. Create an **Approval** record of type `FINANCIAL` for the schedule
3. When Approval → `APPROVED`: FundingSchedule moves to `READY_FOR_EXECUTION`

### Step 3 — Variation / Execution
1. Create a **VariationDeed** (status `DRAFT`, type `INITIAL` for first activation)
2. Add **VariationItem** rows with appropriate `option_type`
3. Send to Council (`SENT`); obtain execution
4. When VariationDeed → `EXECUTED`: target FundingSchedule moves to `EXECUTED`

### Step 4 — Allocation
1. Create **Allocation** rows linking the FundingSchedule to either a **Project** or a **Work**
2. `total_amount` on FundingSchedule = `SUM(allocations.amount)`

### Step 5 — First Payment
1. Generate a **Payment** row (status `PENDING`)
2. Obtain **Approval** of type `PAYMENT`
3. When Approval → `APPROVED`: Payment → `APPROVED`; FundingSchedule → `ACTIVE`
4. Release payment: Payment → `RELEASED`
5. Reconcile: Payment → `RECONCILED`

### Step 6 — Reporting & Subsequent Payments
1. Submit **Report** (Stage 1) → `SUBMITTED → ASSESSED → APPROVED`
2. Stage 1 APPROVED → second payment unlocked
3. Submit **Report** (Stage 2) → same lifecycle
4. Stage 2 APPROVED → final payment unlocked

### Step 7 — FundingNotice Pathway (separate track)
1. Create **FundingNotice** for a project with `capped_amount`
2. Contractor submits **ExpenseClaim** against the notice
3. Claims approved up to `capped_amount`
4. When fully expended or project complete: FundingNotice → `CLOSED`

---

## 11. Session History — Design Decision Log

*Chronological record of prompts and key decisions made during today's modelling session (2026-04-26).*

---

### 10:35 — Initial Domain Model
**Prompt:** Design a Django system for government infrastructure funding and works management. Analyse and model the domain before writing any code.

**Key decisions:**
- Two parallel tracks identified: FundingSchedule-based and FundingNotice-based
- All entities tied to a Council (external client)
- RBAC via Django groups planned

---

### 10:44 — Refactor: Unified Project Entity
**Prompt:** Replace LandProject and Project(Dwelling) with a single Project entity with a type field.

**Key decisions:**
- Single `Project` entity with `type = LAND | DWELLING`
- `parent_land_project_id` self-reference (FK, nullable) on DWELLING projects
- Removes separate LandProject table

---

### 10:56 — Funding Domain Refactor
**Prompt (`d87781e76615893e.txt`):** Separate FundingAgreement (legal umbrella) from FundingSchedule (contract content). Introduce VariationDeed. Introduce FundingNotice as a separate payment pathway.

**Key decisions:**
- `FundingAgreement` = legal umbrella only (no monetary detail)
- `FundingSchedule` = actual contract content with projects, works, allocations
- `VariationDeed` introduced to activate or amend a FundingSchedule
- A FundingSchedule is NOT active unless a VariationDeed with status `EXECUTED` exists
- `FundingNotice` introduced as a capped, schedule-free payment pathway via ExpenseClaims

---

### 11:26 — PaymentRule, Address, ProjectStage, Report
**Prompt (`f9e50a91608207ce.txt`):** Add PaymentRule, refine lifecycle, add Address, introduce ProjectStage and Report.

**Key decisions:**
- `PaymentRule` introduced with `rule_type = SPLIT | INVOICE_BASED`
- FundingSchedule lifecycle: `DRAFT → INTERNAL_APPROVED → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED`
- `Address` entity added (allows TBA placeholders)
- `ProjectStage` introduced for stage-based tracking
- `Report` entity with type/state machine added

---

### 11:35 — Financial Model Corrections
**Prompt (`7616ea3c5a204232.txt`):** Fix cap logic (move cap from PaymentRule to FundingNotice), fix FundingSchedule uniqueness constraint.

**Key decisions:**
- `capped_amount` moved from `PaymentRule.config_json` to `FundingNotice` entity
- `PaymentRule` must be generic and reusable — no project-specific or cap values
- FundingSchedule uniqueness changed from `(council_id, council_number)` to `(funding_agreement_id, schedule_number)` — reflects contractual hierarchy correctly
- Reason: FundingAgreement already links to Council; schedule numbers are relative to the agreement

---

### 11:37 — Final Corrections to Funding Model
**Prompt (`2e8586c45474a3bf.txt`):** Add PaymentRule linkage to FundingSchedule, fix Project completeness, fix Report entity, standardise FundingSchedule status, expand FundingNotice and ExpenseClaim for auditability.

**Key decisions:**
- `payment_rule_id` FK added to FundingSchedule as NOT NULL
- Project confirmed to include: `parent_land_project_id`, `status`, `start_date`, `completion_date`
- Report uses only `project_id` (not `land_project_id` — land projects are just Projects with `type = LAND`)
- FundingSchedule status standardised to: `DRAFT → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED`
- FundingNotice expanded with: `issued_date`, `approved_by`, `description`, `reference_number`
- ExpenseClaim expanded with: `approved_by`, `approved_date`

---

### 11:47 — Approval Entity + VariationItem + Lifecycle Depth
**Prompt (`b427b93360726a22.txt`):** Introduce generic Approval entity, expand Report, expand ProjectStage, define Payment lifecycle, introduce VariationItem.

**Key decisions:**
- Generic `Approval` entity introduced for: Reports, ExpenseClaims, Funding approvals, VariationDeeds
- `VariationItem` entity introduced — a VariationDeed has many VariationItems
- VariationItem `option_type` enum defined (ADD_SCHEDULE, REMOVE_SCHEDULE, REPLACE_SCHEDULE, VARY_*, OTHER)
- Payment lifecycle confirmed: `PENDING → APPROVED → RELEASED → RECONCILED`
- `replaces_schedule_id` added to FundingSchedule for REPLACE_SCHEDULE tracking

---

### 12:01 — Final Complete Domain Model
**Prompt (`f9422e4fd220a0a2.txt` / `a904debc03541ed5.txt`):** Produce the complete, final, implementation-ready domain model.

**Key decisions (consolidated final state):**
- `BriefFinancialApproval` added as a pre-condition entity for FundingSchedule creation
- `WorkflowAction` added as immutable event log (separate from Approval decision authority)
- `AuditLog` added for data-level change tracking
- `Payment.payment_source_type = SCHEDULE | NOTICE` added for clarity
- `VariationItem.config_json` restricted to `option_type = OTHER` only — all other types use structured columns
- FundingSchedule lifecycle finalised: `DRAFT → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED → SUPERSEDED`
- Confirmed: Approval system governs decisions; WorkflowAction is log-only

> **Note:** The session ended with an API token limit error at ~12:05. The process flow section (Step 4 onwards) was partially cut off in the raw output but has been reconstructed from the prompt specification above.

---

## 12. Remaining Work / Next Steps

Based on the session, the domain model is **complete**. The following Django implementation work remains:

### Immediate — Django Models
- [ ] Scaffold all Django models from the entity table above
- [ ] Add `Meta.constraints` for all UNIQUE and CHECK constraints (especially Allocation's `project_id`/`work_id` check)
- [ ] Configure `on_delete` behaviour for all FK relationships
- [ ] Add `__str__` methods and `Meta.ordering` where useful
- [ ] Set up Django model signals (or override `save()`) to auto-generate `WorkflowAction` and `AuditLog` records on state changes

### Migrations & DB Setup
- [ ] Run `makemigrations` and `migrate`
- [ ] Add DB-level CHECK constraint for Allocation (`project_id` XOR `work_id`)
- [ ] Add DB-level UNIQUE constraints for FundingSchedule and FundingNotice

### Admin / API Layer
- [ ] Register all models with Django Admin (or configure DRF viewsets)
- [ ] Implement serializers for each entity
- [ ] Add business rule validation in serializer `.validate()` methods or model `.clean()` methods:
  - BriefFinancialApproval must be APPROVED before FundingSchedule creation
  - ExpenseClaim cap enforcement before approval
  - PaymentRule immutability once linked
  - FundingSchedule lifecycle transition guards

### Lifecycle Automation
- [ ] Implement signal or service to set FundingSchedule → `ACTIVE` on first approved Payment
- [ ] Implement logic to set FundingSchedule → `SUPERSEDED` on REPLACE_FUNDING_SCHEDULE execution
- [ ] Implement payment gate checks for Stage 1/Stage 2 report approval

### Future Considerations
- RBAC / permission model (Django groups or django-guardian)
- Django REST Framework API design
- Frontend (likely React or similar)
- Integration with OpenDocs or Google Drive for document_uri generation
- Reporting dashboard for financial traceability views

---

## 13. Work Step Infrastructure & Cashflow Forecasting

*Added: 2026-05-21*

### Overview

Capital Works projects require a rolling S-curve cashflow forecast based on construction work steps. This is distinct from Capital Grants projects which use payment milestone dates.

### New Entities

#### WorkStepDefinition
Global catalogue of named work steps. Not tied to any WorkType — reused across groups.

| Field | Type / Notes |
|-------|-------------|
| `name` | varchar(200), required |
| `description` | text, optional |
| `is_active` | boolean, default True |

#### WorkStepGroup
A named package of ordered steps, linked to a WorkType.

| Field | Type / Notes |
|-------|-------------|
| `work_type` | FK → WorkType |
| `name` | varchar(200) |
| `is_active` | boolean |
| `total_cost_percentage()` | property — sum of item cost percentages (must equal 100) |

#### WorkStepGroupItem
Through table: group → step with ordering and financial metadata.

| Field | Type / Notes |
|-------|-------------|
| `group` | FK → WorkStepGroup |
| `step` | FK → WorkStepDefinition |
| `order` | PositiveInteger, unique per group |
| `cost_percentage` | Decimal(5,2) |
| `expected_duration_days` | PositiveInteger |
| `stage_gate` | enum: `''` (none) / `STAGE1` / `STAGE2` — at most one of each per group |

### New Fields on Existing Models

**WorkType:** `short_code` varchar(10) — abbreviation for report labels (e.g. `DH`, `TRI`, `EXT`)

**Work:**
- `cashflow_method` — `MILESTONE` (Capital Grants) / `WORKSTEP` (Capital Works)
- `step_group` — FK → WorkStepGroup (null/blank)
- `actual_start_date` — DateField (null/blank) — anchors rolling forecast

**WorkStep (expanded):**
- `group_item` FK → WorkStepGroupItem, `step_name`, `order`, `expected_duration_days`, `expected_cost_percentage`, `is_active`, `forecast_start_date`, `forecast_completion_date`, `actual_completion_date`

**Payment:** `forecast_release_date` DateField — Capital Grants cashflow planning

### Services (`apps.core.services.workstep_forecast`)

- **`apply_group_to_work(work)`** — idempotently creates WorkStep rows from the group; calls `recalculate_forecast`
- **`recalculate_forecast(work)`** — cascades forecast dates through active steps; `actual_completion_date` anchors subsequent steps; uses `bulk_update`

Signals auto-trigger `recalculate_forecast` on Work save (when `cashflow_method=WORKSTEP`) and on WorkStep save.

### Monthly Progress Report

URL: `/reports/monthly/<council_pk>/` — per-council, cumulative, living document.

**Scope:** projects with ≥1 RELEASED payment and state ≠ COMPLETED.

**Row format:** `234 Smith St (Lot 23 SP32435) (2B DH)` — street + lot/plan + bedrooms + WorkType.short_code. Links open work detail in a new tab.

**Columns:** Address/Work, Cashflow method, Work status, Stage 1 gate (✓ + date), Stage 2 gate (✓ + date), Notes.

---

*End of RICD Project Reference Document*
*Generated: 2026-04-26 | Updated: 2026-05-21*
