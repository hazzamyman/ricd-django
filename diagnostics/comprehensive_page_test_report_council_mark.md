# Comprehensive Django Application Testing Report

**Date:** 2025-09-30 11:52:47
**Test Environment:** Django Development Server on http://192.168.5.64:8000
**Test Credentials:** Council User (mark) (mark)
**User Type:** Council

## Test Summary
- **Total Tests:** 33
- **Successful:** 20
- **Failed:** 13
- **Success Rate:** 60.6%

## Test Results

| URL | Status | Error Details |
|-----|--------|---------------|
| `/` | ✓ (200) |  |
| `/accounts/login/` | ✓ (200) |  |
| `/portal/ricd/` | ✓ (200) |  |
| `/portal/council/` | ✓ (200) |  |
| `/portal/projects/` | ✓ (200) |  |
| `/portal/councils/` | ✓ (200) |  |
| `/portal/works/` | ✓ (200) |  |
| `/portal/analytics/` | ✓ (200) |  |
| `/portal/help/ricd/` | ✓ (200) |  |
| `/portal/help/council/` | ✓ (200) |  |
| `/portal/maintenance/construction-methods/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/site-configuration/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/defects/` | ✓ (200) |  |
| `/portal/defects/create/` | ✓ (200) |  |
| `/portal/users/` | ✓ (200) |  |
| `/portal/officers/` | ✓ (200) |  |
| `/portal/work-types/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/output-types/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/monthly-tracker-items/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/monthly-tracker-item-groups/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/quarterly-report-items/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/stage1-steps/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/maintenance/stage2-steps/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/funding-approvals/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/agreements/remote-capital/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/agreements/forward-rpf/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/agreements/interim-frp/` | ✗ (403) | HTTP 403 - Forbidden (authentication required) |
| `/portal/reports/enhanced-monthly/` | ✓ (200) |  |
| `/portal/reports/enhanced-quarterly/` | ✓ (200) |  |
| `/portal/reports/enhanced-stage1/` | ✓ (200) |  |
| `/portal/reports/enhanced-stage2/` | ✓ (200) |  |
| `/portal/reports/monthly/` | ✓ (200) |  |
| `/portal/reports/quarterly/` | ✓ (200) |  |

## Detailed Results

### /
- **Full URL:** http://192.168.5.64:8000/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 5743 bytes
- **Timestamp:** 2025-09-30T11:52:44.525354

### /accounts/login/
- **Full URL:** http://192.168.5.64:8000/accounts/login/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 5743 bytes
- **Timestamp:** 2025-09-30T11:52:44.569314

### /portal/ricd/
- **Full URL:** http://192.168.5.64:8000/portal/ricd/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 21436 bytes
- **Timestamp:** 2025-09-30T11:52:45.585396

### /portal/council/
- **Full URL:** http://192.168.5.64:8000/portal/council/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 21436 bytes
- **Timestamp:** 2025-09-30T11:52:45.645198

### /portal/projects/
- **Full URL:** http://192.168.5.64:8000/portal/projects/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 23677 bytes
- **Timestamp:** 2025-09-30T11:52:45.709219

### /portal/councils/
- **Full URL:** http://192.168.5.64:8000/portal/councils/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 47485 bytes
- **Timestamp:** 2025-09-30T11:52:45.743504

### /portal/works/
- **Full URL:** http://192.168.5.64:8000/portal/works/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 22119 bytes
- **Timestamp:** 2025-09-30T11:52:45.821399

### /portal/analytics/
- **Full URL:** http://192.168.5.64:8000/portal/analytics/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 24457 bytes
- **Timestamp:** 2025-09-30T11:52:45.925257

### /portal/help/ricd/
- **Full URL:** http://192.168.5.64:8000/portal/help/ricd/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 15751 bytes
- **Timestamp:** 2025-09-30T11:52:45.977158

### /portal/help/council/
- **Full URL:** http://192.168.5.64:8000/portal/help/council/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 18508 bytes
- **Timestamp:** 2025-09-30T11:52:46.041186

### /portal/maintenance/construction-methods/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/construction-methods/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 61 bytes
- **Timestamp:** 2025-09-30T11:52:46.089190
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/site-configuration/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/site-configuration/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 59 bytes
- **Timestamp:** 2025-09-30T11:52:46.173136
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/defects/
- **Full URL:** http://192.168.5.64:8000/portal/defects/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 11643 bytes
- **Timestamp:** 2025-09-30T11:52:46.241148

### /portal/defects/create/
- **Full URL:** http://192.168.5.64:8000/portal/defects/create/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 11722 bytes
- **Timestamp:** 2025-09-30T11:52:46.313303

### /portal/users/
- **Full URL:** http://192.168.5.64:8000/portal/users/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 29349 bytes
- **Timestamp:** 2025-09-30T11:52:46.389235

### /portal/officers/
- **Full URL:** http://192.168.5.64:8000/portal/officers/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 10947 bytes
- **Timestamp:** 2025-09-30T11:52:46.461184

### /portal/work-types/
- **Full URL:** http://192.168.5.64:8000/portal/work-types/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 51 bytes
- **Timestamp:** 2025-09-30T11:52:46.509234
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/output-types/
- **Full URL:** http://192.168.5.64:8000/portal/output-types/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 53 bytes
- **Timestamp:** 2025-09-30T11:52:46.557195
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/monthly-tracker-items/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/monthly-tracker-items/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 62 bytes
- **Timestamp:** 2025-09-30T11:52:46.605155
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/monthly-tracker-item-groups/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/monthly-tracker-item-groups/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 14 bytes
- **Timestamp:** 2025-09-30T11:52:46.693141
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/quarterly-report-items/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/quarterly-report-items/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 14 bytes
- **Timestamp:** 2025-09-30T11:52:46.741193
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/stage1-steps/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/stage1-steps/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 14 bytes
- **Timestamp:** 2025-09-30T11:52:46.789264
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/maintenance/stage2-steps/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/stage2-steps/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 14 bytes
- **Timestamp:** 2025-09-30T11:52:46.837153
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/funding-approvals/
- **Full URL:** http://192.168.5.64:8000/portal/funding-approvals/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 58 bytes
- **Timestamp:** 2025-09-30T11:52:46.885123
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/agreements/remote-capital/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/remote-capital/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 74 bytes
- **Timestamp:** 2025-09-30T11:52:46.937123
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/agreements/forward-rpf/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/forward-rpf/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 63 bytes
- **Timestamp:** 2025-09-30T11:52:46.985148
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/agreements/interim-frp/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/interim-frp/
- **Status:** FAILED
- **HTTP Code:** 403
- **Response Size:** 63 bytes
- **Timestamp:** 2025-09-30T11:52:47.033177
- **Error Details:** HTTP 403 - Forbidden (authentication required)

### /portal/reports/enhanced-monthly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-monthly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 102829 bytes
- **Timestamp:** 2025-09-30T11:52:47.275637

### /portal/reports/enhanced-quarterly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-quarterly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 15517 bytes
- **Timestamp:** 2025-09-30T11:52:47.340011

### /portal/reports/enhanced-stage1/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-stage1/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 15491 bytes
- **Timestamp:** 2025-09-30T11:52:47.401192

### /portal/reports/enhanced-stage2/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-stage2/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 15502 bytes
- **Timestamp:** 2025-09-30T11:52:47.461494

### /portal/reports/monthly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/monthly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 19423 bytes
- **Timestamp:** 2025-09-30T11:52:47.569317

### /portal/reports/quarterly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/quarterly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 25100 bytes
- **Timestamp:** 2025-09-30T11:52:47.657408

