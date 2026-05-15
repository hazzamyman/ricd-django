from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import Project, Council


@login_required
def land_projects_list_view(request):
    """List all land-type projects with filtering"""
    council_id = request.GET.get('council', '')
    status_filter = request.GET.get('status', '')

    land_projects = Project.objects.filter(project_type=Project.Type.LAND).select_related('council')

    if council_id:
        land_projects = land_projects.filter(council_id=council_id)
    if status_filter:
        land_projects = land_projects.filter(state=status_filter)

    context = {
        'land_projects': land_projects,
        'councils': Council.objects.all(),
        'selected_council': council_id,
        'selected_status': status_filter,
    }
    return render(request, 'land_infra/list.html', context)
