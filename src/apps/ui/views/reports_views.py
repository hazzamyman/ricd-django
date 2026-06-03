import csv
import datetime
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from apps.core.models import StageReport, QuarterlyReport, Project, Council, Payment


@login_required
def reports_dashboard_view(request):
    """Reports dashboard showing stage and quarterly reports"""
    # Get filter parameters
    project_id = request.GET.get('project', '')
    status_filter = request.GET.get('status', '')
    
    # Build querysets — QuarterlyReport is per-council now
    stage_reports = StageReport.objects.select_related('project')
    quarterly_reports = QuarterlyReport.objects.select_related('council')

    if project_id:
        stage_reports = stage_reports.filter(project_id=project_id)
        # QR no longer has a project FK; filter by the project's council
        try:
            council_id_for_project = Project.objects.filter(pk=project_id).values_list('council_id', flat=True).first()
            if council_id_for_project:
                quarterly_reports = quarterly_reports.filter(council_id=council_id_for_project)
            else:
                quarterly_reports = quarterly_reports.none()
        except Exception:
            quarterly_reports = quarterly_reports.none()
    if status_filter:
        stage_reports = stage_reports.filter(status=status_filter)
        quarterly_reports = quarterly_reports.filter(status=status_filter)
    
    # Get filter options
    projects = Project.objects.all()
    
    context = {
        'stage_reports': stage_reports,
        'quarterly_reports': quarterly_reports,
        'projects': projects,
        'selected_project': project_id,
        'selected_status': status_filter,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def monthly_report_council_select(request):
    """Show list of councils — click one to open its monthly progress report."""
    councils = Council.objects.order_by('name')
    return render(request, 'reports/monthly_select.html', {'councils': councils})


@login_required
def monthly_report_view(request, council_pk):
    """
    Per-council cumulative monthly progress report.
    Shows all in-flight projects (at least one RELEASED payment, not COMPLETED).
    Each project lists its work items with formatted address labels.
    """
    council = get_object_or_404(Council, pk=council_pk)

    # Projects for this council that have at least one RELEASED payment and are not COMPLETED
    released_project_ids = (
        Payment.objects
        .filter(status=Payment.Status.RELEASED, funding_schedule__project__council=council)
        .values_list('funding_schedule__project_id', flat=True)
        .distinct()
    )
    projects = (
        Project.objects
        .filter(pk__in=released_project_ids)
        .exclude(state=Project.State.COMPLETED)
        .prefetch_related(
            'works__address__suburb',
            'works__work_type',
        )
        .select_related('program')
        .order_by('name')
    )

    # Pre-build display rows per project
    report_rows = []
    for project in projects:
        works = []
        for work in project.works.all():
            addr = work.address
            if addr:
                lot_plan = f"Lot {addr.lot} {addr.plan}" if addr.lot and addr.plan else (addr.lot or addr.plan or '')
                lot_plan_str = f" ({lot_plan})" if lot_plan else ''
                br_str = f"{work.bedrooms}B " if work.bedrooms else ''
                short_code = (work.work_type.short_code if work.work_type and work.work_type.short_code
                              else (work.work_type.name[:4] if work.work_type else ''))
                label = f"{addr.street}{lot_plan_str} ({br_str}{short_code})"
            else:
                label = str(work)
            works.append({'label': label, 'work': work})
        report_rows.append({'project': project, 'works': works})

    return render(request, 'reports/monthly_report.html', {
        'council': council,
        'report_rows': report_rows,
    })


# ────────────────────────────────────────────────────────────────────
# End-of-Month Reconciliation (per-program payment allocations)
# ────────────────────────────────────────────────────────────────────

def _eom_resolve_month(request):
    """Return (year, month, label) for the requested ?month=YYYY-MM or current month."""
    raw = (request.GET.get('month') or '').strip()
    today = datetime.date.today()
    if raw:
        try:
            y, m = raw.split('-')
            year, month = int(y), int(m)
            datetime.date(year, month, 1)  # validate
        except (ValueError, TypeError):
            year, month = today.year, today.month
    else:
        year, month = today.year, today.month
    label = datetime.date(year, month, 1).strftime('%B %Y')
    return year, month, label


def _eom_rows_for_month(year, month):
    """Iterate PaymentAllocation rows where parent Payment released that month.

    Yields dicts ready for table/CSV. One row per (payment, program) allocation.
    """
    from apps.core.models import PaymentAllocation
    qs = (
        PaymentAllocation.objects
        .filter(
            payment__release_date__year=year,
            payment__release_date__month=month,
            payment__status='RELEASED',
        )
        .select_related(
            'payment__project__council',
            'payment__project__program',
            'payment__funding_schedule',
            'program',
        )
        .order_by('payment__project__council__name', 'program__name', 'payment__release_date')
    )
    for alloc in qs:
        p = alloc.payment
        prog = alloc.program or p.project.program
        yield {
            'council': p.project.council.name,
            'project': p.project.name,
            'program': prog.name if prog else '',
            'cost_centre': (prog.cost_centre if prog else '') or '',
            'gl_code': (prog.gl_code if prog else '') or '',
            'payment_type': p.get_payment_type_display(),
            'amount': alloc.amount,
            'ratio': alloc.ratio,
            'release_date': p.release_date,
            'sap_ref': p.release_sap_reference or p.sap_payment_reference or '',
            'tax_invoice_ref': p.tax_invoice_reference or '',
            'fs_number': p.funding_schedule.schedule_number if p.funding_schedule_id else '',
            'payment': p,
        }


@login_required
def eom_reconciliation_view(request):
    """End-of-month reconciliation: all released payment allocations for the month,
    grouped by program. Supports ?month=YYYY-MM (defaults to current month)."""
    year, month, label = _eom_resolve_month(request)
    rows = list(_eom_rows_for_month(year, month))

    # Group totals by program
    by_program = {}
    grand_total = Decimal('0')
    for r in rows:
        key = (r['program'], r['cost_centre'], r['gl_code'])
        bucket = by_program.setdefault(key, {
            'program': r['program'],
            'cost_centre': r['cost_centre'],
            'gl_code': r['gl_code'],
            'rows': [],
            'subtotal': Decimal('0'),
        })
        bucket['rows'].append(r)
        bucket['subtotal'] += r['amount']
        grand_total += r['amount']

    # Also a flat by-council summary
    by_council = {}
    for r in rows:
        by_council.setdefault(r['council'], Decimal('0'))
        by_council[r['council']] += r['amount']

    return render(request, 'reports/eom_reconciliation.html', {
        'year': year,
        'month': month,
        'month_label': label,
        'rows': rows,
        'row_count': len(rows),
        'program_groups': sorted(by_program.values(), key=lambda b: b['program']),
        'council_totals': sorted(by_council.items()),
        'grand_total': grand_total,
        'current_month_input': f"{year:04d}-{month:02d}",
    })


@login_required
def eom_reconciliation_export(request):
    """CSV export of the EOM reconciliation for ?month=YYYY-MM."""
    year, month, label = _eom_resolve_month(request)
    rows = list(_eom_rows_for_month(year, month))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="eom_reconciliation_{year:04d}-{month:02d}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'Release Date', 'Council', 'Project', 'FS #', 'Program',
        'Cost Centre', 'GL Code', 'Payment Type',
        'Amount', 'Ratio', 'SAP Reference', 'Tax Invoice Reference',
    ])
    for r in rows:
        writer.writerow([
            r['release_date'].isoformat() if r['release_date'] else '',
            r['council'], r['project'], r['fs_number'],
            r['program'], r['cost_centre'], r['gl_code'],
            r['payment_type'],
            f"{r['amount']:.2f}",
            f"{r['ratio']:.6f}" if r['ratio'] is not None else '',
            r['sap_ref'], r['tax_invoice_ref'],
        ])
    # Grand total footer
    total = sum((r['amount'] for r in rows), Decimal('0'))
    writer.writerow([])
    writer.writerow(['', '', '', '', '', '', '', 'TOTAL', f"{total:.2f}", '', '', ''])
    return response


# ────────────────────────────────────────────────────────────────────
# Construction Creation List (CCL) — works in active funding schedules
# ────────────────────────────────────────────────────────────────────

def _ccl_queryset(request):
    """Return the Work queryset for the CCL, with filters applied.

    Filters (all optional, via GET):
      council    — Council pk
      include_completed — '1' to include COMPLETED works
    Only Works whose project is on an ACTIVE or EXECUTED FundingSchedule
    are returned (i.e., works actually committed for construction).
    """
    from apps.core.models import Work
    qs = (
        Work.objects
        .select_related(
            'project__council', 'project__program', 'project__funding_schedule',
            'work_type', 'address__suburb',
        )
        .filter(
            project__funding_schedule__status__in=['ACTIVE', 'EXECUTED'],
        )
    )
    council_id = (request.GET.get('council') or '').strip()
    if council_id:
        try:
            qs = qs.filter(project__council_id=int(council_id))
        except ValueError:
            pass
    if request.GET.get('include_completed') != '1':
        qs = qs.exclude(status='COMPLETED')
    return qs.order_by(
        'project__council__name', 'project__name', 'address__street', 'work_type__name'
    )


@login_required
def construction_creation_list_view(request):
    """Capital Works construction list — every Work currently in delivery."""
    works = list(_ccl_queryset(request))

    # Group by council for presentation
    by_council = {}
    for w in works:
        key = w.project.council.name
        by_council.setdefault(key, []).append(w)

    total_estimated = sum((w.total_estimated_cost or Decimal('0') for w in works), Decimal('0'))
    selected_council = request.GET.get('council') or ''
    include_completed = request.GET.get('include_completed') == '1'

    return render(request, 'reports/construction_creation_list.html', {
        'works': works,
        'works_count': len(works),
        'by_council': sorted(by_council.items()),
        'total_estimated': total_estimated,
        'councils': Council.objects.order_by('name'),
        'selected_council': selected_council,
        'include_completed': include_completed,
    })


@login_required
def construction_creation_list_export(request):
    """CSV export of the Construction Creation List."""
    works = list(_ccl_queryset(request))

    response = HttpResponse(content_type='text/csv')
    today = datetime.date.today().isoformat()
    response['Content-Disposition'] = (
        f'attachment; filename="construction_creation_list_{today}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'Council', 'Project', 'Program', 'FS #',
        'Address', 'Suburb',
        'Work Type', 'Bedrooms', 'Quantity',
        'Estimated Cost', 'Total Estimated',
        'Status', 'Cashflow Method',
        'Stage 1 Target', 'Stage 2 Target', 'Stage 2 Sunset',
        'Forecast PC', 'Actual PC', 'Forecast Handover', 'Actual Handover',
    ])
    for w in works:
        p = w.project
        fs = p.funding_schedule
        addr = w.address
        writer.writerow([
            p.council.name,
            p.name,
            p.program.name if p.program_id else '',
            fs.schedule_number if fs else '',
            f"{addr.street}" if addr else '',
            (addr.suburb.name if addr and addr.suburb_id else '') if addr else '',
            w.work_type.name if w.work_type_id else (w.work_type_other or ''),
            w.bedrooms or '',
            w.quantity,
            f"{w.estimated_cost:.2f}" if w.estimated_cost is not None else '',
            f"{(w.total_estimated_cost or Decimal('0')):.2f}",
            w.get_status_display(),
            w.get_cashflow_method_display(),
            p.stage1_target_date.isoformat() if p.stage1_target_date else '',
            p.stage2_target_date.isoformat() if p.stage2_target_date else '',
            p.stage2_sunset_date.isoformat() if p.stage2_sunset_date else '',
            w.forecast_practical_completion_date.isoformat() if w.forecast_practical_completion_date else '',
            w.practical_completion_date.isoformat() if w.practical_completion_date else '',
            w.forecast_handover_date.isoformat() if w.forecast_handover_date else '',
            w.handover_date.isoformat() if w.handover_date else '',
        ])
    return response
