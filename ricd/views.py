from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Council, Project, Work, Address, MonthlyReport, CouncilQuarterlyReport
from datetime import datetime, date


def monthly_report_form(request, council_id, period):
    is_authenticated = request.user.is_authenticated
    is_ricd = is_authenticated and (getattr(request.user, 'user_type', '') == 'ricd' or request.user.is_staff)
    council = get_object_or_404(Council, id=council_id)
    try:
        period_date = datetime.strptime(period, '%Y-%m').date().replace(day=1)
    except ValueError:
        # Invalid period format
        return render(request, 'error.html', {'message': 'Invalid period format. Use YYYY-MM.'})

    # Get or create the MonthlyReport
    monthly_report, created = MonthlyReport.objects.get_or_create(
        council=council,
        period=period_date
    )

    # Load all active Projects for that council (only commenced and under construction)
    active_projects = council.projects.filter(state__in=[
        'commenced', 'under_construction'
    ]).prefetch_related('addresses', 'works')

    # Prepare data for the table: list of (address, work) tuples or something
    report_data = []
    for project in active_projects:
        for address in project.addresses.all():
            # For each address, list the works on that address
            works = project.works.filter(address_line__icontains=address.street if address.street else '')
            for work in works:
                report_data.append({
                    'project': project,
                    'address': address,
                    'work_type': work.work_type,
                    'output': work.output_type,
                    'progress': None,  # Will be input in form
                    'notes': None,  # Will be in form
                })

    if request.method == 'POST':

        monthly_report.council_comments = request.POST.get('council_comments', '')

        monthly_report.save()

    context = {
        'council': council,
        'period': period,
        'monthly_report': monthly_report,
        'report_data': report_data,
        'is_ricd': is_ricd,
    }
    return render(request, 'reports/monthly_report_form.html', context)


def quarterly_report_form(request, council_id, period):
    is_authenticated = request.user.is_authenticated
    is_ricd = is_authenticated and (getattr(request.user, 'user_type', '') == 'ricd' or request.user.is_staff)
    council = get_object_or_404(Council, id=council_id)
    try:
        # Assume period is like '2025-Q1'
        year, quarter = period.split('-')
        quarter_num = int(quarter[1])
        month = (quarter_num - 1) * 3 + 1
        period_date = date(int(year), month, 1)
    except:
        return render(request, 'error.html', {'message': 'Invalid period format. Use YYYY-Q1, etc.'})

    # Get or create the CouncilQuarterlyReport
    quarterly_report, created = CouncilQuarterlyReport.objects.get_or_create(
        council=council,
        period=period_date
    )

    # Same as above for active_projects and report_data
    active_projects = council.projects.filter(state__in=[
        'commenced', 'under_construction'
    ]).prefetch_related('addresses', 'works')

    report_data = []
    for project in active_projects:
        for address in project.addresses.all():
            works = project.works.filter(address_line__icontains=address.street if address.street else '')
            for work in works:
                report_data.append({
                    'project': project,
                    'address': address,
                    'work_type': work.work_type,
                    'output': work.output_type,
                    'progress': None,
                    'notes': None,
                })

    if request.method == 'POST':

        quarterly_report.council_comments = request.POST.get('council_comments', '')

        quarterly_report.save()

    context = {
        'council': council,
        'period': period,
        'quarterly_report': quarterly_report,
        'report_data': report_data,
        'is_ricd': is_ricd,
    }
    return render(request, 'reports/quarterly_report_form.html', context)


def ricd_review_report(request, report_id):
    # Assume report_id can be for MonthlyReport or CouncilQuarterlyReport
    # Would need to distinguish, perhaps by prefix or query
    # For simplicity, assume separate views or check both
    try:
        report = get_object_or_404(MonthlyReport, id=report_id)
        report_type = 'monthly'
    except:
        report = get_object_or_404(CouncilQuarterlyReport, id=report_id)
        report_type = 'quarterly'

    if request.method == 'POST':
        status = request.POST.get('ricd_status')
        comments = request.POST.get('ricd_comments')
        report.ricd_status = status
        report.ricd_comments = comments
        report.save()
        return HttpResponseRedirect(reverse('ricd_dashboard'))  # Assume reverse to dashboard

    context = {
        'report': report,
        'report_type': report_type,
    }
    return render(request, 'reports/ricd_review_report.html', context)
