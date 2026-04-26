from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.contrib.auth.decorators import login_required
from apps.projects.models import Project
from apps.programs.models import Program
from apps.councils.models import Council
from apps.funding.models import FundingSchedule
from apps.reports.models import MonthlyTracker, QuarterlyReport, StageReport
from datetime import date


def get_user_permissions(request):
    """Determine user role and permissions"""
    if not request.user.is_authenticated:
        return {
            'is_fnc_user': False,
            'is_council_user': False,
            'can_edit_projects': False,
            'can_approve_reports': False,
            'user_group': None,
            'council': None,
        }
    
    user = request.user
    is_fnc_user = False
    is_council_user = False
    can_edit_projects = False
    can_approve_reports = False
    user_group = None
    council = None
    
    # Check if user is staff (FNC)
    if user.is_staff:
        is_fnc_user = True
        can_edit_projects = True
        can_approve_reports = True
        user_group = 'FNC Manager'
    
    # Check group permissions
    if hasattr(user, 'groups'):
        for group in user.groups.all():
            if 'FNC' in group.name:
                is_fnc_user = True
                can_edit_projects = True
                can_approve_reports = True
                user_group = group.name
            elif 'Council' in group.name:
                is_council_user = True
                if 'Manager' in group.name:
                    can_approve_reports = True
                    user_group = group.name
                else:
                    user_group = group.name
    
    # Get council from profile
    if hasattr(user, 'profile') and user.profile.council:
        council = user.profile.council
    
    return {
        'is_fnc_user': is_fnc_user,
        'is_council_user': is_council_user,
        'can_edit_projects': can_edit_projects,
        'can_approve_reports': can_approve_reports,
        'user_group': user_group,
        'council': council,
    }


@login_required
def dashboard_view(request):
    # Get user permissions
    perms = get_user_permissions(request)
    council = perms['council']
    
    # Get filter parameters
    council_id = request.GET.get('council')
    program_id = request.GET.get('program')
    status_filter = request.GET.get('status')
    
    # Base queryset - filter by council for council users
    projects = Project.objects.select_related('council', 'program').prefetch_related('funding_schedules')
    
    if perms['is_council_user'] and council:
        projects = projects.filter(council=council)
    elif council_id:
        projects = projects.filter(council_id=council_id)
    
    # Apply filters
    if program_id:
        projects = projects.filter(program_id=program_id)
    if status_filter:
        projects = projects.filter(status_flag=status_filter)
    
    # Calculate metrics
    total_projects = projects.count()
    
    # Status flags
    late_projects = projects.filter(status_flag=Project.StatusFlag.LATE).count()
    overdue_projects = projects.filter(status_flag=Project.StatusFlag.OVERDUE).count()
    on_track_projects = projects.filter(status_flag=Project.StatusFlag.ON_TRACK).count()
    
    # Budget metrics (total funding across all funding schedules)
    total_budget = FundingSchedule.objects.filter(
        project__in=projects
    ).aggregate(total=Sum('total_funding'))['total'] or 0
    
    # Active projects (not completed)
    active_projects = projects.exclude(
        state__in=[Project.State.COMPLETED, 'CANCELLED']
    ).count()
    
    # Get overdue reports
    today = date.today()
    # Monthly trackers overdue (14 days since month end)
    # Quarterly reports overdue
    # Stage reports that are due
    
    # Projects by state
    projects_by_state = projects.values('state').annotate(count=Count('id'))
    
    # Context for template
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'late_projects': late_projects,
        'overdue_projects': overdue_projects,
        'on_track_projects': on_track_projects,
        'total_budget': total_budget,
        'projects_by_state': projects_by_state,
        'councils': Council.objects.all(),
        'programs': Program.objects.all(),
        'selected_council': council_id,
        'selected_program': program_id,
        'selected_status': status_filter,
        # RBAC
        'is_fnc_user': perms['is_fnc_user'],
        'is_council_user': perms['is_council_user'],
        'can_edit_projects': perms['can_edit_projects'],
        'can_approve_reports': perms['can_approve_reports'],
        'user_group': perms['user_group'],
    }
    return render(request, 'dashboard/dashboard.html', context)


def cashflow_view(request):
    """Cashflow dashboard - forecast vs actual by FY"""
    from apps.payments.models import Payment
    
    # Get active projects with funding schedules
    projects = Project.objects.exclude(
        state=Project.State.COMPLETED
    ).select_related('council', 'program').prefetch_related('funding_schedules', 'payments')
    
    # Calculate forecast (based on funding schedules)
    total_forecast = FundingSchedule.objects.filter(
        project__in=projects
    ).aggregate(total=Sum('total_funding'))['total'] or 0
    
    # Calculate actual (released payments)
    actual_payments = Payment.objects.filter(
        project__in=projects,
        status=Payment.Status.RELEASED
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Remaining
    remaining = total_forecast - actual_payments
    
    # By program
    by_program = []
    for program in Program.objects.all():
        program_projects = projects.filter(program=program)
        forecast = FundingSchedule.objects.filter(project__in=program_projects).aggregate(
            total=Sum('total_funding')
        )['total'] or 0
        actual = Payment.objects.filter(
            project__in=program_projects,
            status=Payment.Status.RELEASED
        ).aggregate(total=Sum('amount'))['total'] or 0
        by_program.append({
            'program': program,
            'forecast': forecast,
            'actual': actual,
            'remaining': forecast - actual
        })
    
    context = {
        'projects': projects,
        'total_forecast': total_forecast,
        'actual_payments': actual_payments,
        'remaining': remaining,
        'by_program': by_program,
    }
    return render(request, 'dashboard/cashflow.html', context)


def aggregate_outputs_view(request):
    """Aggregate outputs by LGA, Program, Dwelling Type"""
    from apps.works.models import Work, WorkType
    
    # By Council (LGA)
    by_council = Project.objects.exclude(
        state=Project.State.COMPLETED
    ).values('council__name').annotate(
        project_count=Count('id'),
        total_budget=Sum('funding_schedules__total_funding')
    )
    
    # By Program
    by_program = Project.objects.exclude(
        state=Project.State.COMPLETED
    ).values('program__name').annotate(
        project_count=Count('id'),
        total_budget=Sum('funding_schedules__total_funding')
    )
    
    # By Work Type
    by_work_type = Work.objects.filter(
        project__state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
    ).values('work_type__name').annotate(
        total_quantity=Sum('quantity')
    )
    
    context = {
        'by_council': by_council,
        'by_program': by_program,
        'by_work_type': by_work_type,
    }
    return render(request, 'dashboard/aggregate.html', context)
