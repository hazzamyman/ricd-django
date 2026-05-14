"""
CRUD views for core domain entities using Django class-based views.
All views require login via LoginRequiredMixin.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView,
)

from apps.core.models import (
    Council, Program, Project, WorkType, FundingSchedule,
    Variation, Payment, StageReport, QuarterlyReport,
)


# ---------------------------------------------------------------------------
# Council
# ---------------------------------------------------------------------------

class CouncilListView(LoginRequiredMixin, ListView):
    model = Council
    template_name = 'councils/list.html'
    context_object_name = 'councils'
    paginate_by = 50


class CouncilCreateView(LoginRequiredMixin, CreateView):
    model = Council
    template_name = 'crud/form.html'
    fields = ['name', 'region', 'state_electorate', 'federal_electorate',
              'contact_email', 'contact_phone', 'is_registered_housing_provider',
              'rcpa_contact_name', 'rcpa_contact_phone', 'rcpa_contact_email']
    success_url = reverse_lazy('ui:council_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Council'
        ctx['back_url'] = reverse_lazy('ui:council_list')
        return ctx


class CouncilDetailView(LoginRequiredMixin, DetailView):
    model = Council
    template_name = 'councils/detail.html'
    context_object_name = 'council'


class CouncilUpdateView(LoginRequiredMixin, UpdateView):
    model = Council
    template_name = 'crud/form.html'
    fields = ['name', 'region', 'state_electorate', 'federal_electorate',
              'contact_email', 'contact_phone', 'is_registered_housing_provider',
              'rcpa_contact_name', 'rcpa_contact_phone', 'rcpa_contact_email']
    success_url = reverse_lazy('ui:council_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Council: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:council_list')
        return ctx


class CouncilDeleteView(LoginRequiredMixin, DeleteView):
    model = Council
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:council_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:council_list')
        return ctx


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

class ProgramListView(LoginRequiredMixin, ListView):
    model = Program
    template_name = 'programs/list.html'
    context_object_name = 'programs'
    paginate_by = 50


class ProgramCreateView(LoginRequiredMixin, CreateView):
    model = Program
    template_name = 'crud/form.html'
    fields = ['name', 'funding_source', 'funding_source_other', 'budget',
              'gl_code', 'business_case_reference', 'description', 'is_active']
    success_url = reverse_lazy('ui:program_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Program'
        ctx['back_url'] = reverse_lazy('ui:program_list')
        return ctx


class ProgramDetailView(LoginRequiredMixin, DetailView):
    model = Program
    template_name = 'programs/detail.html'
    context_object_name = 'program'


class ProgramUpdateView(LoginRequiredMixin, UpdateView):
    model = Program
    template_name = 'crud/form.html'
    fields = ['name', 'funding_source', 'funding_source_other', 'budget',
              'gl_code', 'business_case_reference', 'description', 'is_active']
    success_url = reverse_lazy('ui:program_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Program: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:program_list')
        return ctx


class ProgramDeleteView(LoginRequiredMixin, DeleteView):
    model = Program
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:program_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:program_list')
        return ctx


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'financial_year',
              'state', 'dwelling_status']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Project'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'financial_year',
              'state', 'dwelling_status']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Project: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


# ---------------------------------------------------------------------------
# WorkType
# ---------------------------------------------------------------------------

class WorkTypeListView(LoginRequiredMixin, ListView):
    model = WorkType
    template_name = 'work_types/list.html'
    context_object_name = 'work_types'
    paginate_by = 50


class WorkTypeCreateView(LoginRequiredMixin, CreateView):
    model = WorkType
    template_name = 'crud/form.html'
    fields = ['name', 'category', 'has_bedrooms', 'default_bedrooms', 'description', 'is_active']
    success_url = reverse_lazy('ui:work_type_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Work Type'
        ctx['back_url'] = reverse_lazy('ui:work_type_list')
        return ctx


class WorkTypeDetailView(LoginRequiredMixin, DetailView):
    model = WorkType
    template_name = 'work_types/detail.html'
    context_object_name = 'work_type'


class WorkTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkType
    template_name = 'crud/form.html'
    fields = ['name', 'category', 'has_bedrooms', 'default_bedrooms', 'description', 'is_active']
    success_url = reverse_lazy('ui:work_type_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Work Type: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:work_type_list')
        return ctx


class WorkTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkType
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:work_type_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:work_type_list')
        return ctx


# ---------------------------------------------------------------------------
# FundingSchedule
# ---------------------------------------------------------------------------

class FundingScheduleListView(LoginRequiredMixin, ListView):
    model = FundingSchedule
    template_name = 'funding_schedules/list.html'
    context_object_name = 'funding_schedules'
    paginate_by = 50


class FundingScheduleCreateView(LoginRequiredMixin, CreateView):
    model = FundingSchedule
    template_name = 'crud/form.html'
    fields = ['project', 'amount', 'contingency', 'payment_split', 'status']
    success_url = reverse_lazy('ui:funding_schedule_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Schedule'
        ctx['back_url'] = reverse_lazy('ui:funding_schedule_list')
        return ctx


class FundingScheduleDetailView(LoginRequiredMixin, DetailView):
    model = FundingSchedule
    template_name = 'funding_schedules/detail.html'
    context_object_name = 'funding_schedule'


class FundingScheduleUpdateView(LoginRequiredMixin, UpdateView):
    model = FundingSchedule
    template_name = 'crud/form.html'
    fields = ['project', 'amount', 'contingency', 'payment_split', 'status']
    success_url = reverse_lazy('ui:funding_schedule_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Funding Schedule #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:funding_schedule_list')
        return ctx


class FundingScheduleDeleteView(LoginRequiredMixin, DeleteView):
    model = FundingSchedule
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:funding_schedule_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_schedule_list')
        return ctx


# ---------------------------------------------------------------------------
# Variation
# ---------------------------------------------------------------------------

class VariationCreateView(LoginRequiredMixin, CreateView):
    model = Variation
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'variation_option', 'status', 'description',
              'council_signed_date', 'department_executed_date', 'document_link']
    success_url = reverse_lazy('ui:variations_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Variation'
        ctx['back_url'] = reverse_lazy('ui:variations_list')
        return ctx


class VariationDetailView(LoginRequiredMixin, DetailView):
    model = Variation
    template_name = 'variations/detail.html'
    context_object_name = 'variation'


class VariationUpdateView(LoginRequiredMixin, UpdateView):
    model = Variation
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'variation_option', 'status', 'description',
              'council_signed_date', 'department_executed_date', 'document_link']
    success_url = reverse_lazy('ui:variations_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Variation #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:variations_list')
        return ctx


class VariationDeleteView(LoginRequiredMixin, DeleteView):
    model = Variation
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:variations_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:variations_list')
        return ctx


# ---------------------------------------------------------------------------
# Payment  (nested under project: /ui/projects/<project_pk>/payments/)
# ---------------------------------------------------------------------------

class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'payments/list.html'
    context_object_name = 'payments'

    def get_queryset(self):
        return Payment.objects.filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = Project.objects.get(pk=self.kwargs['project_pk'])
        return ctx


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    template_name = 'crud/form.html'
    fields = ['project', 'funding_schedule', 'payment_type', 'calculation_type',
              'payment_split', 'percentage', 'amount', 'status']

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_initial(self):
        return {'project': self.kwargs['project_pk']}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Payment'
        ctx['back_url'] = reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'payments/detail.html'
    context_object_name = 'payment'


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    template_name = 'crud/form.html'
    fields = ['project', 'funding_schedule', 'payment_type', 'calculation_type',
              'payment_split', 'percentage', 'amount', 'status']

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Payment #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


# ---------------------------------------------------------------------------
# StageReport  (nested under project)
# ---------------------------------------------------------------------------

class StageReportListView(LoginRequiredMixin, ListView):
    model = StageReport
    template_name = 'stage_reports/list.html'
    context_object_name = 'stage_reports'

    def get_queryset(self):
        return StageReport.objects.filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = Project.objects.get(pk=self.kwargs['project_pk'])
        return ctx


class StageReportCreateView(LoginRequiredMixin, CreateView):
    model = StageReport
    template_name = 'crud/form.html'
    fields = ['project', 'stage_type', 'status', 'funding_schedule', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_initial(self):
        return {'project': self.kwargs['project_pk']}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Stage Report'
        ctx['back_url'] = reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class StageReportDetailView(LoginRequiredMixin, DetailView):
    model = StageReport
    template_name = 'stage_reports/detail.html'
    context_object_name = 'stage_report'


class StageReportUpdateView(LoginRequiredMixin, UpdateView):
    model = StageReport
    template_name = 'crud/form.html'
    fields = ['project', 'stage_type', 'status', 'funding_schedule', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Stage Report #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class StageReportDeleteView(LoginRequiredMixin, DeleteView):
    model = StageReport
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


# ---------------------------------------------------------------------------
# QuarterlyReport  (nested under project)
# ---------------------------------------------------------------------------

class QuarterlyReportListView(LoginRequiredMixin, ListView):
    model = QuarterlyReport
    template_name = 'quarterly_reports/list.html'
    context_object_name = 'quarterly_reports'

    def get_queryset(self):
        return QuarterlyReport.objects.filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = Project.objects.get(pk=self.kwargs['project_pk'])
        return ctx


class QuarterlyReportCreateView(LoginRequiredMixin, CreateView):
    model = QuarterlyReport
    template_name = 'crud/form.html'
    fields = ['project', 'year', 'quarter', 'status', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_initial(self):
        return {'project': self.kwargs['project_pk']}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Quarterly Report'
        ctx['back_url'] = reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class QuarterlyReportDetailView(LoginRequiredMixin, DetailView):
    model = QuarterlyReport
    template_name = 'quarterly_reports/detail.html'
    context_object_name = 'quarterly_report'


class QuarterlyReportUpdateView(LoginRequiredMixin, UpdateView):
    model = QuarterlyReport
    template_name = 'crud/form.html'
    fields = ['project', 'year', 'quarter', 'status', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Quarterly Report #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class QuarterlyReportDeleteView(LoginRequiredMixin, DeleteView):
    model = QuarterlyReport
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:quarterly_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx
