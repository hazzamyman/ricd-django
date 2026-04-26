from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Work, WorkType


@login_required
def work_create(request, project_id):
    """Create a new work for a dwelling project"""
    from apps.projects.models import Project
    from apps.addresses.models import Address
    
    project = get_object_or_404(Project, id=project_id)
    addresses = project.addresses.all()
    work_types = WorkType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        address_id = request.POST.get('address')
        work_type_id = request.POST.get('work_type')
        work_type_other = request.POST.get('work_type_other', '')
        bedrooms = request.POST.get('bedrooms', 0) or 0
        quantity = request.POST.get('quantity', 1)
        estimated_cost = request.POST.get('estimated_cost', 0)
        
        if address_id and (work_type_id or work_type_other):
            address = Address.objects.get(id=address_id)
            work_type = WorkType.objects.get(id=work_type_id) if work_type_id else None
            
            Work.objects.create(
                project=project,
                project_type=Work.ProjectType.DWELLING,
                address=address,
                work_type=work_type,
                work_type_other=work_type_other,
                bedrooms=int(bedrooms),
                quantity=quantity or 1,
                estimated_cost=estimated_cost or 0
            )
            messages.success(request, 'Work added.')
        
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def work_create_land(request, land_project_id):
    """Create a new work for a land/infra project"""
    from apps.land_infra.models import LandProject
    
    land_project = get_object_or_404(LandProject, id=land_project_id)
    work_types = WorkType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        work_type_id = request.POST.get('work_type')
        work_type_other = request.POST.get('work_type_other', '')
        quantity = request.POST.get('quantity', 1)
        estimated_cost = request.POST.get('estimated_cost', 0)
        
        if work_type_id or work_type_other:
            work_type = WorkType.objects.get(id=work_type_id) if work_type_id else None
            
            Work.objects.create(
                land_project=land_project,
                project_type=Work.ProjectType.LAND,
                work_type=work_type,
                work_type_other=work_type_other,
                quantity=quantity or 1,
                estimated_cost=estimated_cost or 0
            )
            messages.success(request, 'Work added.')
        
        return redirect('land_infra:land_project_detail', project_id=land_project.id)
    
    return redirect('land_infra:land_project_detail', project_id=land_project.id)


@login_required
def work_delete(request, work_id):
    """Delete a work"""
    work = get_object_or_404(Work, id=work_id)
    
    if work.project_type == Work.ProjectType.DWELLING and work.project:
        project_id = work.project.id
        redirect_url = 'projects:project_detail'
    elif work.land_project:
        project_id = work.land_project.id
        redirect_url = 'land_infra:land_project_detail'
    else:
        messages.error(request, 'Cannot determine project to redirect to.')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        work.delete()
        messages.success(request, 'Work deleted.')
    
    return redirect(redirect_url, project_id=project_id)