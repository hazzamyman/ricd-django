# Project Debug Rules (Non-Obvious Only)
- Pytest --reuse-db speeds up but risks DB state bleed (e.g., stale council data); use --create-db for isolation if issues.
- Playwright requires Django runserver on 192.168.5.64:8000 (not localhost); trace: 'on-first-retry' – view in playwright-report/index.html.
- Robust tests from ricd/ (not testproj/); fails if robust_system_test.py missing – checks URLs/models silently via Selenium.
- Integration browser tests (tests/integration/) use Selenium (selenium==4.21.0) – headless by default, but set options for visible debugging.
- Management commands (e.g., import_master_data) log to console; watch for xlsx path errors (FNHHRICDMasterData.xlsx in ricd/).
- Duplicated context_portal/ (ricd/ vs testproj/) – use testproj/ for app DB; conport_vector_data/ chroma.sqlite3 for semantic search debugging.
- Post-migration: Run auto_fix_modelstring_refs.py or NameError in views (string refs break choices).