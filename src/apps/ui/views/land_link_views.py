"""Land-project linking actions, all COUNCIL-SCOPED.

Wires the previously-stubbed buttons on the land project detail page:
  * Link child dwelling projects   (Project.parent_land_project)
  * Link land parcels              (Project.land_parcels M2M -> LandTenure)
  * Link development application    (Project.development_application FK)
  * Edit infrastructure readiness   (Project.infra_* text fields)

Every picker only offers records from the SAME council as the project. The
multi-select pickers support client-side search + status filtering (completed
projects are hidden by default but toggleable).
"""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, UpdateView

from apps.core.mixins import WriteRequiredMixin
from apps.core.models import Project, LandTenure, DevelopmentApplication

from .crud_views import WidgetUpgradeMixin


def _detail_url(project):
    return reverse('ui:project_detail', kwargs={'pk': project.pk})


# ── Filterable checkbox pickers (child dwellings, land parcels) ───────

class _PickerView(WriteRequiredMixin, View):
    """Council-scoped multi-select with client-side search + status filter."""
    template_name = 'projects/link_picker.html'
    field_name = 'items'
    title = 'Link'
    subtitle = ''
    success_message = 'Updated.'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    # --- subclass hooks ---
    def candidates(self):
        raise NotImplementedError

    def current_ids(self):
        raise NotImplementedError

    def item(self, obj, checked):
        raise NotImplementedError

    def statuses(self):
        return []

    def apply(self, selected_ids):
        raise NotImplementedError

    # --- request handling ---
    def get(self, request, *args, **kwargs):
        current = set(self.current_ids())
        items = [self.item(o, o.pk in current) for o in self.candidates()]
        return render(request, self.template_name, {
            'title': self.title, 'subtitle': self.subtitle,
            'back_url': _detail_url(self.project), 'field_name': self.field_name,
            'items': items, 'statuses': self.statuses(),
        })

    def post(self, request, *args, **kwargs):
        candidate_ids = {o.pk for o in self.candidates()}
        selected = {int(x) for x in request.POST.getlist(self.field_name) if x.isdigit()}
        selected &= candidate_ids  # never trust a pk outside the council-scoped set
        self.apply(selected)
        messages.success(request, self.success_message)
        return redirect(_detail_url(self.project))


class LinkChildDwellingsView(_PickerView):
    title = 'Link child dwelling projects'
    subtitle = 'Only dwelling projects under the same council are shown.'
    field_name = 'children'
    success_message = 'Child dwelling projects updated.'

    def candidates(self):
        return (Project.objects
                .filter(council=self.project.council,
                        project_type=Project.Type.DWELLING, is_archived=False)
                .exclude(pk=self.project.pk).order_by('name'))

    def current_ids(self):
        return self.project.child_dwellings.values_list('pk', flat=True)

    def item(self, obj, checked):
        return {'pk': obj.pk, 'label': obj.name, 'status': obj.state,
                'status_display': obj.get_state_display(), 'checked': checked}

    def statuses(self):
        labels = dict(Project.State.choices)
        present = list(dict.fromkeys(self.candidates().values_list('state', flat=True)))
        return [{'code': s, 'label': labels.get(s, s),
                 'default_on': s != Project.State.COMPLETED}
                for s in present if s]

    def apply(self, selected_ids):
        self.project.child_dwellings.exclude(pk__in=selected_ids).update(parent_land_project=None)
        self.candidates().filter(pk__in=selected_ids).update(parent_land_project=self.project)


class LinkLandParcelsView(_PickerView):
    title = 'Link land parcels'
    subtitle = 'Only land parcels registered under the same council are shown.'
    field_name = 'parcels'
    success_message = 'Land parcels updated.'

    def candidates(self):
        return LandTenure.objects.filter(council=self.project.council).order_by('lot_number', 'plan_number')

    def current_ids(self):
        return self.project.land_parcels.values_list('pk', flat=True)

    def item(self, obj, checked):
        return {'pk': obj.pk, 'label': str(obj), 'status': '', 'status_display': '', 'checked': checked}

    def apply(self, selected_ids):
        self.project.land_parcels.set(LandTenure.objects.filter(pk__in=selected_ids))


# ── Development application (single select) ──────────────────────────

class _LinkDAForm(forms.Form):
    development_application = forms.ModelChoiceField(
        queryset=DevelopmentApplication.objects.none(), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Development application",
        help_text="Only DAs lodged for this council are shown.",
    )


class LinkDAView(WriteRequiredMixin, FormView):
    template_name = 'crud/form.html'
    form_class = _LinkDAForm
    title = 'Link development application'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['development_application'].queryset = (
            DevelopmentApplication.objects.filter(council=self.project.council)
            .order_by('application_reference')
        )
        return form

    def get_initial(self):
        return {'development_application': self.project.development_application_id}

    def form_valid(self, form):
        self.project.development_application = form.cleaned_data['development_application']
        self.project.save(update_fields=['development_application'])
        messages.success(self.request, 'Development application updated.')
        return redirect(_detail_url(self.project))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = self.title
        ctx['back_url'] = _detail_url(self.project)
        return ctx


# ── Infrastructure readiness ─────────────────────────────────────────

class ProjectInfraUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = Project
    pk_url_kwarg = 'project_pk'
    template_name = 'crud/form.html'
    fields = ['infra_water_assessment', 'infra_electricity_assessment',
              'infra_sewerage_assessment', 'infra_comments']

    def get_success_url(self):
        return _detail_url(self.object)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Infrastructure readiness'
        ctx['back_url'] = _detail_url(self.object)
        return ctx
