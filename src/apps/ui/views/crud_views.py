"""
CRUD views for core domain entities using Django class-based views.
All views require login via LoginRequiredMixin.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView, View,
)

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from django.utils import timezone

from apps.core.models import (
    Approval, Address, BriefFinancialApproval, Council, DevelopmentApplication, LandTenure,
    PaymentRule, Program, Project, Work, WorkType, FundingSchedule,
    Variation, VariationItem, Payment, StageReport, QuarterlyReport,
    FundingAgreement, FundingNotice, ExpenseClaim, WorkFunding,
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


# ---------------------------------------------------------------------------
# FundingAgreement
# ---------------------------------------------------------------------------

class FundingAgreementListView(LoginRequiredMixin, ListView):
    model = FundingAgreement
    template_name = 'funding_agreements/list.html'
    context_object_name = 'agreements'
    paginate_by = 50

    def get_queryset(self):
        return FundingAgreement.objects.select_related('council').order_by('-created_at')


class FundingAgreementCreateView(LoginRequiredMixin, CreateView):
    model = FundingAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'name', 'execution_date', 'status', 'document_uri', 'notes']
    success_url = reverse_lazy('ui:funding_agreement_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Agreement'
        ctx['back_url'] = reverse_lazy('ui:funding_agreement_list')
        return ctx


class FundingAgreementDetailView(LoginRequiredMixin, DetailView):
    model = FundingAgreement
    template_name = 'funding_agreements/detail.html'
    context_object_name = 'agreement'

    def get_queryset(self):
        return FundingAgreement.objects.select_related('council')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schedules'] = self.object.schedules.select_related('payment_rule').order_by('schedule_number')
        return ctx


class FundingAgreementUpdateView(LoginRequiredMixin, UpdateView):
    model = FundingAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'name', 'execution_date', 'status', 'document_uri', 'notes']
    success_url = reverse_lazy('ui:funding_agreement_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Agreement: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_agreement_list')
        return ctx


class FundingAgreementDeleteView(LoginRequiredMixin, DeleteView):
    model = FundingAgreement
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:funding_agreement_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_agreement_list')
        return ctx


# ---------------------------------------------------------------------------
# FundingNotice
# ---------------------------------------------------------------------------

class FundingNoticeListView(LoginRequiredMixin, ListView):
    model = FundingNotice
    template_name = 'funding_notices/list.html'
    context_object_name = 'notices'
    paginate_by = 50

    def get_queryset(self):
        return FundingNotice.objects.select_related('project').order_by('-issued_date')


class FundingNoticeCreateView(LoginRequiredMixin, CreateView):
    model = FundingNotice
    template_name = 'crud/form.html'
    fields = ['project', 'capped_amount', 'issued_date', 'notes']
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Notice'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeDetailView(LoginRequiredMixin, DetailView):
    model = FundingNotice
    template_name = 'funding_notices/detail.html'
    context_object_name = 'notice'

    def get_queryset(self):
        return FundingNotice.objects.select_related('project')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['claims'] = self.object.claims.select_related('approved_by').order_by('-date_submitted')
        return ctx


class FundingNoticeUpdateView(LoginRequiredMixin, UpdateView):
    model = FundingNotice
    template_name = 'crud/form.html'
    fields = ['project', 'capped_amount', 'issued_date', 'notes']
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Funding Notice — {self.object.project.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeDeleteView(LoginRequiredMixin, DeleteView):
    model = FundingNotice
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeCloseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notice = get_object_or_404(FundingNotice, pk=pk)
        notice.status = FundingNotice.Status.CLOSED
        notice.save()
        messages.success(request, 'Funding notice closed.')
        return redirect('ui:funding_notice_detail', pk=pk)


# ---------------------------------------------------------------------------
# ExpenseClaim  (nested under FundingNotice)
# ---------------------------------------------------------------------------

class ExpenseClaimCreateView(LoginRequiredMixin, CreateView):
    model = ExpenseClaim
    template_name = 'crud/form.html'
    fields = ['amount', 'date_submitted', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.kwargs['notice_pk']})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-populate so ExpenseClaim.clean() can access self.funding_notice during validation
        kwargs['instance'] = ExpenseClaim(funding_notice_id=self.kwargs['notice_pk'])
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        notice = get_object_or_404(FundingNotice, pk=self.kwargs['notice_pk'])
        ctx['title'] = f'Add Expense Claim — {notice.project.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.kwargs['notice_pk']})
        return ctx


class ExpenseClaimUpdateView(LoginRequiredMixin, UpdateView):
    model = ExpenseClaim
    template_name = 'crud/form.html'
    fields = ['amount', 'date_submitted', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Expense Claim #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})
        return ctx


class ExpenseClaimDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpenseClaim
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})
        return ctx


class ExpenseClaimApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from django.utils import timezone
        claim = get_object_or_404(ExpenseClaim, pk=pk)
        notice = claim.funding_notice
        # Cap enforcement
        approved_total = notice.approved_claims_total
        if approved_total + claim.amount > notice.capped_amount:
            remaining = notice.capped_amount - approved_total
            messages.error(
                request,
                f'Cannot approve: claim ${claim.amount:,.2f} exceeds remaining cap '
                f'${remaining:,.2f}.'
            )
            return redirect('ui:funding_notice_detail', pk=notice.pk)
        claim.status = ExpenseClaim.Status.APPROVED
        claim.approved_by = request.user
        claim.approved_date = timezone.now().date()
        claim.save()
        if notice.is_exhausted:
            notice.status = FundingNotice.Status.CLOSED
            notice.save()
            messages.success(request, 'Claim approved. Notice cap exhausted — notice closed.')
        else:
            messages.success(request, f'Claim approved. ${notice.remaining:,.2f} remaining.')
        return redirect('ui:funding_notice_detail', pk=notice.pk)


class ExpenseClaimRejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        claim = get_object_or_404(ExpenseClaim, pk=pk)
        notice_pk = claim.funding_notice_id
        claim.status = ExpenseClaim.Status.REJECTED
        claim.save()
        messages.info(request, 'Claim rejected.')
        return redirect('ui:funding_notice_detail', pk=notice_pk)


# ---------------------------------------------------------------------------
# BriefFinancialApproval  (nested under project)
# ---------------------------------------------------------------------------

class BriefFinancialApprovalListView(LoginRequiredMixin, ListView):
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/list.html'
    context_object_name = 'approvals'

    def get_queryset(self):
        return BriefFinancialApproval.objects.filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class BriefFinancialApprovalCreateView(LoginRequiredMixin, CreateView):
    model = BriefFinancialApproval
    template_name = 'crud/form.html'
    fields = ['funding_amount', 'contingency_amount', 'delegate_level', 'mincor_reference', 'comments']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = BriefFinancialApproval(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Brief Financial Approval'
        ctx['back_url'] = reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class BriefFinancialApprovalDetailView(LoginRequiredMixin, DetailView):
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/detail.html'
    context_object_name = 'bfa'


class BriefFinancialApprovalUpdateView(LoginRequiredMixin, UpdateView):
    model = BriefFinancialApproval
    template_name = 'crud/form.html'
    fields = ['funding_amount', 'contingency_amount', 'delegate_level', 'mincor_reference', 'comments']

    def get_success_url(self):
        return reverse_lazy('ui:bfa_detail', kwargs={
            'project_pk': self.kwargs['project_pk'],
            'pk': self.object.pk,
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Brief Financial Approval #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:bfa_detail', kwargs={
            'project_pk': self.kwargs['project_pk'],
            'pk': self.object.pk,
        })
        return ctx


class BriefFinancialApprovalDeleteView(LoginRequiredMixin, DeleteView):
    model = BriefFinancialApproval
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class BriefFinancialApprovalApproveView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        bfa = get_object_or_404(BriefFinancialApproval, pk=pk, project_id=project_pk)
        if bfa.status != BriefFinancialApproval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be approved.')
            return redirect('ui:bfa_detail', project_pk=project_pk, pk=pk)
        bfa.status = BriefFinancialApproval.Status.APPROVED
        bfa.approved_by = request.user
        bfa.approved_at = timezone.now()
        bfa.save()
        messages.success(request, 'Brief Financial Approval approved.')
        return redirect('ui:bfa_detail', project_pk=project_pk, pk=pk)


class BriefFinancialApprovalRejectView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        bfa = get_object_or_404(BriefFinancialApproval, pk=pk, project_id=project_pk)
        if bfa.status != BriefFinancialApproval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be rejected.')
            return redirect('ui:bfa_detail', project_pk=project_pk, pk=pk)
        bfa.status = BriefFinancialApproval.Status.REJECTED
        bfa.save()
        messages.success(request, 'Brief Financial Approval rejected.')
        return redirect('ui:bfa_detail', project_pk=project_pk, pk=pk)


# ---------------------------------------------------------------------------
# PaymentRule (issue #19 — read-only; admin-create only)
# ---------------------------------------------------------------------------

class PaymentRuleListView(LoginRequiredMixin, ListView):
    model = PaymentRule
    template_name = 'payment_rules/list.html'
    context_object_name = 'payment_rules'
    paginate_by = 50

    def get_queryset(self):
        return PaymentRule.objects.order_by('name', '-version')


class PaymentRuleDetailView(LoginRequiredMixin, DetailView):
    model = PaymentRule
    template_name = 'payment_rules/detail.html'
    context_object_name = 'payment_rule'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rule = self.object
        ctx['schedule_count'] = FundingSchedule.objects.filter(payment_rule=rule).count()
        milestones = []
        if rule.rule_type == PaymentRule.RuleType.SPLIT:
            milestones = rule.config_json.get('milestones', [])
        ctx['milestones'] = milestones
        return ctx


# ---------------------------------------------------------------------------
# Approval (issue #15 — system-generated; approve/reject from UI)
# ---------------------------------------------------------------------------

class ApprovalListView(LoginRequiredMixin, ListView):
    model = Approval
    template_name = 'approvals/list.html'
    context_object_name = 'approvals'
    paginate_by = 50

    def get_queryset(self):
        qs = Approval.objects.select_related('approved_by').order_by('-created_at')
        status = self.request.GET.get('status', '')
        approval_type = self.request.GET.get('type', '')
        if status:
            qs = qs.filter(status=status)
        if approval_type:
            qs = qs.filter(approval_type=approval_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['approval_types'] = Approval.ApprovalType.choices
        ctx['status_choices'] = Approval.Status.choices
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class ApprovalDetailView(LoginRequiredMixin, DetailView):
    model = Approval
    template_name = 'approvals/detail.html'
    context_object_name = 'approval'


class ApprovalApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        approval = get_object_or_404(Approval, pk=pk)
        if approval.status != Approval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be approved.')
            return redirect('ui:approval_detail', pk=pk)
        approval.status = Approval.Status.APPROVED
        approval.approved_by = request.user
        approval.approved_at = timezone.now()
        approval.save()
        messages.success(request, 'Approval granted.')
        return redirect('ui:approval_detail', pk=pk)


class ApprovalRejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        approval = get_object_or_404(Approval, pk=pk)
        if approval.status != Approval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be rejected.')
            return redirect('ui:approval_detail', pk=pk)
        approval.status = Approval.Status.REJECTED
        approval.save()
        messages.success(request, 'Approval rejected.')
        return redirect('ui:approval_detail', pk=pk)


# ---------------------------------------------------------------------------
# Work (issue #18 — nested under project)
# ---------------------------------------------------------------------------

class WorkListView(LoginRequiredMixin, ListView):
    model = Work
    template_name = 'works/list.html'
    context_object_name = 'works'

    def get_queryset(self):
        return Work.objects.filter(
            project_id=self.kwargs['project_pk']
        ).select_related('work_type', 'address').order_by('created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class WorkCreateView(LoginRequiredMixin, CreateView):
    model = Work
    template_name = 'crud/form.html'
    fields = ['work_type', 'work_type_other', 'bedrooms', 'quantity',
              'estimated_cost', 'status', 'is_notional_cost', 'actual_cost', 'address']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get('instance') is None:
            kwargs['instance'] = Work(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:work_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Work Item'
        ctx['back_url'] = reverse_lazy('ui:work_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class WorkDetailView(LoginRequiredMixin, DetailView):
    model = Work
    template_name = 'works/detail.html'
    context_object_name = 'work'


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    model = Work
    template_name = 'crud/form.html'
    fields = ['work_type', 'work_type_other', 'bedrooms', 'quantity',
              'estimated_cost', 'status', 'is_notional_cost', 'actual_cost', 'address']

    def get_success_url(self):
        return reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Work: {self.object}'
        ctx['back_url'] = reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})
        return ctx


class WorkDeleteView(LoginRequiredMixin, DeleteView):
    model = Work
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})
        return ctx


# ---------------------------------------------------------------------------
# Address (issue #18 — nested under project)
# ---------------------------------------------------------------------------

class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = 'addresses/list.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return Address.objects.filter(
            project_id=self.kwargs['project_pk']
        ).select_related('suburb').order_by('street')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    template_name = 'crud/form.html'
    fields = ['street', 'suburb', 'lot', 'plan', 'residence_plc_ref']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get('instance') is None:
            kwargs['instance'] = Address(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:address_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Address'
        ctx['back_url'] = reverse_lazy('ui:address_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class AddressDetailView(LoginRequiredMixin, DetailView):
    model = Address
    template_name = 'addresses/detail.html'
    context_object_name = 'address'


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    template_name = 'crud/form.html'
    fields = ['street', 'suburb', 'lot', 'plan', 'residence_plc_ref']

    def get_success_url(self):
        return reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Address: {self.object}'
        ctx['back_url'] = reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id})
        return ctx


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = Address
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id})
        return ctx


# ---------------------------------------------------------------------------
# FundingSchedule lifecycle actions (issue #21)
# DRAFT → READY_FOR_EXECUTION → EXECUTED → ACTIVE → COMPLETED/SUPERSEDED/CANCELLED
# ---------------------------------------------------------------------------

class FundingScheduleMarkReadyView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status != FundingSchedule.Status.DRAFT:
            messages.error(request, 'Only draft schedules can be marked ready.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.READY_FOR_EXECUTION
        fs.save()
        messages.success(request, 'Funding schedule marked ready for execution.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status != FundingSchedule.Status.ACTIVE:
            messages.error(request, 'Only active schedules can be completed.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.COMPLETED
        fs.save()
        messages.success(request, 'Funding schedule completed.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleSupersededView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status in (FundingSchedule.Status.COMPLETED, FundingSchedule.Status.SUPERSEDED, FundingSchedule.Status.CANCELLED):
            messages.error(request, 'This schedule cannot be superseded.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.SUPERSEDED
        fs.save()
        messages.success(request, 'Funding schedule superseded.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status in (FundingSchedule.Status.COMPLETED, FundingSchedule.Status.SUPERSEDED, FundingSchedule.Status.CANCELLED):
            messages.error(request, 'This schedule is already finalised.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.CANCELLED
        fs.save()
        messages.success(request, 'Funding schedule cancelled.')
        return redirect('ui:funding_schedule_detail', pk=pk)


# ---------------------------------------------------------------------------
# Payment lifecycle actions (issue #22)
# PENDING → RECOMMENDED → APPROVED → RELEASED  (or REJECTED at any pre-final step)
# ---------------------------------------------------------------------------

class PaymentRecommendView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.PENDING:
            messages.error(request, 'Only pending payments can be recommended.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.RECOMMENDED
        payment.save()
        messages.success(request, 'Payment recommended.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentApproveView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.RECOMMENDED:
            messages.error(request, 'Only recommended payments can be approved.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.APPROVED
        payment.save()
        messages.success(request, 'Payment approved.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentReleaseView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.APPROVED:
            messages.error(request, 'Only approved payments can be released.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.RELEASED
        payment.save()
        messages.success(request, 'Payment released.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentRejectView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status in (Payment.Status.RELEASED, Payment.Status.REJECTED):
            messages.error(request, 'This payment is already finalised.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.REJECTED
        payment.save()
        messages.success(request, 'Payment rejected.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


# StageReport lifecycle actions (nested under project)
# ---------------------------------------------------------------------------

class StageReportSubmitView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        report = get_object_or_404(StageReport, pk=pk, project_id=project_pk)
        if report.status != StageReport.Status.DRAFT:
            messages.error(request, 'Only draft reports can be submitted.')
            return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)
        report.submit(request.user)
        messages.success(request, 'Stage report submitted.')
        return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)


class StageReportEndorseView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        report = get_object_or_404(StageReport, pk=pk, project_id=project_pk)
        if report.status != StageReport.Status.SUBMITTED:
            messages.error(request, 'Only submitted reports can be endorsed.')
            return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)
        report.endorse(request.user)
        messages.success(request, 'Stage report endorsed.')
        return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)


class StageReportAssessView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        report = get_object_or_404(StageReport, pk=pk, project_id=project_pk)
        if report.status != StageReport.Status.ENDORSED:
            messages.error(request, 'Only endorsed reports can be assessed.')
            return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)
        report.assess(request.user)
        messages.success(request, 'Stage report assessed.')
        return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)


class StageReportApproveView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        report = get_object_or_404(StageReport, pk=pk, project_id=project_pk)
        if report.status != StageReport.Status.ASSESSED:
            messages.error(request, 'Only assessed reports can be approved.')
            return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)
        report.approve(request.user)
        messages.success(request, 'Stage report approved.')
        return redirect('ui:stage_report_detail', project_pk=project_pk, pk=pk)


# ---------------------------------------------------------------------------
# VariationItem (nested under Variation)
# ---------------------------------------------------------------------------

class VariationItemCreateView(LoginRequiredMixin, CreateView):
    model = VariationItem
    template_name = 'crud/form.html'
    fields = ['option', 'description', 'funding_schedule', 'council',
              'stage1_target_date', 'stage2_target_date',
              'original_scope', 'new_scope',
              'original_amount', 'new_amount',
              'monthly_required', 'quarterly_required', 'stage1_required', 'stage2_required']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get('instance') is None:
            kwargs['instance'] = VariationItem(variation_id=self.kwargs['variation_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Variation Item'
        ctx['back_url'] = reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})
        return ctx


class VariationItemUpdateView(LoginRequiredMixin, UpdateView):
    model = VariationItem
    template_name = 'crud/form.html'
    fields = ['option', 'description', 'funding_schedule', 'council',
              'stage1_target_date', 'stage2_target_date',
              'original_scope', 'new_scope',
              'original_amount', 'new_amount',
              'monthly_required', 'quarterly_required', 'stage1_required', 'stage2_required']

    def get_success_url(self):
        return reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Variation Item #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})
        return ctx


class VariationItemDeleteView(LoginRequiredMixin, DeleteView):
    model = VariationItem
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})
        return ctx


class VariationExecuteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        variation = get_object_or_404(Variation, pk=pk)
        if variation.status not in (Variation.Status.DRAFT, Variation.Status.COUNCIL_SIGNED):
            messages.error(request, 'Only draft or council-signed variations can be executed.')
            return redirect('ui:variation_detail', pk=pk)
        variation.status = Variation.Status.EXECUTED
        variation.save()
        messages.success(request, 'Variation executed.')
        return redirect('ui:variation_detail', pk=pk)


# ---------------------------------------------------------------------------
# WorkFunding / Allocation
# ---------------------------------------------------------------------------

class WorkFundingListView(LoginRequiredMixin, ListView):
    model = WorkFunding
    template_name = 'allocations/list.html'
    context_object_name = 'allocations'
    paginate_by = 50

    def get_queryset(self):
        return WorkFunding.objects.select_related(
            'funding_schedule', 'project', 'work'
        ).order_by('funding_schedule', 'id')


class WorkFundingCreateView(LoginRequiredMixin, CreateView):
    model = WorkFunding
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'project', 'work', 'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes']
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Allocation'
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx


class WorkFundingDetailView(LoginRequiredMixin, DetailView):
    model = WorkFunding
    template_name = 'allocations/detail.html'
    context_object_name = 'allocation'


class WorkFundingUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkFunding
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'project', 'work', 'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes']
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Allocation #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx


class WorkFundingDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkFunding
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx
