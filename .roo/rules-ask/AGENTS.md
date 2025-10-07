# Project Documentation Rules (Non-Obvious Only)
- Architecture: Dual apps (portal/ for views/forms/templates, ricd/ for models/services/management); portal/ handles UI, ricd/ core logic.
- Field visibility counterintuitive: Council users see subset via FieldVisibilitySetting (per-council) + ProjectFieldVisibilityOverride (per-project); use is_field_visible(field_name, council, user, project) util.
- Report configs per-project (ProjectReportConfiguration): Links groups (monthly_tracker_groups, stage1_step_groups) – not global; empty configs raise ValidationError.
- Custom managers filter queries (Project.objects.for_user(user) – RICD Staff sees all, others council-only).
- Data flow: Funding via multiple FKs (FundingSchedule/ForwardRemoteProgramFundingAgreement); variations in separate Variation model (agreement_id links).
- Hidden coupling: Officers auto-populate in Project.save() from council defaults; progress_percentage manual but validated 0-100.
- Docs in CHANGELOG/tests-and-analytics.md (testing notes); diagnostics/ for test outputs (e.g., manage_check_after_fix.txt).