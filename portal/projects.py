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
    Project, Program, Council, QuarterlyReport, FundingApproval, FundingSchedule, Defect,
    FieldVisibilitySetting, UserProfile, ProjectReportConfiguration, ProgramProjectAllocation
)
from .forms import (
    ProjectForm, ProjectStateForm, ProjectReportConfigurationForm, ProgramProjectAllocationForm
)
from django.forms import modelformset_factory


# Project Detail
class ProjectDetailView(DetailView):
    model = Project
    template_name = "portal/project_detail.html"
    context_object_name = "project"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only RICD Staff and RICD Managers can access this view
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view RICD project details.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funding_approvals'] = self.object.funding_approvals.all()

        # Calculate total funding from addresses/works budgets for all users
        from django.db.models import Sum
        calculated_total_funding = self.object.addresses.aggregate(
            total=Sum('budget')
        )['total'] or 0

        # For RICD users, override the stored total_funding with calculated value
        if not hasattr(self.request.user, 'council') or not self.request.user.council:
            # Temporarily override project.total_funding for template display
            self.object.calculated_total_funding = calculated_total_funding
        else:
            # For council users, still provide the calculated amount separately
            context['council_funding_amount'] = calculated_total_funding

        # Add field visibility settings for council users
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            try:
                user_profile = self.request.user.profile
                user_council = user_profile.council
                from ricd.models import get_field_visibility_settings
                context['field_visibility'] = get_field_visibility_settings(user_council, self.request.user)
            except:
                # Default to visible if profile doesn't exist
                context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}
        else:
            # For anonymous users or users without council, show all fields (though they shouldn't reach here)
            context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}

        # Add context variables to help with work display logic
        works_count = self.object.works.count()
        addresses_with_work = self.object.addresses.filter(
            work_type_id__isnull=False,
            output_type_id__isnull=False
        ).count()

        context['has_works'] = works_count > 0
        context['has_addresses_with_work'] = addresses_with_work > 0
        context['has_any_work_content'] = works_count > 0 or addresses_with_work > 0

        return context


# Council Project Detail View
class CouncilProjectDetailView(DetailView):
    model = Project
    template_name = "portal/council_project_detail.html"
    context_object_name = "project"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only Council Users and Council Managers can access this view
        if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only council users can view council project details.")

        # Check if user has permission to view this project
        project = self.get_object()

        # Council Users and Council Managers can only access their own council's projects
        # Check profile directly to avoid property issues
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if user_council and project.council == user_council:
            return super().dispatch(request, *args, **kwargs)

        # Deny access for all other cases
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to view this project.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        # Add funding agreement information
        context['funding_agreement'] = project.funding_agreement
        context['funding_schedule'] = project.funding_schedule
        context['forward_rpf'] = project.forward_rpf_agreement
        context['interim_frp'] = project.interim_fp_agreement

        # Calculate funding amount (sum of all address budgets - for council view)
        from django.db.models import Sum
        total_budget = project.addresses.aggregate(
            total=Sum('budget')
        )['total'] or 0
        context['funding_amount_less_contingency'] = total_budget

        # Get overall progress from latest quarterly reports
        from django.db.models import Avg
        latest_reports = QuarterlyReport.objects.filter(
            work__address__project=project
        ).order_by('-submission_date')[:5]  # Last 5 reports

        if latest_reports.exists():
            avg_progress = latest_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
            context['overall_progress'] = avg_progress or 0
        else:
            context['overall_progress'] = 0

        # Get defects for this project
        context['defects'] = Defect.objects.filter(work__address__project=project).select_related('work__address')

        # Add field visibility settings for council users
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            try:
                user_profile = self.request.user.profile
                user_council = user_profile.council
                from ricd.models import get_field_visibility_settings
                context['field_visibility'] = get_field_visibility_settings(user_council, self.request.user)
            except:
                # Default to visible if profile doesn't exist
                context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}
        else:
            # For anonymous users or users without council, show all fields (though they shouldn't reach here)
            context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}

        return context


# Project CRUD Views
class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects with filtering"""
    model = Project
    template_name = "portal/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        queryset = Project.objects.select_related('council', 'program', 'funding_schedule')

        # Apply user-specific filtering (council users see only their projects)
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectListView - User: {self.request.user.username}, User Council: {user_council}, Is Staff: {self.request.user.is_staff}, Groups: {[g.name for g in self.request.user.groups.all()]}")

        if user_council:
            queryset = queryset.filter(council=user_council)
            logger.info(f"DEBUG: ProjectListView - Filtering by council: {user_council.name}")

        # Apply search/filtering
        search = self.request.GET.get('search')
        program_filter = self.request.GET.get('program')
        council_filter = self.request.GET.get('council')
        state_filter = self.request.GET.get('state')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sap_project__icontains=search)
            )
        if program_filter:
            queryset = queryset.filter(program_id=program_filter)
        if council_filter:
            queryset = queryset.filter(council_id=council_filter)
            logger.info(f"DEBUG: ProjectListView - Additional council filter applied: {council_filter}")
        if state_filter:
            queryset = queryset.filter(state=state_filter)

        final_queryset = queryset.order_by('name')
        logger.info(f"DEBUG: ProjectListView - Final queryset count: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.all()
        context['councils'] = Council.objects.all()
        context['states'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project"""
    model = Project
    form_class = ProjectForm
    template_name = "portal/project_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # Check if user is in Council groups
        if self.request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            form.instance.state = 'prospective'
        messages.success(self.request, f'Project "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectForm
    template_name = "portal/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to update this project
        project = self.get_object()
        user_council = getattr(request.user, 'council', None)

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectUpdateView.dispatch - User: {request.user.username}, User Council: {user_council}, Project ID: {kwargs.get('pk')}, Project Council: {project.council}")

        # If user has a council (council user), they can only update their own council's projects
        if user_council and project.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to update this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectUpdateView.form_valid - User: {self.request.user.username}, Project: {form.instance.name}, Council: {form.instance.council}")
        messages.success(self.request, f'Project "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project"""
    model = Project
    template_name = "portal/project_confirm_delete.html"
    success_url = reverse_lazy('portal:project_list')

    def form_valid(self, form):
        project = self.get_object()
        messages.success(self.request, f'Project "{project.name}" has been deleted.')
        return super().form_valid(form)


class ProjectStateUpdateView(LoginRequiredMixin, UpdateView):
    """Update project state only"""
    model = Project
    form_class = ProjectStateForm
    template_name = "portal/project_state_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # Check if user is in RICD groups (only RICD officers can change project state)
        if not self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            messages.error(self.request, 'Only RICD officers can change project state.')
            return self.form_invalid(form)

        old_state = self.get_object().state
        response = super().form_valid(form)
        new_state = self.object.state
        if old_state != new_state:
            messages.success(self.request, f'Project state changed from {dict(Project.STATE_CHOICES)[old_state]} to {dict(Project.STATE_CHOICES)[new_state]}.')
        return response


class ProjectReportConfigurationView(LoginRequiredMixin, UpdateView):
    """Configure report items and groups for a specific project"""

    model = ProjectReportConfiguration
    form_class = ProjectReportConfigurationForm
    template_name = "portal/project_report_configuration.html"

    def dispatch(self, request, *args, **kwargs):
        # Check permissions
        project = Project.objects.get(pk=self.kwargs['pk'])
        user_council = getattr(request.user, 'council', None)

        if user_council and project.council != user_council:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to configure this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        project = Project.objects.get(pk=self.kwargs['pk'])
        obj, created = ProjectReportConfiguration.objects.get_or_create(project=project)
        return obj

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Report configuration for project "{self.object.project.name}" has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context


class ProjectAllocationsView(LoginRequiredMixin, View):
    """Manage program allocations for a project"""
    template_name = "portal/project_allocations.html"

    def dispatch(self, request, *args, **kwargs):
        # Check permissions
        project = get_object_or_404(Project, pk=self.kwargs['pk'])
        user_council = getattr(request.user, 'council', None)

        if user_council and project.council != user_council:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to manage this project.")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        AllocationFormSet = modelformset_factory(
            ProgramProjectAllocation,
            form=ProgramProjectAllocationForm,
            extra=1,
            can_delete=True
        )
        formset = AllocationFormSet(queryset=project.allocations.all())
        return render(request, self.template_name, {
            'project': project,
            'formset': formset,
            'total_allocated': sum(form.instance.amount for form in formset if form.instance.pk),
            'project_total_funding': project.total_funding,
        })

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        AllocationFormSet = modelformset_factory(
            ProgramProjectAllocation,
            form=ProgramProjectAllocationForm,
            extra=1,
            can_delete=True
        )
        formset = AllocationFormSet(request.POST, queryset=project.allocations.all())

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.project = project
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()

            # Validate total allocations don't exceed project funding
            total_allocated = sum(allocation.amount for allocation in project.allocations.all())
            if total_allocated > project.total_funding:
                messages.warning(request, f'Total allocated (${total_allocated:,.2f}) exceeds project funding (${project.total_funding:,.2f}). Please adjust allocations.')

            messages.success(request, 'Program allocations updated successfully!')
            return redirect('portal:project_allocations', pk=project.pk)
        else:
            messages.error(request, 'Please correct the errors below.')

        return render(request, self.template_name, {
            'project': project,
            'formset': formset,
            'total_allocated': 0,  # Recalculate on error
            'project_total_funding': project.total_funding,
        })