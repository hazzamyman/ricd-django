"""
CRUD views for core domain entities using Django class-based views.
All views require login via LoginRequiredMixin.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse, reverse_lazy

from apps.core.mixins import (
    CouncilOrFNCMixin, CouncilScopedMixin, WriteRequiredMixin,
    FNCOnlyMixin, CouncilSubmitMixin, InternalOnlyMixin,
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
    SiteSettings, PaymentMilestoneSchedule, PaymentMilestoneRule, Contractor,
    EmailTemplate, SentNotification,
)

COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})


def _officer_role(user):
    return getattr(getattr(user, 'profile', None), 'officer_role', None)


def _safe_next(request, default):
    """Return a validated ?next= redirect target, else `default`.

    The CRUD form/delete templates post to the current URL (no action attr), so a
    ?next= in the query string survives the POST round-trip and is read here.
    """
    from django.utils.http import url_has_allowed_host_and_scheme
    nxt = request.GET.get('next') or request.POST.get('next')
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return nxt
    return default


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
                attrs.setdefault('step', 'any')
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
    ordering = ['name']


class CouncilCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Council
    template_name = 'crud/form.html'
    fields = ['name', 'region', 'lead_officer',
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
        from decimal import Decimal
        from datetime import date
        from django.db.models import Sum, Count
        from apps.core.models import (
            Project, StageReport, MonthlyTracker, QuarterlyReport,
            AuditLog, CouncilTrackerConfig,
            BriefFinancialApprovalItem, PaymentAllocation, FundingSchedule, Payment,
        )
        ctx = super().get_context_data(**kwargs)
        council = self.object

        projects_qs = council.projects.select_related('program').order_by('-created_at')
        project_ids = list(projects_qs.values_list('pk', flat=True))

        ctx['projects'] = projects_qs[:200]
        ctx['project_count'] = projects_qs.count()
        ctx['active_count'] = projects_qs.filter(
            state__in=[Project.State.COMMENCED, Project.State.UNDER_CONSTRUCTION]
        ).count()
        ctx['contacts'] = council.contacts.order_by('role', 'name')

        # ── Financial summary ─────────────────────────────────────────────
        approved_total = (
            BriefFinancialApprovalItem.objects
            .filter(project__council=council, bfa__status='APPROVED')
            .aggregate(t=Sum('funding_amount'), c=Sum('contingency_amount'))
        )
        approved_funding = approved_total['t'] or Decimal('0')
        # Council users must never see contingency (FNC holds it back, releases only if needed).
        hide_contingency = _officer_role(self.request.user) in COUNCIL_ROLES
        approved_contingency = Decimal('0') if hide_contingency else (approved_total['c'] or Decimal('0'))
        approved_grand = approved_funding + approved_contingency

        active_fses = FundingSchedule.objects.filter(
            project__in=project_ids,
            status__in=[FundingSchedule.Status.EXECUTED, FundingSchedule.Status.ACTIVE],
        ).distinct()
        committed_via_fs = active_fses.aggregate(t=Sum('amount'))['t'] or Decimal('0')

        released_total = (
            PaymentAllocation.objects
            .filter(payment__project__council=council)
            .aggregate(t=Sum('amount'))['t'] or Decimal('0')
        )

        # Most recent QR's unspent funding figure (council's own report)
        latest_qr_with_unspent = (
            QuarterlyReport.objects
            .filter(council=council, unspent_funding__isnull=False)
            .order_by('-year', '-quarter').first()
        )
        council_reported_unspent = latest_qr_with_unspent.unspent_funding if latest_qr_with_unspent else None

        drawdown_pct = (released_total / approved_grand * Decimal('100')) if approved_grand else Decimal('0')

        ctx['fin_summary'] = {
            'approved_funding': approved_funding,
            'approved_contingency': approved_contingency,
            'approved_grand': approved_grand,
            'committed_via_fs': committed_via_fs,
            'released_total': released_total,
            'council_reported_unspent': council_reported_unspent,
            'unspent_reported_at': latest_qr_with_unspent.quarter_label if latest_qr_with_unspent else None,
            'drawdown_pct': drawdown_pct,
            'remaining': approved_grand - released_total,
        }

        # ── Reporting health ─────────────────────────────────────────────
        today = date.today()
        all_qrs = QuarterlyReport.objects.filter(council=council)
        overdue_qrs = [q for q in all_qrs if q.status in ('DRAFT', 'IN_PROGRESS') and q.due_date < today]
        upcoming_qrs = [q for q in all_qrs if q.status in ('DRAFT', 'IN_PROGRESS') and q.due_date >= today]
        ctx['reporting_health'] = {
            'qr_overdue_count': len(overdue_qrs),
            'qr_overdue': overdue_qrs,
            'qr_upcoming': upcoming_qrs[:3],
            'latest_qr': all_qrs.order_by('-year', '-quarter').first(),
        }
        ctx['monthly_trackers'] = MonthlyTracker.objects.filter(council=council).order_by('-year', '-month')[:6]
        ctx['quarterly_reports'] = all_qrs.order_by('-year', '-quarter')[:6]
        ctx['stage_reports'] = StageReport.objects.filter(project__council=council).select_related('project').order_by('-updated_at')[:10]

        # ── Active funding schedules with per-FS drawdown ────────────────
        fs_summary = []
        for fs in active_fses.select_related('payment_rule').order_by('schedule_number'):
            fs_released = (
                PaymentAllocation.objects.filter(payment__funding_schedule=fs).aggregate(t=Sum('amount'))['t']
                or Decimal('0')
            )
            fs_drawdown = (fs_released / fs.amount * Decimal('100')) if fs.amount else Decimal('0')
            fs_summary.append({
                'fs': fs,
                'released': fs_released,
                'drawdown_pct': fs_drawdown,
                'forecast_pc': fs.project.forecast_practical_completion_date if fs.project_id else None,
            })
        ctx['active_fs_summary'] = fs_summary

        # ── Project pipeline by state (counts) ───────────────────────────
        state_counts = dict(
            projects_qs.values('state').annotate(c=Count('id')).values_list('state', 'c')
        )
        ctx['pipeline_counts'] = [
            {'state': s.value, 'label': s.label, 'count': state_counts.get(s.value, 0)}
            for s in Project.State
        ]

        # Council-scoped audit log
        ctx['audit_logs'] = (
            AuditLog.objects.filter(entity_type='project', entity_id__in=project_ids)
            .order_by('-timestamp')[:20]
        )
        ctx['tracker_config'] = CouncilTrackerConfig.objects.filter(council=council).first()
        return ctx


class CouncilContactCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = CouncilContact
    template_name = 'crud/form.html'
    fields = ['role', 'name', 'email', 'phone', 'receives_notifications']

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
    fields = ['role', 'name', 'email', 'phone', 'receives_notifications']

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
    fields = ['name', 'region', 'lead_officer',
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
    ordering = ['name']


class ProgramCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Program
    template_name = 'crud/form.html'
    fields = ['name', 'funding_source', 'funding_source_other', 'budget',
              'gl_code', 'cost_centre', 'business_case_reference', 'description', 'is_active']
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
        hide_contingency = _officer_role(self.request.user) in COUNCIL_ROLES
        cashflow = build_program_cashflow(program=program, hide_contingency=hide_contingency)
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
              'gl_code', 'cost_centre', 'business_case_reference', 'description', 'is_active']
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

_PROJECT_ADVANCED_FIELDS = ['cli_no', 'initial_caa_date']
_ADDRESS_ADVANCED_FIELDS = [
    'land_status', 'lease_status', 'lease_executed_date',
]

_WORK_ADVANCED_FIELDS = [
    'floor_number', 'livable_housing_level', 'usage_type',
    'floor_material', 'frame_material', 'wall_material', 'roof_material', 'car_accommodation',
    'bathrooms_count', 'kitchens_count', 'living_rooms_count',
]


class ProjectCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'cashflow_method', 'financial_year',
              'financial_year_completed', 'lead_officer',
              'state', 'dwelling_status', 'qbuild_delivered',
              'stage1_item_group', 'stage2_item_group', 'quarterly_report_item_group',
              'sap_ion', 'cli_no', 'initial_caa_date']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Project'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        ctx['advanced_fields'] = _PROJECT_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(
            ctx['form'].has_error(f) for f in _PROJECT_ADVANCED_FIELDS
        )
        return ctx


class ProjectDetailView(CouncilScopedMixin, CouncilOrFNCMixin, CommentsMixin, NoticesMixin, DetailView):
    model = Project
    council_filter_field = 'council'
    template_name = 'projects/detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = self.request.GET.get('tab', 'overview')

        # Funding split (per program) — approved BFA totals vs released-to-date
        from decimal import Decimal
        from apps.core.models import BriefFinancialApprovalItem, PaymentAllocation, Program
        project = self.object
        # Council users must never see contingency — it would let them budget
        # against funds FNC holds back and releases only if needed.
        hide_contingency = _officer_role(self.request.user) in COUNCIL_ROLES
        approved_by_prog = {}
        for item in BriefFinancialApprovalItem.objects.filter(
            project=project, bfa__status='APPROVED'
        ).select_related('program'):
            pid = item.program_id or project.program_id
            if pid is None:
                continue
            contingency = Decimal('0') if hide_contingency else (item.contingency_amount or 0)
            approved_by_prog[pid] = approved_by_prog.get(pid, Decimal('0')) + (
                (item.funding_amount or 0) + contingency
            )
        released_by_prog = {}
        for a in PaymentAllocation.objects.filter(payment__project=project):
            released_by_prog[a.program_id] = released_by_prog.get(a.program_id, Decimal('0')) + a.amount
        all_program_ids = set(approved_by_prog) | set(released_by_prog)
        if all_program_ids:
            program_map = {p.pk: p for p in Program.objects.filter(pk__in=all_program_ids)}
            grand_approved = sum(approved_by_prog.values()) or Decimal('1')
            rows = []
            for pid in all_program_ids:
                approved = approved_by_prog.get(pid, Decimal('0'))
                released = released_by_prog.get(pid, Decimal('0'))
                share = (approved / grand_approved * Decimal('100')) if grand_approved else Decimal('0')
                drawdown = (released / approved * Decimal('100')) if approved else Decimal('0')
                rows.append({
                    'program': program_map.get(pid),
                    'approved': approved,
                    'released': released,
                    'share': share,
                    'drawdown_pct': drawdown,
                    'is_primary': pid == project.program_id,
                })
            rows.sort(key=lambda r: (-r['approved'], r['program'].name if r['program'] else ''))
            ctx['funding_split'] = rows
            ctx['has_co_funding'] = len([r for r in rows if r['approved'] > 0]) > 1
        else:
            ctx['funding_split'] = []
            ctx['has_co_funding'] = False

        # KPI totals for Overview header tiles
        total_approved = sum(r['approved'] for r in ctx['funding_split']) if ctx['funding_split'] else Decimal('0')
        total_released = sum(r['released'] for r in ctx['funding_split']) if ctx['funding_split'] else Decimal('0')
        ctx['total_approved'] = total_approved
        ctx['total_released'] = total_released
        ctx['total_remaining'] = total_approved - total_released
        ctx['drawdown_pct'] = int(total_released / total_approved * 100) if total_approved else 0

        # Estimated cost of all child works — what the project should be funded for.
        # Lets the user compare the bottom-up works estimate against the BFA approval
        # and see how much more funding to apply for.
        from django.db.models import Sum, F
        from apps.core.models import Work
        works_cost = Work.objects.filter(project=project).aggregate(
            total=Sum(F('estimated_cost') * F('quantity'))
        )['total'] or Decimal('0')
        ctx['total_works_cost'] = works_cost
        ctx['funding_gap'] = works_cost - total_approved

        # Timeline milestones with pre-computed left-% for CSS positioning
        from datetime import date as _date_t
        _today = _date_t.today()
        _ms = []

        def _add_ms(d, kind, label):
            if d:
                _ms.append({'date': d, 'kind': kind, 'label': label})

        _add_ms(project.start_date,
                'done' if project.start_date and project.start_date <= _today else 'forecast',
                'Start')
        _add_ms(project.stage1_target_date,
                'done' if project.stage1_target_date and project.stage1_target_date <= _today else 'forecast',
                'S1 Target')
        _add_ms(project.stage1_sunset_date, 'sunset', 'S1 Sunset')
        _add_ms(project.stage2_target_date,
                'done' if project.stage2_target_date and project.stage2_target_date <= _today else 'forecast',
                'S2 Target')
        _add_ms(project.stage2_sunset_date, 'sunset', 'S2 Sunset')
        _pc = project.practical_completion_date
        _fpc = project.forecast_practical_completion_date
        if _pc:
            _add_ms(_pc, 'done', 'PC')
        elif _fpc:
            _add_ms(_fpc, 'breach' if project.pc_breaches_sunset else 'forecast', 'Forecast PC')
        _ho = project.handover_date
        _fho = project.forecast_handover_date
        if _ho:
            _add_ms(_ho, 'done', 'Handover')
        elif _fho:
            _add_ms(_fho, 'forecast', 'Handover')

        if _ms:
            _all_dates = [m['date'] for m in _ms] + [_today]
            _min, _max = min(_all_dates), max(_all_dates)
            _span = max((_max - _min).days, 1)
            for m in _ms:
                m['pct'] = round(max(0.0, min(100.0, (m['date'] - _min).days / _span * 100)), 1)
            ctx['timeline_milestones'] = _ms
            ctx['timeline_today_pct'] = round(max(0.0, min(100.0, (_today - _min).days / _span * 100)), 1)
        else:
            ctx['timeline_milestones'] = []
            ctx['timeline_today_pct'] = 50

        # Land-specific context
        if project.project_type == Project.Type.LAND:
            from apps.core.models import LandPreCondition
            existing = {f.category: f for f in project.land_pre_conditions.all()}
            ctx['land_pre_conditions'] = [
                existing.get(cat) or LandPreCondition(project=project, category=cat, status=LandPreCondition.TrafficLight.RED)
                for cat, _ in LandPreCondition.Category.choices
            ]
            ctx['lpc_green'] = sum(1 for f in ctx['land_pre_conditions'] if f.status == 'GRN')
            ctx['lpc_amber'] = sum(1 for f in ctx['land_pre_conditions'] if f.status == 'AMB')
            ctx['lpc_red'] = sum(1 for f in ctx['land_pre_conditions'] if f.status == 'RED')
            ctx['lpc_all_clear'] = (ctx['lpc_green'] == len(ctx['land_pre_conditions']))
            ctx['da'] = project.development_application
            ctx['land_parcels'] = project.land_parcels.all()
            ctx['child_dwellings'] = project.child_dwellings.select_related(
                'council', 'program', 'funding_schedule'
            ).order_by('name')

        return ctx

    def get_template_names(self):
        if self.object.project_type == Project.Type.LAND:
            return ['projects/land_detail.html']
        return ['projects/detail.html']


class ProjectUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Project
    template_name = 'crud/form.html'
    fields = ['name', 'council', 'program', 'project_type', 'cashflow_method', 'financial_year',
              'financial_year_completed', 'lead_officer',
              'state', 'dwelling_status', 'qbuild_delivered',
              'stage1_item_group', 'stage2_item_group', 'quarterly_report_item_group',
              'sap_ion', 'cli_no', 'initial_caa_date']
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Project: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        ctx['advanced_fields'] = _PROJECT_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(
            ctx['form'].has_error(f) for f in _PROJECT_ADVANCED_FIELDS
        )
        return ctx


class ProjectDeleteView(WriteRequiredMixin, DeleteView):
    # Deleting a project is destructive — it cascades to works, addresses,
    # payments, funding allocations etc. Restrict to RICD Managers and
    # superusers only (regular officers and council/read-only roles cannot).
    required_roles = MANAGER_ROLES
    model = Project
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:projects_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:projects_list')
        return ctx


class ProjectArchiveView(WriteRequiredMixin, View):
    """Reversible archive — for projects that were cancelled / never finished.
    Keeps the record but hides it from active lists. FNC staff only."""
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.is_archived = True
        project.archived_at = timezone.now()
        project.archived_reason = (request.POST.get('reason') or '').strip()[:255]
        project.save(update_fields=['is_archived', 'archived_at', 'archived_reason', 'updated_at'])
        messages.success(request, f"Project '{project.name}' archived.")
        return redirect('ui:project_detail', pk=pk)


class ProjectUnarchiveView(WriteRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.is_archived = False
        project.archived_at = None
        project.archived_reason = ''
        project.save(update_fields=['is_archived', 'archived_at', 'archived_reason', 'updated_at'])
        messages.success(request, f"Project '{project.name}' restored from archive.")
        return redirect('ui:project_detail', pk=pk)


class ProjectTransferWorksView(WriteRequiredMixin, View):
    """Move works from this project to another project of the SAME council.
    Moving a work also moves its address (and any sibling works at that address)
    so an address never spans two projects. FNC staff only."""
    template_name = 'projects/transfer_works.html'

    def _targets(self, source):
        return (Project.objects.filter(council=source.council, is_archived=False)
                .exclude(pk=source.pk).order_by('name'))

    def get(self, request, pk):
        source = get_object_or_404(Project, pk=pk)
        return render(request, self.template_name, {
            'source': source,
            'works': source.works.select_related('work_type', 'address').order_by('id'),
            'targets': self._targets(source),
        })

    def post(self, request, pk):
        source = get_object_or_404(Project, pk=pk)
        target = (Project.objects.filter(
            pk=request.POST.get('target_project'), council=source.council
        ).exclude(pk=source.pk).first())
        work_ids = request.POST.getlist('works')
        if not target:
            messages.error(request, 'Choose a valid target project in the same council.')
            return redirect('ui:project_transfer_works', pk=pk)
        if not work_ids:
            messages.error(request, 'Select at least one work to move.')
            return redirect('ui:project_transfer_works', pk=pk)

        moved = set()

        def _move(w):
            if w.pk in moved:
                return
            w.project = target
            w.save(update_fields=['project', 'updated_at'])
            moved.add(w.pk)

        for w in Work.objects.filter(pk__in=work_ids, project=source).select_related('address'):
            _move(w)
            if w.address_id:
                if w.address.project_id != target.pk:
                    Address.objects.filter(pk=w.address_id).update(project=target)
                for sib in Work.objects.filter(address_id=w.address_id):
                    _move(sib)

        messages.success(
            request,
            f"Moved {len(moved)} work{'' if len(moved) == 1 else 's'} to '{target.name}'. "
            "Any addresses (and their works) moved with them."
        )
        return redirect(f"{reverse('ui:project_detail', kwargs={'pk': pk})}?tab=works")


class ProjectSetCompletionDatesView(WriteRequiredMixin, View):
    """Project-level bulk set: apply Start / PC / Handover dates to every Work.

    The user normally sets these at the project level — all works in a project
    typically share a schedule. Accepts up to 5 optional date fields
    (actual start, forecast PC, actual PC, forecast handover, actual handover)
    and writes each non-blank value down to every child Work. Blank values are
    ignored. Saving `actual_start_date` triggers the rolling-forecast cascade
    via the post_save signal — every child Work's per-step forecasts roll
    forward and Work.forecast_practical_completion_date is recomputed.
    """
    def post(self, request, pk):
        from datetime import datetime
        project = get_object_or_404(Project, pk=pk)
        fields_map = {
            'actual_start_date': request.POST.get('actual_start_date', '').strip(),
            'forecast_practical_completion_date': request.POST.get('forecast_practical_completion_date', '').strip(),
            'practical_completion_date': request.POST.get('practical_completion_date', '').strip(),
            'forecast_handover_date': request.POST.get('forecast_handover_date', '').strip(),
            'handover_date': request.POST.get('handover_date', '').strip(),
        }
        updates = {}
        for field, raw in fields_map.items():
            if not raw:
                continue
            try:
                updates[field] = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, f"Invalid date format for {field}: {raw!r}. Expected YYYY-MM-DD.")
                return redirect('ui:project_detail', pk=pk)
        if not updates:
            messages.warning(request, "No dates provided.")
            return redirect('ui:project_detail', pk=pk)
        works = list(project.works.all())
        for w in works:
            for field, value in updates.items():
                setattr(w, field, value)
            # NB: omit update_fields so the post_save signal sees a generic
            # change and recalculate_forecast (when cashflow_method=WORKSTEP)
            # is allowed to re-enter and roll dates forward.
            w.save()
        messages.success(
            request,
            f"Applied {len(updates)} date(s) to {len(works)} work(s). "
            f"Forecast schedule recalculated where applicable."
        )
        return redirect('ui:project_detail', pk=pk)


# ---------------------------------------------------------------------------
# WorkType
# ---------------------------------------------------------------------------

class WorkTypeListView(CouncilOrFNCMixin, ListView):
    model = WorkType
    template_name = 'work_types/list.html'
    context_object_name = 'work_types'
    paginate_by = 50


from apps.ui.views.popup_mixin import PopupAwareCreateMixin


class WorkTypeCreateView(PopupAwareCreateMixin, WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
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
    ordering = ['-created_at']


from django import forms as _forms


class FundingScheduleForm(_forms.ModelForm):
    """FS form with multi-select for child projects (via Project.funding_schedule FK).

    The legacy single `project` FK is kept on the model as the "primary" project
    but is set automatically to the first selected project; it's not editable here.
    """
    projects = _forms.ModelMultipleChoiceField(
        queryset=Project.objects.all().order_by('name'),
        required=False,
        widget=_forms.SelectMultiple(attrs={'size': '10', 'class': 'form-select'}),
        help_text="Hold Ctrl/Cmd to select multiple projects. Only projects belonging to "
                  "the Funding Agreement's council are valid.",
    )
    amount = _forms.DecimalField(max_digits=12, decimal_places=2, required=False, initial=0)
    council_contribution_amount = _forms.DecimalField(max_digits=12, decimal_places=2, required=False, initial=0)

    class Meta:
        model = FundingSchedule
        fields = ['funding_agreement', 'payment_rule', 'schedule_number', 'status',
                  'amount', 'council_contribution_amount',
                  'lease_clause_type',
                  'start_date', 'stage1_target_date', 'stage1_sunset_date',
                  'stage2_target_date', 'stage2_sunset_date',
                  'stage1_item_group', 'stage2_item_group']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope project picker to the FA's council if we already know one
        fa = None
        if self.instance and self.instance.pk and self.instance.funding_agreement_id:
            fa = self.instance.funding_agreement
        if fa and fa.council_id:
            self.fields['projects'].queryset = (
                Project.objects.filter(council=fa.council).order_by('name')
            )
            self.fields['projects'].help_text = (
                f"Only projects of {fa.council.name} (the Funding Agreement's council) "
                f"are listed."
            )
        # Lock the Funding Agreement dropdown to this schedule's council, so the FS
        # can't be reassigned to a different council's agreement. The council is
        # derived from the FA (FA->Council is 1:1), so on edit we know it already.
        council = None
        if self.instance and self.instance.pk:
            council = self.instance.council or (fa.council if fa else None)
        if council:
            self.fields['funding_agreement'].queryset = (
                FundingAgreement.objects.filter(council=council)
            )
            self.fields['funding_agreement'].help_text = (
                f"Only {council.name}'s Funding Agreement is selectable — a schedule "
                f"cannot move to another council."
            )
        if self.instance and self.instance.pk:
            self.fields['projects'].initial = self.instance.projects.all()

    def clean(self):
        cleaned = super().clean()
        from decimal import Decimal
        if cleaned.get('amount') is None:
            cleaned['amount'] = Decimal('0')
        if cleaned.get('council_contribution_amount') is None:
            cleaned['council_contribution_amount'] = Decimal('0')
        # Enforce: every selected project must belong to the FA's council
        fa = cleaned.get('funding_agreement')
        selected = cleaned.get('projects') or []
        if fa and fa.council_id and selected:
            wrong = [p for p in selected if p.council_id != fa.council_id]
            if wrong:
                names = ', '.join(p.name for p in wrong)
                raise _forms.ValidationError(
                    f"These projects don't belong to {fa.council.name} (the Funding "
                    f"Agreement's council): {names}. "
                    "Remove them or pick a different Funding Agreement."
                )
        return cleaned

    def save(self, commit=True):
        fs = super().save(commit=commit)
        if commit:
            self._sync_projects(fs)
        else:
            # save_m2m-style: caller invokes form.save_m2m()
            self.save_m2m_orig = self.save_m2m
            def _save_m2m():
                self.save_m2m_orig()
                self._sync_projects(fs)
            self.save_m2m = _save_m2m
        return fs

    def _sync_projects(self, fs):
        selected = set(self.cleaned_data.get('projects', []))
        current = set(fs.projects.all())
        # Attach newly-selected projects
        for p in selected - current:
            p.funding_schedule = fs
            p.save(update_fields=['funding_schedule'])
        # Detach projects no longer selected
        for p in current - selected:
            p.funding_schedule = None
            p.save(update_fields=['funding_schedule'])
        # Mirror first selection into the legacy `project` FK for back-compat
        if selected and fs.project_id not in {p.pk for p in selected}:
            fs.project = next(iter(selected))
            fs.save(update_fields=['project'])


class FundingScheduleCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = FundingSchedule
    form_class = FundingScheduleForm
    template_name = 'crud/form.html'
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
        from apps.core.models import AuditLog, Work, Address, Defect, Comment
        from django.contrib.contenttypes.models import ContentType
        fs = self.object
        child_projects = list(fs.projects.select_related('council', 'program').all())
        child_ids = [p.pk for p in child_projects]

        ctx['audit_logs'] = AuditLog.objects.filter(
            entity_type='fundingschedule', entity_id=fs.pk
        ).order_by('-timestamp')[:10]

        # Aggregated rollups across all child projects
        ctx['rollup_works'] = (
            Work.objects.filter(project_id__in=child_ids)
            .select_related('project', 'work_type', 'address')
            .order_by('project__name', 'work_type__name')
        )
        ctx['rollup_addresses'] = (
            Address.objects.filter(project_id__in=child_ids)
            .select_related('project', 'suburb')
            .order_by('project__name', 'street')
        )
        ctx['rollup_defects'] = (
            Defect.objects.filter(project_id__in=child_ids)
            .select_related('project')
            .order_by('-identified_date')
        )

        # Comments across child projects (FS-own comments already injected by CommentsMixin)
        if child_ids:
            project_ct = ContentType.objects.get_for_model(Project)
            ctx['rollup_child_comments'] = (
                Comment.objects.filter(content_type=project_ct, object_id__in=child_ids)
                .select_related('author')
                .order_by('-created_at')[:50]
            )
        else:
            ctx['rollup_child_comments'] = Comment.objects.none()

        # Funding sufficiency (allocations vs approved BFA funding, contingency excluded)
        ctx['funding_has_bfa'] = fs.has_approved_bfa()
        ctx['funding_available'] = fs.approved_bfa_funding_only_for_children
        ctx['funding_allocated'] = fs.total_allocated()
        ctx['funding_shortfall'] = fs.funding_shortfall()
        ctx['funding_sufficient'] = fs.is_funding_sufficient()
        ctx['generated_payment_count'] = fs.payments.count()
        return ctx


class FundingScheduleGenerateInstalmentsView(WriteRequiredMixin, View):
    """Generate per-project sub-payment instalment records for the schedule."""

    def post(self, request, pk):
        fs = get_object_or_404(FundingSchedule, pk=pk)
        if fs.funding_shortfall() is not None and fs.funding_shortfall() < 0:
            messages.error(
                request,
                "Allocations exceed the approved BFA funding for this schedule — "
                "resolve the shortfall before generating instalments."
            )
            return redirect('ui:funding_schedule_detail', pk=pk)
        created, total = fs.generate_project_instalments()
        if created:
            messages.success(
                request,
                f"Generated {created} per-project instalment payment{'' if created == 1 else 's'} "
                f"(total ${total:,.2f}). Dates follow each project's payment milestone schedule."
            )
        else:
            messages.info(
                request,
                "No instalments generated — check the schedule has a payment rule with "
                "milestones and projects with WorkFunding allocations (existing payments are kept)."
            )
        return redirect('ui:funding_schedule_detail', pk=pk)


class FundingScheduleContractReportView(CouncilScopedMixin, CouncilOrFNCMixin, NoticesMixin, DetailView):
    """Contract Management Report — single-page operational summary for a Funding Schedule.

    Combines: financial snapshot, contracts + meetings, payment timeline,
    variations, lifecycle health (PC/Handover + defects), recent activity.
    """
    model = FundingSchedule
    council_filter_field = 'project__council'
    template_name = 'funding_schedules/contract_report.html'
    context_object_name = 'fs'

    def get_context_data(self, **kwargs):
        from decimal import Decimal
        from datetime import date
        from django.db.models import Sum, Count, Q
        from apps.core.models import (
            AuditLog, Work, Defect, PaymentAllocation,
            BriefFinancialApprovalItem, Contract, ContractMeeting,
        )
        ctx = super().get_context_data(**kwargs)
        fs = self.object
        child_projects = list(fs.projects.select_related('council', 'program').all())
        child_ids = [p.pk for p in child_projects]

        # ── Financial snapshot ────────────────────────────────────────────
        approved = (
            BriefFinancialApprovalItem.objects
            .filter(project_id__in=child_ids, bfa__status='APPROVED')
            .aggregate(t=Sum('funding_amount'), c=Sum('contingency_amount'))
        )
        approved_funding = approved['t'] or Decimal('0')
        # Council users must never see contingency (FNC holds it back, releases only if needed).
        hide_contingency = _officer_role(self.request.user) in COUNCIL_ROLES
        approved_contingency = Decimal('0') if hide_contingency else (approved['c'] or Decimal('0'))
        released_total = (
            PaymentAllocation.objects.filter(payment__funding_schedule=fs)
            .aggregate(t=Sum('amount'))['t'] or Decimal('0')
        )
        ctx['financial'] = {
            'approved_funding': approved_funding,
            'approved_contingency': approved_contingency,
            'approved_grand': approved_funding + approved_contingency,
            'fs_amount': fs.amount or Decimal('0'),
            'council_contribution': fs.council_contribution_amount or Decimal('0'),
            'released': released_total,
            'remaining': (fs.amount or Decimal('0')) - released_total,
            'drawdown_pct': (released_total / fs.amount * Decimal('100')) if fs.amount else Decimal('0'),
        }

        # ── Payments timeline ─────────────────────────────────────────────
        ctx['payments'] = (
            fs.payments
            .select_related('project', 'approved_by', 'recommended_by')
            .order_by('payment_type', 'forecast_release_date', 'created_at')
        )

        # ── Contracts + meetings ──────────────────────────────────────────
        contracts = (
            Contract.objects.filter(project_id__in=child_ids)
            .select_related('project')
            .prefetch_related('meetings')
            .order_by('project__name', 'title')
        )
        ctx['contracts'] = contracts
        ctx['meetings'] = (
            ContractMeeting.objects.filter(contract__project_id__in=child_ids)
            .select_related('contract__project')
            .order_by('-meeting_date')[:30]
        )

        # ── Variations on this FS ─────────────────────────────────────────
        ctx['variations'] = (
            fs.variations.select_related('variation_type')
            .order_by('-created_at')
        )

        # ── Lifecycle health ─────────────────────────────────────────────
        today = date.today()
        works = Work.objects.filter(project_id__in=child_ids).select_related('project', 'work_type', 'address')
        work_total = works.count()
        work_pc_complete = works.filter(practical_completion_date__isnull=False).count()
        work_handover_complete = works.filter(handover_date__isnull=False).count()
        sunset_breach = [
            w for w in works
            if w.forecast_practical_completion_date and w.project.stage2_sunset_date
            and (w.forecast_practical_completion_date - w.project.stage2_sunset_date).days > 30
        ]
        defects = Defect.objects.filter(project_id__in=child_ids)
        defects_open = defects.filter(rectified_date__isnull=True).count() if hasattr(Defect, 'rectified_date') else defects.count()
        ctx['lifecycle'] = {
            'work_total': work_total,
            'work_pc_complete': work_pc_complete,
            'work_handover_complete': work_handover_complete,
            'pc_pct': (work_pc_complete / work_total * 100) if work_total else 0,
            'handover_pct': (work_handover_complete / work_total * 100) if work_total else 0,
            'sunset_breach': sunset_breach,
            'defects_open': defects_open,
            'defects_total': defects.count(),
        }

        # ── Recent activity ──────────────────────────────────────────────
        ctx['audit_logs'] = (
            AuditLog.objects.filter(
                Q(entity_type='fundingschedule', entity_id=fs.pk)
                | Q(entity_type='payment', entity_id__in=fs.payments.values_list('pk', flat=True))
            ).order_by('-timestamp')[:15]
        )
        ctx['child_projects'] = child_projects
        return ctx


class FundingScheduleUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = FundingSchedule
    form_class = FundingScheduleForm
    template_name = 'crud/form.html'
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
    fields = ['project', 'funding_schedule', 'work', 'payment_type', 'calculation_type',
              'payment_split', 'percentage', 'amount', 'forecast_anchor',
              'forecast_release_date', 'status']

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_initial(self):
        return {'project': self.kwargs['project_pk']}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'work' in form.fields:
            form.fields['work'].queryset = Work.objects.filter(project_id=self.kwargs['project_pk'])
        return form

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
        from apps.core.models import AuditLog, Program
        ctx['audit_logs'] = AuditLog.objects.filter(
            entity_type='payment', entity_id=self.object.pk
        ).order_by('-timestamp')[:10]
        # Forecast split (only meaningful when not yet RELEASED)
        if self.object.status != Payment.Status.RELEASED:
            split = self.object.compute_program_split()
            program_map = {p.pk: p for p in Program.objects.filter(pk__in=split.keys())}
            ctx['forecast_split'] = [
                {'program': program_map.get(pid), 'amount': amount, 'ratio': ratio}
                for pid, (amount, ratio) in split.items()
                if program_map.get(pid) is not None
            ]
        return ctx


class PaymentUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Payment
    template_name = 'crud/form.html'
    fields = ['project', 'funding_schedule', 'work', 'payment_type', 'calculation_type',
              'payment_split', 'percentage', 'amount', 'forecast_anchor',
              'forecast_release_date', 'status']

    def get_success_url(self):
        return reverse_lazy('ui:payment_list', kwargs={'project_pk': self.kwargs['project_pk']})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if 'work' in form.fields:
            form.fields['work'].queryset = Work.objects.filter(project_id=self.kwargs['project_pk'])
        return form

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

    def get_initial(self):
        initial = super().get_initial()
        project_id = self.request.GET.get('project')
        if project_id:
            initial['project'] = project_id
        return initial

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Funding Notice'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))
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

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Funding Notice — {self.object.project.name}'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))
        return ctx


class FundingNoticeDeleteView(WriteRequiredMixin, DeleteView):
    model = FundingNotice
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:funding_notice_list'))
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

def _bfa_item_formset_factory():
    """Inline formset for BFA -> items.

    `program` is optional in the form (auto-defaults to project.program in
    BFAItem.save) — set it explicitly when capturing co-funding from a
    different program. cost_centre / gl_code stay out of the form (inherited
    from the resolved program). contingency_amount defaults to 10% of
    funding_amount when blank.
    """
    from django.forms import inlineformset_factory
    from apps.core.models import BriefFinancialApprovalItem
    return inlineformset_factory(
        BriefFinancialApproval, BriefFinancialApprovalItem,
        fields=['project', 'program', 'funding_amount', 'contingency_amount'],
        extra=1, can_delete=True,
    )


class BriefFinancialApprovalGlobalListView(InternalOnlyMixin, ListView):
    """All BFAs across all councils — used by the sidebar nav link. FNC/internal only."""
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/list.html'
    context_object_name = 'approvals'
    paginate_by = 50

    def get_queryset(self):
        return BriefFinancialApproval.objects.prefetch_related('items__project__council').order_by('-created_at')


class BriefFinancialApprovalListView(InternalOnlyMixin, ListView):
    """Legacy per-project BFA list: shows BFAs that include the given project. FNC/internal only."""
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/list.html'
    context_object_name = 'approvals'

    def get_queryset(self):
        return BriefFinancialApproval.objects.filter(
            items__project_id=self.kwargs['project_pk']
        ).prefetch_related('items__project__council').distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return ctx


class BriefFinancialApprovalCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/form.html'
    fields = ['mincor_reference', 'document_uri', 'human_rights_assessment_uri', 'delegate_level', 'comments']
    success_url = reverse_lazy('ui:bfa_global_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        FormSet = _bfa_item_formset_factory()
        if self.request.method == 'POST':
            ctx['items_formset'] = FormSet(self.request.POST, instance=self.object)
        else:
            ctx['items_formset'] = FormSet(instance=self.object)
        ctx['title'] = 'Create Brief Financial Approval'
        ctx['back_url'] = reverse_lazy('ui:bfa_global_list')
        return ctx

    def form_valid(self, form):
        FormSet = _bfa_item_formset_factory()
        self.object = form.save(commit=False)
        formset = FormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            self.object.save()
            formset.instance = self.object
            formset.save()
            return redirect('ui:bfa_detail', pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class BriefFinancialApprovalDetailView(InternalOnlyMixin, NoticesMixin, DetailView):
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/detail.html'
    context_object_name = 'bfa'

    def get_queryset(self):
        return BriefFinancialApproval.objects.prefetch_related('items__project__council')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('project').all()
        return ctx


class BriefFinancialApprovalUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = BriefFinancialApproval
    template_name = 'brief_financial_approvals/form.html'
    fields = ['mincor_reference', 'document_uri', 'human_rights_assessment_uri', 'delegate_level', 'comments']

    def get_success_url(self):
        return reverse_lazy('ui:bfa_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        FormSet = _bfa_item_formset_factory()
        if self.request.method == 'POST':
            ctx['items_formset'] = FormSet(self.request.POST, instance=self.object)
        else:
            ctx['items_formset'] = FormSet(instance=self.object)
        ctx['title'] = f'Edit Brief Financial Approval #{self.object.pk}'
        ctx['back_url'] = reverse_lazy('ui:bfa_detail', kwargs={'pk': self.object.pk})
        return ctx

    def form_valid(self, form):
        FormSet = _bfa_item_formset_factory()
        formset = FormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            self.object = form.save()
            formset.save()
            return redirect('ui:bfa_detail', pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class BriefFinancialApprovalDeleteView(WriteRequiredMixin, DeleteView):
    model = BriefFinancialApproval
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:bfa_global_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:bfa_global_list')
        return ctx


class BriefFinancialApprovalApproveView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = MANAGER_ROLES
    def post(self, request, pk):
        bfa = get_object_or_404(BriefFinancialApproval, pk=pk)
        if bfa.status != BriefFinancialApproval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be approved.')
            return redirect('ui:bfa_detail', pk=pk)
        bfa.status = BriefFinancialApproval.Status.APPROVED
        bfa.approved_by = request.user
        bfa.approved_at = timezone.now()
        bfa.save()
        messages.success(request, 'Brief Financial Approval approved.')
        return redirect('ui:bfa_detail', pk=pk)


class BriefFinancialApprovalRejectView(FNCOnlyMixin, View):
    def post(self, request, pk):
        bfa = get_object_or_404(BriefFinancialApproval, pk=pk)
        if bfa.status != BriefFinancialApproval.Status.PENDING:
            messages.error(request, 'Only pending approvals can be rejected.')
            return redirect('ui:bfa_detail', pk=pk)
        bfa.status = BriefFinancialApproval.Status.REJECTED
        bfa.save()
        messages.success(request, 'Brief Financial Approval rejected.')
        return redirect('ui:bfa_detail', pk=pk)


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
              'estimated_cost', 'status', 'is_notional_cost', 'actual_cost', 'address',
              'contractor',
              'forecast_practical_completion_date', 'practical_completion_date',
              'forecast_handover_date', 'handover_date',
              'floor_number', 'livable_housing_level', 'usage_type',
              'floor_material', 'frame_material', 'wall_material', 'roof_material', 'car_accommodation',
              'bathrooms_count', 'kitchens_count', 'living_rooms_count']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get('instance') is None:
            kwargs['instance'] = Work(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_form(self, form_class=None):
        from apps.ui.widgets import PopupAddSelect
        form = super().get_form(form_class)
        if 'work_type' in form.fields:
            form.fields['work_type'].widget = PopupAddSelect(
                add_url=reverse('ui:work_type_create'), add_label='Add work type',
                choices=form.fields['work_type'].choices,
            )
        if 'contractor' in form.fields:
            council_id = Project.objects.filter(
                pk=self.kwargs['project_pk']
            ).values_list('council_id', flat=True).first()
            if council_id:
                form.fields['contractor'].queryset = Contractor.objects.filter(
                    council_id=council_id, is_active=True
                )
            add_url = reverse('ui:contractor_quick_add')
            if council_id:
                add_url += f'?council={council_id}'
            form.fields['contractor'].widget = PopupAddSelect(
                add_url=add_url, add_label='Add contractor',
                choices=form.fields['contractor'].choices,
            )
            form.fields['contractor'].help_text = (
                "If the Council will NOT be the principal contractor, add the contractor here."
            )
        if 'address' in form.fields:
            from apps.core.models import Address
            council_id = Project.objects.filter(
                pk=self.kwargs['project_pk']
            ).values_list('council_id', flat=True).first()
            if council_id:
                form.fields['address'].queryset = (
                    Address.objects.filter(project__council_id=council_id)
                    .select_related('project', 'suburb')
                )
            form.fields['address'].help_text = "Only addresses under this council's projects."
        return form

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.kwargs['project_pk']}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Work Item'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.kwargs['project_pk']}))
        ctx['advanced_fields'] = _WORK_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(ctx['form'].has_error(f) for f in _WORK_ADVANCED_FIELDS)
        return ctx


def _worksteps_inline_formset():
    """Inline formset for editing per-step actual_completion_date / is_active on a Work."""
    from django.forms import inlineformset_factory, DateInput
    class _WorkStepForm(_forms.ModelForm):
        class Meta:
            model = WorkStep
            fields = ['actual_completion_date', 'is_active']
            widgets = {'actual_completion_date': DateInput(attrs={'type': 'date'})}
    return inlineformset_factory(
        Work, WorkStep,
        form=_WorkStepForm,
        extra=0, can_delete=False,
    )


class _WorkAnchorForm(_forms.ModelForm):
    """The 'forecast anchor' for the rolling-forecast page.

    actual_start_date → forward scheduling: step dates cascade left-to-right.
    forecast_handover_date → backward scheduling when no actual start is set:
    step dates cascade right-to-left from the target.  When a start IS known,
    forecast_handover_date is preserved as a manual delivery target if it
    differs from the computed PC; otherwise it tracks PC automatically.
    """
    class Meta:
        model = Work
        fields = ['actual_start_date', 'forecast_handover_date']
        widgets = {
            'actual_start_date': _forms.DateInput(attrs={'type': 'date'}),
            'forecast_handover_date': _forms.DateInput(attrs={'type': 'date'}),
        }


class WorkDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    """Work detail with inline editable rolling-forecast schedule.

    The page bundles three things into one Save:
      - Anchor form: actual_start_date (forecast cascade input)
      - Steps formset: per-step actual_completion_date + is_active toggles
    After save, recalculate_forecast rolls every downstream forecast forward
    based on actuals, then mirrors the final step date onto
    Work.forecast_practical_completion_date and forecast_handover_date.
    """
    model = Work
    council_filter_field = 'project__council'
    template_name = 'works/detail.html'
    context_object_name = 'work'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        work = self.object
        FormSet = _worksteps_inline_formset()
        ctx['anchor_form'] = kwargs.get('anchor_form') or _WorkAnchorForm(instance=work)
        ctx['step_formset'] = kwargs.get('step_formset') or FormSet(
            instance=work,
            queryset=work.steps.select_related('group_item').order_by('order'),
            prefix='steps',
        )
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        work = self.object
        FormSet = _worksteps_inline_formset()
        anchor_form = _WorkAnchorForm(request.POST, instance=work)
        step_formset = FormSet(request.POST, instance=work, prefix='steps')
        if anchor_form.is_valid() and step_formset.is_valid():
            anchor_form.save()
            step_formset.save()
            from apps.core.services.workstep_forecast import recalculate_forecast
            recalculate_forecast(work)
            messages.success(request, 'Saved. Forecast recalculated from latest dates.')
            return redirect('ui:work_detail', project_pk=kwargs['project_pk'], pk=kwargs['pk'])
        messages.error(request, 'Some rows have errors — fix the highlighted fields.')
        ctx = self.get_context_data(anchor_form=anchor_form, step_formset=step_formset)
        return self.render_to_response(ctx)


class WorkUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Work
    template_name = 'crud/form.html'
    fields = ['work_type', 'work_type_other', 'bedrooms', 'quantity',
              'estimated_cost', 'status', 'is_notional_cost', 'actual_cost',
              'forecast_final_cost', 'costs_finalised', 'address',
              'contractor', 'floor_area', 'drawing_no',
              'cashflow_method', 'step_group', 'actual_start_date',
              'forecast_practical_completion_date', 'practical_completion_date',
              'forecast_handover_date', 'handover_date',
              'floor_number', 'livable_housing_level', 'usage_type',
              'floor_material', 'frame_material', 'wall_material', 'roof_material', 'car_accommodation',
              'bathrooms_count', 'kitchens_count', 'living_rooms_count',
              'notes']

    def get_form(self, form_class=None):
        from apps.ui.widgets import PopupAddSelect
        form = super().get_form(form_class)
        if 'work_type' in form.fields:
            form.fields['work_type'].widget = PopupAddSelect(
                add_url=reverse('ui:work_type_create'), add_label='Add work type',
                choices=form.fields['work_type'].choices,
            )
        if 'contractor' in form.fields:
            council_id = self.object.project.council_id if self.object and self.object.project_id else None
            if council_id:
                form.fields['contractor'].queryset = Contractor.objects.filter(
                    council_id=council_id, is_active=True
                )
            add_url = reverse('ui:contractor_quick_add')
            if council_id:
                add_url += f'?council={council_id}'
            form.fields['contractor'].widget = PopupAddSelect(
                add_url=add_url, add_label='Add contractor',
                choices=form.fields['contractor'].choices,
            )
            form.fields['contractor'].help_text = (
                "If the Council will NOT be the principal contractor, add the contractor here."
            )
        if 'address' in form.fields:
            from apps.core.models import Address
            council_id = self.object.project.council_id if (self.object and self.object.project_id) else None
            if council_id:
                form.fields['address'].queryset = (
                    Address.objects.filter(project__council_id=council_id)
                    .select_related('project', 'suburb')
                )
            form.fields['address'].help_text = "Only addresses under this council's projects."
        return form

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Work: {self.object}'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id}))
        ctx['advanced_fields'] = _WORK_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(ctx['form'].has_error(f) for f in _WORK_ADVANCED_FIELDS)
        return ctx


class ContractorQuickAddView(PopupAwareCreateMixin, WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    """Inline (popup) quick-add of a contractor from a Work form, so staff don't
    have to leave to create one. Only the contractor name is required; the
    council is taken from the work's project via the ?council= query param."""
    model = Contractor
    template_name = 'crud/form.html'
    fields = ['company_name', 'abn', 'licence_number', 'email', 'phone',
              'address', 'trade_type', 'notes']

    def _council_id(self):
        return self.request.GET.get('council') or self.request.POST.get('council')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Only the name is mandatory.
        for name, field in form.fields.items():
            field.required = (name == 'company_name')
        form.fields['company_name'].label = 'Name'
        if 'licence_number' in form.fields:
            form.fields['licence_number'].label = 'QBCC licence number'
        if 'phone' in form.fields:
            form.fields['phone'].label = 'Phone'
        return form

    def form_valid(self, form):
        cid = self._council_id()
        if cid:
            form.instance.council_id = cid
        if not form.instance.trade_type:
            form.instance.trade_type = Contractor.TradeType.OTHER
        if not form.instance.council_id:
            from django.contrib import messages as _m
            _m.error(self.request, 'Could not determine the council for this contractor.')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add contractor'
        return ctx


class WorkDeleteView(WriteRequiredMixin, DeleteView):
    model = Work
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:work_list', kwargs={'project_pk': self.object.project_id}))
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


class ProjectAddressesWorksView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    """Combined Addresses & Works page for a project."""
    model = Project
    template_name = 'projects/addresses_works.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Sum
        ctx = super().get_context_data(**kwargs)
        project = self.object
        addresses = (
            Address.objects
            .filter(project=project)
            .select_related('suburb')
            .annotate(work_count=Count('works'))
            .order_by('street')
        )
        works = (
            Work.objects
            .filter(project=project)
            .select_related('work_type', 'contractor', 'address')
            .order_by('address__street', 'pk')
        )
        total = works.aggregate(total=Sum('estimated_cost'))['total'] or 0
        ctx.update({
            'addresses': addresses,
            'works': works,
            'total_cost': total,
            'is_fnc': not self.request.user.groups.filter(
                name__in=['COUNCIL_USER', 'COUNCIL_MANAGER']
            ).exists(),
        })
        return ctx


class AddressCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = Address
    template_name = 'crud/form.html'
    fields = ['street', 'suburb', 'lot', 'plan', 'residence_plc_ref',
              'land_status', 'lease_status', 'lease_executed_date']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get('instance') is None:
            kwargs['instance'] = Address(project_id=self.kwargs['project_pk'])
        return kwargs

    def get_form(self, form_class=None):
        from apps.ui.widgets import PopupAddSelect
        form = super().get_form(form_class)
        if 'suburb' in form.fields:
            form.fields['suburb'].widget = PopupAddSelect(
                add_url=reverse('ui:suburb_create'), add_label='Add suburb',
                choices=form.fields['suburb'].choices,
            )
        return form

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:project_addresses_works', kwargs={'pk': self.kwargs['project_pk']}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Address'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:project_addresses_works', kwargs={'pk': self.kwargs['project_pk']}))
        ctx['advanced_fields'] = _ADDRESS_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(ctx['form'].has_error(f) for f in _ADDRESS_ADVANCED_FIELDS)
        return ctx


class AddressDetailView(CouncilOrFNCMixin, DetailView):
    model = Address
    template_name = 'addresses/detail.html'
    context_object_name = 'address'


class AddressUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Address
    template_name = 'crud/form.html'
    fields = ['street', 'suburb', 'lot', 'plan', 'residence_plc_ref',
              'land_status', 'lease_status', 'lease_executed_date']

    def get_form(self, form_class=None):
        from apps.ui.widgets import PopupAddSelect
        form = super().get_form(form_class)
        if 'suburb' in form.fields:
            form.fields['suburb'].widget = PopupAddSelect(
                add_url=reverse('ui:suburb_create'), add_label='Add suburb',
                choices=form.fields['suburb'].choices,
            )
        return form

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Address: {self.object}'
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id}))
        ctx['advanced_fields'] = _ADDRESS_ADVANCED_FIELDS
        ctx['advanced_has_errors'] = any(ctx['form'].has_error(f) for f in _ADDRESS_ADVANCED_FIELDS)
        return ctx


class AddressDeleteView(WriteRequiredMixin, DeleteView):
    model = Address
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = _safe_next(self.request, reverse_lazy('ui:address_list', kwargs={'project_pk': self.object.project_id}))
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


class PaymentReconcileView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = MANAGER_ROLES
    def post(self, request, project_pk, pk):
        payment = get_object_or_404(Payment, pk=pk, project_id=project_pk)
        if payment.status != Payment.Status.RELEASED:
            messages.error(request, 'Only released payments can be reconciled.')
            return redirect('ui:payment_detail', project_pk=project_pk, pk=pk)
        payment.status = Payment.Status.RECONCILED
        payment.save()  # save() stamps reconciled_date
        messages.success(request, 'Payment reconciled (acquitted).')
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


class SuburbCreateView(PopupAwareCreateMixin, LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
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
# WorkStepGroup — central CRUD under Maintenance.
# Groups are stand-alone (M2M to WorkType). Both the WorkType detail page
# and the Maintenance index link here. The Clone action duplicates a group
# + its items so you can tweak from a known starting point.
# ---------------------------------------------------------------------------

class WorkStepGroupListView(LoginRequiredMixin, ListView):
    model = WorkStepGroup
    template_name = 'work_step_groups/list.html'
    context_object_name = 'groups'
    paginate_by = 50

    def get_queryset(self):
        return WorkStepGroup.objects.prefetch_related('work_types', 'items').order_by('name')


def _workstep_group_items_formset():
    """Inline formset: edit all WorkStepGroupItem rows in one grid."""
    from django.forms import inlineformset_factory
    return inlineformset_factory(
        WorkStepGroup, WorkStepGroupItem,
        fields=['order', 'step', 'expected_duration_days',
                'cost_percentage', 'stage_gate', 'is_monthly_tracker_column'],
        extra=3, can_delete=True,
    )


def _renumber_group_items(group):
    """Reset all items' order field to a clean 1..N sequence.

    Sort key: existing `order` (so user-typed values determine the relative
    rank), then `id` (stable tiebreak). Done in two phases to dodge the
    UniqueConstraint(group, order) — first move everyone to a safe high
    offset, then back down to 1..N.
    """
    items = list(group.items.order_by('order', 'id'))
    if not items:
        return
    high = (max(i.order for i in items) or 0) + 1000
    for i, item in enumerate(items, start=1):
        item.order = high + i
        item.save(update_fields=['order'])
    for i, item in enumerate(items, start=1):
        item.order = i
        item.save(update_fields=['order'])


class WorkStepGroupDetailView(LoginRequiredMixin, View):
    """Single-page inline editable grid for a Work Step Group's items.

    GET  → render the formset.
    POST → save all rows at once, then renumber sequentially so the order
           column stays clean even when the user rearranges values.
    """

    template_name = 'work_step_groups/detail.html'

    def _ctx(self, group, formset):
        return {
            'group': group,
            'formset': formset,
        }

    def get(self, request, pk):
        group = get_object_or_404(WorkStepGroup, pk=pk)
        FormSet = _workstep_group_items_formset()
        formset = FormSet(
            instance=group,
            queryset=group.items.select_related('step').order_by('order'),
            prefix='items',
        )
        return render(request, self.template_name, self._ctx(group, formset))

    def post(self, request, pk):
        group = get_object_or_404(WorkStepGroup, pk=pk)
        FormSet = _workstep_group_items_formset()
        formset = FormSet(request.POST, instance=group, prefix='items')
        if not formset.is_valid():
            messages.error(request, 'Some rows have errors — fix the highlighted fields.')
            return render(request, self.template_name, self._ctx(group, formset))
        formset.save()
        _renumber_group_items(group)
        messages.success(request, 'Saved. Order renumbered 1..N.')
        return redirect('ui:work_step_group_detail', pk=group.pk)


class WorkStepGroupCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkStepGroup
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'work_types', 'is_active']

    def get_initial(self):
        initial = super().get_initial()
        wt_pk = self.kwargs.get('wt_pk') or self.request.GET.get('work_type')
        if wt_pk:
            initial['work_types'] = [int(wt_pk)]
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wt_pk = self.kwargs.get('wt_pk')
        ctx['title'] = (
            f'Add Step Group — {get_object_or_404(WorkType, pk=wt_pk).name}'
            if wt_pk else 'Add Work Step Group'
        )
        return ctx

    def get_success_url(self):
        if self.kwargs.get('wt_pk'):
            return reverse('ui:work_type_detail', kwargs={'pk': self.kwargs['wt_pk']})
        return reverse('ui:work_step_group_detail', kwargs={'pk': self.object.pk})


class WorkStepGroupUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkStepGroup
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'work_types', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Step Group — {self.object.name}'
        return ctx

    def get_success_url(self):
        return reverse('ui:work_step_group_detail', kwargs={'pk': self.object.pk})


class WorkStepGroupCloneView(LoginRequiredMixin, View):
    """POST-only: duplicate a WorkStepGroup + its items, redirect to the new
    group's edit page so the user can rename / re-link work types immediately."""

    def post(self, request, pk):
        original = get_object_or_404(WorkStepGroup, pk=pk)
        new = original.clone()
        messages.success(
            request,
            f'Cloned "{original.name}" → "{new.name}". '
            f'Adjust the name, link the right Work Types, and edit items as needed.'
        )
        return redirect('ui:work_step_group_edit', pk=new.pk)


class WorkStepGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkStepGroup
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:work_step_group_list')


# ---------------------------------------------------------------------------
# WorkStepGroupItem — nested under WorkStepGroup
# ---------------------------------------------------------------------------

class WorkStepGroupItemCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = WorkStepGroupItem
    template_name = 'crud/form.html'
    fields = ['step', 'order', 'cost_percentage', 'expected_duration_days',
              'stage_gate', 'is_monthly_tracker_column']

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
        return reverse('ui:work_step_group_detail', kwargs={'pk': self.kwargs['group_pk']})


class WorkStepGroupItemUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = WorkStepGroupItem
    template_name = 'crud/form.html'
    fields = ['step', 'order', 'cost_percentage', 'expected_duration_days',
              'stage_gate', 'is_monthly_tracker_column']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Step — {self.object.step.name}'
        return ctx

    def get_success_url(self):
        return reverse('ui:work_step_group_detail', kwargs={'pk': self.object.group_id})


class WorkStepGroupItemDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkStepGroupItem
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:work_step_group_detail', kwargs={'pk': self.object.group_id})


# ---------------------------------------------------------------------------
# PaymentMilestoneSchedule CRUD (Maintenance) — when payments are timed
# ---------------------------------------------------------------------------

def _payment_milestone_rules_formset():
    """Inline formset: edit all PaymentMilestoneRule rows for a schedule."""
    from django.forms import inlineformset_factory
    return inlineformset_factory(
        PaymentMilestoneSchedule, PaymentMilestoneRule,
        fields=['payment_type', 'anchor_type', 'work_step_definition', 'offset_days'],
        extra=1, can_delete=True,
    )


class PaymentMilestoneScheduleListView(LoginRequiredMixin, ListView):
    model = PaymentMilestoneSchedule
    template_name = 'payment_milestones/list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        return (PaymentMilestoneSchedule.objects
                .select_related('work_step_group')
                .prefetch_related('rules'))


class PaymentMilestoneScheduleCreateView(LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
    model = PaymentMilestoneSchedule
    template_name = 'crud/form.html'
    fields = ['name', 'work_step_group', 'is_default', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Payment Milestone Schedule'
        ctx['back_url'] = reverse_lazy('ui:payment_milestone_schedule_list')
        return ctx

    def get_success_url(self):
        return reverse('ui:payment_milestone_schedule_detail', kwargs={'pk': self.object.pk})


class PaymentMilestoneScheduleUpdateView(LoginRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = PaymentMilestoneSchedule
    template_name = 'crud/form.html'
    fields = ['name', 'work_step_group', 'is_default', 'is_active']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Schedule — {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:payment_milestone_schedule_detail', kwargs={'pk': self.object.pk})
        return ctx

    def get_success_url(self):
        return reverse('ui:payment_milestone_schedule_detail', kwargs={'pk': self.object.pk})


class PaymentMilestoneScheduleDeleteView(LoginRequiredMixin, DeleteView):
    model = PaymentMilestoneSchedule
    template_name = 'crud/confirm_delete.html'

    def get_success_url(self):
        return reverse('ui:payment_milestone_schedule_list')


class PaymentMilestoneScheduleDetailView(LoginRequiredMixin, View):
    """Single-page inline grid for a schedule's payment timing rules."""

    template_name = 'payment_milestones/detail.html'

    def _ctx(self, schedule, formset):
        return {'schedule': schedule, 'formset': formset}

    def get(self, request, pk):
        schedule = get_object_or_404(PaymentMilestoneSchedule, pk=pk)
        FormSet = _payment_milestone_rules_formset()
        formset = FormSet(instance=schedule, prefix='rules')
        return render(request, self.template_name, self._ctx(schedule, formset))

    def post(self, request, pk):
        schedule = get_object_or_404(PaymentMilestoneSchedule, pk=pk)
        FormSet = _payment_milestone_rules_formset()
        formset = FormSet(request.POST, instance=schedule, prefix='rules')
        if not formset.is_valid():
            messages.error(request, 'Some rows have errors — fix the highlighted fields.')
            return render(request, self.template_name, self._ctx(schedule, formset))
        formset.save()
        messages.success(request, 'Payment timing rules saved.')
        return redirect('ui:payment_milestone_schedule_detail', pk=schedule.pk)


# ---------------------------------------------------------------------------
# ConstructionMethod CRUD (Maintenance)
# ---------------------------------------------------------------------------

class ConstructionMethodListView(LoginRequiredMixin, ListView):
    model = ConstructionMethod
    template_name = 'construction_methods/list.html'
    context_object_name = 'methods'


class ConstructionMethodCreateView(PopupAwareCreateMixin, LoginRequiredMixin, WidgetUpgradeMixin, CreateView):
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
        ctx['payment_milestone_schedule_count'] = PaymentMilestoneSchedule.objects.count()
        ctx['user_count'] = User.objects.count()
        ctx['site_settings'] = SiteSettings.get()
        ctx['active_nav'] = 'maintenance'
        return ctx


class SiteSettingsView(LoginRequiredMixin, View):
    template_name = 'maintenance/site_settings.html'

    def _check_permission(self, user):
        role = getattr(getattr(user, 'profile', None), 'officer_role', None)
        return user.is_superuser or role in {'MANAGER'}

    def get(self, request):
        if not self._check_permission(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        settings_obj = SiteSettings.get()
        return render(request, self.template_name, {
            'settings_obj': settings_obj,
            'active_nav': 'maintenance',
        })

    def post(self, request):
        if not self._check_permission(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        settings_obj = SiteSettings.get()
        reports_email = request.POST.get('reports_email', '').strip()
        from_email = request.POST.get('notifications_from_email', '').strip()
        if reports_email:
            settings_obj.reports_email = reports_email
            if from_email:
                settings_obj.notifications_from_email = from_email
            settings_obj.save()
            messages.success(request, 'Site settings updated.')
        else:
            messages.error(request, 'A valid email address is required.')
        return redirect('ui:site_settings')


class CashflowRulesView(LoginRequiredMixin, View):
    """Maintenance: stipulate how cashflow accrual is forecast per cashflow method.

    Cash basis is always milestone payments (shown read-only). The accrual basis is
    editable per method (Capital Grant / Capital Works).
    """
    template_name = 'maintenance/cashflow_rules.html'

    def _check_permission(self, user):
        role = getattr(getattr(user, 'profile', None), 'officer_role', None)
        return user.is_superuser or role in {'MANAGER'}

    def _rules(self):
        from apps.core.models import CashflowMethodRule
        return [CashflowMethodRule.get('MILESTONE'), CashflowMethodRule.get('WORKSTEP')]

    def get(self, request):
        if not self._check_permission(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        from apps.core.models import CashflowMethodRule
        return render(request, self.template_name, {
            'rules': self._rules(),
            'accrual_sources': CashflowMethodRule.AccrualSource.choices,
            'workstep_dates': CashflowMethodRule.WorkstepDate.choices,
            'cost_bases': CashflowMethodRule.CostBasis.choices,
            'active_nav': 'maintenance',
        })

    def post(self, request):
        if not self._check_permission(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        from apps.core.models import CashflowMethodRule
        valid_src = {c[0] for c in CashflowMethodRule.AccrualSource.choices}
        valid_date = {c[0] for c in CashflowMethodRule.WorkstepDate.choices}
        valid_cost = {c[0] for c in CashflowMethodRule.CostBasis.choices}
        for rule in self._rules():
            p = rule.method
            src = request.POST.get(f'{p}_accrual_source')
            wd = request.POST.get(f'{p}_workstep_date')
            cb = request.POST.get(f'{p}_cost_basis')
            if src in valid_src:
                rule.accrual_source = src
            if wd in valid_date:
                rule.workstep_date = wd
            if cb in valid_cost:
                rule.cost_basis = cb
            rule.notes = request.POST.get(f'{p}_notes', '').strip()
            rule.save()
        messages.success(request, 'Cashflow forecasting rules updated.')
        return redirect('ui:cashflow_rules')


class EmailTemplateListView(WriteRequiredMixin, ListView):
    model = EmailTemplate
    template_name = 'maintenance/email_templates.html'
    context_object_name = 'templates'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'maintenance'
        return ctx


class EmailTemplateUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = EmailTemplate
    template_name = 'maintenance/email_template_form.html'
    fields = ['subject', 'body', 'is_active']

    def get_success_url(self):
        return reverse_lazy('ui:email_template_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.core.services.notifications import EVENT_PLACEHOLDERS
        ctx['placeholders'] = EVENT_PLACEHOLDERS.get(self.object.event, [])
        ctx['event_label'] = self.object.get_event_display()
        ctx['active_nav'] = 'maintenance'
        return ctx


class NotificationLogView(WriteRequiredMixin, ListView):
    model = SentNotification
    template_name = 'maintenance/notification_log.html'
    context_object_name = 'notifications'
    paginate_by = 50

    def get_queryset(self):
        return SentNotification.objects.select_related('council', 'project').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'maintenance'
        return ctx


class EmailSettingsView(LoginRequiredMixin, View):
    """Superuser-only runtime email/SMTP config: master on/off, log-vs-SMTP mode,
    host/port/TLS/credentials (password masked), from-address, and a test send."""
    template_name = 'maintenance/email_settings.html'

    def _check(self, user):
        if not user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

    def get(self, request):
        self._check(request.user)
        return render(request, self.template_name,
                      {'s': SiteSettings.get(), 'active_nav': 'maintenance'})

    def post(self, request):
        self._check(request.user)
        s = SiteSettings.get()
        if request.POST.get('action') == 'test':
            from apps.core.services.notifications import send_test_email
            ok, msg = send_test_email((request.user.email or '').strip())
            (messages.success if ok else messages.error)(request, msg)
            return redirect('ui:email_settings')
        s.notifications_enabled = request.POST.get('notifications_enabled') == 'on'
        s.email_send_mode = request.POST.get('email_send_mode') or SiteSettings.EmailSendMode.LOG
        s.email_host = request.POST.get('email_host', '').strip()
        try:
            s.email_port = int(request.POST.get('email_port') or 587)
        except (TypeError, ValueError):
            s.email_port = 587
        s.email_use_tls = request.POST.get('email_use_tls') == 'on'
        s.email_use_ssl = request.POST.get('email_use_ssl') == 'on'
        s.email_host_user = request.POST.get('email_host_user', '').strip()
        from_email = request.POST.get('notifications_from_email', '').strip()
        if from_email:
            s.notifications_from_email = from_email
        pw = request.POST.get('email_host_password', '')
        if pw:  # masked field — only overwrite when a new value is typed
            s.email_host_password = pw
        s.save()
        messages.success(request, 'Email settings saved.')
        return redirect('ui:email_settings')


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


# ============================================================================
# Land Pre-Condition traffic-light editor
# ============================================================================

class LandPreConditionEditView(WriteRequiredMixin, View):
    """Bulk-upsert all 4 land pre-condition flags for a project.

    GET  — renders a form with a row per Category, pre-populated from DB.
    POST — creates-or-updates each flag and redirects to the project detail.
    """
    template_name = 'projects/land_pre_conditions.html'

    def _get_project(self, project_pk):
        from apps.core.models import Project
        return get_object_or_404(Project, pk=project_pk)

    def _get_or_init_flags(self, project):
        from apps.core.models import LandPreCondition
        existing = {f.category: f for f in project.land_pre_conditions.all()}
        flags = []
        for cat, label in LandPreCondition.Category.choices:
            flags.append(existing.get(cat) or LandPreCondition(project=project, category=cat))
        return flags

    def get(self, request, project_pk):
        project = self._get_project(project_pk)
        flags = self._get_or_init_flags(project)
        return render(request, self.template_name, {
            'project': project,
            'flags': flags,
            'title': f'Land Pre-Conditions: {project.name}',
        })

    def post(self, request, project_pk):
        from apps.core.models import LandPreCondition
        project = self._get_project(project_pk)
        for cat, _ in LandPreCondition.Category.choices:
            status = request.POST.get(f'status_{cat}', LandPreCondition.TrafficLight.RED)
            nt_type = request.POST.get(f'nt_type_{cat}', '')
            completed_date_raw = request.POST.get(f'completed_date_{cat}', '')
            notes = request.POST.get(f'notes_{cat}', '')
            from datetime import date
            completed_date = None
            if completed_date_raw:
                try:
                    completed_date = date.fromisoformat(completed_date_raw)
                except ValueError:
                    pass
            LandPreCondition.objects.update_or_create(
                project=project, category=cat,
                defaults={
                    'status': status,
                    'native_title_type': nt_type if cat == LandPreCondition.Category.NATIVE_TITLE else '',
                    'completed_date': completed_date,
                    'notes': notes,
                },
            )
        messages.success(request, 'Land pre-conditions saved.')
        return redirect('ui:project_detail', pk=project_pk)
