# Fix Report: Admin Inline Model String Issue

## Root Cause
The Django admin check was failing with `AttributeError: 'str' object has no attribute '_meta'` during inline model validation. This occurred because the `Address` model in `ricd/models/work.py` had a `ForeignKey` to `'project.Project'` (string reference), and during Django's admin inline checks, the string model reference was not properly resolved to the actual model class, causing the check to attempt to access `_meta` on a string.

## Files Changed
- `ricd/testproj/ricd/models/work.py`: Added import for `Project` and changed `project = models.ForeignKey('project.Project', ...)` to `project = models.ForeignKey(Project, ...)`.

## Why This Fix
Using direct model class references instead of string references ensures that the model relationships are resolved immediately when the module is loaded, preventing issues during Django's validation checks. For same-app models, this is safer and avoids potential resolution failures.

## Commands Run
- Reproduced the original error with `manage.py check --traceback`.
- Searched for Inline classes and inlines usage.
- Ran static detector script to find string model assignments in Inline classes (none found).
- Inspected admin registry to confirm inlines are loaded as class objects.
- After fix, re-ran `manage.py check` - admin checks now pass, though other unrelated form validation errors remain.

## Tests Run
- Django check command: Admin inline checks now pass.
- Test suite: Fails due to unrelated form field issues in portal/forms/users.py (not related to admin inlines).

## Suggested Next Steps
- Fix the OfficerAssignmentForm in portal/forms/users.py to use correct fields for User model.
- Consider using string model references for cross-app relations to avoid circular imports, but for same-app, direct imports are fine.
- Add CI checks to run `python manage.py check` and `python manage.py test` on PRs.
- Review model FK definitions to ensure consistent use of direct classes vs strings.