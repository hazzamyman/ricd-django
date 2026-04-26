from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from .models import (
    Variation, VariationType, VariationItem,
    VariationFundingChange, VariationLandChange, 
    VariationScopeChange, VariationDateChange
)
from apps.funding.models import FundingSchedule
from apps.projects.models import Project
from apps.councils.models import Council


@login_required
def variations_list(request):
    """List all variations with filters"""
    status_filter = request.GET.get('status')
    council_id = request.GET.get('council')
    
    variations = Variation.objects.select_related('funding_schedule__project').all()
    
    if status_filter:
        variations = variations.filter(status=status_filter)
    if council_id:
        variations = variations.filter(funding_schedule__project__council_id=council_id)
    
    context = {
        'variations': variations,
        'statuses': Variation.Status.choices,
        'councils': Council.objects.all(),
        'selected_status': status_filter,
        'selected_council': council_id,
    }
    return render(request, 'variations/variations_list.html', context)


@login_required
def variation_detail(request, variation_id):
    """Show detail of a variation with all items and changes"""
    variation = get_object_or_404(
        Variation.objects.select_related(
            'funding_schedule__project__council',
            'created_by'
        ).prefetch_related(
            'projects',
            'items',
            'funding_schedules__funding_schedule',
            'contact_details',
            'date_changes',
            'scope_changes',
            'land_changes',
            'funding_changes',
            'reporting_changes',
        ),
        id=variation_id
    )
    
    # Get projects for this variation
    projects = variation.projects.all()
    
    # Get all funding schedules from linked projects
    from apps.funding.models import FundingSchedule
    from apps.projects.models import Project
    
    if projects:
        project_ids = projects.values_list('id', flat=True)
        all_funding_schedules = FundingSchedule.objects.filter(
            project_id__in=project_ids
        ).select_related('project__council')
    else:
        all_funding_schedules = FundingSchedule.objects.none()
    
    context = {
        'variation': variation,
        'projects': projects,
        'all_funding_schedules': all_funding_schedules,
    }
    return render(request, 'variations/variation_detail.html', context)


@login_required
def variations_by_council(request):
    """Show variations grouped by council with counts"""
    council_id = request.GET.get('council')
    
    variations = Variation.objects.select_related('funding_schedule__project__council')
    
    if council_id:
        variations = variations.filter(funding_schedule__project__council_id=council_id)
    
    # Group by council
    by_council = variations.values(
        'funding_schedule__project__council__id',
        'funding_schedule__project__council__name'
    ).annotate(
        variation_count=Count('id'),
        executed_count=Count('id', filter=models.Q(status=Variation.Status.EXECUTED))
    ).order_by('funding_schedule__project__council__name')
    
    context = {
        'by_council': by_council,
        'councils': Council.objects.all(),
        'selected_council': council_id,
    }
    return render(request, 'variations/variations_by_council.html', context)


@login_required
def variations_by_project(request):
    """Show variation history for a specific project"""
    project_id = request.GET.get('project')
    
    variations = Variation.objects.filter(projects__isnull=False)
    
    if project_id:
        variations = variations.filter(projects__id=project_id)
    
    # Get variations with project info
    variations = variations.select_related('funding_schedule__project').prefetch_related('projects').distinct()
    
    context = {
        'variations': variations,
        'projects': Project.objects.all(),
        'selected_project': project_id,
    }
    return render(request, 'variations/variations_by_project.html', context)


@login_required
def variation_create(request):
    """Create a new variation - Step 1: Select Council"""
    import json
    from apps.funding.models import FundingSchedule
    
    councils = Council.objects.all().order_by('name')
    
    # Get all active funding schedules grouped by council
    council_funding = []
    for council in councils:
        fs_list = FundingSchedule.objects.filter(
            project__council=council,
            status='ACTIVE'
        ).select_related('project').order_by('-id')[:30]
        
        if fs_list:
            council_funding.append({
                'id': council.id,
                'name': council.name,
                'funding_schedules': [{
                    'id': fs.id,
                    'amount': str(fs.amount) if fs.amount else '0',
                    'project_name': fs.project.name if fs.project else (fs.land_project.name if fs.land_project else 'FS#' + str(fs.id)),
                    'status': fs.status,
                } for fs in fs_list]
            })
    
    council_funding_json = json.dumps(council_funding)
    variation_types = VariationType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        # This handles the FINAL submission after collecting all changes
        # But for the multi-step form, we redirect to variation_detail
        
        funding_schedule_ids = request.POST.getlist('funding_schedules')
        description = request.POST.get('description', '')
        
        # Create variation
        fs_primary = None
        if funding_schedule_ids:
            fs_primary = FundingSchedule.objects.get(id=funding_schedule_ids[0])
        
        variation = Variation.objects.create(
            funding_schedule=fs_primary,
            description=description,
            status=Variation.Status.DRAFT,
            created_by=request.user
        )
        
        # Add multiple funding schedules
        for fs_id in funding_schedule_ids:
            variation.funding_schedules.add(fs_id)
        
        # Link project from primary FS
        if fs_primary and fs_primary.project:
            variation.projects.add(fs_primary.project)
        
        # Now collect the items from form data based on options selected
        options_selected = request.POST.getlist('options')
        
        for option in options_selected:
            item = VariationItem.objects.create(
                variation=variation,
                option=option,
                description=request.POST.get(f'description_{option}', '')
            )
            
            # Option-specific processing
            if option == 'OPTION_5':  # Vary Dates
                item.stage1_target_date = request.POST.get('stage1_target_date') or None
                item.stage2_target_date = request.POST.get('stage2_target_date') or None
                item.stage1_sunset_date = request.POST.get('stage1_sunset_date') or None
                item.stage2_sunset_date = request.POST.get('stage2_sunset_date') or None
                item.save()
            elif option == 'OPTION_6':  # Vary Scope
                item.new_scope = request.POST.get('new_scope', '')
                item.save()
            elif option == 'OPTION_7':  # Vary Land
                item.land_lot = request.POST.get('land_lot', '')
                item.land_plan = request.POST.get('land_plan', '')
                item.land_title_reference = request.POST.get('land_title_reference', '')
                item.land_street_address = request.POST.get('land_street_address', '')
                item.land_annexure_ref = request.POST.get('land_annexure_ref', '')
                item.save()
            elif option == 'OPTION_8':  # Vary Funding
                from decimal import Decimal
                item.new_amount = Decimal(request.POST.get('new_amount') or '0')
                item.new_contingency = Decimal(request.POST.get('new_contingency') or '0')
                item.new_payment_split = request.POST.get('new_payment_split', '')
                item.save()
            elif option == 'OPTION_3':  # Contact Details
                import json
                item.state_contact_details = json.dumps({
                    'attention': request.POST.get('state_attention', ''),
                    'phone': request.POST.get('state_phone', ''),
                    'email': request.POST.get('state_email', ''),
                    'address': request.POST.get('state_address', ''),
                })
                item.update_council_contact = request.POST.get('update_council_contact') == 'on'
                item.council_contact_name = request.POST.get('council_contact_name', '')
                item.council_contact_phone = request.POST.get('council_contact_phone', '')
                item.council_contact_email = request.POST.get('council_contact_email', '')
                item.save()
            elif option == 'OPTION_9':  # Reporting
                item.monthly_required = request.POST.get('monthly_required') == 'on'
                item.quarterly_required = request.POST.get('quarterly_required') == 'on'
                item.stage1_required = request.POST.get('stage1_required') == 'on'
                item.stage2_required = request.POST.get('stage2_required') == 'on'
                item.reporting_notes = request.POST.get('reporting_notes', '')
                item.save()
        
        messages.success(request, 'Draft variation created. Add more items or submit.')
        return redirect('variations:variation_detail', variation_id=variation.id)
    
    # Option choices for the form
    options = VariationItem.OptionType.choices
    
    return render(request, 'variations/variation_form.html', {
        'councils': councils,
        'variation_types': variation_types,
        'council_funding_json': council_funding_json,
        'options': options,
    })


@login_required
def variation_item_create(request, variation_id):
    """Add a change item to a variation"""
    from decimal import Decimal
    from apps.payments.models import Payment
    
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Get the council from the variation's funding schedule
    council = None
    if variation.funding_schedule and variation.funding_schedule.project:
        council = variation.funding_schedule.project.council
    elif variation.funding_schedule and variation.funding_schedule.land_project:
        council = variation.funding_schedule.land_project.council
    
    if request.method == 'POST':
        change_type = request.POST.get('change_type')
        description = request.POST.get('description', '')
        
        # Create the variation item
        item = VariationItem.objects.create(
            variation=variation,
            change_type=change_type,
            description=description
        )
        
        # Handle based on change type
        if change_type == 'REMOVE_PROJECT':
            # Link to the project being removed
            project_id = request.POST.get('project')
            if project_id:
                item.project_id = project_id
                item.field_name = 'state'
                item.old_value = 'COMMENCED'
                item.new_value = 'CANCELLED'
                item.save()
                messages.success(request, 'Remove Project change added.')
            else:
                item.delete()
                messages.error(request, 'Please select a project.')
                return redirect('variations:variation_item_create', variation_id=variation.id)
        
        elif change_type == 'CHANGE_ADDRESS':
            # Link to address being changed
            address_id = request.POST.get('address')
            if address_id:
                from apps.addresses.models import Address
                address = Address.objects.get(id=address_id)
                item.address_id = address_id
                item.field_name = 'address'
                item.old_value = str(address)
                item.new_value = request.POST.get('new_street', '')
                item.save()
                messages.success(request, 'Address change added.')
            else:
                item.delete()
                messages.error(request, 'Please select an address.')
                return redirect('variations:variation_item_create', variation_id=variation.id)
        
        elif change_type == 'CHANGE_WORKS':
            # Link to work being changed
            work_id = request.POST.get('work')
            if work_id:
                from apps.works.models import Work
                work = Work.objects.get(id=work_id)
                item.work_id = work_id
                item.field_name = 'works'
                item.old_value = work.description or work.get_work_type_display()
                item.new_value = request.POST.get('new_works', '')
                item.save()
                messages.success(request, 'Works change added.')
            else:
                item.delete()
                messages.error(request, 'Please select a work item.')
                return redirect('variations:variation_item_create', variation_id=variation.id)
        
        elif change_type == 'CHANGE_FUNDING':
            # Link to funding schedule being changed
            fs_id = request.POST.get('funding_schedule')
            if fs_id:
                from apps.funding.models import FundingSchedule
                fs = FundingSchedule.objects.get(id=fs_id)
                item.funding_schedule_id = fs_id
                item.field_name = 'amount'
                item.old_value = str(fs.amount) if fs.amount else '0'
                item.new_value = request.POST.get('new_amount', '')
                item.save()
                messages.success(request, 'Funding change added.')
            else:
                item.delete()
                messages.error(request, 'Please select a funding schedule.')
                return redirect('variations:variation_item_create', variation_id=variation.id)
        
        elif change_type == 'CHANGE_PAYMENT_AMOUNT':
            # Multiple payments can be selected
            payment_ids = request.POST.getlist('payments')
            new_amount = request.POST.get('new_amount', '')
            
            if payment_ids:
                for payment_id in payment_ids:
                    payment = Payment.objects.get(id=payment_id)
                    # Create separate item for each payment
                    VariationItem.objects.create(
                        variation=variation,
                        change_type=change_type,
                        field_name='payment_amount',
                        old_value=str(payment.amount) if payment.amount else '0',
                        new_value=new_amount,
                        description=description
                    )
                messages.success(request, f'Payment change added for {len(payment_ids)} payment(s).')
            else:
                item.delete()
                messages.error(request, 'Please select at least one payment.')
                return redirect('variations:variation_item_create', variation_id=variation.id)
        
        else:
            # Generic change types - use text fields
            item.field_name = request.POST.get('field_name', '')
            item.old_value = request.POST.get('old_value', '')
            item.new_value = request.POST.get('new_value', '')
            item.save()
            messages.success(request, 'Change item added.')
        
        return redirect('variations:variation_detail', variation_id=variation.id)
    
    # Get data for forms based on council
    active_projects = []
    project_payments = []
    project_addresses = []
    project_works = []
    funding_schedules = []
    
    if council:
        # Active projects in same council
        active_projects = Project.objects.filter(
            council=council,
            state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
        ).order_by('name')
        
        # Funding schedules from the variation's project
        if variation.funding_schedule and variation.funding_schedule.project:
            proj = variation.funding_schedule.project
            project_payments = Payment.objects.filter(project=proj).order_by('created_at')
            project_addresses = proj.addresses.all()
            project_works = proj.works.all()
            funding_schedules = proj.funding_schedules.all()
        elif variation.funding_schedule and variation.funding_schedule.land_project:
            land_proj = variation.funding_schedule.land_project
            funding_schedules = land_proj.funding_schedules.all()
    
    return render(request, 'variations/variation_item_form.html', {
        'variation': variation,
        'council': council,
        'change_types': VariationItem.ChangeType.choices,
        'active_projects': active_projects,
        'project_payments': project_payments,
        'project_addresses': project_addresses,
        'project_works': project_works,
        'funding_schedules': funding_schedules,
    })


@login_required
def variation_update_status(request, variation_id):
    """Update variation status"""
    variation = get_object_or_404(Variation, id=variation_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        variation.status = new_status
        
        if new_status == Variation.Status.COUNCIL_SIGNED:
            variation.council_signed_date = request.POST.get('council_signed_date')
        elif new_status == Variation.Status.EXECUTED:
            variation.department_executed_date = request.POST.get('department_executed_date')
        
        variation.save()
        messages.success(request, f'Status updated to {variation.get_status_display()}')
        return redirect('variations:variation_detail', variation_id=variation.id)
    
    return render(request, 'variations/variation_status_form.html', {
        'variation': variation,
    })


@login_required
def variation_projects(request, variation_id):
    """Add or remove projects from a variation"""
    variation = get_object_or_404(Variation, id=variation_id)
    
    if request.method == 'POST':
        # Get selected project IDs
        selected_projects = request.POST.getlist('projects')
        
        # Clear existing and add selected
        variation.projects.clear()
        for project_id in selected_projects:
            variation.projects.add(project_id)
        
        messages.success(request, 'Projects updated for this variation.')
        return redirect('variations:variation_detail', variation_id=variation.id)
    
    # Get projects - start with those from the same funding schedule's project
    default_project = variation.funding_schedule.project
    related_projects = Project.objects.filter(council=default_project.council)
    
    context = {
        'variation': variation,
        'all_projects': related_projects,
        'selected_projects': variation.projects.values_list('id', flat=True),
    }
    return render(request, 'variations/variation_projects.html', context)


@login_required
def add_funding_change(request, variation_id):
    """Add a funding amount change to a variation"""
    variation = get_object_or_404(Variation, id=variation_id)
    
    if request.method == 'POST':
        # Check if it's a payment change or funding amount change
        funding_schedule_id = request.POST.get('funding_schedule') or request.POST.get('funding_schedule_payment')
        
        if funding_schedule_id:
            from apps.funding.models import FundingSchedule
            funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_id)
            
            # Funding amount change
            original_amount = request.POST.get('original_amount')
            new_amount = request.POST.get('new_amount')
            
            # Payment change
            payment_number = request.POST.get('payment_number')
            original_payment = request.POST.get('original_payment')
            new_payment = request.POST.get('new_payment')
            
            VariationFundingChange.objects.create(
                variation=variation,
                funding_schedule=funding_schedule,
                original_amount=original_amount if original_amount else None,
                new_amount=new_amount if new_amount else None,
                payment_number=payment_number if payment_number else None,
                original_payment=original_payment if original_payment else None,
                new_payment=new_payment if new_payment else None,
            )
            
            messages.success(request, 'Funding/payment change added.')
        else:
            # Check for other changes
            funding_schedule_land = request.POST.get('funding_schedule_land')
            funding_schedule_scope = request.POST.get('funding_schedule_scope')
            funding_schedule_date = request.POST.get('funding_schedule_date')
            
            if funding_schedule_land:
                from apps.funding.models import FundingSchedule
                funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_land)
                VariationLandChange.objects.create(
                    variation=variation,
                    funding_schedule=funding_schedule,
                    original_street_address=request.POST.get('original_street_address', ''),
                    new_street_address=request.POST.get('new_street_address', ''),
                )
                messages.success(request, 'Land change added.')
            elif funding_schedule_scope:
                from apps.funding.models import FundingSchedule
                funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_scope)
                VariationScopeChange.objects.create(
                    variation=variation,
                    funding_schedule=funding_schedule,
                    original_scope=request.POST.get('original_scope', ''),
                    new_scope=request.POST.get('new_scope', ''),
                )
                messages.success(request, 'Scope change added.')
            elif funding_schedule_date:
                from apps.funding.models import FundingSchedule
                funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_date)
                VariationDateChange.objects.create(
                    variation=variation,
                    funding_schedule=funding_schedule,
                    date_type=request.POST.get('date_type', 'STAGE1_TARGET'),
                    original_date=request.POST.get('original_date') or None,
                    new_date=request.POST.get('new_date') or None,
                )
                messages.success(request, 'Date change added.')
        
        return redirect('variations:variation_detail', variation_id=variation.id)
    
    return redirect('variations:variation_detail', variation_id=variation.id)


@login_required
def funding_change_delete(request, change_id):
    """Delete a funding change"""
    change = get_object_or_404(VariationFundingChange, id=change_id)
    variation_id = change.variation_id
    change.delete()
    messages.success(request, 'Funding change removed.')
    return redirect('variations:variation_detail', variation_id=variation_id)


@login_required
def land_change_delete(request, change_id):
    """Delete a land change"""
    change = get_object_or_404(VariationLandChange, id=change_id)
    variation_id = change.variation_id
    change.delete()
    messages.success(request, 'Land change removed.')
    return redirect('variations:variation_detail', variation_id=variation_id)


@login_required
def scope_change_delete(request, change_id):
    """Delete a scope change"""
    change = get_object_or_404(VariationScopeChange, id=change_id)
    variation_id = change.variation_id
    change.delete()
    messages.success(request, 'Scope change removed.')
    return redirect('variations:variation_detail', variation_id=variation_id)


@login_required
def date_change_delete(request, change_id):
    """Delete a date change"""
    change = get_object_or_404(VariationDateChange, id=change_id)
    variation_id = change.variation_id
    change.delete()
    messages.success(request, 'Date change removed.')
    return redirect('variations:variation_detail', variation_id=variation_id)


@login_required
def variation_update_status(request, variation_id, new_status=None):
    """Update variation status"""
    variation = get_object_or_404(Variation, id=variation_id)
    
    if new_status:
        variation.status = new_status
        if new_status == 'EXECUTED':
            variation.department_executed_date = timezone.now().date()
            execute_variation_changes(variation)
        elif new_status == 'COUNCIL_SIGNED':
            variation.council_signed_date = timezone.now().date()
        variation.save()
        messages.success(request, f'Variation status updated to {variation.get_status_display()}.')
    
    return redirect('variations:variation_detail', variation_id=variation.id)


def execute_variation_changes(variation):
    """Execute all changes in a variation and apply them to the project/funding schedule"""
    from django.core.exceptions import ObjectDoesNotExist
    
    # Get all funding schedules for linked projects
    from apps.funding.models import FundingSchedule
    from apps.projects.models import Project
    
    projects = variation.projects.all()
    if not projects and variation.funding_schedule:
        projects = [variation.funding_schedule.project]
    
    # Execute Funding Amount Changes
    for fc in variation.funding_changes.all():
        if fc.new_amount and fc.original_amount != fc.new_amount:
            try:
                fs = fc.funding_schedule
                # Store original value in notes or create variation log
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='amount',
                    old_value=str(fs.amount),
                    new_value=str(fc.new_amount),
                    field_display='Funding Amount'
                )
                fs.amount = fc.new_amount
                fs.save()
            except ObjectDoesNotExist:
                pass
    
    # Execute Payment Changes
    for fc in variation.funding_changes.all():
        if fc.payment_number and fc.new_payment and fc.original_payment != fc.new_payment:
            # Payment changes are handled via Payment model
            from apps.payments.models import Payment
            project = fc.funding_schedule.project
            payments = Payment.objects.filter(
                project=project,
                payment_number=fc.payment_number,
                funding_schedule=fc.funding_schedule
            ).order_by('-created_at')
            
            for payment in payments:
                _record_variation_log(
                    variation=variation,
                    entity='Payment',
                    entity_id=payment.id,
                    field='amount',
                    old_value=str(payment.amount),
                    new_value=str(fc.new_payment),
                    field_display=f'Payment {fc.payment_number} Amount'
                )
                payment.amount = fc.new_payment
                payment.save()
    
    # Execute Date Changes
    for dc in variation.date_changes.all():
        try:
            project = dc.funding_schedule.project
            
            old_date = None
            new_date = dc.new_date
            
            if dc.date_type == 'STAGE1_TARGET':
                old_date = project.stage1_target_date
                project.stage1_target_date = dc.new_date
            elif dc.date_type == 'STAGE2_TARGET':
                old_date = project.stage2_target_date
                project.stage2_target_date = dc.new_date
            elif dc.date_type == 'STAGE1_SUNSET':
                old_date = project.stage1_sunset_date
                project.stage1_sunset_date = dc.new_date
            elif dc.date_type == 'STAGE2_SUNSET':
                old_date = project.stage2_sunset_date
                project.stage2_sunset_date = dc.new_date
            elif dc.date_type == 'COMPLETION':
                old_date = project.completion_date
                project.completion_date = dc.new_date
            
            project.save()
            
            if old_date != new_date:
                _record_variation_log(
                    variation=variation,
                    entity='Project',
                    entity_id=project.id,
                    field=dc.date_type,
                    old_value=str(old_date) if old_date else 'None',
                    new_value=str(new_date) if new_date else 'None',
                    field_display=dc.get_date_type_display()
                )
        except ObjectDoesNotExist:
            pass
    
    # Execute Land/Address Changes
    for lc in variation.land_changes.all():
        # Get addresses for this funding schedule's project
        from apps.addresses.models import Address
        addresses = Address.objects.filter(project=lc.funding_schedule.project)
        
        # Find matching address by old street or create new one
        for address in addresses:
            if address.street == lc.original_street_address or not lc.original_street_address:
                _record_variation_log(
                    variation=variation,
                    entity='Address',
                    entity_id=address.id,
                    field='street',
                    old_value=address.street,
                    new_value=lc.new_street_address,
                    field_display='Street Address'
                )
                address.street = lc.new_street_address
                address.save()
                break
    
    # Execute Scope Changes
    for sc in variation.scope_changes.all():
        # Update works with new scope - this might need custom handling
        # For now, log the change
        from apps.works.models import Work
        works = Work.objects.filter(project=sc.funding_schedule.project)
        
        for work in works:
            _record_variation_log(
                variation=variation,
                entity='Work',
                entity_id=work.id,
                field='scope',
                old_value=work.work_type_other or str(work.work_type) if work.work_type else '',
                new_value=sc.new_scope,
                field_display='Scope of Works'
            )
            # Optionally update work_type_other with new scope
            if not work.work_type:
                work.work_type_other = sc.new_scope[:255]
                work.save()
    
    # ============== NEW: Execute VariationItem changes ==============
    for item in variation.items.all():
        if item.change_type == 'REMOVE_PROJECT' and item.project:
            # Cancel the project
            old_state = item.project.state
            item.project.state = Project.State.CANCELLED
            item.project.save()
            _record_variation_log(
                variation=variation,
                entity='Project',
                entity_id=item.project.id,
                field='state',
                old_value=old_state,
                new_value=Project.State.CANCELLED,
                field_display='Project Status'
            )
        
        elif item.change_type == 'CHANGE_ADDRESS' and item.address:
            # Update address
            old_addr = item.address.street
            item.address.street = item.new_value
            item.address.save()
            _record_variation_log(
                variation=variation,
                entity='Address',
                entity_id=item.address.id,
                field='street',
                old_value=old_addr,
                new_value=item.new_value,
                field_display='Street Address'
            )
        
        elif item.change_type == 'CHANGE_WORKS' and item.work:
            # Update work description
            old_desc = item.work.description
            item.work.description = item.new_value
            item.work.save()
            _record_variation_log(
                variation=variation,
                entity='Work',
                entity_id=item.work.id,
                field='description',
                old_value=old_desc,
                new_value=item.new_value,
                field_display='Works Description'
            )
        
        elif item.change_type == 'CHANGE_FUNDING' and item.funding_schedule:
            # Update funding amount
            from decimal import Decimal
            old_amount = item.funding_schedule.amount
            try:
                item.funding_schedule.amount = Decimal(item.new_value)
                item.funding_schedule.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=item.funding_schedule.id,
                    field='amount',
                    old_value=str(old_amount) if old_amount else '0',
                    new_value=item.new_value,
                    field_display='Funding Amount'
                )
            except:
                pass
        
        elif item.change_type == 'CHANGE_PAYMENT_AMOUNT':
            # Payment changes stored in old_value/new_value - update if payment FK exists
            # Note: Multiple items can be created for payment changes
            pass  # Already handled via VariationFundingChange model
    
    # ============== NEW: Execute Option-specific VariationItems ==============
    for item in variation.items.all():
        option = item.option
        
        # OPTION 2: Remove Funding Schedule
        if option == 'OPTION_2':
            for fs in variation.funding_schedules.all():
                old_status = fs.status
                fs.status = 'CANCELLED'
                fs.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='status',
                    old_value=old_status,
                    new_value='CANCELLED',
                    field_display='FS Status'
                )
                # Update linked projects
                for project in fs.projects.all():
                    if project.had_approved_funding_approval:
                        project.state = Project.State.FUNDED
                    else:
                        project.state = Project.State.PROGRAMMED
                    project.save()
        
        # OPTION 3: Contact Details
        elif option == 'OPTION_3':
            import json
            # Update FundingSchedule contact details
            for fs in variation.funding_schedules.all():
                old_contact = fs.contact_details or {}
                try:
                    new_contact = json.loads(item.state_contact_details) if item.state_contact_details else {}
                    fs.contact_details = new_contact
                    fs.save()
                    _record_variation_log(
                        variation=variation,
                        entity='FundingSchedule',
                        entity_id=fs.id,
                        field='contact_details',
                        old_value=str(old_contact),
                        new_value=str(new_contact),
                        field_display='State Contact'
                    )
                except:
                    pass
            
            # Update Council contact if checkbox was checked
            if item.update_council_contact and item.council:
                item.council.rcpa_contact_name = item.council_contact_name
                item.council.rcpa_contact_phone = item.council_contact_phone
                item.council.rcpa_contact_email = item.council_contact_email
                item.council.save()
        
        # OPTION 5: Dates
        elif option == 'OPTION_5':
            for fs in variation.funding_schedules.all():
                if item.stage1_target_date:
                    fs.stage1_target_date = item.stage1_target_date
                if item.stage2_target_date:
                    fs.stage2_target_date = item.stage2_target_date
                if item.stage1_sunset_date:
                    fs.stage1_sunset_date = item.stage1_sunset_date
                if item.stage2_sunset_date:
                    fs.stage2_sunset_date = item.stage2_sunset_date
                fs.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='dates',
                    old_value='Original dates',
                    new_value='Updated dates',
                    field_display='FS Target/Sunset Dates'
                )
        
        # OPTION 6: Scope
        elif option == 'OPTION_6':
            for fs in variation.funding_schedules.all():
                old_scope = fs.scope_of_works
                fs.scope_of_works = item.new_scope
                fs.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='scope_of_works',
                    old_value=old_scope or '',
                    new_value=item.new_scope,
                    field_display='Scope of Works'
                )
        
        # OPTION 7: Land
        elif option == 'OPTION_7':
            import json
            for fs in variation.funding_schedules.all():
                land_data = {
                    'lot': item.land_lot,
                    'plan': item.land_plan,
                    'title_reference': item.land_title_reference,
                    'street_address': item.land_street_address,
                    'annexure_ref': item.land_annexure_ref,
                }
                old_land = fs.land_details or {}
                fs.land_details = land_data
                fs.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='land_details',
                    old_value=str(old_land),
                    new_value=str(land_data),
                    field_display='Land Details'
                )
                # Update Address if linked
                if item.address:
                    item.address.lot = item.land_lot
                    item.address.plan = item.land_plan
                    item.address.title_reference = item.land_title_reference
                    item.address.street = item.land_street_address
                    item.address.save()
        
        # OPTION 8: Funding
        elif option == 'OPTION_8':
            for fs in variation.funding_schedules.all():
                old_amount = fs.amount
                old_contingency = fs.contingency
                if item.new_amount:
                    fs.amount = item.new_amount
                if item.new_contingency:
                    fs.contingency = item.new_contingency
                if item.new_payment_split:
                    fs.payment_split = item.new_payment_split
                fs.save()
                _record_variation_log(
                    variation=variation,
                    entity='FundingSchedule',
                    entity_id=fs.id,
                    field='amount',
                    old_value=str(old_amount),
                    new_value=str(fs.amount),
                    field_display='Funding Amount'
                )
        
        # OPTION 9: Reporting
        elif option == 'OPTION_9':
            reporting_req = {
                'monthly_required': item.monthly_required,
                'quarterly_required': item.quarterly_required,
                'stage1_required': item.stage1_required,
                'stage2_required': item.stage2_required,
                'notes': item.reporting_notes,
            }
            variation.reporting_requirements = reporting_req
            variation.save()
            
            # Could also update report templates/models here
            # But for now just save to the variation


def _record_variation_log(variation, entity, entity_id, field, old_value, new_value, field_display):
    """Record a variation change for audit trail"""
    from .models import VariationExecutionLog
    
    VariationExecutionLog.objects.create(
        variation=variation,
        entity=entity,
        entity_id=entity_id,
        field_name=field,
        old_value=old_value,
        new_value=new_value,
        field_display=field_display or field
    )


# Import needed for the queryset
from django.db import models
from django.http import JsonResponse


# ============== API ENDPOINTS ==============

@login_required
def api_active_projects(request):
    """Get active projects for a council (state=COMMENCED or UNDER_CONSTRUCTION)"""
    from apps.projects.models import Project
    
    council_id = request.GET.get('council_id')
    if not council_id:
        return JsonResponse({'error': 'council_id required'}, status=400)
    
    # Active states: COMMENCED or UNDER_CONSTRUCTION
    active_projects = Project.objects.filter(
        council_id=council_id,
        state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
    ).select_related('council', 'program').order_by('name')
    
    data = [{
        'id': p.id,
        'name': p.name,
        'state': p.state,
        'state_display': p.get_state_display(),
        'dwelling_status': p.dwelling_status,
    } for p in active_projects]
    
    return JsonResponse({'projects': data})


@login_required
def api_project_payments(request):
    """Get all payments for a project"""
    from apps.payments.models import Payment
    
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'project_id required'}, status=400)
    
    payments = Payment.objects.filter(
        project_id=project_id
    ).order_by('created_at')
    
    data = [{
        'id': p.id,
        'reference': p.reference or f'Payment #{p.id}',
        'payment_type': p.payment_type,
        'payment_type_display': p.get_payment_type_display(),
        'amount': str(p.amount) if p.amount else None,
        'calculated_amount': str(p.calculated_amount) if p.calculated_amount else None,
        'status': p.status,
        'status_display': p.get_status_display(),
    } for p in payments]
    
    return JsonResponse({'payments': data})


@login_required
def api_project_addresses(request):
    """Get all addresses for a project"""
    from apps.addresses.models import Address
    
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'project_id required'}, status=400)
    
    addresses = Address.objects.filter(project_id=project_id)
    
    data = [{
        'id': a.id,
        'street': a.street,
        'suburb': a.suburb,
        'state': a.state,
        'postcode': a.postcode,
        'full_address': str(a),
    } for a in addresses]
    
    return JsonResponse({'addresses': data})


@login_required
def api_project_works(request):
    """Get all works for a project"""
    from apps.works.models import Work
    
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'project_id required'}, status=400)
    
    works = Work.objects.filter(project_id=project_id)
    
    data = [{
        'id': w.id,
        'work_type': w.work_type,
        'work_type_display': w.get_work_type_display() if w.work_type else w.work_type_other,
        'description': w.description,
    } for w in works]
    
    return JsonResponse({'works': data})


@login_required
def api_funding_details(request):
    """Get funding schedule details"""
    from apps.funding.models import FundingSchedule
    
    fs_id = request.GET.get('funding_id')
    if not fs_id:
        return JsonResponse({'error': 'funding_id required'}, status=400)
    
    try:
        fs = FundingSchedule.objects.get(id=fs_id)
    except FundingSchedule.DoesNotExist:
        return JsonResponse({'error': 'FundingSchedule not found'}, status=404)
    
    data = {
        'id': fs.id,
        'amount': str(fs.amount) if fs.amount else None,
        'total_funding': str(fs.total_funding) if fs.total_funding else None,
    }
    
    return JsonResponse({'funding': data})
