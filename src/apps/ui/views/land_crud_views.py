"""
Land infrastructure CRUD views: LandTenure, DevelopmentApplication.

LandProject is not a separate model — land projects are Project(project_type='LAND').
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView

from apps.core.mixins import CouncilOrFNCMixin, CouncilScopedMixin, WriteRequiredMixin
from apps.core.models import DevelopmentApplication, LandTenure, Project

from .crud_views import WidgetUpgradeMixin


# ---------------------------------------------------------------------------
# LandTenure
# ---------------------------------------------------------------------------

class LandTenureListView(LoginRequiredMixin, ListView):
    model = LandTenure
    template_name = 'land_tenures/list.html'
    context_object_name = 'land_tenures'
    paginate_by = 50

    def get_queryset(self):
        return LandTenure.objects.select_related('council').order_by('council', 'lot_number')


class LandTenureCreateView(LoginRequiredMixin, CreateView):
    model = LandTenure
    template_name = 'crud/form.html'
    fields = ['council', 'lot_number', 'plan_number', 'title_reference', 'tenure_type',
              'native_title_status', 'native_title_reference',
              'cultural_heritage_status', 'cultural_heritage_reference',
              'is_developed', 'developed_date', 'parent_lot', 'notes']
    success_url = reverse_lazy('ui:land_tenure_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Land Tenure'
        ctx['back_url'] = reverse_lazy('ui:land_tenure_list')
        return ctx


class LandTenureDetailView(LoginRequiredMixin, DetailView):
    model = LandTenure
    template_name = 'land_tenures/detail.html'
    context_object_name = 'land_tenure'


class LandTenureUpdateView(LoginRequiredMixin, UpdateView):
    model = LandTenure
    template_name = 'crud/form.html'
    fields = ['council', 'lot_number', 'plan_number', 'title_reference', 'tenure_type',
              'native_title_status', 'native_title_reference',
              'cultural_heritage_status', 'cultural_heritage_reference',
              'is_developed', 'developed_date', 'parent_lot', 'notes']
    success_url = reverse_lazy('ui:land_tenure_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Land Tenure: Lot {self.object.lot_number}'
        ctx['back_url'] = reverse_lazy('ui:land_tenure_list')
        return ctx


class LandTenureDeleteView(LoginRequiredMixin, DeleteView):
    model = LandTenure
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:land_tenure_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:land_tenure_list')
        return ctx


# ---------------------------------------------------------------------------
# DevelopmentApplication
# ---------------------------------------------------------------------------

class DevelopmentApplicationListView(CouncilScopedMixin, CouncilOrFNCMixin, ListView):
    model = DevelopmentApplication
    template_name = 'development_applications/list.html'
    context_object_name = 'development_applications'
    council_filter_field = 'council'
    paginate_by = 50
    extra_context = {'active_nav': 'development_applications'}

    def get_queryset(self):
        return super().get_queryset().select_related('council').order_by('-created_at')


class DevelopmentApplicationCreateView(WriteRequiredMixin, WidgetUpgradeMixin, CreateView):
    """Create a DA. With ?project=<pk>, the council is preset from that project
    and the new DA is auto-linked to it (redirecting back to the project)."""
    model = DevelopmentApplication
    template_name = 'crud/form.html'
    fields = ['council', 'application_type', 'application_reference', 'status',
              'lodged_date', 'decision_date', 'lapsing_date',
              'decision_notice_link', 'conditions', 'notes']
    extra_context = {'active_nav': 'development_applications'}

    def _project(self):
        pid = self.request.GET.get('project', '')
        if pid.isdigit():
            return Project.objects.filter(pk=pid).select_related('council').first()
        return None

    def get_initial(self):
        initial = super().get_initial()
        proj = self._project()
        if proj:
            initial['council'] = proj.council_id
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        proj = self._project()
        if proj:
            proj.development_application = self.object
            proj.save(update_fields=['development_application'])
        return response

    def get_success_url(self):
        proj = self._project()
        if proj:
            return reverse('ui:project_detail', kwargs={'pk': proj.pk})
        return reverse('ui:development_application_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        proj = self._project()
        ctx['title'] = (f'Create Development Application — {proj.name}' if proj
                        else 'Create Development Application')
        ctx['back_url'] = (reverse('ui:project_detail', kwargs={'pk': proj.pk}) if proj
                           else reverse('ui:development_application_list'))
        return ctx


class DevelopmentApplicationDetailView(CouncilScopedMixin, CouncilOrFNCMixin, DetailView):
    model = DevelopmentApplication
    template_name = 'development_applications/detail.html'
    context_object_name = 'da'
    council_filter_field = 'council'
    extra_context = {'active_nav': 'development_applications'}


class DevelopmentApplicationUpdateView(WriteRequiredMixin, WidgetUpgradeMixin, UpdateView):
    model = DevelopmentApplication
    template_name = 'crud/form.html'
    fields = ['council', 'application_type', 'application_reference', 'status',
              'lodged_date', 'decision_date', 'lapsing_date',
              'decision_notice_link', 'conditions', 'notes']
    success_url = reverse_lazy('ui:development_application_list')
    extra_context = {'active_nav': 'development_applications'}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit DA: {self.object.application_reference}'
        ctx['back_url'] = reverse_lazy('ui:development_application_list')
        return ctx


class DevelopmentApplicationDeleteView(WriteRequiredMixin, DeleteView):
    model = DevelopmentApplication
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:development_application_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:development_application_list')
        return ctx
