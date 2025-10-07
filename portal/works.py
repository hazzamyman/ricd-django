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
# Work CRUD Views
class WorkCreateView(LoginRequiredMixin, CreateView):
    """Create a new work for a project"""
    model = Work
    form_class = WorkForm
    template_name = "portal/work_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        user_council = getattr(request.user, 'council', None)

        if not (is_ricd or (user_council and self.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Work "{form.instance}" created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

        return context


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing work"""
    model = Work
    form_class = WorkForm
    template_name = "portal/work_form.html"

    def dispatch(self, request, *args, **kwargs):
        work = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and work.address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this work.")

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Work "{form.instance}" updated successfully!')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.object.project  # Pass project for budget validation
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

        return context


class WorkDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a work"""
    model = Work
    template_name = "portal/work_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        work = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and work.address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to delete this work.")

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        work = self.get_object()
        project = work.project
        messages.success(self.request, f'Work "{work}" has been deleted.')
        return super().form_valid(form)


# Work List View
class WorkListView(LoginRequiredMixin, ListView):
    """List all works with filtering and templating features"""
    model = Work
    template_name = "portal/work_list.html"
    context_object_name = "works"
    paginate_by = 25

    def get_queryset(self):
        queryset = Work.objects.select_related(
            'address__project__council',
            'address__project__program',
            'work_type_id',
            'output_type_id'
        )

        # Apply user-specific filtering (council users see only their works)
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        if user_council:
            queryset = queryset.filter(address__project__council=user_council)

        # Apply search/filtering
        search = self.request.GET.get('search')
        construction_filter = self.request.GET.get('construction_type')
        output_filter = self.request.GET.get('output_type')
        project_filter = self.request.GET.get('project')
        status_filter = self.request.GET.get('status')  # completed/pending/all

        if search:
            queryset = queryset.filter(
                Q(address__street__icontains=search) |
                Q(address__project__name__icontains=search) |
                Q(work_type_id__name__icontains=search) |
                Q(output_type_id__name__icontains=search)
            )
        if construction_filter:
            queryset = queryset.filter(work_type_id__code=construction_filter)
        if output_filter:
            queryset = queryset.filter(output_type_id__code=output_filter)
        if project_filter:
            queryset = queryset.filter(address__project_id=project_filter)
        if status_filter == 'completed':
            queryset = queryset.exclude(end_date__isnull=True)
        elif status_filter == 'pending':
            queryset = queryset.filter(end_date__isnull=True)

        # Allow reordering
        order_by = self.request.GET.get('order_by', '-start_date')
        if order_by in ['start_date', '-start_date', 'estimated_cost', '-estimated_cost', 'end_date', '-end_date']:
            queryset = queryset.order_by(order_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter options
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        projects = Project.objects.select_related('council', 'program')
        if user_council:
            projects = projects.filter(council=user_council)

        context.update({
            'projects': projects,
            'work_types': WorkType.objects.filter(is_active=True),
            'output_types': OutputType.objects.filter(is_active=True),
            'order_options': [
                ('-start_date', 'Recent Start First'),
                ('start_date', 'Oldest Start First'),
                ('-estimated_cost', 'Highest Cost First'),
                ('estimated_cost', 'Lowest Cost First'),
                ('-end_date', 'Recently Completed'),
                ('end_date', 'Oldest Completed'),
            ]
        })

        # Add current filters for form pre-population
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'construction_type': self.request.GET.get('construction_type', ''),
            'output_type': self.request.GET.get('output_type', ''),
            'project': self.request.GET.get('project', ''),
            'status': self.request.GET.get('status', ''),
            'order_by': self.request.GET.get('order_by', '-start_date'),
        }

        return context


# Work Step Management Views
class WorkStepListView(LoginRequiredMixin, DetailView):
    """View to list and manage work steps (stages/tasks) for a specific work"""
    model = Work
    template_name = "portal/work_step_list.html"
    context_object_name = "work"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.work_steps.order_by('order')
        return context


class WorkStepReorderView(LoginRequiredMixin, View):
    """View to reorder work steps"""

    def post(self, request, work_pk):
        work = get_object_or_404(Work, pk=work_pk)

        # Check permissions
        if not (request.user.is_staff or (
            hasattr(request.user, 'council') and
            request.user.council == work.address.project.council
        )):
            messages.error(request, "You don't have permission to modify this work.")
            return redirect('portal:work_detail', pk=work_pk)

        step_orders = request.POST.getlist('step_order[]')
        for i, step_id in enumerate(step_orders):
            try:
                step = WorkStep.objects.get(pk=step_id, work=work)
                step.order = i + 1
                step.save()
            except WorkStep.DoesNotExist:
                continue

        messages.success(request, 'Work steps reordered successfully!')
        return redirect('portal:work_step_list', work_pk=work_pk)