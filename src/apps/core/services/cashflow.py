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


def build_program_cashflow(program=None, councils=None):
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

    # 2) Pull every payment (non-rejected) and bucket by FY
    payments = Payment.objects.select_related('project__program', 'project__council').exclude(
        status='REJECTED'
    )
    if program is not None:
        payments = payments.filter(project__program=program)
    if councils is not None:
        payments = payments.filter(project__council__in=councils)

    forecast_by = defaultdict(_zero)
    released_by = defaultdict(_zero)
    for p in payments:
        if p.project is None or p.project.program_id is None:
            continue
        prog_id = p.project.program_id
        programs_seen.setdefault(prog_id, p.project.program)
        amount = (p.amount or _zero())
        forecast_fy = date_to_financial_year(p.forecast_release_date)
        if forecast_fy is None:
            forecast_fy = date_to_financial_year(p.release_date)
        if forecast_fy:
            forecast_by[(prog_id, forecast_fy)] += amount
            fy_set.add(forecast_fy)
        if p.status == 'RELEASED' and p.release_date:
            released_fy = date_to_financial_year(p.release_date)
            released_by[(prog_id, released_fy)] += amount
            fy_set.add(released_fy)

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

    undated_by_prog = defaultdict(_zero)
    undated_projects = []
    for proj in undated_qs:
        if proj.program_id is None:
            continue
        bfa = proj.financial_approvals.filter(status='APPROVED').first()
        estimated = (bfa.total_amount if bfa else _zero())
        undated_by_prog[proj.program_id] += estimated
        programs_seen.setdefault(proj.program_id, proj.program)
        undated_projects.append({'project': proj, 'estimated': estimated})

    # 4) Assemble rows
    fys = sorted(fy_set) if fy_set else []
    rows = []
    col_totals = defaultdict(lambda: {'budgeted': _zero(), 'forecast': _zero(),
                                       'released': _zero(), 'undated': _zero(),
                                       'variance': _zero()})

    for prog_id, prog in sorted(programs_seen.items(), key=lambda x: x[1].name):
        cells = []  # ordered list aligned with `fys`
        total_b = _zero()
        total_f = _zero()
        total_r = _zero()
        for fy in fys:
            b = budgeted_by[(prog_id, fy)]
            f = forecast_by[(prog_id, fy)]
            r = released_by[(prog_id, fy)]
            variance = b - f
            pct = (f / b * Decimal('100')) if b else _zero()
            cells.append({
                'fy': fy,
                'fy_label': _fy_label(fy),
                'budgeted': b,
                'forecast': f,
                'released': r,
                'variance': variance,
                'pct': pct,
                'over': f > b and b > 0,
            })
            total_b += b
            total_f += f
            total_r += r
            col_totals[fy]['budgeted'] += b
            col_totals[fy]['forecast'] += f
            col_totals[fy]['released'] += r
            col_totals[fy]['variance'] += variance

        undated = undated_by_prog[prog_id]
        col_totals['__all__']['budgeted'] += total_b
        col_totals['__all__']['forecast'] += total_f
        col_totals['__all__']['released'] += total_r
        col_totals['__all__']['undated'] += undated
        col_totals['__all__']['variance'] += (total_b - total_f)

        rows.append({
            'program': prog,
            'cells': cells,
            'undated': undated,
            'totals': {
                'budgeted': total_b,
                'forecast': total_f,
                'released': total_r,
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

    return {
        'fys': fys,
        'fy_labels': {fy: _fy_label(fy) for fy in fys},
        'rows': rows,
        'col_totals': dict(col_totals),
        'column_totals_list': column_totals_list,
        'grand_totals': col_totals['__all__'],
        'undated_projects': undated_projects,
    }
