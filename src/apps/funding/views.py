from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from decimal import Decimal
from .models import FundingSchedule, FundingApproval, WorkFunding
from apps.projects.models import Project


@login_required
def funding_schedule_create(request, project_id):
    """Create a new funding schedule for a project (dwelling or land)"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        contingency_str = request.POST.get('contingency', '0')
        payment_split = request.POST.get('payment_split', '30/60/10')
        
        try:
            amount = Decimal(amount_str) if amount_str else Decimal('0')
            contingency = Decimal(contingency_str) if contingency_str else Decimal('0')
        except:
            amount = Decimal('0')
            contingency = Decimal('0')
        
        FundingSchedule.objects.create(
            project=project,
            amount=amount,
            contingency=contingency,
            payment_split=payment_split
        )
        messages.success(request, 'Funding schedule added.')
        
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def funding_schedule_delete(request, fs_id):
    """Delete a funding schedule"""
    fs = get_object_or_404(FundingSchedule, id=fs_id)
    
    if fs.project:
        project_id = fs.project.id
        redirect_url = 'projects:project_detail'
    else:
        messages.error(request, 'Cannot determine project to redirect to.')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        fs.delete()
        messages.success(request, 'Funding schedule deleted.')
    
    return redirect(redirect_url, project_id=project_id)


@login_required
def funding_approval_create(request, project_id):
    """Create a new funding approval for a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        total_amount = request.POST.get('total_amount', 0)
        contingency_amount = request.POST.get('contingency_amount', 0)
        mincor_reference = request.POST.get('mincor_reference', '')
        
        fa = FundingApproval.objects.create(
            total_amount=total_amount or 0,
            contingency_amount=contingency_amount or 0,
            mincor_reference=mincor_reference,
            created_by=request.user
        )
        fa.projects.add(project)
        messages.success(request, 'Funding approval added.')
        
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def funding_approval_delete(request, fa_id):
    """Delete a funding approval"""
    fa = get_object_or_404(FundingApproval, id=fa_id)
    project_id = fa.projects.first().id if fa.projects.exists() else 0
    
    if request.method == 'POST':
        fa.delete()
        messages.success(request, 'Funding approval deleted.')
    
    if project_id:
        return redirect('projects:project_detail', project_id=project_id)
    return redirect('projects:project_list')