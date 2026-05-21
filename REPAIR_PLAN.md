# RICD Application - Comprehensive Repair Plan
**Date:** 2026-05-14  
**Status:** Testing Complete - Issues Documented

---

## Executive Summary

Tested all major pages and endpoints. Found **6 missing navigation endpoints**, **1 template syntax error**, and **1 missing API endpoint**. Dashboard, API layer, and admin panel are functional.

---

## Issues Found

### Category 1: Template Errors (1 issue)

#### Issue 1.1: Cashflow Page - Invalid Template Filter
- **Location:** `/cashflow/` → `src/apps/ui/templates/dashboard/cashflow.html` line 71
- **Error Type:** `TemplateSyntaxError: Invalid filter: 'mul'`
- **Root Cause:** Template uses custom filters `mul` and `div` that don't exist in Django
- **Affected Template Code:**
  ```
  {{ item.actual|add:0|mul:100|div:item.forecast|floatformat:1 }}%
  ```
- **Solution Type:** Move calculation to view (add `drawdown_percent` field to context dict)
- **Severity:** High (blocks cashflow page from loading)

---

### Category 2: Missing Navigation Endpoints (6 issues)

All of these are linked in `src/templates/base.html` navbar but have no URL routes or views.

#### Issue 2.1: Projects Page
- **URL:** `/projects/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** List all projects with filters/search
- **Severity:** High (primary navigation link)

#### Issue 2.2: Variations Page
- **URL:** `/variations/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** List all variation deeds
- **Severity:** High (primary navigation link)

#### Issue 2.3: Reports Page
- **URL:** `/reports/monthly/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** View monthly reports
- **Severity:** High (primary navigation link)

#### Issue 2.4: Planning Page
- **URL:** `/planning/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** Planning interface
- **Severity:** Medium (restricted to FNC users)

#### Issue 2.5: Land & Infrastructure Page
- **URL:** `/land/land-projects/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** Land and infrastructure project management
- **Severity:** Medium (restricted to FNC users)

#### Issue 2.6: Documents Page
- **URL:** `/documents/`
- **Error:** HTTP 404 - Page not found
- **Expected Function:** Document repository/management
- **Severity:** Medium (restricted to FNC users)

---

### Category 3: Missing API Endpoints (1 issue)

#### Issue 3.1: Variations API Endpoint
- **URL:** `/api/variations/`
- **Error:** HTTP 404 - Not Found
- **Existing Similar Endpoints (all 200 OK):**
  - `/api/funding-agreements/` ✓
  - `/api/funding-schedules/` ✓
  - `/api/approvals/` ✓
  - `/api/payments/` ✓
  - `/api/brief-financial-approvals/` ✓
  - `/api/funding-notices/` ✓
  - `/api/expense-claims/` ✓
  - `/api/workflow-actions/` ✓
  - `/api/audit-logs/` ✓
- **Expected Function:** CRUD operations on Variation Deeds
- **Severity:** Medium (API completeness)

---

## Working Components ✓

| Component | URL | Status |
|-----------|-----|--------|
| Dashboard | `/dashboard/` | ✓ Fully functional |
| Aggregate Outputs | `/aggregate/` | ✓ Fully functional |
| Admin Panel | `/admin/` | ✓ Fully functional |
| Payment Rules API | `/api/payment-rules/` | ✓ Working |
| Funding Agreements API | `/api/funding-agreements/` | ✓ Working |
| Funding Schedules API | `/api/funding-schedules/` | ✓ Working |
| Approvals API | `/api/approvals/` | ✓ Working |
| Payments API | `/api/payments/` | ✓ Working |
| Brief Financial Approvals API | `/api/brief-financial-approvals/` | ✓ Working |
| Funding Notices API | `/api/funding-notices/` | ✓ Working |
| Expense Claims API | `/api/expense-claims/` | ✓ Working |
| Workflow Actions API | `/api/workflow-actions/` | ✓ Working |
| Audit Logs API | `/api/audit-logs/` | ✓ Working |

---

## Repair Strategy

### Phase 1: Quick Fixes (Template Error)
- **Time:** ~15 minutes
- **Files:** `src/apps/ui/views/dashboard_views.py` (fix cashflow_view)
- **Tasks:**
  1. Add `drawdown_percent` calculation to `by_program` items
  2. Update `cashflow.html` template to use calculated value

### Phase 2: Missing UI Pages (6 pages)
- **Time:** ~2-3 hours
- **Approach:** Implement stub pages that list entities
- **Pages to implement:**
  1. Projects list page
  2. Variations list page
  3. Reports dashboard page
  4. Planning interface
  5. Land & Infrastructure projects
  6. Documents repository

### Phase 3: Missing API Endpoint (Variations)
- **Time:** ~30 minutes
- **Tasks:**
  1. Create VariationViewSet with standard CRUD operations
  2. Register in API router

### Phase 4: Testing & Verification
- **Time:** ~1 hour

---

## Summary Table

| # | Issue | Type | Severity | Files Affected |
|---|-------|------|----------|-----------------|
| 1.1 | Cashflow filter error | Template | High | cashflow.html, dashboard_views.py |
| 2.1 | Projects 404 | Missing Page | High | urls.py, views.py |
| 2.2 | Variations 404 | Missing Page | High | urls.py, views.py |
| 2.3 | Reports 404 | Missing Page | High | urls.py, views.py |
| 2.4 | Planning 404 | Missing Page | Medium | urls.py, views.py |
| 2.5 | Land/Infra 404 | Missing Page | Medium | urls.py, views.py |
| 2.6 | Documents 404 | Missing Page | Medium | urls.py, views.py |
| 3.1 | Variations API 404 | Missing API | Medium | api/urls.py, api/viewsets/ |

**Total Issues:** 8  
**High Severity:** 4  
**Medium Severity:** 4  

