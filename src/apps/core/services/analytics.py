"""
Aggregate Outputs analytics service (Analytics page).

Per output **category** (Land / Dwellings / Extensions / Demolition / Other,
plus an Overall roll-up), broken down **by LGA (council)**:

  * Pipeline unit counts by Project.state (Potential … Completed) + Funded Yield.
  * **Approved funding by program** — DYNAMIC per-Program columns sourced from
    BriefFinancialApprovalItem.funding_amount (a program column appears only for
    categories it actually funds). This replaces the old funding-source buckets.
  * Total Approved (Σ program columns) and Paid to Council (Σ PaymentAllocation).
  * Development-application unit buckets (Approved / Submitted / None) + Surplus.
  * Effective cost and average cost per unit.
  * An output-mix breakdown (work_type + bedrooms) across pipeline stages.

Funding attribution = method (a): a project's full per-program approved funding
is counted on EVERY category it has works in (flagged as "may double-count" in
the UI). The Overall roll-up counts each project ONCE (no double counting).
"""
from collections import defaultdict

from apps.core.models import (
    Project, Work, BriefFinancialApprovalItem, PaymentAllocation,
    Program, DevelopmentApplication,
)

CATS = ['land', 'dwellings', 'extensions', 'demolition', 'other']
CAT_LABEL = {'overall': 'Overall', 'land': 'Land', 'dwellings': 'Dwellings',
             'extensions': 'Extensions', 'demolition': 'Demolition', 'other': 'Other'}
CAT_UNIT = {'overall': 'outputs', 'land': 'lots', 'dwellings': 'dwellings',
            'extensions': 'extensions', 'demolition': 'demolitions', 'other': 'works'}
CAT_UNIT1 = {'overall': 'output', 'land': 'lot', 'dwellings': 'dwelling',
             'extensions': 'extension', 'demolition': 'demolition', 'other': 'work'}

# WorkType.Category -> page category
_WT_TO_CAT = {
    'LAND_DEV': 'land',
    'RESIDENTIAL': 'dwellings',
    'EXTENSION': 'extensions',
    'DEMOLITION': 'demolition',
    'INFRASTRUCTURE': 'other',
    'PLANNING': 'other',
}

STAGES = ['potential', 'inPipeline', 'fundedNotCommenced', 'commenced',
          'underConstruction', 'completed']
_STATE_STAGE = {
    'PROS': 'potential', 'PROG': 'inPipeline', 'FUND': 'fundedNotCommenced',
    'COMM': 'commenced', 'UC': 'underConstruction', 'COMP': 'completed',
}
_YIELD_STAGES = ('fundedNotCommenced', 'commenced', 'underConstruction', 'completed')


def _program_short(p):
    """A compact column label for a program."""
    name = p.name or ''
    return name if len(name) <= 16 else name[:15] + '…'


def build_aggregate_outputs(region=None):
    """Return a JSON-serialisable dict for the Analytics page.

    Args:
        region: optional council region string to scope to.
    """
    projects = Project.objects.filter(is_archived=False).select_related('council')
    if region:
        projects = projects.filter(council__region=region)

    pmeta = {}
    for p in projects:
        pmeta[p.pk] = {
            'council': p.council.name if p.council_id else '—',
            'region': (p.council.region if (p.council_id and p.council.region) else '—'),
            'stage': _STATE_STAGE.get(p.state),
        }
    pids = list(pmeta)
    if not pids:
        return _empty_payload(region)

    # Works -> per-project category units/cost, and per-category output mix.
    proj_cat_units = defaultdict(lambda: defaultdict(float))   # pid -> cat -> units
    proj_cat_cost = defaultdict(lambda: defaultdict(float))    # pid -> cat -> cost
    mix = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # cat -> (name,beds) -> stage -> units
    for w in Work.objects.filter(project_id__in=pids).select_related('work_type'):
        wt = w.work_type
        cat = _WT_TO_CAT.get(wt.category) if wt else None
        if cat is None:
            continue
        qty = float(w.quantity or 0)
        if qty <= 0:
            continue
        stage = pmeta[w.project_id]['stage']
        if stage is None:
            continue
        proj_cat_units[w.project_id][cat] += qty
        proj_cat_cost[w.project_id][cat] += float(w.total_effective_cost or 0)
        beds = int(w.bedrooms or 0)
        name = wt.name if wt else 'Other'
        mix[cat][(name, beds)][stage] += qty

    # Approved BFA funding + released allocations, per project per program.
    fund = defaultdict(lambda: defaultdict(float))   # pid -> progid -> approved $
    for it in (BriefFinancialApprovalItem.objects
               .filter(bfa__status='APPROVED', project_id__in=pids)):
        fund[it.project_id][it.program_id] += float(it.funding_amount or 0)
    paid = defaultdict(lambda: defaultdict(float))   # pid -> progid -> paid $
    for a in (PaymentAllocation.objects
              .filter(payment__project_id__in=pids).select_related('payment')):
        paid[a.payment.project_id][a.program_id] += float(a.amount or 0)

    prog_ids = set()
    for d in fund.values():
        prog_ids |= set(d)
    for d in paid.values():
        prog_ids |= set(d)
    programs = {p.pk: p for p in Program.objects.filter(pk__in=prog_ids)}

    # DA status per project.
    da_proj = defaultdict(set)   # pid -> {DA.status, ...}
    for da in DevelopmentApplication.objects.filter(projects__in=pids).prefetch_related('projects'):
        for p in da.projects.all():
            if p.pk in pmeta:
                da_proj[p.pk].add(da.status)

    def da_class(pid):
        st = da_proj.get(pid, set())
        if 'APPR' in st:
            return 'daApproved'
        if st & {'SUB', 'ASSESS'}:
            return 'daSubmitted'
        return 'daNotStarted'

    def new_row(council, region_name):
        r = {'council': council, 'region': region_name, 'totalCost': 0.0, 'paid': 0.0,
             'daApproved': 0.0, 'daSubmitted': 0.0, 'daNotStarted': 0.0,
             'funding': defaultdict(float)}
        for s in STAGES:
            r[s] = 0.0
        return r

    def finalise_rows(rows, prog_in_scope):
        order = sorted(programs.values(), key=lambda p: p.name)
        prog_list = [{'id': str(p.pk), 'name': p.name, 'short': _program_short(p)}
                     for p in order if p.pk in prog_in_scope]
        out = []
        for r in sorted(rows.values(), key=lambda x: x['council']):
            r['fundedYield'] = sum(r[s] for s in _YIELD_STAGES)
            r['programmed'] = r['inPipeline'] + r['fundedYield']
            r['totalApproved'] = sum(r['funding'].values())
            r['surplus'] = r['daApproved'] - r['programmed']
            r['avgCost'] = (r['totalCost'] / r['fundedYield']) if r['fundedYield'] else 0.0
            r['funding'] = {str(k): v for k, v in r['funding'].items()}
            out.append(r)
        return out, prog_list

    def totals_of(rows):
        t = {'council': 'All LGAs', 'region': '', 'totalCost': 0.0, 'paid': 0.0,
             'daApproved': 0.0, 'daSubmitted': 0.0, 'daNotStarted': 0.0, 'funding': defaultdict(float)}
        for s in STAGES:
            t[s] = 0.0
        for r in rows:
            for s in STAGES:
                t[s] += r[s]
            for k in ('totalCost', 'paid', 'daApproved', 'daSubmitted', 'daNotStarted'):
                t[k] += r[k]
            for pid, v in r['funding'].items():
                t['funding'][pid] += v
        t['fundedYield'] = sum(t[s] for s in _YIELD_STAGES)
        t['programmed'] = t['inPipeline'] + t['fundedYield']
        t['totalApproved'] = sum(t['funding'].values())
        t['surplus'] = t['daApproved'] - t['programmed']
        t['avgCost'] = (t['totalCost'] / t['fundedYield']) if t['fundedYield'] else 0.0
        t['funding'] = {str(k): v for k, v in t['funding'].items()}
        return t

    def mix_for(cat):
        rows = []
        if cat == 'overall':
            for c2 in CATS:
                counts = {s: 0.0 for s in STAGES}
                for stagemap in mix[c2].values():
                    for s, n in stagemap.items():
                        counts[s] += n
                total = sum(counts.values())
                if total > 0:
                    rows.append({'label': CAT_LABEL[c2], 'form': c2, 'beds': 0,
                                 'counts': counts, 'total': total})
        else:
            for (name, beds), stagemap in mix[cat].items():
                counts = {s: float(stagemap.get(s, 0.0)) for s in STAGES}
                total = sum(counts.values())
                if total > 0:
                    label = (f"{beds} Bed {name}" if beds else name)
                    rows.append({'label': label, 'form': name, 'beds': beds,
                                 'counts': counts, 'total': total})
        rows.sort(key=lambda r: -r['total'])
        return rows

    data = {}

    # Per-category pages: method (a) — full project funding on each category.
    for cat in CATS:
        rows = {}
        prog_in_scope = set()
        for pid, meta in pmeta.items():
            units = proj_cat_units[pid].get(cat, 0.0)
            if units <= 0:
                continue
            r = rows.setdefault(meta['council'], new_row(meta['council'], meta['region']))
            r[meta['stage']] += units
            r['totalCost'] += proj_cat_cost[pid].get(cat, 0.0)
            for progid, amt in fund[pid].items():
                r['funding'][progid] += amt
                if amt:
                    prog_in_scope.add(progid)
            for progid, amt in paid[pid].items():
                r['paid'] += amt
            r[da_class(pid)] += units
        rows_list, prog_list = finalise_rows(rows, prog_in_scope)
        data[cat] = {'programs': prog_list, 'rows': rows_list,
                     'totals': totals_of(rows_list), 'mix': mix_for(cat)}

    # Overall: count each project ONCE (no double counting of funding).
    rows = {}
    prog_in_scope = set()
    for pid, meta in pmeta.items():
        total_units = sum(proj_cat_units[pid].values())
        if total_units <= 0:
            continue
        r = rows.setdefault(meta['council'], new_row(meta['council'], meta['region']))
        r[meta['stage']] += total_units
        r['totalCost'] += sum(proj_cat_cost[pid].values())
        for progid, amt in fund[pid].items():
            r['funding'][progid] += amt
            if amt:
                prog_in_scope.add(progid)
        for progid, amt in paid[pid].items():
            r['paid'] += amt
        r[da_class(pid)] += total_units
    rows_list, prog_list = finalise_rows(rows, prog_in_scope)
    data['overall'] = {'programs': prog_list, 'rows': rows_list,
                       'totals': totals_of(rows_list), 'mix': mix_for('overall')}

    regions = list(Project.objects.filter(is_archived=False, council__region__gt='')
                   .values_list('council__region', flat=True).distinct().order_by('council__region'))

    return {
        'categories': ['overall'] + CATS,
        'cat_label': CAT_LABEL, 'cat_unit': CAT_UNIT, 'cat_unit1': CAT_UNIT1,
        'stages': STAGES,
        'data': data,
        'regions': regions,
        'selected_region': region or '',
    }


def _empty_payload(region):
    totals = {'council': 'All LGAs', 'region': '', 'totalCost': 0.0, 'paid': 0.0,
              'daApproved': 0.0, 'daSubmitted': 0.0, 'daNotStarted': 0.0,
              'fundedYield': 0.0, 'programmed': 0.0, 'totalApproved': 0.0,
              'surplus': 0.0, 'avgCost': 0.0, 'funding': {},
              **{s: 0.0 for s in STAGES}}
    return {
        'categories': ['overall'] + CATS,
        'cat_label': CAT_LABEL, 'cat_unit': CAT_UNIT, 'cat_unit1': CAT_UNIT1,
        'stages': STAGES,
        'data': {c: {'programs': [], 'rows': [], 'mix': [], 'totals': dict(totals)}
                 for c in (['overall'] + CATS)},
        'regions': [],
        'selected_region': region or '',
    }
