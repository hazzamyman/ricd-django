# RICD — Remote Indigenous Capital Delivery

Capital expenditure project management system for Queensland Government capital
works in remote Indigenous communities: projects, financial approvals (BFA),
funding agreements & schedules, payments, cashflow forecasting, reporting, and
audit logging.

**Stack:** Django 5 + DRF · SQLite (dev) / PostgreSQL (production)

## Run locally

```bash
pip install -r requirements.txt
cd src
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/dashboard/.

Tests: `python -m pytest` from the repo root (see
[README_ROBUST_TESTING.md](README_ROBUST_TESTING.md)).

## Going into production — fill out `.env`

All deployment configuration lives in one file: **`.env`** at the repo root
(git-ignored; if it doesn't exist, copy [`.env.example`](.env.example) — every
field has help text).

1. Edit `.env`:
   - `DJANGO_DEBUG=False`
   - `DJANGO_SECRET_KEY=` a generated key — the file shows the one-line command
     to generate one. The app refuses to start in production without it.
   - `DJANGO_ALLOWED_HOSTS=` your production domain(s)/server IP
   - `DB_ENGINE=postgresql` plus `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` /
     `DB_PASSWORD` for your PostgreSQL server
2. Initialise the production database:
   `cd src && python manage.py migrate && python manage.py createsuperuser`
3. Configure email **in the app** (not in `.env`): log in as a Manager →
   **Maintenance → Email Settings** — SMTP host/port/TLS/credentials, send
   mode, and the master notifications on/off switch.
4. Restart the server. Real OS environment variables, if set, override `.env`.

## Documentation

- [docs/RICD_domain_model.md](docs/RICD_domain_model.md) — authoritative domain
  model, business rules, and end-to-end process flow
- [docs/gap_analysis.md](docs/gap_analysis.md) — spec-vs-implementation status
- [docs/FNC_BACKLOG.md](docs/FNC_BACKLOG.md) — enhancement backlog
- [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) — UI structure
