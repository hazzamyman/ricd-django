# RICD Domain Model Gap Analysis

**Analysis Date:** 2026-04-27
**Reference:** docs/RICD_domain_model.md

---

## Summary

The current codebase covers ~60% of the domain model entities. Major gaps exist in:
1. FundingAgreement entity (legal umbrella)
2. PaymentRule (immutable, versioned)
3. FundingNotice + ExpenseClaim pathway
4. BriefFinancialApproval (pre-condition)
5. Generic Approval + WorkflowAction + AuditLog

---

## Entity Mapping

### ✅ Present & Aligned

| Domain Entity | Current Model | App | Status |
|--------------|---------------|-----|--------|
| Council | Council | councils | ✅ Matches spec |
| Program | Program | programs | ✅ Matches spec |
| Project | Project | projects | ✅ Has type field, parent ref |
| Address | Address | addresses | ✅ Matches spec |
| Work | Work | works | ✅ Matches spec |
| WorkType | WorkType | works | ✅ Matches spec |
| ProjectStage | Stage | stages | ✅ Matches spec |
| Report | Report | reports | ✅ Matches spec |
| VariationDeed | Variation | variations | ✅ Matches spec |
| VariationItem | VariationItem | variations | ✅ Matches spec |
| Payment | Payment | payments | ✅ Matches spec |

### ⚠️ Present but Different Structure

| Domain Entity | Current Model | Issues |
|--------------|--------------|--------|
| **FundingAgreement** | `FundingSchedule` (funding app) | Currently serves as both agreement + schedule. Spec requires split. |
| **FundingSchedule** | `FundingSchedule` (funding app) | Missing: payment_rule_id (NOT NULL), schedule_number, replaces_schedule_id, agreement link |
| **Allocation** | `WorkFunding` (funding app) | Partial. Missing DB CHECK for XOR project/work |
| **Project (LAND)** | `LandProject` (land_infra app) | Separate app instead of type=LAND on Project |
| **Approval** | `FundingApproval` (funding app) | Specific to funding, not generic |
| **FundingNotice** | None | Missing entity |
| **ExpenseClaim** | None | Missing entity |
| **BriefFinancialApproval** | `FundingApproval` (funding app) | Partial - serves similar purpose |
| **WorkflowAction** | `ProjectStateLog` (funding app) | Partial - only projects, not generic |
| **AuditLog** | None | Missing entity |
| **PaymentRule** | None | Missing entity |

### ❌ Missing Entities

| Domain Entity | Priority | Notes |
|--------------|----------|-------|
| PaymentRule | HIGH | Required for FundingSchedule (NOT NULL) |
| FundingAgreement | HIGH | Legal umbrella - split from FundingSchedule |
| FundingNotice | MEDIUM | Capped payment pathway |
| ExpenseClaim | MEDIUM | Against FundingNotice |
| BriefFinancialApproval | HIGH | Pre-condition for funding creation |
| Approval (generic) | HIGH | Unified governance |
| WorkflowAction | MEDIUM | Generic event log |
| AuditLog | LOW | Data-level change tracking |

---

## Structural Gaps

### 1. FundingSchedule
**Current:** Links to Project OR LandProject directly
**Spec Required:**
- `funding_agreement_id` FK → FundingAgreement
- `schedule_number` int
- `payment_rule_id` FK (NOT NULL)
- `replaces_schedule_id` self-FK
- Status: `DRAFT → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED/SUPERSEDED`

### 2. Project
**Current:** Uses LandProject for land, Project for dwelling
**Spec Required:** Single entity with `type = LAND | DWELLING`, `parent_land_project_id` self-FK

### 3. PaymentRule
**Spec Required (NOT NULL on FundingSchedule):**
- `id`, `name`, `rule_type` (SPLIT/INVOICE_BASED), `config_json`, `version`

### 4. Approval Chain
**Current:** FundingApproval has hardcoded chain (manager → director → ed → gm → ddg → dg)
**Spec Required:** Generic Approval entity with `entity_type`, `entity_id`, `approval_type`, `required_role`

---

## Key Business Rules Not Implemented

1. **BriefFinancialApproval must be APPROVED before FundingSchedule creation**
2. **PaymentRule immutable once linked to FundingSchedule**
3. **ExpenseClaim cap enforcement** (SUM approved ≤ capped_amount)
4. **FundingSchedule.status = ACTIVE** on first APPROVED payment
5. **FundingSchedule.status = SUPERSEDED** on REPLACE variation
6. **Stage 1 APPROVED** → unlocks second payment
7. **Stage 2 APPROVED** → unlocks final payment

---

## Recommendations

### Phase 1: Core Structure (HIGH)
1. Create PaymentRule model
2. Create FundingAgreement model  
3. Refactor FundingSchedule to reference FundingAgreement, add payment_rule_id (NOT NULL)
4. Add BriefFinancialApproval model

### Phase 2: Payment Pathways (MEDIUM)
1. Create FundingNotice model
2. Create ExpenseClaim model
3. Implement cap enforcement logic

### Phase 3: Governance (MEDIUM)
1. Create generic Approval model
2. Create WorkflowAction model (generic, not just projects)
3. Create AuditLog model

### Phase 4: Cleanup (LOW)
1. Merge LandProject → Project with type field
2. Add DB CHECK constraint for Allocation (project XOR work)
3. Implement lifecycle signals/automation

---

## Migration Complexity Estimate

| Phase | Complexity | Models Affected |
|-------|-----------|---------------|
| Phase 1 | High | funding |
| Phase 2 | Medium | funding, payments |
| Phase 3 | Medium | funding, accounts |
| Phase 4 | High | projects, land_infra |

**Total models to modify/create:** ~12
**Estimated migration files:** 8-10