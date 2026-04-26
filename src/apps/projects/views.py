from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q as DBQ
from .models import Project, Comment
from apps.funding.models import FundingSchedule, FundingApproval
from apps.variations.models import Variation
from apps.reports.models import MonthlyTracker, QuarterlyReport, StageReport
from apps.works.models import Work, WorkType
from apps.addresses.models import Address
from apps.payments.models import Payment
from apps.defects.models import Defect
from apps.core.utils import CURRENT_FINANCIAL_YEAR, FINANCIAL_YEAR_CHOICES


@login_required
def project_list(request):
    """List all projects with filters"""
    council_id = request.GET.get('council')
    program_id = request.GET.get('program')
    state_filter = request.GET.get('state')
    financial_year = request.GET.get('financial_year')
    
    projects = Project.objects.select_related('council', 'program').prefetch_related('funding_schedules').order_by('-start_date')
    
    if council_id:
        projects = projects.filter(council_id=council_id)
    if program_id:
        projects = projects.filter(program_id=program_id)
    if state_filter:
        projects = projects.filter(state=state_filter)
    if financial_year:
        projects = projects.filter(financial_year=financial_year)
    
    from apps.councils.models import Council
    from apps.programs.models import Program
    
    context = {
        'projects': projects,
        'states': Project.State.choices,
        'councils': Council.objects.order_by('name'),
        'programs': Program.objects.order_by('name'),
        'financial_years': sorted(set(Project.objects.values_list('financial_year', flat=True).distinct())),
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_detail(request, project_id):
    """Show project details with tabbed interface"""
    project = get_object_or_404(
        Project.objects.select_related('council', 'program').prefetch_related(
            'funding_schedules', 'works', 'addresses', 'defects', 'comments'
        ),
        id=project_id
    )
    
    # Get funding schedules and calculate totals
    funding_schedules = project.funding_schedules.all()
    total_funding = funding_schedules.aggregate(total=Sum('total_funding'))['total'] or 0
    
    # Get funding approvals
    funding_approvals = FundingApproval.objects.filter(projects=project)
    
    # Get all variations linked to this project
    variations = Variation.objects.filter(
        DBQ(funding_schedule__project=project) | DBQ(projects=project)
    ).distinct().select_related('funding_schedule')
    
    # Get pending (draft) variations
    pending_variations = variations.filter(status=Variation.Status.DRAFT)
    
    # Get pending changes from variations
    from apps.variations.models import VariationLandChange, VariationFundingChange, VariationScopeChange, VariationDateChange
    
    # Get all funding schedules for this project
    project_fs_ids = FundingSchedule.objects.filter(project=project).values_list('id', flat=True)
    
    # Get pending changes for these funding schedules
    pending_land_changes = VariationLandChange.objects.filter(
        funding_schedule_id__in=project_fs_ids,
        variation__status=Variation.Status.DRAFT
    ).select_related('variation', 'funding_schedule')
    
    pending_funding_changes = VariationFundingChange.objects.filter(
        funding_schedule_id__in=project_fs_ids,
        variation__status=Variation.Status.DRAFT
    ).select_related('variation', 'funding_schedule')
    
    pending_scope_changes = VariationScopeChange.objects.filter(
        funding_schedule_id__in=project_fs_ids,
        variation__status=Variation.Status.DRAFT
    ).select_related('variation', 'funding_schedule')
    
    pending_date_changes = VariationDateChange.objects.filter(
        funding_schedule_id__in=project_fs_ids,
        variation__status=Variation.Status.DRAFT
    ).select_related('variation', 'funding_schedule')
    
    # Get reports
    monthly_trackers = MonthlyTracker.objects.filter(funding_schedule__project=project)
    quarterly_reports = QuarterlyReport.objects.filter(project=project)
    stage_reports = StageReport.objects.filter(project=project)
    
    # Get addresses with works
    addresses = project.addresses.prefetch_related('works').all()
    
    # Get works with status - prefetch work type steps
    works = project.works.select_related('address', 'work_type').prefetch_related('work_type__step_templates').all()
    
    # Calculate notional vs actual costs
    notional_total = 0
    actual_total = 0
    for work in works:
        # Get notional cost (calculated from notional rates)
        notional_cost = work.calculate_notional_cost() or 0
        # Get effective cost (actual if set, otherwise estimated)
        effective_cost = work.effective_cost * work.quantity
        notional_total += notional_cost * work.quantity
        actual_total += effective_cost
    
    # Get work step templates for each work type - no longer needed, using prefetch_related in works query
    work_type_steps = {}
    
    # Get defects
    defects = project.defects.all()
    
    # Get payments (for cashflow)
    payments = Payment.objects.filter(project=project).select_related('funding_schedule').order_by('payment_type')
    
    # Calculate cashflow totals - use Python calculation instead of aggregate on property
    total_budget = total_funding
    total_paid = 0
    total_approved = 0
    for payment in payments:
        amount = payment.calculated_amount or 0
        if payment.status == Payment.Status.RELEASED:
            total_paid += amount
        if payment.status in [Payment.Status.APPROVED, Payment.Status.RELEASED]:
            total_approved += amount
    
    # Get comments visible to current user
    user_groups = set(request.user.groups.values_list('name', flat=True))
    all_comments = project.comments.select_related('author').all()
    visible_comments = []
    for comment in all_comments:
        if comment.visibility == Comment.Visibility.ALL:
            visible_comments.append(comment)
        elif request.user.is_superuser:
            visible_comments.append(comment)
        elif any('FNC' in g for g in user_groups) and comment.visibility in [Comment.Visibility.FNC_ONLY, Comment.Visibility.ALL]:
            visible_comments.append(comment)
        elif any('Council' in g for g in user_groups):
            user_council = getattr(getattr(request.user, 'profile', None), 'council', None)
            if user_council == project.council:
                if comment.visibility in [Comment.Visibility.COUNCIL_ONLY, Comment.Visibility.PROJECT_TEAM, Comment.Visibility.ALL]:
                    visible_comments.append(comment)
    
    # Check if user can edit (admin/staff/FNC users can edit all; Council users edit their projects)
    can_edit = request.user.is_superuser or request.user.is_staff or any('FNC' in g for g in user_groups) or (
        any('Council' in g for g in user_groups) and 
        getattr(getattr(request.user, 'profile', None), 'council', None) == project.council
    )
    
    # Get work types for the modal
    work_types = WorkType.objects.filter(is_active=True)
    
    context = {
        'project': project,
        'funding_schedules': funding_schedules,
        'total_funding': total_funding,
        'funding_approvals': funding_approvals,
        'variations': variations,
        'pending_variations': pending_variations,
        'pending_land_changes': pending_land_changes,
        'pending_funding_changes': pending_funding_changes,
        'pending_scope_changes': pending_scope_changes,
        'pending_date_changes': pending_date_changes,
        'monthly_trackers': monthly_trackers,
        'quarterly_reports': quarterly_reports,
        'stage_reports': stage_reports,
        'addresses': addresses,
        'works': works,
        'defects': defects,
        'payments': payments,
        'total_budget': total_budget,
        'total_paid': total_paid,
        'total_approved': total_approved,
        'notional_total': notional_total,
        'actual_total': actual_total,
        'comments': visible_comments,
        'can_edit': can_edit,
        'work_types': work_types,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_create(request):
    """Create a new project"""
    from apps.councils.models import Council
    from apps.programs.models import Program
    
    if request.method == 'POST':
        name = request.POST.get('name')
        council_id = request.POST.get('council')
        program_id = request.POST.get('program')
        financial_year = request.POST.get('financial_year')
        
        if name and council_id and program_id:
            council = Council.objects.get(id=council_id)
            program = Program.objects.get(id=program_id)
            project = Project.objects.create(
                name=name,
                council=council,
                program=program,
                financial_year=financial_year or CURRENT_FINANCIAL_YEAR
            )
            messages.success(request, f'Project "{project.name}" created.')
            return redirect('projects:project_detail', project_id=project.id)
    
    councils = Council.objects.all()
    programs = Program.objects.all()
    return render(request, 'projects/project_form.html', {
        'councils': councils,
        'programs': programs,
        'financial_year_choices': FINANCIAL_YEAR_CHOICES,
        'current_financial_year': CURRENT_FINANCIAL_YEAR,
    })


@login_required
def project_update(request, project_id):
    """Update project basic info"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project.name = request.POST.get('name', project.name)
        project.financial_year = request.POST.get('financial_year', project.financial_year)
        project.start_date = request.POST.get('start_date') or None
        project.stage1_target_date = request.POST.get('stage1_target_date') or None
        project.stage2_target_date = request.POST.get('stage2_target_date') or None
        project.stage1_sunset_date = request.POST.get('stage1_sunset_date') or None
        project.stage2_sunset_date = request.POST.get('stage2_sunset_date') or None
        project.state = request.POST.get('state', project.state)
        project.status_flag = request.POST.get('status_flag', project.status_flag)
        project.completion_date = request.POST.get('completion_date') or None
        project.warranty_end_date = request.POST.get('warranty_end_date') or None
        project.handover_checklist_link = request.POST.get('handover_checklist_link', '')
        
        funding_schedule_id = request.POST.get('funding_schedule')
        if funding_schedule_id:
            from apps.funding.models import FundingSchedule
            project.funding_schedule = FundingSchedule.objects.filter(id=funding_schedule_id).first()
        else:
            project.funding_schedule = None
        
        project.save()
        
        messages.success(request, 'Project updated successfully.')
        return redirect('projects:project_detail', project_id=project.id)
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def comment_create(request, project_id):
    """Add a comment to a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        visibility = request.POST.get('visibility', Comment.Visibility.ALL)
        
        if content:
            Comment.objects.create(
                project=project,
                author=request.user,
                content=content,
                visibility=visibility
            )
            messages.success(request, 'Comment added.')
    
    return redirect('projects:project_detail', project_id=project.id)


@login_required
def comment_delete(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(Comment, id=comment_id)
    project_id = comment.project.id
    
    # Only allow author or users who can edit to delete
    if request.user == comment.author or request.user.is_superuser:
        if request.method == 'POST':
            comment.delete()
            messages.success(request, 'Comment deleted.')
    else:
        messages.error(request, 'You cannot delete this comment.')
    
    return redirect('projects:project_detail', project_id=project_id)
