from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Defect


@login_required
def defect_create(request, project_id):
    """Create a new defect for a project"""
    from apps.projects.models import Project
    
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        description = request.POST.get('description')
        identified_date = request.POST.get('identified_date')
        notes = request.POST.get('notes', '')
        
        if description and identified_date:
            Defect.objects.create(
                project=project,
                description=description,
                identified_date=identified_date,
                notes=notes
            )
            messages.success(request, 'Defect added.')
        
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def defect_delete(request, defect_id):
    """Delete a defect"""
    defect = get_object_or_404(Defect, id=defect_id)
    project_id = defect.project.id
    
    if request.method == 'POST':
        defect.delete()
        messages.success(request, 'Defect deleted.')
    
    return redirect('projects:project_detail', project_id=project_id)
