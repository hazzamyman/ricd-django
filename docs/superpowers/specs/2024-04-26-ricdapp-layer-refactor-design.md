# RICDapp Layer Refactor – Design Specification

**Date:** 2024-04-26

## 1. Goal Overview
- Reduce the number of Django apps from ~25 to 3 to simplify navigation and improve maintainability.
- Improve startup and test performance by cutting the `INSTALLED_APPS` list.
- Establish a clear separation of concerns: core data/utility layer, API/business‑logic layer, UI/template layer.

## 2. Target Layout
```
src/
└─ ricdapp/
   ├─ core/      # Shared models, utilities, auth, admin registrations
   │   ├─ __init__.py
   │   ├─ apps.py                # CoreConfig
   │   ├─ models/                # All data models (councils, programs, projects, …)
   │   │   ├─ __init__.py
   │   │   ├─ councils.py
   │   │   ├─ programs.py
   │   │   ├─ projects.py
   │   │   ├─ land_infra.py
   │   │   └─ …
   │   ├─ utils/                 # Shared utilities, permissions, mixins
   │   └─ admin.py                # Admin registrations
   │
   ├─ api/                           # API / business‑logic endpoints
   │   ├─ __init__.py
   │   ├─ apps.py                # ApiConfig
   │   ├─ views/                 # CBVs / viewsets returning JSON
   │   │   ├─ __init__.py
   │   │   ├─ projects.py
   │   │   ├─ land_infra.py
   │   │   ├─ funding.py
   │   │   └─ …
   │   ├─ serializers/           # Placeholder for future DRF serializers
   │   └─ urls.py                # API namespace (e.g., /api/…)
   │
   └─ ui/                            # Template‑based UI
       ├─ __init__.py
       ├─ apps.py                # UiConfig
       ├─ views/                 # TemplateRendering CBVs
       │   ├─ __init__.py
       │   ├─ dashboard.py
       │   ├─ reports.py
       │   └─ maintenance.py
       ├─ templatetags/          # Custom template tags (project_extras, reports_extras)
       ├─ static/                # CSS/JS/images
       └─ templates/             # HTML templates mirroring original structure
```

## 3. Mapping of Existing Apps → New Layers
| Existing app | New layer | Reason |
|--------------|-----------|--------|
| `accounts`, `councils`, `programs`, `addresses`, `documents` | **core** | Pure data models and auth utilities.
| `projects`, `land_infra`, `works`, `defects`, `funding`, `payments`, `contracts`, `variations`, `stages`, `planning`, `contractors` | **api** | Business‑logic heavy views that return JSON / perform state changes.
| `dashboard`, `reports`, `maintenance` (and any other template‑rendering apps) | **ui** | Views that render HTML templates and static assets.

## 4. Implementation Steps (single commit)
1. Create `src/ricdapp/` with sub‑packages `core`, `api`, `ui` and corresponding `apps.py` files.
2. Move all model files into `core/models/`. Add `Meta: app_label = '<original_app_name>'` if we want to keep migration table names unchanged, or set a unified label (`core`).
3. Move API‑style view files (those that return JSON or perform redirects without templates) into `api/views/`.
4. Move template‑based view files into `ui/views/` and copy the original template directories under `ui/templates/`.
5. Consolidate admin registrations into `core/admin.py` and update imports.
6. Update `src/ricdapp/urls.py` to include three namespaces:
   ```python
   urlpatterns = [
       path('', include('ricdapp.ui.urls')),
       path('api/', include('ricdapp.api.urls')),
   ]
   ```
7. Adjust `settings.py`:
   - `INSTALLED_APPS = ['ricdapp.core', 'ricdapp.api', 'ricdapp.ui', ...]`
   - Update `TEMPLATES['DIRS']` to point at `BASE_DIR / 'src' / 'ricdapp' / 'ui' / 'templates'`.
8. Update all import statements throughout the codebase to use the new package paths (e.g., `from ricdapp.core.models.councils import Council`).
9. Run `python manage.py makemigrations --empty ricdapp.core` if we need to create a migration that sets the new `app_label` for each model (optional; can keep original labels to avoid data migration).
10. Run the full test suite (`pytest`). All tests should pass after the import path updates.
11. Commit the changes as a single atomic commit with a clear message.

## 5. Performance Impact
- **Startup:** Django loads only three app configs instead of ~25, reducing import overhead.
- **Migrations:** Fewer apps to scan, so `manage.py migrate` runs faster.
- **Test discovery:** `pytest` collects far fewer top‑level directories, speeding up CI.

## 6. Testing & Verification
1. Execute `pytest` – expect 0 failures.
2. Start the dev server (`python manage.py runserver`) and verify a handful of UI pages (dashboard, reports) load correctly.
3. Hit a few API endpoints (e.g., `/api/projects/`) to confirm JSON responses.
4. Run `python manage.py check` to ensure no missing migrations or config errors.

## 7. Future Extensibility
- Adding a full‑blown REST API (DRF) will live in `api/`.
- A future Council portal can be added as a new sub‑package under `ui/` or as a separate Django app that imports from `core` and `api`.
- New reusable utilities should be placed in `core/utils/`.

---

**Next steps:**
- Write this spec file to the repository.
- Perform a quick self‑review (remove placeholders, verify consistency).
- Ask the user to review the spec before moving to the implementation plan.
