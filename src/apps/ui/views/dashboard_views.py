from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render

from apps.core.models import (
    Council, FundingAgreement, FundingSchedule, Payment,
    Program, Project, WorkFunding,
)


def _user_council(request):
    """Return the council for council-scoped users, or None."""
    try:
        return request.user.profile.council
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    council = _user_council(request)
    council_id = request.GET.get('council')
    program_id = request.GET.get('program')
    status_filter = request.GET.get('status')

    projects = Project.objects.select_related('council', 'program').prefetch_related('funding_schedules')

    if council:
        projects = projects.filter(council=council)
    elif council_id:
        projects = projects.filter(council_id=council_id)

    if program_id:
        projects = projects.filter(program_id=program_id)
    if status_filter:
        projects = projects.filter(status_flag=status_filter)

    total_projects = projects.count()
    late_projects = projects.filter(status_flag=Project.StatusFlag.LATE).count()
    overdue_projects = projects.filter(status_flag=Project.StatusFlag.OVERDUE).count()
    on_track_projects = projects.filter(status_flag=Project.StatusFlag.ON_TRACK).count()
    total_budget = (
        FundingSchedule.objects.filter(project__in=projects)
        .aggregate(total=Sum('total_funding'))['total'] or 0
    )
    active_projects = projects.exclude(state__in=[Project.State.COMPLETED, 'CANCELLED']).count()
    projects_by_state = projects.values('state').annotate(count=Count('id'))

    return render(request, 'dashboard/dashboard.html', {
        'projects': projects,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'late_projects': late_projects,
        'overdue_projects': overdue_projects,
        'on_track_projects': on_track_projects,
        'total_budget': total_budget,
        'projects_by_state': projects_by_state,
        'councils': Council.objects.all().order_by('name'),
        'programs': Program.objects.all().order_by('name'),
        'selected_council': council_id,
        'selected_program': program_id,
        'selected_status': status_filter,
    })


# ---------------------------------------------------------------------------
# Cashflow forecast — per-Program x per-FY matrix (PR 5)
# ---------------------------------------------------------------------------

@login_required
def cashflow_view(request):
    """Cashflow forecast — per-Program x per-FY matrix.

    Compares ProgramBudget (allocated $ per FY) against forecast committed
    (Payment.forecast_release_date bucketed into FYs) and released (actual)
    payments. Surfaces over/under-commitment and "undated" projects that are
    committed but don't yet have a forecast release date.
    """
    from apps.core.services.cashflow import build_program_cashflow

    program_id = request.GET.get('program', '').strip()
    council_id = request.GET.get('council', '').strip()

    program = None
    if program_id:
        try:
            program = Program.objects.get(pk=int(program_id))
        except (Program.DoesNotExist, ValueError):
            program = None

    councils = None
    if council_id:
        try:
            councils = [int(council_id)]
        except ValueError:
            councils = None

    role = getattr(getattr(request.user, 'profile', None), 'officer_role', None)
    hide_contingency = role in ('COUNCIL_USER', 'COUNCIL_MANAGER')
    data = build_program_cashflow(program=program, councils=councils, hide_contingency=hide_contingency)

    # Notice / Expense-Claim pathway runs alongside the schedule-based matrix:
    # these disbursements are ExpenseClaims against a FundingNotice cap, NOT
    # Payment rows, so they don't appear in the matrix above. Summarise them so
    # the cashflow page acknowledges this funding stream (same program/council
    # filters as the matrix).
    from decimal import Decimal
    from apps.core.models import FundingNotice
    notices = FundingNotice.objects.select_related('project')
    if program:
        notices = notices.filter(project__program=program)
    if councils:
        notices = notices.filter(project__council_id__in=councils)
    notice_list = list(notices)
    notice_capped = sum((n.capped_amount or Decimal('0')) for n in notice_list)
    notice_approved = sum((n.approved_claims_total or Decimal('0')) for n in notice_list)
    notice_summary = {
        'count': len(notice_list),
        'capped': notice_capped,
        'approved': notice_approved,
        'remaining': notice_capped - notice_approved,
        'open': sum(1 for n in notice_list if n.status == 'OPEN'),
    }

    return render(request, 'dashboard/cashflow.html', {
        'data': data,
        'notice_summary': notice_summary,
        'programs': Program.objects.filter(is_active=True).order_by('name'),
        'councils': Council.objects.order_by('name'),
        'selected_program_id': program_id,
        'selected_council_id': council_id,
    })


@login_required
def cashflow_monthly_view(request):
    """Monthly cashflow — per-Program x per-calendar-MONTH grid.

    Plots approved payments by their forecast/actual release month (a separate
    breakdown from the FY cashflow page). Programmed (unapproved) projects are
    excluded — they have a FY but no payment month. ProgramBudget is surfaced as
    per-FY context only (there is no monthly budget figure).
    """
    import json
    from apps.core.services.cashflow import build_program_monthly_cashflow

    program_id = request.GET.get('program', '').strip()
    council_id = request.GET.get('council', '').strip()
    start = request.GET.get('start', '').strip() or None

    try:
        months = int(request.GET.get('months', '24'))
    except (TypeError, ValueError):
        months = 24
    if months not in (12, 24, 36):
        months = 24

    program = None
    if program_id:
        try:
            program = Program.objects.get(pk=int(program_id))
        except (Program.DoesNotExist, ValueError):
            program = None

    councils = None
    if council_id:
        try:
            councils = [int(council_id)]
        except ValueError:
            councils = None

    role = getattr(getattr(request.user, 'profile', None), 'officer_role', None)
    hide_contingency = role in ('COUNCIL_USER', 'COUNCIL_MANAGER')
    data = build_program_monthly_cashflow(
        program=program, councils=councils, start=start, months=months,
        hide_contingency=hide_contingency,
    )

    return render(request, 'dashboard/cashflow_monthly.html', {
        'data_json': json.dumps(data),
        'data': data,
        'programs': Program.objects.filter(is_active=True).order_by('name'),
        'councils': Council.objects.order_by('name'),
        'selected_program_id': program_id,
        'selected_council_id': council_id,
        'selected_start': data['start'],
        'selected_months': months,
        'active_nav': 'cashflow_monthly',
    })


# ---------------------------------------------------------------------------
# Aggregate outputs
# ---------------------------------------------------------------------------

@login_required
def aggregate_outputs_view(request):
    """Work-level output report: what we are actually funding — dwellings by
    type and bedroom count, residential allotments, and their costs (actual
    where entered, otherwise estimated from notional rates)."""
    from collections import defaultdict
    from decimal import Decimal
    from apps.core.models import Work

    works = (
        Work.objects.exclude(project__state=Project.State.COMPLETED)
        .select_related('work_type', 'project__council', 'project__program')
    )

    def _bucket():
        return {'units': 0, 'bedrooms': 0, 'cost': Decimal('0'), 'projects': set()}

    by_work_type = {}
    by_bedrooms = defaultdict(_bucket)
    by_category = defaultdict(_bucket)
    by_council = defaultdict(_bucket)
    by_program = defaultdict(_bucket)
    totals = _bucket()

    for w in works:
        qty = w.quantity or 0
        cost = w.total_effective_cost or Decimal('0')
        beds = (w.bedrooms or 0) * qty
        has_bedrooms = bool(w.work_type and w.work_type.has_bedrooms)
        name = w.work_type.name if w.work_type else (w.work_type_other or 'Other')
        category = w.work_type.get_category_display() if w.work_type else 'Other'

        wt_key = (category, name)
        row = by_work_type.setdefault(wt_key, {
            'name': name, 'category': category,
            'short_code': w.work_type.short_code if w.work_type else '',
            'has_bedrooms': has_bedrooms, **_bucket(),
        })
        for tgt in (row, by_category[category], by_council[w.project.council.name if w.project.council else '—'],
                    by_program[w.project.program.name if w.project.program else '—'], totals):
            tgt['units'] += qty
            tgt['bedrooms'] += beds
            tgt['cost'] += cost
            tgt['projects'].add(w.project_id)

        if has_bedrooms and w.bedrooms:
            b = by_bedrooms[w.bedrooms]
            b['units'] += qty
            b['cost'] += cost
            b['projects'].add(w.project_id)

    def _finalise(bucket, **extra):
        units = bucket['units']
        return {
            **extra,
            'units': units,
            'bedrooms': bucket['bedrooms'],
            'cost': bucket['cost'],
            'avg_cost': (bucket['cost'] / units) if units else Decimal('0'),
            'project_count': len(bucket['projects']),
        }

    work_type_rows = [
        _finalise(r, name=r['name'], category=r['category'],
                  short_code=r['short_code'], has_bedrooms=r['has_bedrooms'])
        for r in sorted(by_work_type.values(), key=lambda x: (x['category'], x['name']))
    ]
    bedroom_rows = [
        _finalise(v, bedrooms_label=b) for b, v in sorted(by_bedrooms.items())
    ]
    category_rows = [
        _finalise(v, category=c) for c, v in sorted(by_category.items())
    ]
    council_rows = [
        _finalise(v, council=c) for c, v in sorted(by_council.items())
    ]
    program_rows = [
        _finalise(v, program=p) for p, v in sorted(by_program.items())
    ]

    return render(request, 'dashboard/aggregate.html', {
        'work_type_rows': work_type_rows,
        'bedroom_rows': bedroom_rows,
        'category_rows': category_rows,
        'council_rows': council_rows,
        'program_rows': program_rows,
        'totals': _finalise(totals),
    })


# ---------------------------------------------------------------------------
# Issue #26 — Project status board (/dashboard/projects/)
# ---------------------------------------------------------------------------

@login_required
def projects_board_view(request):
    """Kanban-style project status board grouped by lifecycle stage."""
    program_id = request.GET.get('program')
    council_id = request.GET.get('council')
    financial_year = request.GET.get('financial_year')

    projects = (
        Project.objects
        .select_related('council', 'program')
        .prefetch_related('funding_schedules')
        .order_by('name')
    )
    if program_id:
        projects = projects.filter(program_id=program_id)
    if council_id:
        projects = projects.filter(council_id=council_id)
    if financial_year:
        projects = projects.filter(financial_year=financial_year)

    today = date.today()

    def _card(project):
        total_funding = (
            project.funding_schedules.aggregate(t=Sum('total_funding'))['t'] or 0
        )
        target = project.completion_date or project.stage2_sunset_date
        days_left = (target - today).days if target else None
        return {
            'project': project,
            'total_funding': total_funding,
            'days_left': days_left,
            'overdue': days_left is not None and days_left < 0,
        }

    column_order = [
        Project.State.PROSPECTIVE,
        Project.State.PROGRAMMED,
        Project.State.FUNDED,
        Project.State.COMMENCED,
        Project.State.UNDER_CONSTRUCTION,
        Project.State.COMPLETED,
    ]
    state_labels = dict(Project.State.choices)

    columns = []
    for state in column_order:
        state_projects = [_card(p) for p in projects if p.state == state]
        columns.append({
            'state': state,
            'label': state_labels.get(state, state),
            'projects': state_projects,
            'count': len(state_projects),
        })

    financial_years = (
        Project.objects.exclude(financial_year='')
        .values_list('financial_year', flat=True)
        .distinct()
        .order_by('financial_year')
    )

    return render(request, 'dashboard/projects_board.html', {
        'columns': columns,
        'councils': Council.objects.all().order_by('name'),
        'programs': Program.objects.all().order_by('name'),
        'financial_years': financial_years,
        'selected_program': program_id,
        'selected_council': council_id,
        'selected_year': financial_year,
        'total_projects': sum(c['count'] for c in columns),
    })


# ---------------------------------------------------------------------------
# Issue #25 — Financial traceability (/dashboard/traceability/)
# ---------------------------------------------------------------------------

@login_required
def traceability_view(request):
    """'Follow the money' drill-down: Council -> Agreement -> Schedule -> Allocations -> Payments."""
    council_id = request.GET.get('council')
    selected_council = None
    chain = []

    if council_id:
        selected_council = Council.objects.filter(pk=council_id).first()

    if selected_council:
        agreements = (
            FundingAgreement.objects.filter(council=selected_council)
            .order_by('-execution_date')
        )
        for agreement in agreements:
            schedules = (
                FundingSchedule.objects.filter(funding_agreement=agreement)
                .select_related('project', 'payment_rule')
                .order_by('schedule_number')
            )
            agreement_total = 0
            agreement_paid = 0
            schedule_rows = []

            for schedule in schedules:
                payments = (
                    Payment.objects.filter(funding_schedule=schedule)
                    .select_related('project')
                    .order_by('release_date')
                )
                allocations = (
                    WorkFunding.objects.filter(funding_schedule=schedule)
                    .select_related('project', 'work')
                )
                paid = (
                    payments.filter(status__in=[Payment.Status.RELEASED])
                    .aggregate(t=Sum('amount'))['t'] or 0
                )
                pct = round(paid / schedule.total_funding * 100, 1) if schedule.total_funding else 0
                remaining = schedule.total_funding - paid
                agreement_total += schedule.total_funding
                agreement_paid += paid

                schedule_rows.append({
                    'schedule': schedule,
                    'paid': paid,
                    'remaining': remaining,
                    'pct_expended': pct,
                    'allocations': list(allocations),
                    'payments': list(payments),
                })

            agreement_pct = round(agreement_paid / agreement_total * 100, 1) if agreement_total else 0
            chain.append({
                'agreement': agreement,
                'total': agreement_total,
                'paid': agreement_paid,
                'remaining': agreement_total - agreement_paid,
                'pct_expended': agreement_pct,
                'schedules': schedule_rows,
            })

    grand_total = sum(a['total'] for a in chain)
    grand_paid = sum(a['paid'] for a in chain)
    grand_pct = round(grand_paid / grand_total * 100, 1) if grand_total else 0

    return render(request, 'dashboard/traceability.html', {
        'councils': Council.objects.all().order_by('name'),
        'selected_council': selected_council,
        'chain': chain,
        'grand_total': grand_total,
        'grand_paid': grand_paid,
        'grand_remaining': grand_total - grand_paid,
        'grand_pct': grand_pct,
    })


# ---------------------------------------------------------------------------
# In-app Help / documentation (standalone page, opened in a new tab)
# ---------------------------------------------------------------------------

@login_required
def help_view(request):
    """Standalone user guide — features, roles, workflows, domain model.

    Rendered without the app chrome so it reads cleanly in a new tab/popup and
    prints well. Role context (is_fnc/is_council/...) is supplied globally by the
    context processor, so the page can tailor what it shows to the viewer."""
    return render(request, 'help/index.html')
