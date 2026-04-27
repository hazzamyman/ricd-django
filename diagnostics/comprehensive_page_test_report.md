# Comprehensive Django Application Testing Report

**Date:** 2025-09-30 10:24:55
**Test Environment:** Django Development Server on http://192.168.5.64:8000
**Test Credentials:** Username: harry

## Test Summary
- **Total Tests:** 33
- **Successful:** 32
- **Failed:** 1
- **Success Rate:** 97.0%

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
| `/portal/maintenance/construction-methods/` | ✓ (200) |  |
| `/portal/maintenance/site-configuration/` | ✓ (200) |  |
| `/portal/defects/` | ✓ (200) |  |
| `/portal/defects/create/` | ✗ (500) | HTTP 500 - Internal server error
Traceback:       toggle('browserTraceback', 'pastebinTraceback');       return false;     }   </script>    </head> <body> <div id="summary">   <h1>NameError        at /portal/defects/create/</h1> |
| `/portal/users/` | ✓ (200) |  |
| `/portal/officers/` | ✓ (200) |  |
| `/portal/work-types/` | ✓ (200) |  |
| `/portal/output-types/` | ✓ (200) |  |
| `/portal/maintenance/monthly-tracker-items/` | ✓ (200) |  |
| `/portal/maintenance/monthly-tracker-item-groups/` | ✓ (200) |  |
| `/portal/maintenance/quarterly-report-items/` | ✓ (200) |  |
| `/portal/maintenance/stage1-steps/` | ✓ (200) |  |
| `/portal/maintenance/stage2-steps/` | ✓ (200) |  |
| `/portal/funding-approvals/` | ✓ (200) |  |
| `/portal/agreements/remote-capital/` | ✓ (200) |  |
| `/portal/agreements/forward-rpf/` | ✓ (200) |  |
| `/portal/agreements/interim-frp/` | ✓ (200) |  |
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
- **Timestamp:** 2025-09-30T10:24:52.913582

### /accounts/login/
- **Full URL:** http://192.168.5.64:8000/accounts/login/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 5743 bytes
- **Timestamp:** 2025-09-30T10:24:52.957411

### /portal/ricd/
- **Full URL:** http://192.168.5.64:8000/portal/ricd/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 41676 bytes
- **Timestamp:** 2025-09-30T10:24:53.603529

### /portal/council/
- **Full URL:** http://192.168.5.64:8000/portal/council/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 29271 bytes
- **Timestamp:** 2025-09-30T10:24:53.681262

### /portal/projects/
- **Full URL:** http://192.168.5.64:8000/portal/projects/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 59355 bytes
- **Timestamp:** 2025-09-30T10:24:53.733946

### /portal/councils/
- **Full URL:** http://192.168.5.64:8000/portal/councils/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 63903 bytes
- **Timestamp:** 2025-09-30T10:24:53.852094

### /portal/works/
- **Full URL:** http://192.168.5.64:8000/portal/works/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 40104 bytes
- **Timestamp:** 2025-09-30T10:24:53.906626

### /portal/analytics/
- **Full URL:** http://192.168.5.64:8000/portal/analytics/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 40875 bytes
- **Timestamp:** 2025-09-30T10:24:53.970331

### /portal/help/ricd/
- **Full URL:** http://192.168.5.64:8000/portal/help/ricd/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 32169 bytes
- **Timestamp:** 2025-09-30T10:24:54.025299

### /portal/help/council/
- **Full URL:** http://192.168.5.64:8000/portal/help/council/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 34926 bytes
- **Timestamp:** 2025-09-30T10:24:54.055729

### /portal/maintenance/construction-methods/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/construction-methods/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 26626 bytes
- **Timestamp:** 2025-09-30T10:24:54.125234

### /portal/maintenance/site-configuration/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/site-configuration/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 43805 bytes
- **Timestamp:** 2025-09-30T10:24:54.145596

### /portal/defects/
- **Full URL:** http://192.168.5.64:8000/portal/defects/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 32055 bytes
- **Timestamp:** 2025-09-30T10:24:54.209296

### /portal/defects/create/
- **Full URL:** http://192.168.5.64:8000/portal/defects/create/
- **Status:** FAILED
- **HTTP Code:** 500
- **Response Size:** 103050 bytes
- **Timestamp:** 2025-09-30T10:24:54.261767
- **Error Details:** HTTP 500 - Internal server error
Traceback:       toggle('browserTraceback', 'pastebinTraceback');       return false;     }   </script>    </head> <body> <div id="summary">   <h1>NameError        at /portal/defects/create/</h1>

### /portal/users/
- **Full URL:** http://192.168.5.64:8000/portal/users/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 74200 bytes
- **Timestamp:** 2025-09-30T10:24:54.294047

### /portal/officers/
- **Full URL:** http://192.168.5.64:8000/portal/officers/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 27767 bytes
- **Timestamp:** 2025-09-30T10:24:54.349232

### /portal/work-types/
- **Full URL:** http://192.168.5.64:8000/portal/work-types/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 36776 bytes
- **Timestamp:** 2025-09-30T10:24:54.425197

### /portal/output-types/
- **Full URL:** http://192.168.5.64:8000/portal/output-types/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 49073 bytes
- **Timestamp:** 2025-09-30T10:24:54.509320

### /portal/maintenance/monthly-tracker-items/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/monthly-tracker-items/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 68555 bytes
- **Timestamp:** 2025-09-30T10:24:54.526228

### /portal/maintenance/monthly-tracker-item-groups/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/monthly-tracker-item-groups/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 29287 bytes
- **Timestamp:** 2025-09-30T10:24:54.581446

### /portal/maintenance/quarterly-report-items/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/quarterly-report-items/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 25540 bytes
- **Timestamp:** 2025-09-30T10:24:54.637244

### /portal/maintenance/stage1-steps/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/stage1-steps/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 25504 bytes
- **Timestamp:** 2025-09-30T10:24:54.693257

### /portal/maintenance/stage2-steps/
- **Full URL:** http://192.168.5.64:8000/portal/maintenance/stage2-steps/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 25506 bytes
- **Timestamp:** 2025-09-30T10:24:54.749369

### /portal/funding-approvals/
- **Full URL:** http://192.168.5.64:8000/portal/funding-approvals/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 30322 bytes
- **Timestamp:** 2025-09-30T10:24:54.805403

### /portal/agreements/remote-capital/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/remote-capital/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 29521 bytes
- **Timestamp:** 2025-09-30T10:24:54.861285

### /portal/agreements/forward-rpf/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/forward-rpf/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 26700 bytes
- **Timestamp:** 2025-09-30T10:24:54.917249

### /portal/agreements/interim-frp/
- **Full URL:** http://192.168.5.64:8000/portal/agreements/interim-frp/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 26726 bytes
- **Timestamp:** 2025-09-30T10:24:54.973249

### /portal/reports/enhanced-monthly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-monthly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 137039 bytes
- **Timestamp:** 2025-09-30T10:24:55.143459

### /portal/reports/enhanced-quarterly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-quarterly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 32180 bytes
- **Timestamp:** 2025-09-30T10:24:55.205225

### /portal/reports/enhanced-stage1/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-stage1/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 32144 bytes
- **Timestamp:** 2025-09-30T10:24:55.293263

### /portal/reports/enhanced-stage2/
- **Full URL:** http://192.168.5.64:8000/portal/reports/enhanced-stage2/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 32155 bytes
- **Timestamp:** 2025-09-30T10:24:55.353277

### /portal/reports/monthly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/monthly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 35801 bytes
- **Timestamp:** 2025-09-30T10:24:55.413431

### /portal/reports/quarterly/
- **Full URL:** http://192.168.5.64:8000/portal/reports/quarterly/
- **Status:** SUCCESS
- **HTTP Code:** 200
- **Response Size:** 41478 bytes
- **Timestamp:** 2025-09-30T10:24:55.473570

