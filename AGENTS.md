# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Lint/Test Commands (Non-Obvious)
- Run full regression: From ricd/ root, `./run_robust_tests.sh` (runs pre_deployment_setup.sh + robust_system_test.py; post-run: `cd testproj && python manage.py migrate`).
- Unit/Integration: From testproj/, `pytest` (uses --reuse-db – watch for state bleed; single: `pytest -k "pattern"` or `pytest tests/forms/test_forms.py::TestProjectForms::test_valid_data`).
- E2E/JS: From testproj/, `npx playwright test` (baseURL http://192.168.5.64:8000 – runserver on that IP first; reuseExistingServer; single: `npx playwright test navbar_harry_test.js --project=chromium`; reports in playwright-report/).
- Browser Integration: Uses Selenium in tests/integration/ (e.g., test_agreement_workflow.py).
- Post-model changes: Run `python scripts/auto_fix_modelstring_refs.py` to fix choice/help_text string refs.
- Data import: `cd testproj && python manage.py import_master_data` (loads from FNHHRICDMasterData.xlsx).

## Code Style Guidelines (Non-Obvious)
- Models: Override clean() for strict validations (dates/ finances/choices); save() auto-calcs stage dates (relativedelta) + populates officers from council defaults.
- Naming: Domain-split models (ricd/models/project.py for core); custom choices (STATE_CHOICES with "prospective"/"varied"); snake_case fields with validators (MinValueValidator(Decimal('0.01'))).
- Imports: Standard Django + dateutil.relativedelta; group by django.contrib, django.core, etc.
- Error Handling: Raise ValidationError in clean() for sequences (stage1 < stage2); use properties for computed (is_late, total_funding from addresses.all()).
- Patterns: Custom Manager.for_user() filters by groups ('RICD Staff')/council; services/ricd/services/ for business logic (project.py/reporting.py); FieldVisibilitySetting for per-council hiding (use get_field_visibility_settings util).
- Conventions: No linters – manual PEP8; views in portal/views.py use class-based with custom mixins; forms split core/reporting.py with modelform validators.