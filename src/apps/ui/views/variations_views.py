from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import Variation, Project


@login_required
def variations_list_view(request):
    """List all variations with filtering"""
    # Get filter parameters
    project_id = request.GET.get('project', '')
    status_filter = request.GET.get('status', '')
    
    # Build queryset
    variations = Variation.objects.select_related('funding_schedule__project', 'variation_type').prefetch_related('projects').all()
    
    # Apply filters
    if project_id:
        variations = variations.filter(project_id=project_id)
    if status_filter:
        variations = variations.filter(status=status_filter)
    
    # Get filter options
    projects = Project.objects.all()
    
    context = {
        'variations': variations,
        'projects': projects,
        'selected_project': project_id,
        'selected_status': status_filter,
    }
    return render(request, 'variations/list.html', context)
