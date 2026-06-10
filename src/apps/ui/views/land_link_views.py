"""Land-project linking actions, all COUNCIL-SCOPED.

Wires the previously-stubbed buttons on the land project detail page:
  * Link child dwelling projects   (Project.parent_land_project)
  * Link land parcels              (Project.land_parcels M2M -> LandTenure)
  * Link development application    (Project.development_application FK)
  * Edit infrastructure readiness   (Project.infra_* text fields)

Every picker only offers records from the SAME council as the project.
"""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, UpdateView

from apps.core.mixins import WriteRequiredMixin
from apps.core.models import Project, LandTenure, DevelopmentApplication

from .crud_views import WidgetUpgradeMixin


def _detail_url(project):
    return reverse('ui:project_detail', kwargs={'pk': project.pk})


class _ProjectLinkView(WriteRequiredMixin, FormView):
    """Base for the council-scoped link forms (rendered via the generic form template)."""
    template_name = 'crud/form.html'
    title = 'Link'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return _detail_url(self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = self.title
        ctx['back_url'] = _detail_url(self.project)
        return ctx


# ── Child dwellings ──────────────────────────────────────────────────

class _ChildDwellingsForm(forms.Form):
    children = forms.ModelMultipleChoiceField(
        queryset=Project.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Dwelling projects in this council",
        help_text="Only dwelling projects under the same council are shown.",
    )


class LinkChildDwellingsView(_ProjectLinkView):
    form_class = _ChildDwellingsForm
    title = 'Link child dwelling projects'

    def _candidates(self):
        return (Project.objects
                .filter(council=self.project.council,
                        project_type=Project.Type.DWELLING, is_archived=False)
                .exclude(pk=self.project.pk).order_by('name'))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['children'].queryset = self._candidates()
        return form

    def get_initial(self):
        return {'children': list(self.project.child_dwellings.values_list('pk', flat=True))}

    def form_valid(self, form):
        sel_ids = set(form.cleaned_data['children'].values_list('pk', flat=True))
        # Unlink children that were removed; link the selected candidates.
        self.project.child_dwellings.exclude(pk__in=sel_ids).update(parent_land_project=None)
        self._candidates().filter(pk__in=sel_ids).update(parent_land_project=self.project)
        messages.success(self.request, 'Child dwelling projects updated.')
        return super().form_valid(form)


# ── Land parcels ─────────────────────────────────────────────────────

class _LandParcelsForm(forms.Form):
    parcels = forms.ModelMultipleChoiceField(
        queryset=LandTenure.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Land parcels (lots / plans) in this council",
        help_text="Only land parcels registered under the same council are shown.",
    )


class LinkLandParcelsView(_ProjectLinkView):
    form_class = _LandParcelsForm
    title = 'Link land parcels'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['parcels'].queryset = LandTenure.objects.filter(
            council=self.project.council
        ).order_by('lot_number', 'plan_number')
        return form

    def get_initial(self):
        return {'parcels': list(self.project.land_parcels.values_list('pk', flat=True))}

    def form_valid(self, form):
        self.project.land_parcels.set(form.cleaned_data['parcels'])
        messages.success(self.request, 'Land parcels updated.')
        return super().form_valid(form)


# ── Development application ───────────────────────────────────────────

class _LinkDAForm(forms.Form):
    development_application = forms.ModelChoiceField(
        queryset=DevelopmentApplication.objects.none(), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Development application",
        help_text="Only DAs lodged for this council are shown.",
    )


class LinkDAView(_ProjectLinkView):
    form_class = _LinkDAForm
    title = 'Link development application'

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
        return super().form_valid(form)


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
