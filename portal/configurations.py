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


class SiteConfigurationView(LoginRequiredMixin, UpdateView):
    """View for site-wide configuration settings - RICD users only"""
    model = SiteConfiguration
    form_class = SiteConfigurationForm
    template_name = "portal/site_configuration.html"
    success_url = reverse_lazy('portal:site_configuration')

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can configure site settings.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Return the singleton instance
        return SiteConfiguration.get_instance()

    def form_valid(self, form):
        messages.success(self.request, 'Site configuration updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_config'] = self.get_object()
        return context


class WorkOutputTypeConfigView(LoginRequiredMixin, TemplateView):
    """Configuration page for managing work type and output type relationships - RICD users only"""
    template_name = "portal/work_output_type_config.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can access work/output type configuration.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all work types and output types
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        output_types = OutputType.objects.filter(is_active=True)

        context['work_types'] = work_types
        context['output_types'] = output_types

        # Create mapping for JavaScript
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[str(work_type.id)] = list(work_type.allowed_output_types.values_list('id', flat=True))

        context['work_type_mappings'] = json.dumps(work_type_mappings)

        return context

    def post(self, request, *args, **kwargs):
        """Handle drag and drop updates"""
        action = request.POST.get('action')
        work_type_id = request.POST.get('work_type_id')
        output_type_id = request.POST.get('output_type_id')

        if not work_type_id or not output_type_id:
            messages.error(request, 'Invalid request data.')
            return redirect('portal:work_output_type_config')

        try:
            work_type = WorkType.objects.get(pk=work_type_id)
            output_type = OutputType.objects.get(pk=output_type_id)

            if action == 'add':
                work_type.allowed_output_types.add(output_type)
                messages.success(request, f'Added {output_type.name} to {work_type.name}')
            elif action == 'remove':
                work_type.allowed_output_types.remove(output_type)
                messages.success(request, f'Removed {output_type.name} from {work_type.name}')
            else:
                messages.error(request, 'Invalid action specified.')

        except (WorkType.DoesNotExist, OutputType.DoesNotExist):
            messages.error(request, 'Work type or output type not found.')

        return redirect('portal:work_output_type_config')


class ProjectFieldVisibilityView(LoginRequiredMixin, TemplateView):
    """Configure field visibility settings for a specific project - RICD users only"""
    template_name = "portal/project_field_visibility.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can configure field visibility.")

        self.project = get_object_or_404(Project, pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['form'] = ProjectFieldVisibilityForm(project=self.project)
        return context

    def post(self, request, *args, **kwargs):
        form = ProjectFieldVisibilityForm(request.POST, project=self.project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Field visibility settings for project "{self.project.name}" have been updated successfully!')
            return redirect('portal:project_detail', pk=self.project.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
            return self.render_to_response({'form': form, 'project': self.project})