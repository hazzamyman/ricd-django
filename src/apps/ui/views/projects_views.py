from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from apps.core.models import Project, Council, Program, FundingSchedule, Payment


@login_required
def projects_list_view(request):
    """List all projects with filtering"""
    # Get filter parameters
    council_id = request.GET.get('council', '')
    program_id = request.GET.get('program', '')
    state_filter = request.GET.get('state', '')
    
    # Build queryset
    projects = Project.objects.select_related('council', 'program').prefetch_related('funding_schedules', 'payments')
    
    # Apply filters
    if council_id:
        projects = projects.filter(council_id=council_id)
    if program_id:
        projects = projects.filter(program_id=program_id)
    if state_filter:
        projects = projects.filter(state=state_filter)
    
    # Add calculated fields
    project_list = []
    for project in projects:
        total_budget = project.funding_schedules.aggregate(total=Sum('total_funding'))['total'] or 0
        project_list.append({
            'id': project.id,
            'name': project.name,
            'council': project.council.name if project.council else 'N/A',
            'program': project.program.name if project.program else 'N/A',
            'state': project.get_state_display() if hasattr(project, 'get_state_display') else project.state,
            'total_budget': total_budget,
            'project': project,
        })
    
    # Get filter options
    councils = Council.objects.all()
    programs = Program.objects.filter(is_active=True)
    
    context = {
        'projects': project_list,
        'councils': councils,
        'programs': programs,
        'selected_council': council_id,
        'selected_program': program_id,
        'selected_state': state_filter,
    }
    return render(request, 'projects/list.html', context)
