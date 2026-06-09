"""Send time-based notification emails — run DAILY.

Schedule one run per day:
  * Linux/cron:        0 7 * * *  cd <repo>/src && python manage.py send_due_notifications
  * Windows Task Scheduler: daily action running
      <path>\\.venv\\Scripts\\python.exe manage.py send_due_notifications  (Start in: <repo>\\src)

Each reminder is idempotent (a per-object dedupe key), so running daily will not
re-send. Use --dry-run to preview without recording/sending.
"""
import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send due time-based notifications (overdue trackers/quarterly, stage target/sunset). Run daily."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="List what would be sent without recording or sending.")

    def handle(self, *args, **options):
        from apps.core.models import MonthlyTracker, QuarterlyReport, Project
        from apps.core.services import notifications as N

        dry = options['dry_run']
        today = datetime.date.today()
        sent = 0

        def fire(event, *, council, project, ctx, key):
            nonlocal sent
            if dry:
                self.stdout.write(f"  would send {event} → {key}")
                sent += 1
                return
            if N.send_event_email(event, council=council, project=project, context=ctx, dedupe_key=key):
                sent += 1

        # 1) Overdue Monthly Trackers (council-level)
        for mt in MonthlyTracker.objects.select_related('council'):
            if mt.is_overdue:
                ctx = {'council': mt.council.name, 'period': f"{mt.year}-{mt.month:02d}",
                       'due_date': mt.due_date.strftime('%d %b %Y'), 'date': N._today()}
                fire('MONTHLY_TRACKER_OVERDUE', council=mt.council, project=None, ctx=ctx,
                     key=f"MONTHLY_TRACKER_OVERDUE:{mt.pk}")

        # 2) Overdue Quarterly Reports (council-level)
        for qr in QuarterlyReport.objects.select_related('council'):
            if qr.is_overdue:
                ctx = {'council': qr.council.name, 'period': str(qr),
                       'due_date': qr.due_date.strftime('%d %b %Y'), 'date': N._today()}
                fire('QUARTERLY_REPORT_OVERDUE', council=qr.council, project=None, ctx=ctx,
                     key=f"QUARTERLY_REPORT_OVERDUE:{qr.pk}")

        # 3) Stage target / sunset approaching (per project) at 30 days and 1 day out.
        #    Uses <= window so a missed daily run still triggers; dedupe fires once.
        stage_fields = [
            ('STAGE_TARGET_DUE', 'Stage 1', 'stage1_target_date'),
            ('STAGE_TARGET_DUE', 'Stage 2', 'stage2_target_date'),
            ('STAGE_SUNSET_DUE', 'Stage 1', 'stage1_sunset_date'),
            ('STAGE_SUNSET_DUE', 'Stage 2', 'stage2_sunset_date'),
        ]
        projects = (Project.objects.filter(is_archived=False)
                    .exclude(state=Project.State.COMPLETED).select_related('council'))
        for proj in projects:
            base_ctx = N.project_context(proj)
            for event, stage_label, field in stage_fields:
                due = getattr(proj, field, None)
                if not due:
                    continue
                delta = (due - today).days
                for window in (30, 1):
                    if 0 <= delta <= window:
                        ctx = dict(base_ctx)
                        ctx['stage'] = stage_label
                        ctx['due_date'] = due.strftime('%d %b %Y')
                        ctx['days'] = f"{window} day" + ("" if window == 1 else "s")
                        fire(event, council=proj.council, project=proj, ctx=ctx,
                             key=f"{event}:{proj.pk}:{field}:{window}")

        self.stdout.write(self.style.SUCCESS(
            f"{'[dry-run] ' if dry else ''}{sent} due notification(s) "
            f"{'to send' if dry else 'sent/logged'}."))
