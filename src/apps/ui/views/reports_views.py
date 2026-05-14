from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import StageReport, QuarterlyReport, Project


@login_required
def reports_dashboard_view(request):
    """Reports dashboard showing stage and quarterly reports"""
    # Get filter parameters
    project_id = request.GET.get('project', '')
    status_filter = request.GET.get('status', '')
    
    # Build querysets
    stage_reports = StageReport.objects.select_related('project')
    quarterly_reports = QuarterlyReport.objects.select_related('project')
    
    # Apply filters
    if project_id:
        stage_reports = stage_reports.filter(project_id=project_id)
        quarterly_reports = quarterly_reports.filter(project_id=project_id)
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
