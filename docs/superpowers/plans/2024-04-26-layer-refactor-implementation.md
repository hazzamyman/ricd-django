# RICDapp Layer Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the existing ~25 Django apps into three logical layers (`core`, `api`, `ui`) while preserving all functionality and passing the test suite.

**Architecture:** All data models and shared utilities relocate to `ricdapp/core`; API‑style viewsets move to `ricdapp/api`; template‑rendering views, static assets, and templates move to `ricdapp/ui`. URL routing is adjusted to include three namespaces.

**Tech Stack:** Python 3.13, Django 5.x, PostgreSQL, pytest, ruff.

---

### Task 1: Create new package structure

**Files:**
- Create: `src/ricdapp/__init__.py`
- Create: `src/ricdapp/core/__init__.py`
- Create: `src/ricdapp/core/apps.py`
- Create: `src/ricdapp/api/__init__.py`
- Create: `src/ricdapp/api/apps.py`
- Create: `src/ricdapp/ui/__init__.py`
- Create: `src/ricdapp/ui/apps.py`
- Create: `src/ricdapp/core/models/__init__.py`
- Create: `src/ricdapp/api/views/__init__.py`
- Create: `src/ricdapp/ui/views/__init__.py`
- Create: `src/ricdapp/ui/templates/__init__.py`
- Create: `src/ricdapp/ui/static/__init__.py`
- Create: `src/ricdapp/urls.py`
- Create: `src/ricdapp/wsgi.py` (copy from existing `src/ricdapp/wsgi.py`)

- [ ] **Step 1: Add package init files**
```bash
touch src/ricdapp/__init__.py src/ricdapp/core/__init__.py src/ricdapp/api/__init__.py src/ricdapp/ui/__init__.py
```
- [ ] **Step 2: Add apps.py files**
```python
# src/ricdapp/core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ricdapp.core'
```
```python
# src/ricdapp/api/apps.py
from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ricdapp.api'
```
```python
# src/ricdapp/ui/apps.py
from django.apps import AppConfig

class UiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ricdapp.ui'
```
- [ ] **Step 3: Add empty __init__ for sub‑packages** (no code needed).
- [ ] **Step 4: Copy existing wsgi file**
```bash
cp src/ricdapp/wsgi.py src/ricdapp/wsgi.py
```
- [ ] **Step 5: Create top‑level urls.py**
```python
# src/ricdapp/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ricdapp.ui.urls')),            # UI routes (templates)
    path('api/', include('ricdapp.api.urls')),        # API routes
]
```
- [ ] **Step 6: Commit package skeleton**
```bash
git add src/ricdapp
git commit -m "chore: create ricdapp core/api/ui package skeleton"
```

### Task 2: Move all model files to `core/models`

**Files:**
- Modify: each existing model file path, e.g., `src/apps/councils/models.py` → `src/ricdapp/core/models/councils.py`
- Update imports throughout the repo to point to `ricdapp.core.models.<module>`.
- Ensure each model class includes `class Meta: app_label = 'core'` (optional if we keep original app labels; we will keep original labels to avoid DB table renames).

- [ ] **Step 1: Create target directory**
```bash
mkdir -p src/ricdapp/core/models
```
- [ ] **Step 2: Move files** (example for a few; repeat for all model files listed in the grep results):
```bash
mv src/apps/councils/models.py src/ricdapp/core/models/councils.py
mv src/apps/programs/models.py src/ricdapp/core/models/programs.py
mv src/apps/projects/models.py src/ricdapp/core/models/projects.py
mv src/apps/land_infra/models.py src/ricdapp/core/models/land_infra.py
# ... repeat for all other model modules ...
```
- [ ] **Step 3: Add `__init__.py` imports**
```python
# src/ricdapp/core/models/__init__.py
from .councils import *
from .programs import *
from .projects import *
from .land_infra import *
# ... import the rest of the model modules ...
```
- [ ] **Step 4: Update intra‑app imports** (e.g., other apps referencing `src/apps/councils/models.py`). Replace with:
```python
from ricdapp.core.models.councils import Council
```
- [ ] **Step 5: Run a quick import sanity check**
```bash
python - <<'PY'
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricdapp.settings')
django.setup()
print('Models imported successfully')
PY
```
- [ ] **Step 6: Commit model migration**
```bash
git add src/ricdapp/core/models
git commit -m "refactor: relocate all models to ricdapp.core.models"
```

### Task 3: Move API‑style views to `api/views`

**Files:**
- Move every view that returns JSON or redirects without rendering a template (e.g., `src/apps/projects/views.py`, `src/apps/funding/views.py`, `src/apps/payments/views.py`, etc.) to `src/ricdapp/api/views/` preserving file names.
- Adjust import paths for models and utils to the new core location.
- Create `src/ricdapp/api/urls.py` that aggregates the previous per‑app URL patterns.

- [ ] **Step 1: Create views directory**
```bash
mkdir -p src/ricdapp/api/views
```
- [ ] **Step 2: Move files** (example for a few):
```bash
mv src/apps/projects/views.py src/ricdapp/api/views/projects.py
mv src/apps/funding/views.py src/ricdapp/api/views/funding.py
mv src/apps/payments/views.py src/ricdapp/api/views/payments.py
# ... repeat for all API‑style view modules ...
```
- [ ] **Step 3: Update imports inside each moved view** to use `ricdapp.core.models.<module>` and any utilities now under `ricdapp.core.utils`.
- [ ] **Step 4: Create `src/ricdapp/api/urls.py`** that includes the former app URL configs:
```python
# src/ricdapp/api/urls.py
from django.urls import path, include

urlpatterns = [
    path('projects/', include('ricdapp.api.views.projects')),  # projects API
    path('funding/', include('ricdapp.api.views.funding')),
    path('payments/', include('ricdapp.api.views.payments')),
    # ... add includes for every moved view module ...
]
```
- [ ] **Step 5: Remove old per‑app urls.py files** (or keep them if they are imported elsewhere; we will delete them after confirming no references).
- [ ] **Step 6: Commit API view migration**
```bash
git add src/ricdapp/api/views src/ricdapp/api/urls.py
git commit -m "refactor: relocate API views to ricdapp.api"
```

### Task 4: Move template‑based views, templates, and static assets to `ui`

**Files:**
- Move view files that render templates (e.g., `src/apps/dashboard/views.py`, `src/apps/reports/views.py`, `src/apps/maintenance/views.py`, etc.) to `src/ricdapp/ui/views/`.
- Move all HTML templates under `src/apps/*/templates/` into `src/ricdapp/ui/templates/` preserving sub‑folder hierarchy.
- Move static files (CSS/JS under each app) into `src/ricdapp/ui/static/` preserving relative paths.
- Adjust imports for forms, models, and utils.
- Create `src/ricdapp/ui/urls.py` that aggregates the former UI routes.

- [ ] **Step 1: Create ui directories**
```bash
mkdir -p src/ricdapp/ui/views src/ricdapp/ui/templates src/ricdapp/ui/static
```
- [ ] **Step 2: Move UI view files** (example):
```bash
mv src/apps/dashboard/views.py src/ricdapp/ui/views/dashboard.py
mv src/apps/reports/views.py src/ricdapp/ui/views/reports.py
mv src/apps/maintenance/views.py src/ricdapp/ui/views/maintenance.py
# ... repeat for all template‑based view modules ...
```
- [ ] **Step 3: Relocate templates**
```bash
# Assuming each app has a templates/<app_name>/ folder
mv src/apps/dashboard/templates/* src/ricdapp/ui/templates/dashboard/
mv src/apps/reports/templates/* src/ricdapp/ui/templates/reports/
# ... repeat for each app ...
```
- [ ] **Step 4: Relocate static assets**
```bash
mv src/apps/dashboard/static/* src/ricdapp/ui/static/dashboard/
mv src/apps/reports/static/* src/ricdapp/ui/static/reports/
# ... repeat ...
```
- [ ] **Step 5: Update UI view imports** (e.g., `from ricdapp.core.models import Project`).
- [ ] **Step 6: Create `src/ricdapp/ui/urls.py`** that mirrors previous UI routing:
```python
# src/ricdapp/ui/urls.py
from django.urls import path, include

urlpatterns = [
    path('', include('ricdapp.ui.views.dashboard')),
    path('reports/', include('ricdapp.ui.views.reports')),
    path('maintenance/', include('ricdapp.ui.views.maintenance')),
    # ... add remaining UI view includes ...
]
```
- [ ] **Step 7: Remove old UI app directories** after confirming no stray imports.
- [ ] **Step 8: Commit UI migration**
```bash
git add src/ricdapp/ui
git commit -m "refactor: relocate UI views, templates, static assets to ricdapp.ui"
```

### Task 5: Update project settings

**Files:**
- Modify: `src/ricdapp/settings.py`
- Adjust `INSTALLED_APPS`, `TEMPLATES['DIRS']`, and any app‑specific config that referenced old app names.

- [ ] **Step 1: Open settings file**
- [ ] **Step 2: Replace INSTALLED_APPS**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ricdapp.core',
    'ricdapp.api',
    'ricdapp.ui',
]
```
- [ ] **Step 3: Update TEMPLATES DIRS**
```python
TEMPLATES[0]['DIRS'] = [BASE_DIR / 'src' / 'ricdapp' / 'ui' / 'templates']
```
- [ ] **Step 4: Remove any references to old app labels** (e.g., `LOGIN_REDIRECT_URL = '/dashboard/'` stays unchanged).
- [ ] **Step 5: Run `python manage.py check`** to ensure settings are valid.
- [ ] **Step 6: Commit settings update**
```bash
git add src/ricdapp/settings.py
git commit -m "chore: update INSTALLED_APPS and template dirs for new package layout"
```

### Task 6: Update URL imports throughout the codebase

**Files:**
- Any `include('src.apps.xxx.urls')` statements in remaining files must point to the new locations (`ricdapp.api.urls` or `ricdapp.ui.urls`).

- [ ] **Step 1: Grep for old include patterns**
```bash
grep -R "include('src.apps" -n src/ricdapp || true
```
- [ ] **Step 2: Replace each occurrence** with the appropriate new path.
- [ ] **Step 3: Run `pytest` to ensure no import errors.
- [ ] **Step 4: Commit URL updates**
```bash
git add src/ricdapp
git commit -m "refactor: update include statements to new ricdapp api/ui urls"
```

### Task 7: Adjust test imports

**Files:**
- All test files under `tests/` that import models or views must be updated to the new package paths.

- [ ] **Step 1: Grep for old import paths**
```bash
grep -R "src.apps" -n tests || true
```
- [ ] **Step 2: Replace with `ricdapp.core.models` or `ricdapp.api.views` / `ricdapp.ui.views` as appropriate.
- [ ] **Step 3: Run the full test suite**
```bash
pytest -q
```
- [ ] **Step 4: If failures appear, fix the import paths or adjust any referenced constants.
- [ ] **Step 5: Commit test updates**
```bash
git add tests
git commit -m "test: update imports to match new ricdapp package layout"
```

### Task 8: Verify migrations & database integrity

**Files:** (no new files, just commands)

- [ ] **Step 1: Run makemigrations (should be a no‑op because we kept original app labels)**
```bash
python manage.py makemigrations --check
```
- [ ] **Step 2: Run migrate**
```bash
python manage.py migrate
```
- [ ] **Step 3: Run a quick sanity check – create a superuser and launch the dev server**
```bash
python manage.py createsuperuser --noinput --username admin --email admin@example.com
python manage.py runserver
```
- [ ] **Step 4: Visit a few UI pages and API endpoints in the browser to confirm they work.
- [ ] **Step 5: Commit any final adjustments**
```bash
git commit -am "chore: final verification after layer refactor"
```

### Task 9: Clean up obsolete files & directories

**Files:**
- Remove now‑empty original app directories under `src/apps/`.
- Remove any leftover empty `migrations/` folders that are no longer referenced.

- [ ] **Step 1: Delete empty app folders**
```bash
rm -rf src/apps/*   # after confirming each folder is empty
```
- [ ] **Step 2: Remove empty `migrations` sub‑folders**
```bash
find src/ -type d -name "migrations" -empty -delete
```
- [ ] **Step 3: Run `git status` to ensure no stray files remain.
- [ ] **Step 4: Final commit**
```bash
git add -u
git commit -m "chore: clean up obsolete app directories after layer refactor"
```

---

## Self‑Review Checklist
- [ ] Every requirement from the design spec is mapped to a task.
- [ ] No placeholders (`TBD`, `TODO`) remain.
- [ ] All code snippets contain real, executable code.
- [ ] File paths are absolute relative to the repo root.
- [ ] Commands include expected outcomes where appropriate.
- [ ] The plan follows DRY, YAGNI, and TDD principles.

---

**Plan saved to** `docs/superpowers/plans/2024-04-26-layer-refactor-implementation.md`.

**Execution options:**
1. **Sub‑agent‑driven (recommended)** – I will dispatch a fresh sub‑agent for each task, allowing review between tasks.
2. **Inline execution** – I will run the steps in this session sequentially.

Which approach would you like to use?