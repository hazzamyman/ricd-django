"""
CRUD views for core domain entities using Django class-based views.
All views require login via LoginRequiredMixin.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse, reverse_lazy

from apps.core.mixins import (
    CouncilOrFNCMixin, CouncilScopedMixin, WriteRequiredMixin,
    FNCOnlyMixin, CouncilSubmitMixin,
)
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView, View, TemplateView,
)

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

from apps.core.models import (
    Approval, Address, BriefFinancialApproval, Comment, CommentSettings,
    Council, CouncilContact, DevelopmentApplication, LandTenure,
    Notice, NoticeTarget,
    NotionalCost, PaymentRule, Program, ProgramBudget, Project, Suburb, Work, WorkType, FundingSchedule,
    WorkStepDefinition, WorkStepGroup, WorkStepGroupItem, WorkStep, ConstructionMethod,
    ForwardRPFAgreement, InterimFRPAgreement,
    Variation, VariationItem, Payment, StageReport, QuarterlyReport,
    FundingAgreement, FundingNotice, ExpenseClaim, WorkFunding,
    StateElectorate, FederalElectorate, QhigiRegion,
)

COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})


def _officer_role(user):
    return getattr(getattr(user, 'profile', None), 'officer_role', None)


class CommentsMixin:
    """
    Injects threaded comments into any DetailView context.

    Context variables added:
      comments          — top-level Comment queryset (visibility-filtered, with prefetched replies)
      comment_ct_id     — ContentType pk for the form hidden field
      comment_object_id — object pk for the form hidden field
      user_is_fnc       — True if the user is FNC staff (can see/post INTERNAL comments)
      can_comment       — True if the user may post a comment
    """

    def _comments_enabled(self):
        model_name = self.model._meta.model_name
        return CommentSettings.is_comments_enabled(model_name)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not self._comments_enabled():
            ctx['comments_disabled'] = True
            return ctx

        user = self.request.user
        role = _officer_role(user)
        is_council = role in COUNCIL_ROLES
        is_fnc = (role is not None and not is_council) or user.is_superuser

        ct = ContentType.objects.get_for_model(self.model)
        qs = Comment.objects.filter(
            content_type=ct, object_id=self.object.pk, parent=None,
        ).select_related('author').prefetch_related(
            'replies__author',
        )
        if is_council:
            qs = qs.filter(visibility=Comment.Visibility.EXTERNAL)

        ctx['comments'] = qs
        ctx['comment_ct_id'] = ct.pk
        ctx['comment_object_id'] = self.object.pk
        ctx['user_is_fnc'] = is_fnc
        ctx['can_comment'] = role is not None or user.is_superuser
        return ctx


class NoticesMixin:
    """
    Injects broadcast notices into any DetailView context.

    Context variables added:
      notices           — Notice queryset targeting this object (visibility-filtered)
      notice_entity_key — model_name key used in the notice create URL (?entity_type=...)
      notice_object_id  — pk of the current object (for the pre-select query param)
    """

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role = _officer_role(self.request.user)
        is_council = role in COUNCIL_ROLES
        ct = ContentType.objects.get_for_model(self.model)
        qs = Notice.objects.filter(
            targets__content_type=ct,
            targets__object_id=self.object.pk,
        ).prefetch_related('targets').order_by('-created_at')
        if is_council:
            qs = qs.filter(visibility=Notice.Visibility.EXTERNAL)
        ctx['notices'] = qs
        ctx['notice_entity_key'] = self.model._meta.model_name
        ctx['notice_object_id'] = self.object.pk
        return ctx


# ---------------------------------------------------------------------------
# Role-based access control mixin
# ---------------------------------------------------------------------------

MANAGER_ROLES = frozenset({'MANAGER', 'DIRECTOR'})


class WidgetUpgradeMixin:
    """Drop-in mixin for ModelForm-based CreateView / UpdateView.

    Upgrades default Django widgets so forms render natively in the design system:
      * DateField -> HTML5 date picker (<input type="date">)
      * DecimalField / FloatField -> step="0.01", inputmode="decimal"
      * All text-style inputs get Bootstrap class="form-control"
      * Select -> class="form-select"; Checkbox -> class="form-check-input"
    """
    def get_form(self, form_class=None):
        from django import forms as djforms
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field, djforms.DateField) and not isinstance(field, djforms.DateTimeField):
                field.widget = djforms.DateInput(attrs={'type': 'date'})
            elif isinstance(field, (djforms.DecimalField, djforms.FloatField)):
                attrs = dict(field.widget.attrs)
                attrs.setdefault('step', '0.01')
                attrs.setdefault('inputmode', 'decimal')
                field.widget.attrs = attrs
            w = field.widget
            if isinstance(w, (djforms.TextInput, djforms.NumberInput, djforms.DateInput,
                              djforms.EmailInput, djforms.URLInput, djforms.Textarea)):
                w.attrs.setdefault('class', 'form-control')
            elif isinstance(w, (djforms.Select, djforms.SelectMultiple)):
                w.attrs.setdefault('class', 'form-select')
            elif isinstance(w, djforms.CheckboxInput):
                w.attrs.setdefault('class', 'form-check-input')
        return form


class CouncilScopedQuerysetMixin:
    """
    For council-role users: filter the queryset to their council.
    Attach to any ListView/DetailView that queries Projects.
    """
    council_lookup_field = 'council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = _officer_role(self.request.user)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                if council:
                    qs = qs.filter(**{self.council_lookup_field: council})
            except Exception:
                pass
        return qs


class RoleRequiredMixin:
    """
    Mixin that gates a view behind officer_role checks.
    Set  on the subclass (e.g. MANAGER_ROLES).
    Superusers bypass the check.
    On failure: renders a 403 error message and redirects to the HTTP referer.
    """
    required_roles: frozenset = frozenset()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser or _officer_role(request.user) in self.required_roles:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'You do not have permission to perform that action.')
        return redirect(request.META.get('HTTP_REFERER', '/'))


# ---------------------------------------------------------------------------
# Council
# ---------------------------------------------------------------------------

class CouncilListView(CouncilOrFNCMixin, ListView):
    model = Council
    template_name = 'councils/list.html'
    context_object_name = 'councils'
    paginate_by = 50


class CouncilCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Council
    template_name = 'crud/form.html'
    fields = ['name', 'region',
              'state_electorate_link', 'federal_electorate_link',
              'contact_email', 'contact_phone', 'is_registered_housing_provider',
              'rcpa_contact_name', 'rcpa_contact_phone', 'rcpa_contact_email']
    success_url = reverse_lazy('ui:council_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Council'
        ctx['back_url'] = reverse_lazy('ui:council_list')
        return ctx


class CouncilDetailView(LoginRequiredMixin, NoticesMixin, DetailView):
    """Council detail with built-in dashboard: projects, reports, contacts, audit."""
    model = Council
    template_name = 'councils/detail.html'
    context_object_name = 'council'

    def get_context_data(self, **kwargs):
        from apps.core.models import (
            Project, StageReport, MonthlyTracker, QuarterlyReport,
            AuditLog, CouncilTrackerConfig,
        )
        ctx = super().get_context_data(**kwargs)
        council = self.object

        projects_qs = council.projects.select_related('program').order_by('-created_at')
        ctx['projects'] = projects_qs[:200]
        ctx['project_count'] = projects_qs.count()
        ctx['active_count'] = projects_qs.filter(
            state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
        ).count()

        ctx['contacts'] = council.contacts.order_by('role', 'name')

        # Outstanding reports for this council
        ctx['monthly_trackers'] = MonthlyTracker.objects.filter(council=council).order_by('-year', '-month')[:6]
        ctx['quarterly_reports'] = QuarterlyReport.objects.filter(council=council).order_by('-year', '-quarter')[:6]
        ctx['stage_reports'] = StageReport.objects.filter(project__council=council).select_related('project').order_by('-updated_at')[:10]

        # Council-scoped audit log: any financial entity attached to projects in this council
        project_ids = list(projects_qs.values_list('pk', flat=True))
        ctx['audit_logs'] = (
            AuditLog.objects.filter(entity_type='project', entity_id__in=project_ids)
            .order_by('-timestamp')[:20]
        )

        ctx['tracker_config'] = CouncilTrackerConfig.objects.filter(council=council).first()
        return ctx


class CouncilContactCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = CouncilContact
    template_name = 'crud/form.html'
    fields = ['role', 'name', 'email', 'phone']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = CouncilContact(council_id=self.kwargs['council_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:council_detail', kwargs={'pk': self.kwargs['council_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Council Contact'
        ctx['back_url'] = reverse_lazy('ui:council_detail', kwargs={'pk': self.kwargs['council_pk']})
        return ctx


class CouncilContactUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = CouncilContact
    template_name = 'crud/form.html'
    fields = ['role', 'name', 'email', 'phone']

    def get_success_url(self):
        return reverse_lazy('ui:council_detail', kwargs={'pk': self.object.council_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Contact: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:council_detail', kwargs={'pk': self.object.council_id})
        return ctx


class CouncilContactDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contact = get_object_or_404(CouncilContact, pk=pk)
        council_pk = contact.council_id
        contact.delete()
        messages.success(request, 'Contact removed.')
        return redirect('ui:council_detail', pk=council_pk)


class CouncilUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Council
    template_name = 'crud/form.html'
    fields = ['name', 'region',
              'state_electorate_link', 'federal_electorate_link',
              'contact_email', 'contact_phone', 'is_registered_housing_provider',
              'rcpa_contact_name', 'rcpa_contact_phone', 'rcpa_contact_email']
    success_url = reverse_lazy('ui:council_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Council: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:council_list')
        return ctx


class CouncilDeleteView(WriteRequiredMixin, DeleteView):
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

class ProgramListView(CouncilOrFNCMixin, ListView):
    model = Program
    template_name = 'programs/list.html'
    context_object_name = 'programs'
    paginate_by = 50


class ProgramCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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
    """Program detail with built-in dashboard: budgets per FY, projects, cashflow extract."""
    model = Program
    template_name = 'programs/detail.html'
    context_object_name = 'program'

    def get_context_data(self, **kwargs):
        from apps.core.models import Payment
        from apps.core.services.cashflow import build_program_cashflow
        from django.db.models import Sum
        ctx = super().get_context_data(**kwargs)
        program = self.object

        projects_qs = program.projects.select_related('council').order_by('-created_at')
        ctx['projects'] = projects_qs[:200]
        ctx['project_count'] = projects_qs.count()
        ctx['active_count'] = projects_qs.filter(
            state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
        ).count()

        ctx['budgets'] = program.budgets.order_by('financial_year')

        released = Payment.objects.filter(
            project__program=program, status=Payment.Status.RELEASED
        ).aggregate(total=Sum('amount'))['total'] or 0
        ctx['released_total'] = released

        # Cashflow extract: single-program slice of the full matrix
        cashflow = build_program_cashflow(program=program)
        ctx['cashflow'] = cashflow
        ctx['cashflow_row'] = cashflow['rows'][0] if cashflow['rows'] else None
        return ctx


class ProgramBudgetCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = ProgramBudget
    template_name = 'crud/form.html'
    fields = ['financial_year', 'allocated', 'notes']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = ProgramBudget(program_id=self.kwargs['program_pk'])
        return kwargs

    def get_success_url(self):
        return reverse_lazy('ui:program_detail', kwargs={'pk': self.kwargs['program_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Program Budget (per FY)'
        ctx['back_url'] = reverse_lazy('ui:program_detail', kwargs={'pk': self.kwargs['program_pk']})
        return ctx


class ProgramBudgetUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = ProgramBudget
    template_name = 'crud/form.html'
    fields = ['financial_year', 'allocated', 'notes']

    def get_success_url(self):
        return reverse_lazy('ui:program_detail', kwargs={'pk': self.object.program_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Budget: {self.object.financial_year}'
        ctx['back_url'] = reverse_lazy('ui:program_detail', kwargs={'pk': self.object.program_id})
        return ctx


class ProgramBudgetDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        budget = get_object_or_404(ProgramBudget, pk=pk)
        program_pk = budget.program_id
        budget.delete()
        messages.success(request, 'Budget allocation removed.')
        return redirect('ui:program_detail', pk=program_pk)


class ProgramUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class ProgramDeleteView(WriteRequiredMixin, DeleteView):
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

class ProjectCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'financial_year',
              'state', 'dwelling_status',
              'stage1_item_group', 'stage2_item_group']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Project'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


class ProjectDetailView(CouncilScopedMixin, CouncilOrFNCMixin, CommentsMixin, NoticesMixin, DetailView):
    model = Project
    council_filter_field = 'council'
    template_name = 'projects/detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = self.request.GET.get('tab', 'overview')
        return ctx


class ProjectUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'financial_year',
              'state', 'dwelling_status',
              'stage1_item_group', 'stage2_item_group']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Project: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


class ProjectDeleteView(WriteRequiredMixin, DeleteView):
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

class WorkTypeListView(CouncilOrFNCMixin, ListView):
    model = WorkType
    template_name = 'work_types/list.html'
    context_object_name = 'work_types'
    paginate_by = 50


class WorkTypeCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkType
    template_name = 'crud/form.html'
    fields = ['name', 'category', 'short_code', 'has_bedrooms',
              'default_bedrooms', 'min_bedrooms', 'max_bedrooms',
              'description', 'is_active']
    success_url = reverse_lazy('ui:work_type_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Work Type'
        ctx['back_url'] = reverse_lazy('ui:work_type_list')
        return ctx


class WorkTypeDetailView(CouncilOrFNCMixin, DetailView):
    model = WorkType
    template_name = 'work_types/detail.html'
    context_object_name = 'work_type'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['notional_costs'] = (
            self.object.costs.select_related()
            .order_by('financial_year', 'bedrooms')
        )
        return ctx


class WorkTypeUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkType
    template_name = 'crud/form.html'
    fields = ['name', 'category', 'short_code', 'has_bedrooms',
              'default_bedrooms', 'min_bedrooms', 'max_bedrooms',
              'description', 'is_active']
    success_url = reverse_lazy('ui:work_type_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Work Type: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:work_type_list')
        return ctx


class WorkTypeDeleteView(WriteRequiredMixin, DeleteView):
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

class FundingScheduleListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = FundingSchedule
    council_filter_field = 'project__council'
    template_name = 'funding_schedules/list.html'
    context_object_name = 'funding_schedules'
    paginate_by = 50


class FundingScheduleCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = FundingSchedule
    template_name = 'crud/form.html'
    fields = ['project', 'funding_agreement', 'payment_rule', 'schedule_number', 'status',
              'start_date', 'stage1_target_date', 'stage1_sunset_date',
              'stage2_target_date', 'stage2_sunset_date',
              'stage1_item_group', 'stage2_item_group']
    success_url = reverse_lazy('ui:funding_schedule_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Schedule'
        ctx['back_url'] = reverse_lazy('ui:funding_schedule_list')
        return ctx


class FundingScheduleDetailView(CouncilScopedMixin, CouncilOrFNCMixin, CommentsMixin, NoticesMixin, DetailView):
    model = FundingSchedule
    council_filter_field = 'project__council'
    template_name = 'funding_schedules/detail.html'
    context_object_name = 'funding_schedule'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.core.models import AuditLog
        ctx['audit_logs'] = AuditLog.objects.filter(
            entity_type='fundingschedule', entity_id=self.object.pk
        ).order_by('-timestamp')[:10]
        return ctx


class FundingScheduleUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = FundingSchedule
    template_name = 'crud/form.html'
    fields = ['project', 'funding_agreement', 'payment_rule', 'schedule_number', 'status',
              'start_date', 'stage1_target_date', 'stage1_sunset_date',
              'stage2_target_date', 'stage2_sunset_date',
              'stage1_item_group', 'stage2_item_group']
    success_url = reverse_lazy('ui:funding_schedule_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Funding Schedule #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:funding_schedule_list')
        return ctx


class FundingScheduleDeleteView(WriteRequiredMixin, DeleteView):
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

class VariationCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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


class VariationDetailView(CouncilScopedMixin, CouncilOrFNCMixin, CommentsMixin, NoticesMixin, DetailView):
    model = Variation
    council_filter_field = 'funding_schedule__project__council'
    template_name = 'variations/detail.html'
    context_object_name = 'variation'


class VariationUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class VariationDeleteView(WriteRequiredMixin, DeleteView):
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

class PaymentListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = Payment
    council_filter_field = 'project__council'
    template_name = 'payments/list.html'
    context_object_name = 'payments'

    def get_queryset(self):
        return super().get_queryset().filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class PaymentCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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


class PaymentDetailView(CouncilScopedMixin, CouncilOrFNCMixin, NoticesMixin, DetailView):
    model = Payment
    council_filter_field = 'project__council'
    template_name = 'payments/detail.html'
    context_object_name = 'payment'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.core.models import AuditLog
        ctx['audit_logs'] = AuditLog.objects.filter(
            entity_type='payment', entity_id=self.object.pk
        ).order_by('-timestamp')[:10]
        return ctx
class PaymentUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class PaymentDeleteView(WriteRequiredMixin, DeleteView):
    model = Payment
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


# ---------------------------------------------------------------------------
# StageReport (REDESIGNED — see stage_views.py)
# The old project-nested CRUD endpoints survive as redirect stubs so external
# bookmarks still work. The real flow lives at /stage-reports/<pk>/.
# ---------------------------------------------------------------------------

class StageReportListView(LoginRequiredMixin, ListView):
    """Project-scoped list of stage reports (read-only — the real editor is the grid)."""
    model = StageReport
    council_filter_field = 'project__council'
    template_name = 'stage_reports/list.html'
    context_object_name = 'stage_reports'

    def get_queryset(self):
        return StageReport.objects.filter(project_id=self.kwargs['project_pk']).order_by('stage_type')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class StageReportCreateView(LoginRequiredMixin, View):
    """Backwards-compat: sends users to the new FS-based open-or-create flow (via legacy redirect)."""
    def get(self, request, project_pk):
        return redirect('ui:stage_report_open_legacy_project', project_pk=project_pk, stage_type='STAGE1')


class StageReportDetailView(LoginRequiredMixin, View):
    """Backwards-compat: redirect to the grid view by pk."""
    def get(self, request, project_pk, pk):
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, View):
    """Backwards-compat: redirect to the grid view by pk."""
    def get(self, request, project_pk, pk):
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportDeleteView(WriteRequiredMixin, DeleteView):
    model = StageReport
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:stage_report_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


# ---------------------------------------------------------------------------
# QuarterlyReport  (now per-council — see tracker_views.py)
# These project-nested URL endpoints redirect to the new per-council list.
# ---------------------------------------------------------------------------

class QuarterlyReportListView(LoginRequiredMixin, View):
    """Project-nested URL kept for backward compat; redirects to per-council list."""
    def get(self, request, project_pk):
        return redirect('ui:quarterly_report_global_list')


class QuarterlyReportCreateView(LoginRequiredMixin, View):
    def get(self, request, project_pk):
        return redirect('ui:quarterly_report_global_list')


class QuarterlyReportDetailView(LoginRequiredMixin, View):
    def get(self, request, project_pk, pk):
        return redirect('ui:quarterly_report_detail', pk=pk)


class QuarterlyReportUpdateView(LoginRequiredMixin, View):
    def get(self, request, project_pk, pk):
        return redirect('ui:quarterly_report_detail', pk=pk)


class QuarterlyReportDeleteView(LoginRequiredMixin, View):
    def get(self, request, project_pk, pk):
        return redirect('ui:quarterly_report_global_list')


# ---------------------------------------------------------------------------
# FundingAgreement
# ---------------------------------------------------------------------------

class FundingAgreementListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = FundingAgreement
    council_filter_field = 'council'
    template_name = 'funding_agreements/list.html'
    context_object_name = 'agreements'
    paginate_by = 50

    def get_queryset(self):
        return super().get_queryset().select_related('council').order_by('-created_at')


class FundingAgreementCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = FundingAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'name', 'execution_date', 'status', 'document_uri', 'notes']
    success_url = reverse_lazy('ui:funding_agreement_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Agreement'
        ctx['back_url'] = reverse_lazy('ui:funding_agreement_list')
        return ctx


class FundingAgreementDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    model = FundingAgreement
    council_filter_field = 'council'
    template_name = 'funding_agreements/detail.html'
    context_object_name = 'agreement'

    def get_queryset(self):
        return super().get_queryset().select_related('council')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schedules'] = self.object.schedules.select_related('payment_rule').order_by('schedule_number')
        return ctx


class FundingAgreementUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = FundingAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'name', 'execution_date', 'status', 'document_uri', 'notes']
    success_url = reverse_lazy('ui:funding_agreement_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Agreement: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_agreement_list')
        return ctx


class FundingAgreementDeleteView(WriteRequiredMixin, DeleteView):
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

class FundingNoticeListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = FundingNotice
    council_filter_field = 'project__council'
    template_name = 'funding_notices/list.html'
    context_object_name = 'notices'
    paginate_by = 50

    def get_queryset(self):
        return super().get_queryset().select_related('project').order_by('-issued_date')


class FundingNoticeCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = FundingNotice
    template_name = 'crud/form.html'
    fields = ['project', 'capped_amount', 'issued_date', 'notes']
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Notice'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    model = FundingNotice
    council_filter_field = 'project__council'
    template_name = 'funding_notices/detail.html'
    context_object_name = 'notice'

    def get_queryset(self):
        return super().get_queryset().select_related('project')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['claims'] = self.object.claims.select_related('approved_by').order_by('-date_submitted')
        return ctx


class FundingNoticeUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = FundingNotice
    template_name = 'crud/form.html'
    fields = ['project', 'capped_amount', 'issued_date', 'notes']
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Funding Notice — {self.object.project.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeDeleteView(WriteRequiredMixin, DeleteView):
    model = FundingNotice
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:funding_notice_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_notice_list')
        return ctx


class FundingNoticeCloseView(WriteRequiredMixin, View):
    def post(self, request, pk):
        notice = get_object_or_404(FundingNotice, pk=pk)
        notice.status = FundingNotice.Status.CLOSED
        notice.save()
        messages.success(request, 'Funding notice closed.')
        return redirect('ui:funding_notice_detail', pk=pk)


# ---------------------------------------------------------------------------
# ExpenseClaim  (nested under FundingNotice)
# ---------------------------------------------------------------------------

EXPENSE_CLAIM_FIELDS = [
    'amount', 'date_submitted', 'status', 'approved_date',
    'sap_document_reference', 'notes',
]


class ExpenseClaimCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = ExpenseClaim
    template_name = 'crud/form.html'
    fields = EXPENSE_CLAIM_FIELDS

    def get_success_url(self):
        return reverse_lazy('ui:expense_claim_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = ExpenseClaim(funding_notice_id=self.kwargs['notice_pk'])
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        notice = get_object_or_404(FundingNotice, pk=self.kwargs['notice_pk'])
        ctx['title'] = f'Add Expense Claim — {notice.project.name}'
        ctx['back_url'] = reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.kwargs['notice_pk']})
        return ctx


class ExpenseClaimUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = ExpenseClaim
    template_name = 'crud/form.html'
    fields = EXPENSE_CLAIM_FIELDS

    def get_success_url(self):
        return reverse_lazy('ui:expense_claim_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Expense Claim #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:expense_claim_detail', kwargs={'pk': self.object.pk})
        return ctx


class ExpenseClaimDetailView(LoginRequiredMixin, View):
    """Detail page for an expense claim — fields plus attachment list with add/delete."""
    def get(self, request, pk):
        claim = get_object_or_404(
            ExpenseClaim.objects.select_related('funding_notice__project__council'),
            pk=pk
        )
        return render(request, 'expense_claims/detail.html', {
            'claim': claim,
            'attachments': claim.attachments.all(),
        })


class ExpenseClaimAttachmentAddView(LoginRequiredMixin, View):
    def post(self, request, claim_pk):
        from apps.core.models import ExpenseClaimAttachment
        claim = get_object_or_404(ExpenseClaim, pk=claim_pk)
        uri = (request.POST.get('document_uri') or '').strip()
        if not uri:
            messages.error(request, 'A document URL is required.')
            return redirect('ui:expense_claim_detail', pk=claim_pk)
        ExpenseClaimAttachment.objects.create(
            claim=claim,
            document_uri=uri,
            description=(request.POST.get('description') or '').strip(),
            uploaded_by=request.user,
        )
        messages.success(request, 'Attachment added.')
        return redirect('ui:expense_claim_detail', pk=claim_pk)


class ExpenseClaimAttachmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from apps.core.models import ExpenseClaimAttachment
        att = get_object_or_404(ExpenseClaimAttachment, pk=pk)
        claim_pk = att.claim_id
        att.delete()
        messages.success(request, 'Attachment removed.')
        return redirect('ui:expense_claim_detail', pk=claim_pk)


class ExpenseClaimDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpenseClaim
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:funding_notice_detail', kwargs={'pk': self.object.funding_notice_id})
        return ctx


class ExpenseClaimApproveView(FNCOnlyMixin, View):
    def post(self, request, pk):
        from django.utils import timezone
        claim = get_object_or_404(ExpenseClaim, pk=pk)
        if claim.status != ExpenseClaim.Status.SUBMITTED:
            messages.error(request, 'Only submitted claims can be approved.')
            return redirect('ui:funding_notice_detail', pk=claim.funding_notice_id)
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


class ExpenseClaimSubmitView(CouncilSubmitMixin, View):
    def post(self, request, pk):
        claim = get_object_or_404(ExpenseClaim, pk=pk)
        if claim.status != ExpenseClaim.Status.DRAFT:
            messages.error(request, 'Only draft claims can be submitted.')
            return redirect('ui:funding_notice_detail', pk=claim.funding_notice_id)
        claim.status = ExpenseClaim.Status.SUBMITTED
        claim.save()
        messages.success(request, 'Claim submitted for approval.')
        return redirect('ui:funding_notice_detail', pk=claim.funding_notice_id)


class ExpenseClaimRejectView(FNCOnlyMixin, View):
    def post(self, request, pk):
        claim = get_object_or_404(ExpenseClaim, pk=pk)
        if claim.status not in (ExpenseClaim.Status.SUBMITTED, ExpenseClaim.Status.APPROVED):
            messages.error(request, 'Only submitted or approved claims can be rejected.')
            return redirect('ui:funding_notice_detail', pk=claim.funding_notice_id)
        notice_pk = claim.funding_notice_id
        claim.status = ExpenseClaim.Status.REJECTED
        claim.save()
        messages.info(request, 'Claim rejected.')
        return redirect('ui:funding_notice_detail', pk=notice_pk)


# ---------------------------------------------------------------------------
# BriefFinancialApproval  (nested under project)
# ---------------------------------------------------------------------------

class BriefFinancialApprovalGlobalListView(LoginRequiredMixin, ListView):
    """All BFAs across all projects — used by the sidebar nav link."""
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/list.html'
    context_object_name = 'approvals'

    def get_queryset(self):
        return BriefFinancialApproval.objects.select_related('project').order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = None  # no project filter
        return ctx


class BriefFinancialApprovalListView(LoginRequiredMixin, ListView):
    model = BriefFinancialApproval
    council_filter_field = 'project__council'
    template_name = 'brief_financial_approvals/list.html'
    context_object_name = 'approvals'

    def get_queryset(self):
        return super().get_queryset().filter(project_id=self.kwargs['project_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class BriefFinancialApprovalCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = BriefFinancialApproval
    template_name = 'crud/form.html'
    fields = ['funding_amount', 'contingency_amount', 'delegate_level', 'mincor_reference', 'comments']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = BriefFinancialApproval(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_success_url(self):
        return reverse('ui:project_detail', kwargs={'pk': self.kwargs['project_pk']}) + '?tab=funding'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Brief Financial Approval'
        ctx['back_url'] = reverse('ui:project_detail', kwargs={'pk': self.kwargs['project_pk']}) + '?tab=funding'
        return ctx


class BriefFinancialApprovalDetailView(CouncilScopedMixin, CouncilOrFNCMixin, NoticesMixin, DetailView):
    model = BriefFinancialApproval
    council_filter_field = 'project__council'
    template_name = 'brief_financial_approvals/detail.html'
    context_object_name = 'bfa'


class BriefFinancialApprovalUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class BriefFinancialApprovalDeleteView(WriteRequiredMixin, DeleteView):
    model = BriefFinancialApproval
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:bfa_list', kwargs={'project_pk': self.kwargs['project_pk']})
        return ctx


class BriefFinancialApprovalApproveView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = MANAGER_ROLES
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


class BriefFinancialApprovalRejectView(FNCOnlyMixin, View):
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

class PaymentRuleListView(CouncilOrFNCMixin, ListView):
    model = PaymentRule
    template_name = 'payment_rules/list.html'
    context_object_name = 'payment_rules'
    paginate_by = 50

    def get_queryset(self):
        return PaymentRule.objects.order_by('name', '-version')


class PaymentRuleDetailView(CouncilOrFNCMixin, DetailView):
    model = PaymentRule
    template_name = 'payment_rules/detail.html'
    context_object_name = 'payment_rule'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rule = self.object
        ctx['schedule_count'] = FundingSchedule.objects.filter(payment_rule=rule).count()
        ctx['milestones'] = rule.milestones.all().order_by('order')
        ctx['is_locked'] = rule.is_locked
        return ctx


class PaymentRuleCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = PaymentRule
    template_name = 'crud/form.html'
    fields = ['name', 'rule_type', 'version', 'is_active']

    def get_success_url(self):
        return reverse('ui:payment_rule_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Payment Rule'
        ctx['back_url'] = reverse_lazy('ui:payment_rule_list')
        return ctx


class PaymentRuleUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = PaymentRule
    template_name = 'crud/form.html'
    fields = ['name', 'rule_type', 'version', 'is_active']

    def dispatch(self, request, *args, **kwargs):
        rule = self.get_object()
        if rule.is_locked:
            messages.error(
                request,
                f"'{rule.name}' is in use by a Funding Schedule. Create a new version instead."
            )
            return redirect('ui:payment_rule_detail', pk=rule.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('ui:payment_rule_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Payment Rule: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:payment_rule_detail', kwargs={'pk': self.object.pk})
        return ctx


class PaymentRuleDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        rule = get_object_or_404(PaymentRule, pk=pk)
        return render(request, 'crud/confirm_delete.html', {
            'object': rule,
            'back_url': reverse('ui:payment_rule_detail', kwargs={'pk': pk}),
            'extra_warning': "This will also delete all milestone rows." if not rule.is_locked else None,
        })

    def post(self, request, pk):
        rule = get_object_or_404(PaymentRule, pk=pk)
        if rule.is_locked:
            messages.error(
                request,
                f"Cannot delete '{rule.name}' — it is in use by a Funding Schedule."
            )
            return redirect('ui:payment_rule_detail', pk=pk)
        name = rule.name
        rule.delete()
        messages.success(request, f"Deleted payment rule '{name}'.")
        return redirect('ui:payment_rule_list')


# ---------------------------------------------------------------------------
# PaymentRuleMilestone — inline rows under PaymentRule
# ---------------------------------------------------------------------------

class PaymentRuleMilestoneCreateView(LoginRequiredMixin, View):
    """POST-only: add a milestone row from the detail page form."""
    def post(self, request, rule_pk):
        from apps.core.models import PaymentRuleMilestone
        rule = get_object_or_404(PaymentRule, pk=rule_pk)
        if rule.is_locked:
            messages.error(request, f"'{rule.name}' is in use; cannot add milestones.")
            return redirect('ui:payment_rule_detail', pk=rule_pk)
        try:
            from decimal import Decimal
            next_order = (rule.milestones.order_by('-order').values_list('order', flat=True).first() or 0) + 1
            PaymentRuleMilestone.objects.create(
                rule=rule,
                order=int(request.POST.get('order') or next_order),
                name=(request.POST.get('name') or '').strip() or f'Milestone {next_order}',
                percentage=Decimal(request.POST.get('percentage') or '0'),
            )
            rule.sync_config_json()
            messages.success(request, 'Milestone added.')
        except Exception as e:
            messages.error(request, f'Could not add milestone: {e}')
        return redirect('ui:payment_rule_detail', pk=rule_pk)


class PaymentRuleMilestoneUpdateView(LoginRequiredMixin, View):
    """POST-only: update a milestone row in-place."""
    def post(self, request, pk):
        from apps.core.models import PaymentRuleMilestone
        from decimal import Decimal
        ms = get_object_or_404(PaymentRuleMilestone, pk=pk)
        rule = ms.rule
        if rule.is_locked:
            messages.error(request, f"'{rule.name}' is in use; cannot edit milestones.")
            return redirect('ui:payment_rule_detail', pk=rule.pk)
        try:
            ms.order = int(request.POST.get('order') or ms.order)
            ms.name = (request.POST.get('name') or '').strip() or ms.name
            ms.percentage = Decimal(request.POST.get('percentage') or ms.percentage)
            ms.save()
            rule.sync_config_json()
            messages.success(request, 'Milestone updated.')
        except Exception as e:
            messages.error(request, f'Could not update milestone: {e}')
        return redirect('ui:payment_rule_detail', pk=rule.pk)


class PaymentRuleMilestoneDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from apps.core.models import PaymentRuleMilestone
        ms = get_object_or_404(PaymentRuleMilestone, pk=pk)
        rule = ms.rule
        if rule.is_locked:
            messages.error(request, f"'{rule.name}' is in use; cannot delete milestones.")
            return redirect('ui:payment_rule_detail', pk=rule.pk)
        ms.delete()
        rule.sync_config_json()
        messages.success(request, 'Milestone removed.')
        return redirect('ui:payment_rule_detail', pk=rule.pk)


# ---------------------------------------------------------------------------
# Approval (issue #15 — system-generated; approve/reject from UI)
# ---------------------------------------------------------------------------

class ApprovalListView(CouncilOrFNCMixin, ListView):
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


class ApprovalDetailView(CouncilOrFNCMixin, DetailView):
    model = Approval
    template_name = 'approvals/detail.html'
    context_object_name = 'approval'


class ApprovalApproveView(FNCOnlyMixin, View):
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


class ApprovalRejectView(FNCOnlyMixin, View):
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

class WorkListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = Work
    council_filter_field = 'project__council'
    template_name = 'works/list.html'
    context_object_name = 'works'

    def get_queryset(self):
        return super().get_queryset().filter(project_id=self.kwargs['project_pk']).select_related('work_type', 'address').order_by('created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class WorkCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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


class WorkDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    model = Work
    council_filter_field = 'project__council'
    template_name = 'works/detail.html'
    context_object_name = 'work'


class WorkUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Work
    template_name = 'crud/form.html'
    fields = ['work_type', 'work_type_other', 'bedrooms', 'quantity',
              'estimated_cost', 'status', 'is_notional_cost', 'actual_cost', 'address',
              'cashflow_method', 'step_group', 'actual_start_date']

    def get_success_url(self):
        return reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Work: {self.object}'
        ctx['back_url'] = reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})
        return ctx


class WorkDeleteView(WriteRequiredMixin, DeleteView):
    model = Work
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id})
        return ctx


class WorkStepApplyGroupView(LoginRequiredMixin, View):
    """POST-only: apply the work's step_group to create WorkStep instances."""

    def post(self, request, project_pk, pk):
        from apps.core.services.workstep_forecast import apply_group_to_work
        work = get_object_or_404(Work, pk=pk, project_id=project_pk)
        if work.step_group:
            created, skipped = apply_group_to_work(work)
            messages.success(request, f'Applied group: {created} step(s) created, {skipped} already existed.')
        else:
            messages.warning(request, 'No step group assigned to this work item.')
        return redirect('ui:work_detail', project_pk=project_pk, pk=pk)


class WorkStepUpdateView(LoginRequiredMixin, UpdateView):
    """Update a single WorkStep (actual_completion_date, is_active)."""
    model = WorkStep
    template_name = 'crud/form.html'
    fields = ['actual_completion_date', 'is_active']

    def get_success_url(self):
        work = self.object.work
        from apps.core.services.workstep_forecast import recalculate_forecast
        recalculate_forecast(work)
        return reverse_lazy('ui:work_detail', kwargs={
            'project_pk': work.project_id, 'pk': work.pk
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        work = self.object.work
        ctx['title'] = f'Update Step: {self.object.step_name}'
        ctx['back_url'] = reverse_lazy('ui:work_detail', kwargs={
            'project_pk': work.project_id, 'pk': work.pk
        })
        return ctx


# ---------------------------------------------------------------------------
# Address (issue #18 — nested under project)
# ---------------------------------------------------------------------------

class AddressListView(CouncilOrFNCMixin, ListView):
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


class AddressCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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


class AddressDetailView(CouncilOrFNCMixin, DetailView):
    model = Address
    template_name = 'addresses/detail.html'
    context_object_name = 'address'


class AddressUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class AddressDeleteView(WriteRequiredMixin, DeleteView):
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

class FundingScheduleMarkReadyView(WriteRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status != FundingSchedule.Status.DRAFT:
            messages.error(request, 'Only draft schedules can be marked ready.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.READY_FOR_EXECUTION
        fs.save()
        messages.success(request, 'Funding schedule marked ready for execution.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleCompleteView(WriteRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status != FundingSchedule.Status.ACTIVE:
            messages.error(request, 'Only active schedules can be completed.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.COMPLETED
        fs.save()
        messages.success(request, 'Funding schedule completed.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleSupersededView(WriteRequiredMixin, View):
    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.status in (FundingSchedule.Status.COMPLETED, FundingSchedule.Status.SUPERSEDED, FundingSchedule.Status.CANCELLED):
            messages.error(request, 'This schedule cannot be superseded.')
            return redirect('ui:funding_schedule_detail', pk=pk)
        fs.status = FundingSchedule.Status.SUPERSEDED
        fs.save()
        messages.success(request, 'Funding schedule superseded.')
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleCancelView(WriteRequiredMixin, View):
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

class PaymentRecommendView(WriteRequiredMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.PENDING:
            messages.error(request, 'Only pending payments can be recommended.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.RECOMMENDED
        payment.save()
        messages.success(request, 'Payment recommended.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentApproveView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = MANAGER_ROLES
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.RECOMMENDED:
            messages.error(request, 'Only recommended payments can be approved.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.APPROVED
        payment.save()
        messages.success(request, 'Payment approved.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentReleaseView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = MANAGER_ROLES
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.APPROVED:
            messages.error(request, 'Only approved payments can be released.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.RELEASED
        payment.save()
        messages.success(request, 'Payment released.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


class PaymentRejectView(FNCOnlyMixin, View):
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status in (Payment.Status.RELEASED, Payment.Status.REJECTED):
            messages.error(request, 'This payment is already finalised.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.REJECTED
        payment.save()
        messages.success(request, 'Payment rejected.')
        return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)


# StageReport lifecycle actions
# These project-nested URLs survive as redirect stubs; the canonical actions
# live at /stage-reports/<pk>/{submit,endorse,assess,approve,reject}/ in
# stage_views.py.
# ---------------------------------------------------------------------------

class StageReportSubmitView(CouncilSubmitMixin, View):
    def post(self, request, project_pk, pk):
        from apps.core.models import StageReport
        from django.utils import timezone
        report = get_object_or_404(StageReport, pk=pk)
        if report.status == StageReport.Status.DRAFT:
            report.status = StageReport.Status.SUBMITTED
            report.submitted_by = request.user
            report.submitted_at = timezone.now()
            report.save(update_fields=['status', 'submitted_by', 'submitted_at'])
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportEndorseView(FNCOnlyMixin, View):
    def post(self, request, project_pk, pk):
        return redirect('ui:stage_report_endorse', pk=pk)


class StageReportAssessView(FNCOnlyMixin, View):
    def post(self, request, project_pk, pk):
        return redirect('ui:stage_report_assess', pk=pk)


class StageReportApproveView(FNCOnlyMixin, View):
    def post(self, request, project_pk, pk):
        return redirect('ui:stage_report_approve', pk=pk)


# ---------------------------------------------------------------------------
# VariationItem (nested under Variation)
# ---------------------------------------------------------------------------

class VariationItemCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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


class VariationItemUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
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


class VariationItemDeleteView(WriteRequiredMixin, DeleteView):
    model = VariationItem
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:variation_detail', kwargs={'pk': self.kwargs['variation_pk']})
        return ctx


class VariationExecuteView(FNCOnlyMixin, View):
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

class WorkFundingListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = WorkFunding
    council_filter_field = 'project__council'
    template_name = 'allocations/list.html'
    context_object_name = 'allocations'
    paginate_by = 50

    def get_queryset(self):
        return super().get_queryset().select_related('funding_schedule', 'project', 'work').order_by('funding_schedule', 'id')


class WorkFundingCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkFunding
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'project', 'work', 'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes']
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Allocation'
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx


class WorkFundingDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    model = WorkFunding
    council_filter_field = 'project__council'
    template_name = 'allocations/detail.html'
    context_object_name = 'allocation'


class WorkFundingUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkFunding
    template_name = 'crud/form.html'
    fields = ['funding_schedule', 'project', 'work', 'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes']
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Allocation #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx


class WorkFundingDeleteView(WriteRequiredMixin, DeleteView):
    model = WorkFunding
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:allocation_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:allocation_list')
        return ctx


# ---------------------------------------------------------------------------
# Suburb
# ---------------------------------------------------------------------------

class SuburbListView(LoginRequiredMixin, ListView):
    model = Suburb
    template_name = 'suburbs/list.html'
    context_object_name = 'suburbs'
    paginate_by = 100

    def get_queryset(self):
        qs = Suburb.objects.order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class SuburbCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Suburb
    template_name = 'crud/form.html'
    fields = ['name', 'postcode', 'state',
              'state_electorate_link', 'federal_electorate_link', 'qhigi_region_link',
              'is_active']
    success_url = reverse_lazy('ui:suburb_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Suburb'
        ctx['back_url'] = reverse_lazy('ui:suburb_list')
        return ctx


class SuburbUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Suburb
    template_name = 'crud/form.html'
    fields = ['name', 'postcode', 'state',
              'state_electorate_link', 'federal_electorate_link', 'qhigi_region_link',
              'is_active']
    success_url = reverse_lazy('ui:suburb_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Suburb — {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:suburb_list')
        return ctx


class SuburbDeleteView(LoginRequiredMixin, DeleteView):
    model = Suburb
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:suburb_list')


# ---------------------------------------------------------------------------
# NotionalCost — global list, bulk update, and nested CRUD under WorkType
# ---------------------------------------------------------------------------

class NotionalCostListView(LoginRequiredMixin, View):
    """Maintenance page: all notional costs across work types and financial years.

    Renders a row per (work_type, bedrooms) with columns per financial_year so
    you can see how costs are evolving across FYs at a glance.
    """
    def get(self, request):
        from apps.core.utils import FINANCIAL_YEAR_CHOICES, CURRENT_FINANCIAL_YEAR
        fy_filter = request.GET.get('fy', '')
        work_types = WorkType.objects.filter(is_active=True).order_by('category', 'name')
        qs = NotionalCost.objects.select_related('work_type').order_by(
            'work_type__category', 'work_type__name', 'bedrooms', 'financial_year'
        )
        if fy_filter:
            qs = qs.filter(financial_year=fy_filter)
        all_costs = list(qs)
        fys_present = sorted({c.financial_year for c in all_costs} | {CURRENT_FINANCIAL_YEAR})
        rows = []
        for wt in work_types:
            wt_costs = [c for c in all_costs if c.work_type_id == wt.pk]
            if not wt_costs:
                continue
            br_keys = sorted({c.bedrooms or 0 for c in wt_costs})
            for br in br_keys:
                costs_by_fy = {c.financial_year: c for c in wt_costs if (c.bedrooms or 0) == br}
                in_typical_range = (
                    not wt.has_bedrooms
                    or (wt.min_bedrooms and wt.max_bedrooms and wt.min_bedrooms <= br <= wt.max_bedrooms)
                )
                # Align cells to fys_present
                cells = [costs_by_fy.get(fy) for fy in fys_present]
                rows.append({
                    'work_type': wt,
                    'bedrooms': br,
                    'in_typical_range': in_typical_range,
                    'cells': cells,
                })
        return render(request, 'notional_costs/list.html', {
            'rows': rows,
            'fys': fys_present,
            'fy_choices': FINANCIAL_YEAR_CHOICES,
            'selected_fy': fy_filter,
            'current_fy': CURRENT_FINANCIAL_YEAR,
        })


class NotionalCostBulkUpdateView(LoginRequiredMixin, View):
    """Roll notional costs from a source FY into a target FY, multiplied by inflation %.

    GET shows the form. POST without ``confirm`` shows a preview. POST with
    ``confirm=true`` applies — creating missing target rows, skipping existing.
    """
    def _form_ctx(self):
        from apps.core.utils import FINANCIAL_YEAR_CHOICES, CURRENT_FINANCIAL_YEAR
        from apps.core.models import NotionalCostSettings
        return {
            'fy_choices': FINANCIAL_YEAR_CHOICES,
            'current_fy': CURRENT_FINANCIAL_YEAR,
            'default_rate': NotionalCostSettings.get_settings().default_inflation_rate,
        }

    def _build_preview(self, source_fy, target_fy, multiplier):
        from decimal import Decimal
        rows = []
        for src in NotionalCost.objects.filter(financial_year=source_fy).select_related('work_type'):
            new_cost = (src.cost_per_unit * (Decimal('1') + Decimal(str(multiplier)) / Decimal('100'))).quantize(Decimal('0.01'))
            already = NotionalCost.objects.filter(
                work_type=src.work_type, financial_year=target_fy, bedrooms=src.bedrooms
            ).first()
            rows.append({
                'work_type': src.work_type,
                'bedrooms': src.bedrooms,
                'source_cost': src.cost_per_unit,
                'new_cost': new_cost,
                'already_exists': already,
            })
        return rows

    def get(self, request):
        return render(request, 'notional_costs/bulk_update.html', self._form_ctx())

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        ctx = self._form_ctx()
        source_fy = request.POST.get('source_fy', '').strip()
        target_fy = request.POST.get('target_fy', '').strip()
        try:
            multiplier = Decimal(request.POST.get('multiplier_percent') or '0')
        except InvalidOperation:
            multiplier = Decimal('0')
        confirm = request.POST.get('confirm') == 'true'
        if not source_fy or not target_fy or source_fy == target_fy:
            messages.error(request, 'Pick distinct source and target financial years.')
            return render(request, 'notional_costs/bulk_update.html', ctx)

        rows = self._build_preview(source_fy, target_fy, multiplier)
        if not rows:
            messages.warning(request, f'No notional costs found for {source_fy}.')
            return render(request, 'notional_costs/bulk_update.html', ctx)

        if confirm:
            created = 0
            skipped = 0
            for r in rows:
                if r['already_exists']:
                    skipped += 1
                    continue
                NotionalCost.objects.create(
                    work_type=r['work_type'],
                    financial_year=target_fy,
                    bedrooms=r['bedrooms'],
                    cost_per_unit=r['new_cost'],
                )
                created += 1
            messages.success(
                request,
                f'Applied: created {created} row{"s" if created != 1 else ""}; '
                f'skipped {skipped} (target row already exists).'
            )
            return redirect('ui:notional_cost_list')

        ctx.update({
            'preview_rows': rows,
            'source_fy': source_fy,
            'target_fy': target_fy,
            'multiplier': multiplier,
            'total_rows': len(rows),
            'will_create': sum(1 for r in rows if not r['already_exists']),
            'will_skip': sum(1 for r in rows if r['already_exists']),
        })
        return render(request, 'notional_costs/bulk_update.html', ctx)


class NotionalCostCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = NotionalCost
    template_name = 'crud/form.html'
    fields = ['financial_year', 'bedrooms', 'cost_per_unit', 'is_default']

    def _work_type(self):
        return get_object_or_404(WorkType, pk=self.kwargs['wt_pk'])

    def form_valid(self, form):
        form.instance.work_type = self._work_type()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wt = self._work_type()
        ctx['title'] = f'Add Notional Cost — {wt.name}'
        ctx['back_url'] = reverse('ui:work_type_detail', kwargs={'pk': wt.pk})
        return ctx


class NotionalCostUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = NotionalCost
    template_name = 'crud/form.html'
    fields = ['financial_year', 'bedrooms', 'cost_per_unit', 'is_default']

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Notional Cost — {self.object}'
        ctx['back_url'] = reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})
        return ctx


class NotionalCostDeleteView(LoginRequiredMixin, DeleteView):
    model = NotionalCost
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})


# ---------------------------------------------------------------------------
# WorkStepDefinition — global step catalogue
# ---------------------------------------------------------------------------

class WorkStepDefinitionListView(LoginRequiredMixin, ListView):
    model = WorkStepDefinition
    template_name = 'work_step_definitions/list.html'
    context_object_name = 'definitions'
    paginate_by = 50

    def get_queryset(self):
        qs = WorkStepDefinition.objects.order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class WorkStepDefinitionCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkStepDefinition
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:work_step_definition_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Work Step Definition'
        return ctx


class WorkStepDefinitionUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkStepDefinition
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:work_step_definition_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Step — {self.object.name}'
        return ctx


class WorkStepDefinitionDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkStepDefinition
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:work_step_definition_list')


# ---------------------------------------------------------------------------
# WorkStepGroup — nested under WorkType
# ---------------------------------------------------------------------------

class WorkStepGroupCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkStepGroup
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']

    def _work_type(self):
        return get_object_or_404(WorkType, pk=self.kwargs['wt_pk'])

    def form_valid(self, form):
        form.instance.work_type = self._work_type()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Add Step Group — {self._work_type().name}'
        return ctx

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})


class WorkStepGroupUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkStepGroup
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Step Group — {self.object.name}'
        return ctx

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.object.work_type_id})


class WorkStepGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkStepGroup
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.object.work_type_id})


# ---------------------------------------------------------------------------
# WorkStepGroupItem — nested under WorkStepGroup
# ---------------------------------------------------------------------------

class WorkStepGroupItemCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkStepGroupItem
    template_name = 'crud/form.html'
    fields = ['step', 'order', 'cost_percentage', 'expected_duration_days', 'stage_gate']

    def _group(self):
        return get_object_or_404(WorkStepGroup, pk=self.kwargs['group_pk'])

    def form_valid(self, form):
        form.instance.group = self._group()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self._group()
        ctx['title'] = f'Add Step to {group.name}'
        ctx['group'] = group
        return ctx

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self._group().work_type_id})


class WorkStepGroupItemUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkStepGroupItem
    template_name = 'crud/form.html'
    fields = ['step', 'order', 'cost_percentage', 'expected_duration_days', 'stage_gate']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Step — {self.object.step.name}'
        return ctx

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.object.group.work_type_id})


class WorkStepGroupItemDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkStepGroupItem
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:work_type_detail', kwargs={'pk': self.object.group.work_type_id})



# ---------------------------------------------------------------------------
# ConstructionMethod CRUD (Maintenance)
# ---------------------------------------------------------------------------

class ConstructionMethodListView(LoginRequiredMixin, ListView):
    model = ConstructionMethod
    template_name = 'construction_methods/list.html'
    context_object_name = 'methods'


class ConstructionMethodCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = ConstructionMethod
    template_name = 'crud/form.html'
    fields = ['name', 'code', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Construction Method'
        ctx['back_url'] = reverse_lazy('ui:construction_method_list')
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:construction_method_list')


class ConstructionMethodUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = ConstructionMethod
    template_name = 'crud/form.html'
    fields = ['name', 'code', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:construction_method_list')
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:construction_method_list')


class ConstructionMethodDeleteView(LoginRequiredMixin, DeleteView):
    model = ConstructionMethod
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:construction_method_list')


# ---------------------------------------------------------------------------
# ForwardRPFAgreement CRUD
# ---------------------------------------------------------------------------

class ForwardRPFListView(LoginRequiredMixin, ListView):
    model = ForwardRPFAgreement
    template_name = 'legacy_agreements/forward_rpf_list.html'
    context_object_name = 'agreements'


class ForwardRPFCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = ForwardRPFAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'reference', 'status', 'date_sent_to_council',
              'date_council_signed', 'date_delegate_signed', 'document_uri', 'notes', 'projects']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Forward RPF Agreement'
        ctx['back_url'] = reverse_lazy('ui:forward_rpf_list')
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:forward_rpf_detail', kwargs={'pk': self.object.pk})


class ForwardRPFDetailView(LoginRequiredMixin, DetailView):
    model = ForwardRPFAgreement
    template_name = 'legacy_agreements/forward_rpf_detail.html'
    context_object_name = 'agreement'


class ForwardRPFUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = ForwardRPFAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'reference', 'status', 'date_sent_to_council',
              'date_council_signed', 'date_delegate_signed', 'document_uri', 'notes', 'projects']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object}'
        ctx['back_url'] = reverse_lazy('ui:forward_rpf_detail', kwargs={'pk': self.object.pk})
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:forward_rpf_detail', kwargs={'pk': self.object.pk})


class ForwardRPFDeleteView(LoginRequiredMixin, DeleteView):
    model = ForwardRPFAgreement
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:forward_rpf_list')


# ---------------------------------------------------------------------------
# InterimFRPAgreement CRUD
# ---------------------------------------------------------------------------

class InterimFRPListView(LoginRequiredMixin, ListView):
    model = InterimFRPAgreement
    template_name = 'legacy_agreements/interim_frp_list.html'
    context_object_name = 'agreements'


class InterimFRPCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = InterimFRPAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'reference', 'status', 'date_sent_to_council',
              'date_council_signed', 'date_delegate_signed', 'document_uri', 'notes', 'projects']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Interim FRP Agreement'
        ctx['back_url'] = reverse_lazy('ui:interim_frp_list')
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:interim_frp_detail', kwargs={'pk': self.object.pk})


class InterimFRPDetailView(LoginRequiredMixin, DetailView):
    model = InterimFRPAgreement
    template_name = 'legacy_agreements/interim_frp_detail.html'
    context_object_name = 'agreement'


class InterimFRPUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = InterimFRPAgreement
    template_name = 'crud/form.html'
    fields = ['council', 'reference', 'status', 'date_sent_to_council',
              'date_council_signed', 'date_delegate_signed', 'document_uri', 'notes', 'projects']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object}'
        ctx['back_url'] = reverse_lazy('ui:interim_frp_detail', kwargs={'pk': self.object.pk})
        return ctx

    def get_success_url(self):
        return reverse_lazy('ui:interim_frp_detail', kwargs={'pk': self.object.pk})


class InterimFRPDeleteView(LoginRequiredMixin, DeleteView):
    model = InterimFRPAgreement
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:interim_frp_list')


# ---------------------------------------------------------------------------
# Maintenance dashboard
# ---------------------------------------------------------------------------

class MaintenanceView(LoginRequiredMixin, TemplateView):
    template_name = 'maintenance/index.html'

    def get_context_data(self, **kwargs):
        User = get_user_model()
        ctx = super().get_context_data(**kwargs)
        ctx['council_count'] = Council.objects.count()
        ctx['program_count'] = Program.objects.count()
        ctx['work_type_count'] = WorkType.objects.count()
        ctx['suburb_count'] = Suburb.objects.count()
        ctx['workstep_definition_count'] = WorkStepDefinition.objects.count()
        ctx['construction_method_count'] = ConstructionMethod.objects.count()
        ctx['user_count'] = User.objects.count()
        ctx['active_nav'] = 'maintenance'
        return ctx


# ============================================================================
# Geographic / electoral lookup CRUD (Maintenance)
# ============================================================================

# Generic CRUD: each lookup has the same shape (name, description, is_active).

class _LookupBase:
    template_name = 'lookups/list.html'  # used by list view
    list_url_name = None  # subclass sets
    label = None  # human-readable, e.g. "State Electorate"


class StateElectorateListView(LoginRequiredMixin, ListView):
    model = StateElectorate
    template_name = 'lookups/list.html'
    context_object_name = 'items'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['label'] = 'State Electorate'
        ctx['label_plural'] = 'State Electorates'
        ctx['create_url'] = reverse_lazy('ui:state_electorate_create')
        ctx['edit_url_name'] = 'ui:state_electorate_edit'
        ctx['delete_url_name'] = 'ui:state_electorate_delete'
        return ctx


class StateElectorateCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = StateElectorate
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:state_electorate_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add State Electorate'
        ctx['back_url'] = reverse_lazy('ui:state_electorate_list')
        return ctx


class StateElectorateUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = StateElectorate
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:state_electorate_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:state_electorate_list')
        return ctx


class StateElectorateDeleteView(LoginRequiredMixin, DeleteView):
    model = StateElectorate
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:state_electorate_list')


class FederalElectorateListView(LoginRequiredMixin, ListView):
    model = FederalElectorate
    template_name = 'lookups/list.html'
    context_object_name = 'items'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['label'] = 'Federal Electorate'
        ctx['label_plural'] = 'Federal Electorates'
        ctx['create_url'] = reverse_lazy('ui:federal_electorate_create')
        ctx['edit_url_name'] = 'ui:federal_electorate_edit'
        ctx['delete_url_name'] = 'ui:federal_electorate_delete'
        return ctx


class FederalElectorateCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = FederalElectorate
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:federal_electorate_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Federal Electorate'
        ctx['back_url'] = reverse_lazy('ui:federal_electorate_list')
        return ctx


class FederalElectorateUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = FederalElectorate
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:federal_electorate_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:federal_electorate_list')
        return ctx


class FederalElectorateDeleteView(LoginRequiredMixin, DeleteView):
    model = FederalElectorate
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:federal_electorate_list')


class QhigiRegionListView(LoginRequiredMixin, ListView):
    model = QhigiRegion
    template_name = 'lookups/list.html'
    context_object_name = 'items'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['label'] = 'QHIGI Region'
        ctx['label_plural'] = 'QHIGI Regions'
        ctx['create_url'] = reverse_lazy('ui:qhigi_region_create')
        ctx['edit_url_name'] = 'ui:qhigi_region_edit'
        ctx['delete_url_name'] = 'ui:qhigi_region_delete'
        return ctx


class QhigiRegionCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = QhigiRegion
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:qhigi_region_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add QHIGI Region'
        ctx['back_url'] = reverse_lazy('ui:qhigi_region_list')
        return ctx


class QhigiRegionUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = QhigiRegion
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:qhigi_region_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:qhigi_region_list')
        return ctx


class QhigiRegionDeleteView(LoginRequiredMixin, DeleteView):
    model = QhigiRegion
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:qhigi_region_list')
