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
    Project, Program, Council, QuarterlyReport, MonthlyTracker, Stage1Report, Stage2Report,
    FundingSchedule, Address, Work, WorkStep, FundingApproval, WorkType, OutputType, ConstructionMethod, Officer,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement,
    RemoteCapitalProgramFundingAgreement, Defect, UserProfile, FieldVisibilitySetting,
    MonthlyTrackerItem, MonthlyTrackerItemGroup, QuarterlyReportItem, QuarterlyReportItemGroup,
    Stage1Step, Stage1StepGroup, Stage2Step, Stage2StepGroup, ProjectReportConfiguration,
    MonthlyTrackerEntry, QuarterlyReportItemEntry, Stage1StepCompletion, Stage2StepCompletion,
    SiteConfiguration
)
from .forms import (
    MonthlyTrackerForm, QuarterlyReportForm, Stage1ReportForm, Stage2ReportForm,
    CouncilForm, ProgramForm, ProjectForm, ProjectStateForm, AddressForm, WorkForm,
    WorkTypeForm, OutputTypeForm, ConstructionMethodForm, ForwardRemoteProgramFundingAgreementForm,
    InterimForwardProgramFundingAgreementForm, RemoteCapitalProgramFundingAgreementForm,
    UserCreationForm, OfficerForm, OfficerAssignmentForm, FundingApprovalForm,
    CustomExcelExportForm, DefectForm, CouncilUserCreationForm, CouncilUserUpdateForm,
    MonthlyTrackerItemForm, MonthlyTrackerItemGroupForm, QuarterlyReportItemForm,
    Stage1StepForm, Stage2StepForm, ProjectReportConfigurationForm,
    MonthlyTrackerEntryForm, QuarterlyReportItemEntryForm, Stage1StepCompletionForm, Stage2StepCompletionForm,
    SiteConfigurationForm
)


# Report Form Views
class MonthlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/monthly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MonthlyTrackerForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = MonthlyTrackerForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Monthly report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


class QuarterlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/quarterly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = QuarterlyReportForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = QuarterlyReportForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quarterly report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


class Stage1ReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/stage1_report.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only Council Users and Council Managers can access this view
        if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only council users can submit Stage 1 reports.")

        # Get user's council
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        # If user doesn't have a council profile, deny access
        if not user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. No council profile found.")

        # Check if user has permission to view this project (if project_pk is provided)
        project_pk = kwargs.get('project_pk')
        if project_pk:
            project = get_object_or_404(Project, pk=project_pk)
            # Ensure the project belongs to the user's council
            if project.council != user_council:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("You don't have permission to submit reports for this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_pk = kwargs.get('project_pk')
        project = None

        if project_pk:
            project = get_object_or_404(Project, pk=project_pk)

        context['form'] = Stage1ReportForm(user=self.request.user, project=project)
        context['project'] = project
        return context

    def post(self, request, *args, **kwargs):
        form = Stage1ReportForm(request.POST, request.FILES, user=self.request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stage 1 report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


class Stage2ReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/stage2_report.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only Council Users and Council Managers can access this view
        if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only council users can submit Stage 2 reports.")

        # Check if user has permission to view this project (if project_pk is provided)
        project_pk = kwargs.get('project_pk')
        if project_pk:
            project = get_object_or_404(Project, pk=project_pk)
            try:
                user_profile = request.user.profile
                user_council = user_profile.council
            except:
                user_council = None

            if user_council and project.council != user_council:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("You don't have permission to submit reports for this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_pk = kwargs.get('project_pk')
        project = None

        if project_pk:
            project = get_object_or_404(Project, pk=project_pk)

        context['form'] = Stage2ReportForm(user=self.request.user, project=project)
        context['project'] = project
        return context

    def post(self, request, *args, **kwargs):
        form = Stage2ReportForm(request.POST, request.FILES, user=self.request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stage 2 report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')


class EnhancedQuarterlyReportView(LoginRequiredMixin, TemplateView):
    """Enhanced quarterly report view with configurable items"""

    template_name = "portal/enhanced_quarterly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Get active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Get quarterly report items
        quarterly_items = QuarterlyReportItem.objects.filter(is_active=True).order_by('order')

        # Prepare data for enhanced table view
        quarterly_data = self.prepare_quarterly_data(active_projects, quarterly_items)

        context.update({
            'quarterly_data': quarterly_data,
            'quarterly_items': quarterly_items,
            'total_columns': len(quarterly_items) + 1,  # +1 for work address column
            'is_ricd': is_ricd,
            'user_council': user_council,
        })

        return context

    def prepare_quarterly_data(self, projects, quarterly_items):
        """Prepare quarterly data for enhanced table display"""
        from collections import defaultdict

        project_groups = []

        for project in projects:
            # Get all works for this project
            works = Work.objects.filter(address__project=project).select_related(
                'address', 'work_type_id', 'output_type_id'
            )

            # Prepare work data with quarterly report items
            work_data = []
            for work in works:
                work_info = {
                    'work': work,
                    'address': work.address,
                    'report_values': {}
                }

                # For each quarterly report item, determine if it's applicable and get value
                for item in quarterly_items:
                    work_info['report_values'][item.id] = self.get_quarterly_value_for_work(work, item, project)

                work_data.append(work_info)

            if work_data:  # Only add if there are works
                project_groups.append({
                    'project': project,
                    'works': work_data
                })

        return project_groups

    def get_quarterly_value_for_work(self, work, quarterly_item, project):
        """Determine the value to display for a specific work and quarterly report item"""
        # Check if this quarterly item is configured for this project
        try:
            config = project.report_configuration
            # Check if this quarterly item is in any of the project's configured groups
            applicable_groups = config.quarterly_report_groups.all()
            item_in_groups = any(
                quarterly_item in group.report_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is not applicable
            return {'value': '', 'display': '', 'applicable': False}

        # Item is applicable, check if there's actual data
        try:
            # Get the most recent quarterly report for this work
            latest_quarterly = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()
            if latest_quarterly:
                # Try to get the value from the quarterly report item entry
                try:
                    entry = QuarterlyReportItemEntry.objects.get(
                        quarterly_report=latest_quarterly,
                        report_item=quarterly_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_quarterly_value(entry.value, quarterly_item),
                        'applicable': True,
                        'has_data': True
                    }
                except QuarterlyReportItemEntry.DoesNotExist:
                    pass
        except QuarterlyReport.DoesNotExist:
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if quarterly_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False
            }

    def format_quarterly_value(self, value, quarterly_item):
        """Format the quarterly report value for display based on data type"""
        if not value:
            return ''

        if quarterly_item.data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif quarterly_item.data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif quarterly_item.data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)