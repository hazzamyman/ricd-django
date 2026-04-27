from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from apps.projects.models import Project
from apps.land_infra.models import LandTenure, DevelopmentApplication
from apps.councils.models import Council


@login_required
def land_project_list(request):
    """List all land projects (Project.project_type=LAND) with filters"""
    council_id = request.GET.get('council')
    status_filter = request.GET.get('status')
    financial_year = request.GET.get('financial_year')

    land_projects = Project.objects.filter(
        project_type=Project.Type.LAND
    ).select_related('council').order_by('-created_at')

    if council_id:
        land_projects = land_projects.filter(council_id=council_id)
    if status_filter:
        land_projects = land_projects.filter(status=status_filter)
    if financial_year:
        land_projects = land_projects.filter(financial_year=financial_year)

    from apps.councils.models import Council

    context = {
        'land_projects': land_projects,
        'statuses': Project.State.choices,
        'councils': Council.objects.order_by('name'),
        'financial_years': sorted(set(
            Project.objects.filter(project_type=Project.Type.LAND)
            .values_list('financial_year', flat=True).distinct()
        )),
    }
    return render(request, 'land_infra/land_project_list.html', context)


@login_required
def land_project_detail(request, project_id):
    """Show land project details"""
    land_project = get_object_or_404(
        Project.objects.filter(project_type=Project.Type.LAND)
        .select_related('council', 'development_application'),
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
        name = request.POST.get('name')
        council_id = request.POST.get('council')
        financial_year = request.POST.get('financial_year')

        council = get_object_or_404(Council, id=council_id)
        
        project = Project.objects.create(
            name=name,
            council=council,
            project_type=Project.Type.LAND,
            state=Project.State.PROSPECTIVE,
            financial_year=financial_year
        )
        messages.success(request, f'Land project "{project.name}" created.')
        return redirect('land_infra:land_project_detail', project_id=project.id)

    from apps.councils.models import Council
    context = {
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_project_form.html', context)


@login_required
def land_project_edit(request, project_id):
    """Edit a land project"""
    project = get_object_or_404(
        Project.objects.filter(project_type=Project.Type.LAND),
        id=project_id
    )

    if request.method == 'POST':
        project.name = request.POST.get('name')
        council_id = request.POST.get('council')
        financial_year = request.POST.get('financial_year')
        project.council_id = council_id
        project.financial_year = financial_year
        project.save()
        messages.success(request, f'Land project "{project.name}" updated.')
        return redirect('land_infra:land_project_detail', project_id=project.id)

    from apps.councils.models import Council
    context = {
        'land_project': project,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_project_form.html', context)


@login_required
def land_project_delete(request, project_id):
    """Delete a land project"""
    project = get_object_or_404(
        Project.objects.filter(project_type=Project.Type.LAND),
        id=project_id
    )

    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Land project "{project_name}" deleted.')
        return redirect('land_infra:land_project_list')

    return render(request, 'land_infra/land_project_confirm_delete.html', {'project': project})


@login_required
def land_tenure_list(request):
    """List all land tenures"""
    council_id = request.GET.get('council')

    tenures = LandTenure.objects.select_related('council').order_by('lot_number')

    if council_id:
        tenures = tenures.filter(council_id=council_id)

    context = {
        'land_tenures': tenures,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/land_tenure_list.html', context)


@login_required
def land_tenure_detail(request, tenure_id):
    """Show land tenure details"""
    tenure = get_object_or_404(
        LandTenure.objects.select_related('council'),
        id=tenure_id
    )

    context = {
        'land_tenure': tenure,
    }
    return render(request, 'land_infra/land_tenure_detail.html', context)


@login_required
def land_tenure_create(request):
    """Create a new land tenure"""
    if request.method == 'POST':
        council_id = request.POST.get('council')
        lot_number = request.POST.get('lot_number')
        plan_number = request.POST.get('plan_number')
        tenure_type = request.POST.get('tenure_type')

        tenure = LandTenure.objects.create(
            council_id=council_id,
            lot_number=lot_number,
            plan_number=plan_number,
            tenure_type=tenure_type
        )
        messages.success(request, f'Land tenure created.')
        return redirect('land_infra:land_tenure_detail', tenure_id=tenure.id)

    context = {}
    return render(request, 'land_infra/land_tenure_form.html', context)


@login_required
def land_tenure_edit(request, tenure_id):
    """Edit a land tenure"""
    tenure = get_object_or_404(LandTenure, id=tenure_id)

    if request.method == 'POST':
        tenure.council_id = request.POST.get('council')
        tenure.lot_number = request.POST.get('lot_number')
        tenure.plan_number = request.POST.get('plan_number')
        tenure.tenure_type = request.POST.get('tenure_type')
        tenure.save()
        messages.success(request, 'Land tenure updated.')
        return redirect('land_infra:land_tenure_detail', tenure_id=tenure.id)

    context = {'land_tenure': tenure}
    return render(request, 'land_infra/land_tenure_form.html', context)


@login_required
def land_tenure_delete(request, tenure_id):
    """Delete a land tenure"""
    tenure = get_object_or_404(LandTenure, id=tenure_id)

    if request.method == 'POST':
        tenure.delete()
        messages.success(request, 'Land tenure deleted.')
        return redirect('land_infra:land_tenure_list')

    return render(request, 'land_infra/land_tenure_confirm_delete.html', {'tenure': tenure})


@login_required
def development_application_list(request):
    """List all development applications"""
    council_id = request.GET.get('council')

    applications = DevelopmentApplication.objects.select_related('council').order_by('-lodgement_date')

    if council_id:
        applications = applications.filter(council_id=council_id)

    context = {
        'development_applications': applications,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'land_infra/development_application_list.html', context)


@login_required
def development_application_detail(request, application_id):
    """Show development application details"""
    application = get_object_or_404(
        DevelopmentApplication.objects.select_related('council'),
        id=application_id
    )

    context = {
        'development_application': application,
    }
    return render(request, 'land_infra/development_application_detail.html', context)


@login_required
def development_application_create(request):
    """Create a new development application"""
    if request.method == 'POST':
        council_id = request.POST.get('council')
        application_number = request.POST.get('application_number')
        application_type = request.POST.get('application_type')
        lodgement_date = request.POST.get('lodgement_date')

        application = DevelopmentApplication.objects.create(
            council_id=council_id,
            application_number=application_number,
            application_type=application_type,
            lodgement_date=lodgement_date
        )
        messages.success(request, 'Development application created.')
        return redirect('land_infra:development_application_detail', application_id=application.id)

    context = {}
    return render(request, 'land_infra/development_application_form.html', context)


@login_required
def development_application_edit(request, application_id):
    """Edit a development application"""
    application = get_object_or_404(DevelopmentApplication, id=application_id)

    if request.method == 'POST':
        application.council_id = request.POST.get('council')
        application.application_number = request.POST.get('application_number')
        application.application_type = request.POST.get('application_type')
        application.lodgement_date = request.POST.get('lodgement_date')
        application.save()
        messages.success(request, 'Development application updated.')
        return redirect('land_infra:development_application_detail', application_id=application.id)

    context = {'development_application': application}
    return render(request, 'land_infra/development_application_form.html', context)


@login_required
def development_application_delete(request, application_id):
    """Delete a development application"""
    application = get_object_or_404(DevelopmentApplication, id=application_id)

    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Development application deleted.')
        return redirect('land_infra:development_application_list')

    return render(request, 'land_infra/development_application_confirm_delete.html', {'application': application})