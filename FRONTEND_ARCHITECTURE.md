# Django Frontend Architecture Plan
Goal: Complete the 6 missing UI pages to connect frontend to backend

## Page Routing Map

| Page | URL | View Function | Models | Status |
|------|-----|---|---|---|
| Dashboard | /dashboard/ | dashboard_view | Project, FundingSchedule, Payment | Works |
| Projects | /projects/ | projects_list_view | Project | NEW |
| Variations | /variations/ | variations_list_view | Variation | NEW |
| Reports | /reports/ | reports_dashboard_view | Report | NEW |
| Planning | /planning/ | planning_list_view | StrategicPlan | BROKEN |
| Land & Infra | /land/land-projects/ | land_projects_list_view | LandProject | NEW |
| Documents | /documents/ | documents_list_view | ProjectDocument | NEW |
| Cashflow | /cashflow/ | cashflow_view | FundingSchedule, Payment | Template error |
| Aggregate | /aggregate/ | aggregate_outputs_view | Project, Work | Works |

## Implementation Plan (Estimated 4-6 hours total)

### Phase 1: Fix Existing Issues (30 min)

1. Fix cashflow template error
   - File: src/apps/ui/views/dashboard_views.py
   - Add drawdown_percent calculation to by_program items
   - Estimate: 15 min

2. Fix planning view import
   - File: src/apps/ui/views/planning_views.py
   - Change: Import StrategicPlan from apps.core.models (not .models)
   - Estimate: 5 min

3. Uncomment planning URL route
   - File: src/apps/ui/urls.py
   - Estimate: 2 min

### Phase 2: Create 6 Missing List Pages (3-4 hours)

Each page needs:
- View function in src/apps/ui/views/[name]_views.py
- URL route in src/apps/ui/urls.py
- Template in src/apps/ui/templates/[name]/list.html
- Filter/search functionality
- Action links (view, edit, delete)

Pages to create:
1. Projects List (/projects/) - 40 min
2. Variations List (/variations/) - 40 min
3. Reports Dashboard (/reports/) - 45 min
4. Planning List (/planning/) - 35 min (fix existing)
5. Land & Infrastructure (/land/land-projects/) - 40 min
6. Documents Repository (/documents/) - 40 min

### Phase 3: Update Navigation (20 min)

1. Update base.html navbar
   - Replace hardcoded URLs with {% url %} tags
   - Example: /projects/ becomes {% url 'ui:projects_list' %}
   - Estimate: 10 min

2. Register all routes in ui/urls.py
   - Add all 6 new URL patterns
   - Estimate: 5 min

### Phase 4: Testing & Verification (1 hour)

1. Test all 6 pages load (no 404s or template errors)
2. Test filtering/search on each page
3. Test detail/edit/delete actions
4. Verify API integration via browser network tab

## Files to Create

New Python view files:
- src/apps/ui/views/projects_views.py
- src/apps/ui/views/variations_views.py
- src/apps/ui/views/reports_views.py
- src/apps/ui/views/land_infra_views.py
- src/apps/ui/views/documents_views.py

New HTML templates:
- src/apps/ui/templates/projects/list.html
- src/apps/ui/templates/variations/list.html
- src/apps/ui/templates/reports/dashboard.html
- src/apps/ui/templates/planning/list.html
- src/apps/ui/templates/land_infra/list.html
- src/apps/ui/templates/documents/list.html

Files to modify:
- src/apps/ui/views/planning_views.py (fix imports)
- src/apps/ui/urls.py (add routes)
- src/templates/base.html (update navbar links)

## Dependencies Check

Verify these models exist:
- apps.core.models.Project (YES)
- apps.core.models.Variation (YES)
- apps.core.models.LandProject (YES)
- apps.core.models.ProjectDocument (YES)
- apps.core.models.Report (CHECK)
- apps.core.models.StrategicPlan (CHECK)

## Success Criteria

- All 6 pages load without 404 or template errors
- All navbar links work (using {% url %} tags)
- Data displays correctly
- Filters/search functional
- Edit/delete actions work

