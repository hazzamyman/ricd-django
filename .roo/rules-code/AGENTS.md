# Project Coding Rules (Non-Obvious Only)
- Models require clean() overrides for domain validations (e.g., stage dates: stage1_target < stage2_target using relativedelta; positive Decimals with MinValueValidator(0.01)).
- Use custom ProjectManager.for_user() for queries (filters by 'RICD Staff'/'RICD Manager' groups or user.council – avoids raw filter(council=...)).
- Implement properties for computed fields (e.g., total_funding = sum(address.budget for address in self.addresses.all()); is_late based on state/stage1_target).
- After model choice changes, run scripts/auto_fix_modelstring_refs.py to update string refs in validators/help_text (prevents migration errors).
- Business logic in ricd/services/ (project.py for date calcs, reporting.py for reports) – not in views/forms (keeps thin).
- Imports: django.db.models first, then contrib/core/utils; use Decimal('0.01') for financials, timezone.now().date() for validations.
- Naming: STATE_CHOICES with project states ("prospective", "varied"); fields like sap_project indexed in Meta for perf.