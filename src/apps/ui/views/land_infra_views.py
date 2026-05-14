from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import LandProject, Council, Program


@login_required
def land_projects_list_view(request):
    """List all land and infrastructure projects with filtering"""
    # Get filter parameters
    council_id = request.GET.get('council', '')
    status_filter = request.GET.get('status', '')
    
    # Build queryset
    land_projects = LandProject.objects.select_related('council').all()

    # Apply filters
    if council_id:
        land_projects = land_projects.filter(council_id=council_id)
    if status_filter:
        land_projects = land_projects.filter(status=status_filter)
    
    # Get filter options
    councils = Council.objects.all()

    context = {
        'land_projects': land_projects,
        'councils': councils,
        'selected_council': council_id,
        'selected_status': status_filter,
    }
    return render(request, 'land_infra/list.html', context)
