"""
Stage 1 / Stage 2 Report views.

Three groups of views:
  1. Template Maintenance (RICD only):
       - StageItemDefinitionList/Create/Update/Delete
       - StageItemGroupList/Create/Update/Delete + nested StageItemGroupItem CRUD
  2. Stage Report flow:
       - StageReportOpenOrCreateView (auto-populate items from project's
         pre-assigned group, derive XOR linkage from project)
       - StageReportGridView (display + edit per-cell values)
       - StageReportAttachment add/delete
       - Submit / Endorse / Assess / Approve / Reject actions

Access control:
  - Council users: see their own council only, may edit when status IN
    (DRAFT, IN_PROGRESS) and CouncilTrackerConfig.council_submission_enabled
  - RICD officers: edit/assess any report
  - RICD MANAGER/DIRECTOR: approve/reject
"""
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    View, ListView, CreateView, UpdateView, DeleteView
)

from apps.core.models import (
    CouncilTrackerConfig,
    Project,
    StageItemDefinition, StageItemGroup, StageItemGroupItem,
    StageReport, StageReportItem, StageReportAttachment,
)

COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})
MANAGER_ROLES = frozenset({'MANAGER', 'DIRECTOR'})


# ===========================================================================
# Helpers
# ===========================================================================

def _role(user):
    return getattr(getattr(user, 'profile', None), 'officer_role', None)


def _is_council_user(user):
    return _role(user) in COUNCIL_ROLES


def _is_ricd_staff(user):
    if user.is_superuser:
        return True
    r = _role(user)
    return r is not None and r not in COUNCIL_ROLES


def _is_manager(user):
    return user.is_superuser or _role(user) in MANAGER_ROLES


def _user_council(user):
    return getattr(getattr(user, 'profile', None), 'council', None)


def _project_agreement_for_stage_report(project):
    """Derive which agreement a stage report should be linked to for this project.

    Returns a tuple ``(field_name, instance)`` where field_name is one of
    'funding_schedule', 'interim_frp', 'forward_rpf', or ``(None, None)``.
    Order of preference: active FundingSchedule > InterimFRP > ForwardRPF.
    """
    fs = project.funding_schedules.filter(
        status__in=['ACTIVE', 'EXECUTED', 'READY']
    ).order_by('-schedule_number').first()
    if fs:
        return 'funding_schedule', fs
    interim = project.interim_frp_agreements.first()
    if interim:
        return 'interim_frp', interim
    forward = project.forward_rpf_agreements.first()
    if forward:
        return 'forward_rpf', forward
    return None, None


def _ensure_can_edit(report, user):
    """True if `user` can edit this stage report given its status and the council config."""
    if _is_ricd_staff(user):
        return report.status in (
            StageReport.Status.DRAFT,
            StageReport.Status.IN_PROGRESS,
            StageReport.Status.SUBMITTED,
            StageReport.Status.ENDORSED,
            StageReport.Status.ASSESSED,
        )
    if _is_council_user(user):
        if _user_council(user) != report.project.council:
            return False
        cfg = CouncilTrackerConfig.objects.filter(council=report.project.council).first()
        if not cfg or not cfg.council_submission_enabled:
            return False
        return report.status in (StageReport.Status.DRAFT, StageReport.Status.IN_PROGRESS)
    return False


def _mark_in_progress(report, user):
    """Move DRAFT -> IN_PROGRESS the first time a council user saves cells."""
    if report.status == StageReport.Status.DRAFT and _is_council_user(user):
        report.status = StageReport.Status.IN_PROGRESS
        report.save(update_fields=['status', 'updated_at'])


# ===========================================================================
# StageItemDefinition CRUD (Maintenance -- RICD only)
# ===========================================================================

class StageItemDefinitionListView(LoginRequiredMixin, ListView):
    model = StageItemDefinition
    template_name = 'stage/definition_list.html'
    context_object_name = 'items'
    paginate_by = 100

    def get_queryset(self):
        qs = StageItemDefinition.objects.all().order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['can_edit'] = _is_ricd_staff(self.request.user)
        return ctx


class StageItemDefinitionCreateView(LoginRequiredMixin, CreateView):
    model = StageItemDefinition
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:stage_item_definition_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Stage Item'
        ctx['back_url'] = reverse_lazy('ui:stage_item_definition_list')
        return ctx


class StageItemDefinitionUpdateView(LoginRequiredMixin, UpdateView):
    model = StageItemDefinition
    template_name = 'crud/form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('ui:stage_item_definition_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Stage Item: {self.object.name}'
        ctx['back_url'] = reverse_lazy('ui:stage_item_definition_list')
        return ctx


class StageItemDefinitionDeleteView(LoginRequiredMixin, DeleteView):
    model = StageItemDefinition
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:stage_item_definition_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:stage_item_definition_list')
        return ctx


# ===========================================================================
# StageItemGroup CRUD + nested StageItemGroupItem CRUD
# ===========================================================================

class StageItemGroupListView(LoginRequiredMixin, ListView):
    model = StageItemGroup
    template_name = 'stage/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        qs = StageItemGroup.objects.all().order_by('stage_type', 'name')
        st = self.request.GET.get('stage_type', '')
        if st in ('STAGE1', 'STAGE2'):
            qs = qs.filter(stage_type=st)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_stage_type'] = self.request.GET.get('stage_type', '')
        ctx['stage_types'] = StageItemGroup.StageType.choices
        return ctx


class StageItemGroupCreateView(LoginRequiredMixin, CreateView):
    model = StageItemGroup
    template_name = 'crud/form.html'
    fields = ['stage_type', 'name', 'description', 'is_active']

    def get_success_url(self):
        return reverse('ui:stage_item_group_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Stage Item Group'
        ctx['back_url'] = reverse_lazy('ui:stage_item_group_list')
        return ctx


class StageItemGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = StageItemGroup
    template_name = 'crud/form.html'
    fields = ['stage_type', 'name', 'description', 'is_active']

    def get_success_url(self):
        return reverse('ui:stage_item_group_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Group: {self.object.name}'
        ctx['back_url'] = reverse('ui:stage_item_group_detail', kwargs={'pk': self.object.pk})
        return ctx


class StageItemGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = StageItemGroup
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:stage_item_group_list')


class StageItemGroupDetailView(LoginRequiredMixin, View):
    """List items in a group + add new item inline."""
    def get(self, request, pk):
        group = get_object_or_404(StageItemGroup, pk=pk)
        items = group.items.select_related('item').order_by('order')
        available = StageItemDefinition.objects.filter(is_active=True).order_by('name')
        return render(request, 'stage/group_detail.html', {
            'group': group,
            'items': items,
            'available_items': available,
            'field_type_choices': StageItemGroupItem.FieldType.choices,
            'can_edit': _is_ricd_staff(request.user),
        })


class StageItemGroupItemCreateView(LoginRequiredMixin, View):
    """Add an item to a group (POST only -- from the group detail page)."""
    def post(self, request, group_pk):
        group = get_object_or_404(StageItemGroup, pk=group_pk)
        if not _is_ricd_staff(request.user):
            messages.error(request, 'Only RICD staff can edit templates.')
            return redirect('ui:stage_item_group_detail', pk=group_pk)
        try:
            item = get_object_or_404(StageItemDefinition, pk=request.POST.get('item'))
            next_order = (group.items.order_by('-order').values_list('order', flat=True).first() or 0) + 1
            StageItemGroupItem.objects.create(
                group=group, item=item,
                order=int(request.POST.get('order', next_order)),
                field_type=request.POST.get('field_type', 'CHECKBOX'),
                is_required=request.POST.get('is_required') == 'on',
                requires_attachment=request.POST.get('requires_attachment') == 'on',
                help_text=request.POST.get('help_text', '').strip(),
            )
            messages.success(request, f'Added {item.name} to group.')
        except Exception as e:
            messages.error(request, f'Could not add item: {e}')
        return redirect('ui:stage_item_group_detail', pk=group_pk)


class StageItemGroupItemUpdateView(LoginRequiredMixin, UpdateView):
    model = StageItemGroupItem
    template_name = 'crud/form.html'
    fields = ['order', 'field_type', 'is_required', 'requires_attachment', 'help_text']

    def get_success_url(self):
        return reverse('ui:stage_item_group_detail', kwargs={'pk': self.object.group_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit item: {self.object.item.name}'
        ctx['back_url'] = reverse('ui:stage_item_group_detail', kwargs={'pk': self.object.group_id})
        return ctx


class StageItemGroupItemDeleteView(LoginRequiredMixin, View):
    """POST-only remove (no confirmation page -- uses inline button)."""
    def post(self, request, pk):
        gi = get_object_or_404(StageItemGroupItem, pk=pk)
        if not _is_ricd_staff(request.user):
            messages.error(request, 'Only RICD staff can edit templates.')
            return redirect('ui:stage_item_group_detail', pk=gi.group_id)
        group_pk = gi.group_id
        gi.delete()
        messages.success(request, 'Removed item from group.')
        return redirect('ui:stage_item_group_detail', pk=group_pk)


# ===========================================================================
# Stage Report flow
# ===========================================================================

class StageReportOpenOrCreateView(LoginRequiredMixin, View):
    """Open (or create) a Stage 1 or Stage 2 report for a project.

    Behaviour on first open:
      * Pick which StageItemGroup applies (from project.stage1_item_group or
        stage2_item_group). If unset, redirect back with an error.
      * Snapshot the group on the report.
      * Derive XOR linkage from the project (FundingSchedule > Interim > Forward).
      * Pre-create StageReportItem rows for each StageItemGroupItem.
    """

    def get(self, request, project_pk, stage_type):
        project = get_object_or_404(Project, pk=project_pk)
        if _is_council_user(request.user) and _user_council(request.user) != project.council:
            raise Http404()
        if stage_type not in ('STAGE1', 'STAGE2'):
            raise Http404()

        report = StageReport.objects.filter(project=project, stage_type=stage_type).first()
        if report is None:
            group_field = 'stage1_item_group' if stage_type == 'STAGE1' else 'stage2_item_group'
            group = getattr(project, group_field, None)
            if group is None:
                messages.error(
                    request,
                    f"This project has no {'Stage 1' if stage_type == 'STAGE1' else 'Stage 2'} "
                    "item template assigned. Edit the project and pick one."
                )
                return redirect('ui:project_detail', pk=project.pk)
            agreement_field, agreement_obj = _project_agreement_for_stage_report(project)
            kwargs = {'project': project, 'stage_type': stage_type, 'item_group': group}
            if agreement_field and agreement_obj:
                kwargs[agreement_field] = agreement_obj
            report = StageReport.objects.create(**kwargs)
            self._populate_items(report, group)

        return redirect('ui:stage_report_grid', pk=report.pk)

    @staticmethod
    def _populate_items(report, group):
        for gi in group.items.all():
            StageReportItem.objects.get_or_create(report=report, group_item=gi)


class StageReportGridView(LoginRequiredMixin, View):
    """Display + edit the stage report.

    Vertical layout (one row per item) -- items are template-driven and
    each one has its own input + attachment area.
    """

    def _get(self, pk, user):
        report = get_object_or_404(
            StageReport.objects.select_related(
                'project', 'project__council', 'item_group',
                'funding_schedule', 'interim_frp', 'forward_rpf',
            ),
            pk=pk
        )
        if _is_council_user(user) and _user_council(user) != report.project.council:
            raise Http404()
        return report

    def get(self, request, pk):
        report = self._get(pk, request.user)
        items = (
            report.items
            .select_related('group_item__item')
            .prefetch_related('attachments')
            .order_by('group_item__order')
        )
        return render(request, 'stage/report_grid.html', {
            'report': report,
            'items': items,
            'can_edit': _ensure_can_edit(report, request.user),
            'is_ricd': _is_ricd_staff(request.user),
            'is_manager': _is_manager(request.user),
            'is_council_user': _is_council_user(request.user),
        })

    def post(self, request, pk):
        report = self._get(pk, request.user)
        if not _ensure_can_edit(report, request.user):
            messages.error(request, 'You do not have permission to edit this report.')
            return redirect('ui:stage_report_grid', pk=pk)

        updated = 0
        for entry in report.items.select_related('group_item').all():
            ft = entry.group_item.field_type
            prefix = f'item_{entry.pk}_'
            changed = False

            if ft == 'CHECKBOX':
                val = request.POST.get(prefix + 'bool') == 'on'
                if entry.boolean_value != val:
                    entry.boolean_value = val
                    entry.is_completed = bool(val)
                    entry.completed_at = timezone.now() if val else None
                    changed = True
            elif ft in ('YES_NO', 'YES_NO_NA'):
                raw = request.POST.get(prefix + 'yn', '')
                if raw == 'yes':
                    nb, na = True, False
                elif raw == 'no':
                    nb, na = False, False
                elif raw == 'na' and ft == 'YES_NO_NA':
                    nb, na = None, True
                else:
                    nb, na = None, False
                if entry.boolean_value != nb or entry.is_na != na:
                    entry.boolean_value = nb
                    entry.is_na = na
                    entry.is_completed = nb is not None or na
                    changed = True
            elif ft in ('DATE', 'DATE_NA'):
                raw = request.POST.get(prefix + 'date', '')
                na = request.POST.get(prefix + 'na') == 'on' if ft == 'DATE_NA' else False
                new_date = None
                if raw and not na:
                    try:
                        new_date = datetime.strptime(raw, '%Y-%m-%d').date()
                    except ValueError:
                        new_date = None
                if entry.date_value != new_date or entry.is_na != na:
                    entry.date_value = new_date
                    entry.is_na = na
                    entry.is_completed = new_date is not None or na
                    if new_date and not entry.completed_at:
                        entry.completed_at = timezone.now()
                    changed = True
            elif ft in ('NUMBER', 'CURRENCY'):
                raw = request.POST.get(prefix + 'num', '')
                from decimal import Decimal, InvalidOperation
                try:
                    new_num = Decimal(raw) if raw else None
                except InvalidOperation:
                    new_num = None
                if entry.number_value != new_num:
                    entry.number_value = new_num
                    entry.is_completed = new_num is not None
                    changed = True
            else:  # TEXT
                raw = request.POST.get(prefix + 'text', '')
                if entry.text_value != raw:
                    entry.text_value = raw
                    entry.is_completed = bool(raw.strip())
                    changed = True

            notes = request.POST.get(prefix + 'notes', '')
            if entry.notes != notes:
                entry.notes = notes
                changed = True

            if changed:
                entry.updated_by = request.user
                entry.save()
                updated += 1

        if updated:
            messages.success(request, f'Saved {updated} item(s).')
            _mark_in_progress(report, request.user)
        return redirect('ui:stage_report_grid', pk=pk)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

class StageReportAttachmentAddView(LoginRequiredMixin, View):
    def post(self, request, item_pk):
        item = get_object_or_404(StageReportItem, pk=item_pk)
        report = item.report
        if not _ensure_can_edit(report, request.user):
            messages.error(request, 'You do not have permission to add attachments here.')
            return redirect('ui:stage_report_grid', pk=report.pk)
        uri = (request.POST.get('document_uri') or '').strip()
        description = (request.POST.get('description') or '').strip()
        if not uri:
            messages.error(request, 'A document URL is required.')
            return redirect('ui:stage_report_grid', pk=report.pk)
        StageReportAttachment.objects.create(
            item=item,
            document_uri=uri,
            description=description,
            uploaded_by=request.user,
        )
        _mark_in_progress(report, request.user)
        messages.success(request, 'Attachment added.')
        return redirect('ui:stage_report_grid', pk=report.pk)


class StageReportAttachmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        attachment = get_object_or_404(StageReportAttachment, pk=pk)
        report = attachment.item.report
        if not _ensure_can_edit(report, request.user):
            messages.error(request, 'You do not have permission to delete attachments.')
            return redirect('ui:stage_report_grid', pk=report.pk)
        attachment.delete()
        messages.success(request, 'Attachment removed.')
        return redirect('ui:stage_report_grid', pk=report.pk)


# ---------------------------------------------------------------------------
# Lifecycle actions
# ---------------------------------------------------------------------------

class StageReportSubmitView(LoginRequiredMixin, View):
    """Council User / Manager submits -- moves DRAFT/IN_PROGRESS -> SUBMITTED."""
    def post(self, request, pk):
        report = get_object_or_404(StageReport, pk=pk)
        if _is_council_user(request.user) and _user_council(request.user) != report.project.council:
            raise Http404()
        if report.status not in (StageReport.Status.DRAFT, StageReport.Status.IN_PROGRESS):
            messages.error(request, f'Cannot submit -- already {report.get_status_display()}.')
            return redirect('ui:stage_report_grid', pk=pk)
        if _is_council_user(request.user):
            cfg = CouncilTrackerConfig.objects.filter(council=report.project.council).first()
            if not cfg or not cfg.council_submission_enabled:
                messages.error(request, 'Submission is not enabled for your council.')
                return redirect('ui:stage_report_grid', pk=pk)
        report.submit(request.user)
        messages.success(request, 'Stage report submitted.')
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportEndorseView(LoginRequiredMixin, View):
    """Council Manager endorses a submitted report before it goes to RICD."""
    def post(self, request, pk):
        report = get_object_or_404(StageReport, pk=pk)
        if _role(request.user) != 'COUNCIL_MANAGER' and not _is_ricd_staff(request.user):
            messages.error(request, 'Only Council Managers (or RICD) can endorse.')
            return redirect('ui:stage_report_grid', pk=pk)
        if report.status != StageReport.Status.SUBMITTED:
            messages.error(request, 'Only submitted reports can be endorsed.')
            return redirect('ui:stage_report_grid', pk=pk)
        report.endorse(request.user)
        messages.success(request, 'Stage report endorsed.')
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportAssessView(LoginRequiredMixin, View):
    """RICD officer assesses an endorsed report."""
    def post(self, request, pk):
        if not _is_ricd_staff(request.user):
            messages.error(request, 'Only RICD staff can assess.')
            return redirect('ui:stage_report_grid', pk=pk)
        report = get_object_or_404(StageReport, pk=pk)
        if report.status != StageReport.Status.ENDORSED:
            messages.error(request, 'Only endorsed reports can be assessed.')
            return redirect('ui:stage_report_grid', pk=pk)
        report.assess(request.user)
        messages.success(request, 'Stage report assessed.')
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportApproveView(LoginRequiredMixin, View):
    """RICD MANAGER/DIRECTOR approves an assessed report."""
    def post(self, request, pk):
        if not _is_manager(request.user):
            messages.error(request, 'Only Managers/Directors can approve.')
            return redirect('ui:stage_report_grid', pk=pk)
        report = get_object_or_404(StageReport, pk=pk)
        if report.status != StageReport.Status.ASSESSED:
            messages.error(request, 'Only assessed reports can be approved.')
            return redirect('ui:stage_report_grid', pk=pk)
        report.approve(request.user)
        messages.success(request, 'Stage report approved.')
        return redirect('ui:stage_report_grid', pk=pk)


class StageReportRejectView(LoginRequiredMixin, View):
    """Reject at any non-final stage (sends it back to REJECTED status)."""
    def post(self, request, pk):
        report = get_object_or_404(StageReport, pk=pk)
        if not (_is_manager(request.user) or _is_ricd_staff(request.user)):
            messages.error(request, 'Only RICD staff can reject.')
            return redirect('ui:stage_report_grid', pk=pk)
        if report.status in (StageReport.Status.APPROVED, StageReport.Status.REJECTED):
            messages.error(request, f'Cannot reject -- already {report.get_status_display()}.')
            return redirect('ui:stage_report_grid', pk=pk)
        report.status = StageReport.Status.REJECTED
        report.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Stage report rejected.')
        return redirect('ui:stage_report_grid', pk=pk)
