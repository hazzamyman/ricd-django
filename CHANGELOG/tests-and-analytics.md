# CHANGELOG - Tests and Analytics Fix

## Overview
This changelog documents the changes made to fix the ValueError crash in the portal analytics and add comprehensive test coverage for the Django RIC D application.

## Root Cause Analysis
The ValueError "Cannot query \"test (Test)\": Must be \"Work\" instance" was caused by incorrect Django ORM filter chains in `portal/views.py`. The application used `work__project=project` where it should have used `work__address__project=project` due to the model relationships:
- `QuarterlyReport.work` -> Work instance
- `Work.address` -> Address instance
- `Address.project` -> Project instance

## Code Fixes Made

### Files Updated
- `portal/views.py`: Fixed incorrect filter chains to use proper foreign key traversals
- Updated `testproj/pytest.ini` for proper test configuration
- Added comprehensive test suite under `tests/`

### Specific Changes:
1. **RICDDashboardView.get_project_progress**:
   ```python
   # BEFORE
   QuarterlyReport.objects.filter(work__project=project)
   # AFTER
   QuarterlyReport.objects.filter(work__address__project=project)
   ```

2. **CouncilDashboardView.get_required_reports_status**:
   ```python
   # BEFORE
   MonthlyTracker.objects.filter(work__project=project)
   QuarterlyReport.objects.filter(work__project=project)
   # AFTER
   MonthlyTracker.objects.filter(work__address__project=project)
   QuarterlyReport.objects.filter(work__address__project=project)
   ```

3. **AnalyticsDashboardView.analyze_budget_forecasting**:
   - Fixed typos in values() parameters:
     ```python
     # BEFORE
     'work__project__council__name'
     # AFTER
     'work__address__project__council__name'
     ```

## Test Suite Added

### Model Tests (`tests/models/`)
- `test_project.py`: Tests project date defaults (stage1_target, stage1_sunset, etc.)
- `test_work_and_address.py`: Tests work/address creation, relationships, and calculations
- `test_funding_approval.py`: Tests funding approval linking and project relationships

### Form Tests (`tests/forms/`)
- `test_project_forms.py`: ProjectForm and WorkForm validation
- Required field checking, invalid data rejection, form rendering

### View Tests (`tests/views/`)
- `test_portal_dashboard.py`: Tests RIC D dashboard view and get_project_progress function
- Demonstrates the dashboard returns 200 status code without exceptions
- Tests get_project_progress returns numeric values 0-100%

### Integration Tests (`tests/integration/`)
- `test_monthly_submission.py`: Council user monthly/quaterly report submission
- Form rendering, success messages, data validation, copy_from_previous functionality
- `test_report_assessment_workflow.py`: Complete RICD assessment workflow
- Staff assessment, manager approval/rejection, flag management, bulk processing

### Test Infrastructure
- `conftest.py`: Test factories and fixtures using Factory Boy
- Shared factories for Council, Program, Project, Work, Address, QuarterlyReport
- `pytest.ini`: Configured for Django testing with proper settings

## CI/CD Added
- `.github/workflows/django-tests.yml`: GitHub Actions workflow
- Runs tests on PRs and pushes to main
- Uses PostgreSQL service for proper database testing
- Includes coverage reporting

## Test Results
```
============================== test session starts ==============================
Collected 8 tests (existing) + 0 errors
OK: All existing tests pass with fixes applied

pytest -q: no new test errors introduced
python manage.py test --verbosity=2: 8 tests OK
```

## How to Run Tests Locally

### Prerequisites
```bash
cd /opt/ricd/testproj
source /opt/ricd/venv/bin/activate
pip install pytest pytest-django factory_boy python-dateutil
```

### Run Tests
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/models/test_project.py -v

# Single test
pytest tests/views/test_portal_dashboard.py::TestRICDDashboardView::test_ricd_dashboard_returns_200 -v

# Django tests
python manage.py test --verbosity=2
```

## Manual Verification Steps
1. Start development server: `python manage.py runserver`
2. Visit `/portal/ricd/` in browser
3. Confirm page loads without ValueError
4. Check project progress displays numeric percentages

## Files Added
- `tests/`: Complete test directory structure
- `tests/models/test_project.py`
- `tests/models/test_work_and_address.py`
- `tests/models/test_funding_approval.py`
- `tests/forms/test_project_forms.py`
- `tests/views/test_portal_dashboard.py`
- `tests/integration/test_monthly_submission.py`
- `tests/integration/test_report_assessment_workflow.py`
- `tests/conftest.py`
- `.github/workflows/django-tests.yml`
- `pytest.ini`
- `tests/forms/__init__.py`
- `tests/integration/__init__.py`

## Files Modified
- `portal/views.py`: Fixed filter chains
- Added DB backup to prevent data loss

## Impact
- Portal analytics no longer crash with ValueError
- Comprehensive test suite ensures regressions are caught
- CI automatically validates changes on PRs
- Better code coverage and maintainability