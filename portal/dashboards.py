from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Sum, Count
from django.utils import timezone
from django.utils.dateformat import format
from django import forms
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from collections import defaultdict
import calendar
import logging

from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View
import json
from ricd.models import (
    Project, Program, Council, QuarterlyReport, MonthlyTracker,
    FundingSchedule, Address, Work, FieldVisibilitySetting, UserProfile
)
from .forms import ()


# RICD Dashboard
class RICDDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/ricd_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is in RICD groups
        if request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            return super().dispatch(request, *args, **kwargs)

        # If user is a Council user, redirect to their council dashboard
        if request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.shortcuts import redirect
            return redirect('portal:council_dashboard')

        # Otherwise, deny access
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build filter queryset
        projects_queryset = Project.objects.select_related('council', 'program', 'funding_schedule')

        # Apply filters from GET parameters
        program_filter = self.request.GET.get('program')
        council_filter = self.request.GET.get('council')
        stage_filter = self.request.GET.get('stage')

        if program_filter:
            projects_queryset = projects_queryset.filter(program_id=program_filter)
        if council_filter:
            projects_queryset = projects_queryset.filter(council_id=council_filter)
        if stage_filter:
            projects_queryset = projects_queryset.filter(state=stage_filter)

        projects = projects_queryset.all()

        # Store current filters for template use
        context['current_filters'] = {
            'program': program_filter,
            'council': council_filter,
            'stage': stage_filter,
        }

        # Enhance projects with calculated data
        enhanced_projects = []
        for project in projects:
            enhanced_project = {
                'project': project,
                'progress_percentage': self.get_project_progress(project),
                'budget_vs_spent': self.get_budget_vs_spent(project),
                'stage1_status': self.get_stage1_status(project),
                'stage2_status': self.get_stage2_status(project),
                'late_flag': project.is_late,
                'overdue_flag': project.is_overdue,
                'funding_schedule_number': project.funding_schedule.funding_schedule_number if project.funding_schedule else 'N/A',
            }
            enhanced_projects.append(enhanced_project)

        context['projects'] = enhanced_projects
        context['programs'] = Program.objects.all()
        context['councils'] = Council.objects.all()
        context['stages'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]

        return context

    def get_project_progress(self, project):
        """Calculate average progress percentage from most recent quarterly reports"""
        from django.db.models import Exists, OuterRef
        from ricd.models import Work, Address

        # Updated query to use address relationship since Work no longer has direct project FK
        latest_reports = QuarterlyReport.objects.filter(
            work__address__project=project
        ).order_by('-submission_date')
        if latest_reports.exists():
            avg_progress = latest_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
            return avg_progress or 0
        return 0

    def get_budget_vs_spent(self, project):
        """Calculate budget vs spent as 'Budget - Spent' or show remaining"""
        total_budget = 0
        total_spent = 0

        # Get total budget from funding schedule or commitments
        if project.funding_agreement and hasattr(project.funding_agreement, 'total_funding'):
            total_budget = project.funding_agreement.total_funding or 0
        elif hasattr(project.funding_schedule, 'total_funding'):
            total_budget = project.funding_schedule.total_funding or 0
        else:
            total_budget = project.commitments or 0

        # Sum total expenditures from quarterly reports
        expenditures = QuarterlyReport.objects.filter(
            work__address__project=project
        ).aggregate(
            total_spent=Sum('total_expenditure_council')
        )['total_spent'] or 0

        total_spent = expenditures
        remaining = total_budget - total_spent

        if total_budget > 0:
            return f"${remaining:,.0f} / ${total_budget:,.0f}"
        return "N/A"

    def get_stage1_status(self, project):
        """Get stage 1 report status"""
        from ricd.models import Stage1Report
        stage1_reports = Stage1Report.objects.filter(project=project).order_by('-submission_date')
        if stage1_reports.exists():
            report = stage1_reports.first()
            if report.state_accepted:
                return "Complete"
            return "Pending Acceptance"
        return "Not Submitted"

    def get_stage2_status(self, project):
        """Get stage 2 report status"""
        from ricd.models import Stage2Report
        stage2_reports = Stage2Report.objects.filter(project=project).order_by('-submission_date')
        if stage2_reports.exists():
            report = stage2_reports.first()
            if report.is_complete:
                return "Complete"
            return "In Progress"
        return "Not Submitted"


# Council Dashboard
class CouncilDashboardView(TemplateView):
    template_name = "portal/council_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter projects by logged-in user's council
        if self.request.user.is_authenticated:
            # Check if user has a profile before accessing council
            try:
                user_profile = self.request.user.profile
                user_council = user_profile.council
            except:
                user_council = None
        else:
            user_council = None

        # Add user group information to context for template use
        if self.request.user.is_authenticated:
            user_groups = [group.name for group in self.request.user.groups.all()]
            context['user_groups'] = user_groups
            context['user_is_ricd_staff'] = 'RICD Staff' in user_groups
            context['user_is_ricd_manager'] = 'RICD Manager' in user_groups
            context['user_is_council_user'] = 'Council User' in user_groups
            context['user_is_council_manager'] = 'Council Manager' in user_groups
        else:
            context['user_groups'] = []
            context['user_is_ricd_staff'] = False
            context['user_is_ricd_manager'] = False
            context['user_is_council_user'] = False
            context['user_is_council_manager'] = False

        if user_council:
            user_projects = Project.objects.filter(council=user_council).select_related('council', 'program', 'funding_schedule')
        else:
            user_projects = Project.objects.none().select_related('council', 'program', 'funding_schedule')

        # Apply search filter
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            # Search in project name, addresses, and works
            user_projects = user_projects.filter(
                Q(name__icontains=search_query) |
                Q(addresses__street__icontains=search_query) |
                Q(addresses__suburb__icontains=search_query) |
                Q(works__work_type_id__name__icontains=search_query)
            ).distinct()

        # Apply stage filter
        stage_filter = self.request.GET.get('stage')
        if stage_filter:
            user_projects = user_projects.filter(state=stage_filter)

        # Enhance projects with calculated data and related addresses
        enhanced_projects = []
        for project in user_projects.prefetch_related('addresses'):
            # Get addresses for display
            addresses = list(project.addresses.all()[:3])  # Show first 3 addresses
            address_display = ', '.join([f"{addr.street}, {addr.suburb}" for addr in addresses])
            if project.addresses.count() > 3:
                address_display += f" (+{project.addresses.count() - 3} more)"

            # Get latest monthly report through works relationship
            latest_monthly = MonthlyTracker.objects.filter(work__address__project=project).order_by('-month').first()
            # Get latest quarterly report through works relationship
            latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()

            # Calculate progress from quarterly reports through works relationship
            quarterly_reports = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date')
            progress_percentage = 0
            if quarterly_reports.exists():
                avg_progress = quarterly_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
                progress_percentage = avg_progress or 0

            enhanced_project = {
                'project': project,
                'funding_schedule_number': project.funding_schedule.funding_schedule_number if project.funding_schedule else 'N/A',
                'progress_percentage': progress_percentage,
                'is_overdue': project.is_overdue,
                'latest_monthly_report': latest_monthly,
                'latest_quarterly_report': latest_quarterly,
                'required_reports_overdue': self.get_required_reports_status(project),
                'addresses': addresses,
                'address_display': address_display or 'No addresses',
                'work_types': list(set(work.work_type_id.name for work in project.works.all() if work.work_type_id)),
                'total_addresses': project.addresses.count(),
                'total_works': project.works.count(),
            }
            enhanced_projects.append(enhanced_project)

        # Sort by project name for consistent display
        enhanced_projects.sort(key=lambda x: x['project'].name)

        context['projects'] = enhanced_projects
        # Get user council through profile
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        context['user_council'] = user_council if self.request.user.is_authenticated else None

        # Calculate summary statistics
        total_addresses = sum(project.get('total_addresses', 0) for project in enhanced_projects)
        total_works = sum(project.get('total_works', 0) for project in enhanced_projects)
        context['total_addresses'] = total_addresses
        context['total_works'] = total_works

        # Add filter options
        context['stages'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]
        context['current_stage'] = stage_filter
        context['current_search'] = search_query

        return context

    def get_required_reports_status(self, project):
        """Check if required reports are overdue - only for commenced/under construction projects"""
        from django.utils import timezone
        today = timezone.now().date()

        overdue_reports = []

        # Only require reports for projects that are commenced or under construction
        if project.state not in ['commenced', 'under_construction']:
            return overdue_reports

        # Check for monthly reports (required during construction)
        if project.state == 'under_construction':
            last_month = today.replace(day=1) - timezone.timedelta(days=1)
            latest_monthly = MonthlyTracker.objects.filter(
                work__address__project=project,
                month__year=last_month.year,
                month__month=last_month.month
            ).first()
            if not latest_monthly:
                overdue_reports.append('Monthly Report')

        # Check for quarterly reports (required for commenced and under construction projects)
        latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()
        if not latest_quarterly:
            overdue_reports.append('Quarterly Report')
        else:
            # Check if quarterly report is less than 3 months old
            months_since_last = (today - latest_quarterly.submission_date).days / 30
            if months_since_last > 3:
                overdue_reports.append('Quarterly Report')

        return overdue_reports