"""
Cashflow forecast service.

Computes a per-Program (or per-Council) x per-FinancialYear matrix:

  | Program | 2025-26 budgeted | 2025-26 forecast | 2025-26 released | Variance | % committed |
  | ...     | ...              | ...              | ...              | ...      | ...         |

Plus an "undated" bucket -- projects that are PROSPECTIVE/PROGRAMMED/FUNDED but
have no forecast release date yet. These are tracked as committed-but-not-scheduled
so the program isn't over-allocated.

Inputs:
  * ProgramBudget rows (Budgeted)
  * Payment.forecast_release_date for non-REJECTED payments (Forecast)
  * Payment.release_date for RELEASED payments (Released)
  * Project.state in (PROSPECTIVE, PROGRAMMED, FUNDED) with no Payment rows yet (Undated)
"""
from collections import defaultdict
from decimal import Decimal

from apps.core.models import Payment, ProgramBudget, Project
from apps.core.utils import date_to_financial_year


def _zero():
    return Decimal('0')


def _fy_label(fy_code):
    """Convert internal '2025-2026' to display '2025-26'."""
    if not fy_code or '-' not in fy_code:
        return fy_code or ''
    a, b = fy_code.split('-', 1)
    return f"{a}-{b[-2:]}"


def build_program_cashflow(program=None, councils=None, hide_contingency=False):
    """Return a dict describing the cashflow matrix.

    Args:
        program: optional Program -- limit to this program.
        councils: optional iterable of Council ids -- limit projects to these.

    Returns:
        dict with keys:
            fys: sorted list of FY codes
            fy_labels: {fy_code: short_display}
            rows: per-program rows with cells per FY + totals + undated
            col_totals: per-FY column totals plus '__all__' grand totals
            undated_projects: list of {project, estimated} dicts for the panel
    """
    # 1) Pull every budget row
    budget_qs = ProgramBudget.objects.select_related('program').all()
    if program is not None:
        budget_qs = budget_qs.filter(program=program)
    if councils is not None:
        budget_qs = budget_qs.filter(program__projects__council__in=councils).distinct()

    budgeted_by = defaultdict(_zero)  # (program_id, fy_code) -> Decimal
    fy_set = set()
    programs_seen = {}
    for b in budget_qs:
        key = (b.program_id, b.financial_year)
        budgeted_by[key] += b.allocated or _zero()
        fy_set.add(b.financial_year)
        programs_seen[b.program_id] = b.program

    # 2) Pull every payment (non-rejected) and bucket by FY × program.
    #
    # Co-funding handling:
    # - RELEASED payments: use the LOCKED PaymentAllocation snapshot (per-program
    #   amounts captured at the moment of release; immutable thereafter).
    # - Non-released forecasts: split on-the-fly using the project's current
    #   APPROVED BFAItem ratios.
    from apps.core.models import Program as _Program
    payments = Payment.objects.select_related('project__program', 'project__council').prefetch_related(
        'allocations__program'
    ).exclude(status='REJECTED')
    if program is not None:
        payments = payments.filter(project__program=program)
    if councils is not None:
        payments = payments.filter(project__council__in=councils)

    forecast_by = defaultdict(_zero)
    released_by = defaultdict(_zero)
    undated_payments = []  # actual payments with no forecast/release date yet

    def _record_program(prog_id):
        if prog_id and prog_id not in programs_seen:
            try:
                programs_seen[prog_id] = _Program.objects.get(pk=prog_id)
            except _Program.DoesNotExist:
                pass

    for p in payments:
        if p.project is None:
            continue
        amount = (p.amount or _zero())
        if amount <= 0:
            continue

        # Forecast bucket (uses current ratios)
        forecast_fy = date_to_financial_year(p.forecast_release_date)
        if forecast_fy is None:
            forecast_fy = date_to_financial_year(p.release_date)
        if forecast_fy is None and p.status != 'RELEASED':
            # No forecast date assigned yet — surface it so committed money isn't
            # silently dropped from the matrix.
            undated_payments.append({'payment': p, 'project': p.project, 'amount': amount})
        if forecast_fy:
            fy_set.add(forecast_fy)
            split = p.compute_program_split()
            for prog_id, (share, _ratio) in split.items():
                _record_program(prog_id)
                if program is not None and prog_id != program.pk:
                    continue
                forecast_by[(prog_id, forecast_fy)] += share

        # Released bucket (uses LOCKED PaymentAllocation snapshot when present)
        if p.status == 'RELEASED' and p.release_date:
            released_fy = date_to_financial_year(p.release_date)
            fy_set.add(released_fy)
            allocs = list(p.allocations.all())
            if allocs:
                for a in allocs:
                    _record_program(a.program_id)
                    if program is not None and a.program_id != program.pk:
                        continue
                    released_by[(a.program_id, released_fy)] += a.amount
            else:
                # Legacy released payment with no snapshot — fall back to current ratios
                split = p.compute_program_split()
                for prog_id, (share, _ratio) in split.items():
                    _record_program(prog_id)
                    if program is not None and prog_id != program.pk:
                        continue
                    released_by[(prog_id, released_fy)] += share

    # 3) Undated projects bucket
    undated_qs = Project.objects.select_related('program', 'council').filter(
        state__in=[Project.State.PROSPECTIVE, Project.State.PROGRAMMED, Project.State.FUNDED]
    )
    if program is not None:
        undated_qs = undated_qs.filter(program=program)
    if councils is not None:
        undated_qs = undated_qs.filter(council__in=councils)
    undated_qs = undated_qs.exclude(
        payments__forecast_release_date__isnull=False
    ).distinct()

    from apps.core.models import BriefFinancialApprovalItem
    undated_by_prog = defaultdict(_zero)
    undated_projects = []
    for proj in undated_qs:
        if proj.program_id is None:
            continue
        # Walk BFA item rows so co-funded projects appear in EACH program's column.
        items = BriefFinancialApprovalItem.objects.filter(
            bfa__status='APPROVED', project=proj,
        ).select_related('program')
        estimated_total = _zero()
        for i in items:
            contingency = _zero() if hide_contingency else (i.contingency_amount or _zero())
            t = (i.funding_amount or _zero()) + contingency
            if t <= 0:
                continue
            prog_id = i.program_id or proj.program_id
            if program is not None and prog_id != program.pk:
                continue
            _record_program(prog_id)
            undated_by_prog[prog_id] += t
            estimated_total += t
        # Show the project in the side-panel with its total estimated value
        if estimated_total > 0 or not items:
            undated_projects.append({'project': proj, 'estimated': estimated_total})

    # 3b) Programmed (NOT approved) projects — forward demand for Treasury.
    # A project is "programmed" when it has NO approved BFA and no payments yet.
    # Its estimated cost (works' effective cost) lands in its programmed
    # financial_year. This is the unapproved layer, kept separate from committed.
    approved_pids = set(
        BriefFinancialApprovalItem.objects.filter(bfa__status='APPROVED')
        .values_list('project_id', flat=True)
    )
    paid_pids = set(
        Payment.objects.exclude(status='REJECTED').values_list('project_id', flat=True)
    )
    prog_qs = (
        Project.objects.select_related('program')
        .filter(is_archived=False, program__isnull=False)
        .exclude(state=Project.State.COMPLETED)
        .prefetch_related('works__work_type')
    )
    if program is not None:
        prog_qs = prog_qs.filter(program=program)
    if councils is not None:
        prog_qs = prog_qs.filter(council__in=councils)

    programmed_by = defaultdict(_zero)   # (program_id, fy_code) -> Decimal
    programmed_projects = []
    for proj in prog_qs:
        if proj.pk in approved_pids or proj.pk in paid_pids:
            continue  # already committed (approved BFA or has payments)
        fy = (proj.financial_year or '').strip()
        if not fy:
            continue  # no programmed year to bucket into
        est = sum((w.total_effective_cost for w in proj.works.all()), _zero())
        if est <= 0:
            continue
        fy_set.add(fy)
        _record_program(proj.program_id)
        programmed_by[(proj.program_id, fy)] += est
        programmed_projects.append({'project': proj, 'estimated': est, 'fy': fy})

    # 4) Assemble rows
    fys = sorted(fy_set) if fy_set else []
    rows = []
    col_totals = defaultdict(lambda: {'budgeted': _zero(), 'forecast': _zero(),
                                       'released': _zero(), 'undated': _zero(),
                                       'programmed': _zero(), 'variance': _zero()})

    for prog_id, prog in sorted(programs_seen.items(), key=lambda x: x[1].name):
        cells = []  # ordered list aligned with `fys`
        total_b = _zero()
        total_f = _zero()
        total_r = _zero()
        total_p = _zero()
        for fy in fys:
            b = budgeted_by[(prog_id, fy)]
            f = forecast_by[(prog_id, fy)]
            r = released_by[(prog_id, fy)]
            pr = programmed_by[(prog_id, fy)]
            variance = b - f
            pct = (f / b * Decimal('100')) if b else _zero()
            cells.append({
                'fy': fy,
                'fy_label': _fy_label(fy),
                'budgeted': b,
                'forecast': f,
                'released': r,
                'programmed': pr,
                'total_need': f + pr,
                'variance': variance,
                'pct': pct,
                'over': f > b and b > 0,
            })
            total_b += b
            total_f += f
            total_r += r
            total_p += pr
            col_totals[fy]['budgeted'] += b
            col_totals[fy]['forecast'] += f
            col_totals[fy]['released'] += r
            col_totals[fy]['programmed'] += pr
            col_totals[fy]['variance'] += variance

        undated = undated_by_prog[prog_id]
        col_totals['__all__']['budgeted'] += total_b
        col_totals['__all__']['forecast'] += total_f
        col_totals['__all__']['released'] += total_r
        col_totals['__all__']['undated'] += undated
        col_totals['__all__']['programmed'] += total_p
        col_totals['__all__']['variance'] += (total_b - total_f)

        rows.append({
            'program': prog,
            'cells': cells,
            'undated': undated,
            'totals': {
                'budgeted': total_b,
                'forecast': total_f,
                'released': total_r,
                'programmed': total_p,
                'total_need': total_f + total_p,
                'variance': total_b - total_f,
                'pct': (total_f / total_b * Decimal('100')) if total_b else _zero(),
            },
        })

    # Build a parallel ordered list of column totals so the template doesn't
    # have to do variable-key dict lookups.
    column_totals_list = [
        {'fy': fy, 'fy_label': _fy_label(fy), **col_totals[fy]}
        for fy in fys
    ]

    # Forward demand by FY: budgeted vs (committed forecast + programmed-unapproved).
    forward_demand = []
    for fy in fys:
        ct = col_totals[fy]
        total_need = ct['forecast'] + ct['programmed']
        forward_demand.append({
            'fy': fy, 'fy_label': _fy_label(fy),
            'budgeted': ct['budgeted'],
            'forecast': ct['forecast'],
            'programmed': ct['programmed'],
            'total_need': total_need,
            'gap': ct['budgeted'] - total_need,
        })
    programmed_projects.sort(
        key=lambda x: (x['fy'], x['project'].program.name if x['project'].program_id else '',
                       x['project'].name)
    )

    return {
        'fys': fys,
        'fy_labels': {fy: _fy_label(fy) for fy in fys},
        'rows': rows,
        'col_totals': dict(col_totals),
        'column_totals_list': column_totals_list,
        'grand_totals': col_totals['__all__'],
        'undated_projects': undated_projects,
        'undated_payments': undated_payments,
        'undated_payments_total': sum((u['amount'] for u in undated_payments), _zero()),
        'forward_demand': forward_demand,
        'programmed_projects': programmed_projects,
        'programmed_total': sum((pp['estimated'] for pp in programmed_projects), _zero()),
    }
