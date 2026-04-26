from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date
from apps.reports.models import (
    MonthlyTracker, MonthlyTrackerEntry, MonthlyTrackerItem, MonthlyTrackerItemGroup,
    QuarterlyReport, QuarterlyReportEntry, QuarterlyReportItem, QuarterlyReportItemGroup, QuarterlyReportAttachment,
    StageReport, StageReportItem, StageReportAttachment
)
from apps.projects.models import Project
from apps.funding.models import FundingSchedule
from apps.works.models import Work


# ============== Monthly Tracker Views ==============

@login_required
def monthly_tracker_list(request):
    """List all monthly trackers with filters"""
    year = request.GET.get('year', date.today().year)
    month = request.GET.get('month')
    
    trackers = MonthlyTracker.objects.select_related('funding_schedule__project').all()
    
    if year:
        trackers = trackers.filter(year=int(year))
    if month:
        trackers = trackers.filter(month=int(month))
    
    context = {
        'trackers': trackers,
        'selected_year': int(year),
        'selected_month': int(month) if month else None
    }
    return render(request, 'reports/monthly_tracker_list.html', context)


@login_required
def monthly_tracker_detail(request, tracker_id):
    """Monthly tracker detail view with frozen rows/columns"""
    tracker = get_object_or_404(
        MonthlyTracker.objects.prefetch_related(
            'entries__item', 'entries__work', 'funding_schedule__project__works'
        ),
        id=tracker_id
    )
    
    project = tracker.funding_schedule.project
    works = project.works.select_related('address', 'work_type').all()
    
    # Get items linked to this project's works
    items = MonthlyTrackerItem.objects.filter(
        works__project=project
    ).distinct()[:22]  # Limit to typical monthly tracker items
    
    # Build matrix: work_id -> item_id -> entry
    from collections import defaultdict
    entries = defaultdict(dict)
    for e in tracker.entries.all():
        entries[e.work_id][e.item_id] = e
    
    context = {
        'tracker': tracker,
        'project': project,
        'works': works,
        'tracker_items': items,
        'entries': dict(entries),
    }
    return render(request, 'reports/monthly_tracker_detail.html', context)


@login_required
def monthly_tracker_create(request):
    """Create a new monthly tracker for a funding schedule"""
    if request.method == 'POST':
        funding_schedule_id = request.POST.get('funding_schedule')
        year = request.POST.get('year')
        month = request.POST.get('month')
        
        funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_id)
        
        tracker, created = MonthlyTracker.objects.get_or_create(
            funding_schedule=funding_schedule,
            year=year,
            month=month,
            defaults={'status': MonthlyTracker.Status.DRAFT}
        )
        
        if created:
            messages.success(request, f'Monthly tracker created for {year}-{month}')
        else:
            messages.info(request, 'Monthly tracker already exists for this period')
        
        return redirect('reports:monthly_tracker_detail', tracker_id=tracker.id)
    
    funding_schedules = FundingSchedule.objects.select_related('project').all()
    return render(request, 'reports/monthly_tracker_create.html', {
        'funding_schedules': funding_schedules
    })


@login_required
def monthly_tracker_update_entry(request, entry_id):
    """Update a single entry in the monthly tracker"""
    if request.method == 'POST':
        entry = get_object_or_404(MonthlyTrackerEntry, id=entry_id)
        
        field_type = entry.item.field_type
        value = request.POST.get('value')
        
        if field_type in ['DATE', 'DATE_NA']:
            entry.date_value = value if value else None
        elif field_type == 'CHECKBOX':
            entry.boolean_value = value == 'on'
        elif field_type == 'TEXT':
            entry.text_value = value
        elif field_type in ['NUMBER', 'CURRENCY']:
            entry.number_value = value if value else None
        
        entry.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def monthly_tracker_submit(request, tracker_id):
    """Submit monthly tracker"""
    tracker = get_object_or_404(MonthlyTracker, id=tracker_id)
    
    if request.method == 'POST':
        tracker.status = MonthlyTracker.Status.SUBMITTED
        tracker.submitted_by = request.user
        tracker.submitted_at = timezone.now()
        tracker.save()
        messages.success(request, 'Monthly tracker submitted successfully')
    
    return redirect('reports:monthly_tracker_detail', tracker_id=tracker.id)


# ============== Quarterly Report Views ==============

@login_required
def quarterly_report_list(request):
    """List all quarterly reports"""
    reports = QuarterlyReport.objects.select_related('project').all()
    return render(request, 'reports/quarterly_report_list.html', {'reports': reports})


@login_required
def quarterly_report_detail(request, report_id):
    """Quarterly report detail view"""
    report = get_object_or_404(
        QuarterlyReport.objects.prefetch_related(
            'entries__item', 'entries__work', 'attachments', 'project__works'
        ),
        id=report_id
    )
    
    works = report.project.works.select_related('address', 'work_type').all()
    
    context = {
        'report': report,
        'works': works,
    }
    return render(request, 'reports/quarterly_report_detail.html', context)


@login_required
def quarterly_report_create(request):
    """Create quarterly report for a project"""
    if request.method == 'POST':
        project_id = request.POST.get('project')
        year = request.POST.get('year')
        quarter = request.POST.get('quarter')
        
        project = get_object_or_404(Project, id=project_id)
        
        report, created = QuarterlyReport.objects.get_or_create(
            project=project,
            year=year,
            quarter=quarter,
            defaults={'status': QuarterlyReport.Status.DRAFT}
        )
        
        if created:
            messages.success(request, f'Q{quarter} {year} report created')
        else:
            messages.info(request, 'Report already exists')
        
        return redirect('reports:quarterly_report_detail', report_id=report.id)
    
    projects = Project.objects.exclude(state=Project.State.COMPLETED).all()
    return render(request, 'reports/quarterly_report_create.html', {'projects': projects})


@login_required
def quarterly_report_upload_attachment(request, report_id):
    """Upload attachment to quarterly report"""
    if request.method == 'POST':
        report = get_object_or_404(QuarterlyReport, id=report_id)
        work_id = request.POST.get('work')
        file = request.FILES.get('file')
        
        work = get_object_or_404(Work, id=work_id)
        
        # Check limit (3 per work)
        count = report.attachments.filter(work=work).count()
        if count >= 3:
            messages.error(request, 'Maximum 3 attachments per work allowed')
            return redirect('reports:quarterly_report_detail', report_id=report.id)
        
        if file:
            QuarterlyReportAttachment.objects.create(
                report=report,
                work=work,
                file=file,
                uploaded_by=request.user
            )
            messages.success(request, 'Attachment uploaded successfully')
        
        return redirect('reports:quarterly_report_detail', report_id=report.id)
    
    return redirect('reports:quarterly_report_detail', report_id=report_id)


# ============== Stage Report Views ==============

@login_required
def stage_report_list(request):
    """List all stage reports"""
    reports = StageReport.objects.select_related('project').all()
    return render(request, 'reports/stage_report_list.html', {'reports': reports})


@login_required
def stage_report_detail(request, report_id):
    """Stage report detail with checklist"""
    report = get_object_or_404(
        StageReport.objects.prefetch_related('items__attachments'),
        id=report_id
    )
    
    return render(request, 'reports/stage_report_detail.html', {'report': report})


@login_required
def stage_report_create(request):
    """Create stage report for a project"""
    if request.method == 'POST':
        project_id = request.POST.get('project')
        stage_type = request.POST.get('stage_type')
        
        project = get_object_or_404(Project, id=project_id)
        
        report, created = StageReport.objects.get_or_create(
            project=project,
            stage_type=stage_type,
            defaults={'status': StageReport.Status.DRAFT}
        )
        
        if created:
            # Create default checklist items based on stage type
            if stage_type == StageReport.StageType.STAGE1:
                steps = [
                    'Administrative matters', 'Land description', 'Works description',
                    'Native title & cultural heritage', 'Development approval', 'Tenure',
                    'Survey', 'Subdivision', 'Leases', 'Design', 'Structural certification',
                    'Tendering', 'Contractor appointment', 'Council employees', 'Building approval',
                    'New infrastructure', 'Stage 1 Report'
                ]
            else:
                steps = [
                    'Schedule of Works', 'Works carried out', 'Quarterly Reports',
                    'Monthly Tracker', 'Practical Completion', 'Handover requirements', 'Stage 2 Report'
                ]
            
            for i, step in enumerate(steps):
                StageReportItem.objects.create(
                    report=report,
                    step_name=step,
                    step_order=i
                )
            
            messages.success(request, f'{stage_type} report created')
        else:
            messages.info(request, 'Report already exists')
        
        return redirect('reports:stage_report_detail', report_id=report.id)
    
    projects = Project.objects.all()
    return render(request, 'reports/stage_report_create.html', {'projects': projects})


@login_required
def stage_report_update_item(request, item_id):
    """Update stage report checklist item"""
    if request.method == 'POST':
        item = get_object_or_404(StageReportItem, id=item_id)
        
        item.is_completed = request.POST.get('is_completed') == 'on'
        item.notes = request.POST.get('notes', '')
        
        if item.is_completed and not item.completed_at:
            item.completed_at = timezone.now()
        elif not item.is_completed:
            item.completed_at = None
        
        item.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def stage_report_upload_attachment(request, item_id):
    """Upload evidence attachment to stage report item"""
    if request.method == 'POST':
        item = get_object_or_404(StageReportItem, id=item_id)
        file = request.FILES.get('file')
        
        if file:
            StageReportAttachment.objects.create(
                item=item,
                file=file,
                uploaded_by=request.user
            )
            messages.success(request, 'Evidence uploaded successfully')
        
        return redirect('reports:stage_report_detail', report_id=item.report.id)
    
    return redirect('reports:stage_report_detail', report_id=item.report.id)


@login_required
def stage_report_submit(request, report_id):
    """Submit stage report"""
    report = get_object_or_404(StageReport, id=report_id)
    
    if request.method == 'POST':
        report.submit(request.user)
        messages.success(request, 'Stage report submitted successfully')
    
    return redirect('reports:stage_report_detail', report_id=report.id)


@login_required
def stage_report_endorse(request, report_id):
    """Endorse stage report (Council Manager)"""
    report = get_object_or_404(StageReport, id=report_id)
    
    if request.method == 'POST':
        report.endorse(request.user)
        messages.success(request, 'Stage report endorsed')
    
    return redirect('reports:stage_report_detail', report_id=report.id)


@login_required
def stage_report_assess(request, report_id):
    """Assess stage report (FNC User)"""
    report = get_object_or_404(StageReport, id=report_id)
    
    if request.method == 'POST':
        report.assess(request.user)
        messages.success(request, 'Stage report assessed')
    
    return redirect('reports:stage_report_detail', report_id=report.id)


@login_required
def stage_report_approve(request, report_id):
    """Approve stage report (FNC Manager)"""
    report = get_object_or_404(StageReport, id=report_id)
    
    if request.method == 'POST':
        report.approve(request.user)
        messages.success(request, 'Stage report approved')
    
    return redirect('reports:stage_report_detail', report_id=report.id)


# ============== Maintenance Views ==============

@login_required
def monthly_item_groups(request):
    """List all monthly tracker item groups"""
    groups = MonthlyTrackerItemGroup.objects.all().prefetch_related('items')
    return render(request, 'maintenance/monthly_item_groups.html', {'groups': groups})


@login_required
def monthly_item_group_create(request):
    """Create a new monthly tracker item group"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if name:
            group = MonthlyTrackerItemGroup.objects.create(name=name, description=description)
            messages.success(request, f'Group "{group.name}" created successfully.')
            return redirect('reports:monthly_item_groups')
    
    return render(request, 'maintenance/monthly_item_group_form.html', {'group': None})


@login_required
def monthly_item_group_edit(request, group_id):
    """Edit a monthly tracker item group and its items"""
    group = get_object_or_404(MonthlyTrackerItemGroup, id=group_id)
    
    if request.method == 'POST':
        group.name = request.POST.get('name', group.name)
        group.description = request.POST.get('description', '')
        group.save()
        messages.success(request, f'Group "{group.name}" updated successfully.')
        return redirect('reports:monthly_item_groups')
    
    return render(request, 'maintenance/monthly_item_group_form.html', {'group': group})


@login_required
def monthly_item_group_delete(request, group_id):
    """Delete a monthly tracker item group"""
    group = get_object_or_404(MonthlyTrackerItemGroup, id=group_id)
    
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted successfully.')
        return redirect('reports:monthly_item_groups')
    
    return render(request, 'confirm_delete.html', {'object': group, 'cancel_url': 'reports:monthly_item_groups'})


@login_required
def quarterly_item_groups(request):
    """List all quarterly report item groups"""
    groups = QuarterlyReportItemGroup.objects.all().prefetch_related('items')
    return render(request, 'maintenance/quarterly_item_groups.html', {'groups': groups})


@login_required
def quarterly_item_group_create(request):
    """Create a new quarterly report item group"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if name:
            group = QuarterlyReportItemGroup.objects.create(name=name, description=description)
            messages.success(request, f'Group "{group.name}" created successfully.')
            return redirect('reports:quarterly_item_groups')
    
    return render(request, 'maintenance/quarterly_item_group_form.html', {'group': None})


@login_required
def quarterly_item_group_edit(request, group_id):
    """Edit a quarterly report item group"""
    group = get_object_or_404(QuarterlyReportItemGroup, id=group_id)
    
    if request.method == 'POST':
        group.name = request.POST.get('name', group.name)
        group.description = request.POST.get('description', '')
        group.save()
        messages.success(request, f'Group "{group.name}" updated successfully.')
        return redirect('reports:quarterly_item_groups')
    
    return render(request, 'maintenance/quarterly_item_group_form.html', {'group': group})


@login_required
def stage_templates(request):
    """List stage report templates"""
    projects = Project.objects.filter(stage_reports__isnull=False).distinct()
    return render(request, 'maintenance/stage_templates.html', {'projects': projects})
