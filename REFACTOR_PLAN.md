# Phase 1A: Layer Refactor Plan

## Overview
Consolidate 22 Django apps into 3 layers: **core**, **api**, **ui**

## Current Structure (22 apps)
- **Domain Models**: councils, programs, projects, land_infra, funding, payments, variations, stages, reports, core, core_financial, addresses, contractors
- **Infrastructure**: accounts, contracts, documents, defects, works
- **UI/Views**: dashboard, maintenance, planning
- **API**: api (newly created with DRF)

## Target Structure

```
src/
├── ricdapp/
│   ├── __init__.py
│   ├── settings.py  (update INSTALLED_APPS → 3 apps)
│   ├── urls.py      (update routing)
│   └── asgi.py
├── apps/
│   ├── core/                  (models + business logic)
│   │   ├── models/            (consolidated from 13+ apps)
│   │   │   ├── __init__.py
│   │   │   ├── council.py
│   │   │   ├── program.py
│   │   │   ├── project.py
│   │   │   ├── funding.py
│   │   │   ├── payment.py
│   │   │   ├── variation.py
│   │   │   └── ...
│   │   ├── business_rules.py
│   │   ├── signals.py
│   │   ├── admin.py           (consolidated registrations)
│   │   ├── urls.py
│   │   ├── views.py           (business logic views)
│   │   └── ...
│   ├── api/                   (REST endpoints)
│   │   ├── serializers/
│   │   ├── views/
│   │   ├── urls.py
│   │   └── ...
│   └── ui/                    (template-based views)
│       ├── views/
│       ├── templates/
│       ├── urls.py
│       └── ...
```

## Phase 1A Execution Steps

### Step 1: Create Directory Structure
- [x] `src/apps/api/` — already created
- [ ] `src/apps/core/models/` — create
- [ ] `src/apps/core/admin.py` — consolidated
- [ ] `src/apps/ui/` — create for template views

### Step 2: Move Model Files
Move from individual apps to `core/models/`:
- councils → core/models/council.py
- programs → core/models/program.py
- projects → core/models/project.py
- funding → core/models/funding.py (PaymentRule, FundingAgreement, etc.)
- payments → core/models/payment.py
- variations → core/models/variation.py
- stages → core/models/stage.py
- reports → core/models/report.py
- land_infra → core/models/land_infra.py
- contractors → core/models/contractor.py
- addresses → core/models/address.py
- accounts → core/models/account.py
- contracts → core/models/contract.py
- core/ → core/models/approval.py, core/models/audit.py
- core_financial/ → core/models/financial.py
- defects → core/models/defect.py
- documents → core/models/document.py
- works → core/models/work.py

### Step 3: Move View Files
Move template-based views to `ui/views/`:
- dashboard/views.py → ui/views/dashboard.py
- maintenance/views.py → ui/views/maintenance.py
- planning/views.py → ui/views/planning.py

Keep API views in `api/views/` (already created).

### Step 4: Update Imports (BULK OPERATION)
Use ask-router to systematically update all imports across the codebase:

**Old patterns:**
```python
from apps.funding.models import PaymentRule
from apps.councils.models import Council
from apps.projects.models import Project
```

**New patterns:**
```python
from apps.core.models import PaymentRule
from apps.core.models import Council
from apps.core.models import Project
```

### Step 5: Update settings.py
Replace INSTALLED_APPS:
```python
# Old: 22+ apps
# New: 3 apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.core',
    'apps.api',
    'apps.ui',
]
```

### Step 6: Update URL Routing
Update `src/ricdapp/urls.py`:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('', include('apps.ui.urls')),
]
```

## Safety Measures
1. Create new structure **without deleting** old apps
2. Use ask-router for bulk import updates (parallelizable)
3. Run `python manage.py check` after each step
4. Run full test suite after import updates
5. Once all tests pass, **delete** old app directories

## Timeline
- Step 1-2: Create directories and move files (~30 min)
- Step 3-4: Import updates via ask-router (~1 hour)
- Step 5-6: Settings/routing updates (~15 min)
- Testing & cleanup (~30 min)

**Total: ~2-3 hours**

## Risk Assessment
- **High risk:** Mass import replacement (mitigated by ask-router parallelization)
- **Medium risk:** Missing imports after move (mitigated by systematic grep + update)
- **Low risk:** Settings updates (straightforward)

## Rollback Plan
Keep old apps intact until all tests pass. If anything breaks:
1. Revert imports to old format
2. Run tests to verify
3. Investigate root cause
4. Re-execute specific steps
