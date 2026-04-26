from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from apps.land_infra.models import LandProject, LandTenure, DevelopmentApplication


@login_required
def land_project_list(request):
    """List all land projects with filters"""
    council_id = request.GET.get('council')
    status_filter = request.GET.get('status')
    financial_year = request.GET.get('financial_year')

    land_projects = LandProject.objects.select_related('council').order_by('-created_at')

    if council_id:
        land_projects = land_projects.filter(council_id=council_id)
    if status_filter:
        land_projects = land_projects.filter(status=status_filter)
    if financial_year:
        land_projects = land_projects.filter(financial_year=financial_year)

    from apps.councils.models import Council

    context = {
        'land_projects': land_projects,
        'statuses': LandProject.Status.choices,
        'councils': Council.objects.order_by('name'),
        'financial_years': sorted(set(LandProject.objects.values_list('financial_year', flat=True).distinct())),
    }
    return render(request, 'land_infra/land_project_list.html', context)


@login_required
def land_project_detail(request, project_id):
    """Show land project details"""
    land_project = get_object_or_404(
        LandProject.objects.select_related('council', 'development_application'),
        id=project_id
    )

    from apps.councils.models import Council

    context = {
        'land_project': land_project,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_project_detail.html', context)


@login_required
def land_project_create(request):
    """Create a new land project"""
    if request.method == 'POST':
        from apps.land_infra.forms import LandProjectForm
        form = LandProjectForm(request.POST)
        if form.is_valid():
            land_project = form.save()
            messages.success(request, f'Land project "{land_project.name}" created successfully.')
            return redirect('land_infra:land_project_detail', project_id=land_project.id)
    else:
        from apps.land_infra.forms import LandProjectForm
        form = LandProjectForm()

    from apps.councils.models import Council

    context = {
        'form': form,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_project_form.html', context)


@login_required
def land_project_edit(request, project_id):
    """Edit an existing land project"""
    land_project = get_object_or_404(LandProject, id=project_id)

    if request.method == 'POST':
        from apps.land_infra.forms import LandProjectForm
        form = LandProjectForm(request.POST, instance=land_project)
        if form.is_valid():
            land_project = form.save()
            messages.success(request, f'Land project "{land_project.name}" updated successfully.')
            return redirect('land_infra:land_project_detail', project_id=land_project.id)
    else:
        from apps.land_infra.forms import LandProjectForm
        form = LandProjectForm(instance=land_project)

    from apps.councils.models import Council

    context = {
        'form': form,
        'land_project': land_project,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_project_form.html', context)


@login_required
def land_project_delete(request, project_id):
    """Delete a land project"""
    land_project = get_object_or_404(LandProject, id=project_id)

    if request.method == 'POST':
        name = land_project.name
        land_project.delete()
        messages.success(request, f'Land project "{name}" deleted successfully.')
        return redirect('land_infra:land_project_list')

    return render(request, 'land_infra/land_project_confirm_delete.html', {'land_project': land_project})


@login_required
def land_tenure_list(request):
    """List all land tenures with filters"""
    council_id = request.GET.get('council')
    tenure_type = request.GET.get('tenure_type')
    native_title_status = request.GET.get('native_title_status')
    is_developed = request.GET.get('is_developed')

    land_tenures = LandTenure.objects.select_related('council', 'parent_lot').order_by('council', 'lot_number', 'plan_number')

    if council_id:
        land_tenures = land_tenures.filter(council_id=council_id)
    if tenure_type:
        land_tenures = land_tenures.filter(tenure_type=tenure_type)
    if native_title_status:
        land_tenures = land_tenures.filter(native_title_status=native_title_status)
    if is_developed:
        land_tenures = land_tenures.filter(is_developed=is_developed == 'true')

    from apps.councils.models import Council

    context = {
        'land_tenures': land_tenures,
        'tenure_types': LandTenure.TenureType.choices,
        'native_title_statuses': LandTenure.NativeTitleStatus.choices,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_tenure_list.html', context)


@login_required
def land_tenure_detail(request, tenure_id):
    """Show land tenure details"""
    land_tenure = get_object_or_404(
        LandTenure.objects.select_related('council', 'parent_lot').prefetch_related('subdivided_lots', 'projects'),
        id=tenure_id
    )

    from apps.councils.models import Council

    context = {
        'land_tenure': land_tenure,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_tenure_detail.html', context)


@login_required
def land_tenure_create(request):
    """Create a new land tenure"""
    if request.method == 'POST':
        from apps.land_infra.forms import LandTenureForm
        form = LandTenureForm(request.POST)
        if form.is_valid():
            land_tenure = form.save()
            messages.success(request, f'Land tenure Lot {land_tenure.lot_number} on {land_tenure.plan_number} created successfully.')
            return redirect('land_infra:land_tenure_detail', tenure_id=land_tenure.id)
    else:
        from apps.land_infra.forms import LandTenureForm
        form = LandTenureForm()

    from apps.councils.models import Council

    context = {
        'form': form,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_tenure_form.html', context)


@login_required
def land_tenure_edit(request, tenure_id):
    """Edit an existing land tenure"""
    land_tenure = get_object_or_404(LandTenure, id=tenure_id)

    if request.method == 'POST':
        from apps.land_infra.forms import LandTenureForm
        form = LandTenureForm(request.POST, instance=land_tenure)
        if form.is_valid():
            land_tenure = form.save()
            messages.success(request, f'Land tenure Lot {land_tenure.lot_number} on {land_tenure.plan_number} updated successfully.')
            return redirect('land_infra:land_tenure_detail', tenure_id=land_tenure.id)
    else:
        from apps.land_infra.forms import LandTenureForm
        form = LandTenureForm(instance=land_tenure)

    from apps.councils.models import Council

    context = {
        'form': form,
        'land_tenure': land_tenure,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_tenure_form.html', context)


@login_required
def land_tenure_delete(request, tenure_id):
    """Delete a land tenure"""
    land_tenure = get_object_or_404(LandTenure, id=tenure_id)

    if request.method == 'POST':
        lot_info = f"Lot {land_tenure.lot_number} on {land_tenure.plan_number}"
        land_tenure.delete()
        messages.success(request, f'Land tenure {lot_info} deleted successfully.')
        return redirect('land_infra:land_tenure_list')

    return render(request, 'land_infra/land_tenure_confirm_delete.html', {'land_tenure': land_tenure})


@login_required
def development_application_list(request):
    """List all development applications with filters"""
    council_id = request.GET.get('council')
    application_type = request.GET.get('application_type')
    status_filter = request.GET.get('status')

    dev_apps = DevelopmentApplication.objects.select_related('council').prefetch_related('projects').order_by('-created_at')

    if council_id:
        dev_apps = dev_apps.filter(council_id=council_id)
    if application_type:
        dev_apps = dev_apps.filter(application_type=application_type)
    if status_filter:
        dev_apps = dev_apps.filter(status=status_filter)

    from apps.councils.models import Council

    context = {
        'development_applications': dev_apps,
        'application_types': DevelopmentApplication.ApplicationType.choices,
        'statuses': DevelopmentApplication.Status.choices,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/development_application_list.html', context)


@login_required
def development_application_detail(request, app_id):
    """Show development application details"""
    dev_app = get_object_or_404(
        DevelopmentApplication.objects.select_related('council').prefetch_related('projects'),
        id=app_id
    )

    from apps.councils.models import Council

    context = {
        'development_application': dev_app,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/development_application_detail.html', context)


@login_required
def development_application_create(request):
    """Create a new development application"""
    if request.method == 'POST':
        from apps.land_infra.forms import DevelopmentApplicationForm
        form = DevelopmentApplicationForm(request.POST)
        if form.is_valid():
            dev_app = form.save()
            messages.success(request, f'Development application "{dev_app.application_reference}" created successfully.')
            return redirect('land_infra:development_application_detail', app_id=dev_app.id)
    else:
        from apps.land_infra.forms import DevelopmentApplicationForm
        form = DevelopmentApplicationForm()

    from apps.councils.models import Council

    context = {
        'form': form,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/development_application_form.html', context)


@login_required
def development_application_edit(request, app_id):
    """Edit an existing development application"""
    dev_app = get_object_or_404(DevelopmentApplication, id=app_id)

    if request.method == 'POST':
        from apps.land_infra.forms import DevelopmentApplicationForm
        form = DevelopmentApplicationForm(request.POST, instance=dev_app)
        if form.is_valid():
            dev_app = form.save()
            messages.success(request, f'Development application "{dev_app.application_reference}" updated successfully.')
            return redirect('land_infra:development_application_detail', app_id=dev_app.id)
    else:
        from apps.land_infra.forms import DevelopmentApplicationForm
        form = DevelopmentApplicationForm(instance=dev_app)

    from apps.councils.models import Council

    context = {
        'form': form,
        'development_application': dev_app,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/development_application_form.html', context)


@login_required
def development_application_delete(request, app_id):
    """Delete a development application"""
    dev_app = get_object_or_404(DevelopmentApplication, id=app_id)

    if request.method == 'POST':
        ref = dev_app.application_reference
        dev_app.delete()
        messages.success(request, f'Development application "{ref}" deleted successfully.')
        return redirect('land_infra:development_application_list')

    return render(request, 'land_infra/development_application_confirm_delete.html', {'development_application': dev_app})