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


# Address CRUD Views
class AddressCreateView(LoginRequiredMixin, CreateView):
    """Create a new address for a project"""
    model = Address
    form_class = AddressForm
    template_name = "portal/address_form.html"

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
        kwargs['instance'] = Address(project=self.project)
        kwargs['project'] = self.project  # Pass project for budget validation
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.project.pk})

    def form_valid(self, form):
        form.instance.project = self.project
        messages.success(self.request, f'Address "{form.instance}" created successfully!')
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


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing address"""
    model = Address
    form_class = AddressForm
    template_name = "portal/address_form.html"

    def dispatch(self, request, *args, **kwargs):
        address = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this address.")

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Address "{form.instance}" updated successfully!')
        return super().form_valid(form)

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


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an address"""
    model = Address
    template_name = "portal/address_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        address = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to delete this address.")

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        address = self.get_object()
        project = address.project
        messages.success(self.request, f'Address "{address}" has been deleted.')
        return super().form_valid(form)