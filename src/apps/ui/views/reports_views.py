from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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
