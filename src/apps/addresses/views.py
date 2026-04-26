from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Address


@login_required
def address_create(request, project_id):
    """Create a new address for a project"""
    from apps.projects.models import Project
    
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        street = request.POST.get('street')
        lot = request.POST.get('lot', '')
        plan = request.POST.get('plan', '')
        
        if street:
            Address.objects.create(
                project=project,
                street=street,
                lot=lot,
                plan=plan
            )
            messages.success(request, 'Address added.')
        
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def address_delete(request, address_id):
    """Delete an address"""
    address = get_object_or_404(Address, id=address_id)
    project_id = address.project.id
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted.')
    
    return redirect('projects:project_detail', project_id=project_id)
