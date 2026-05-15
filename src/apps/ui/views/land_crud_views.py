"""
Land infrastructure CRUD views: LandTenure, DevelopmentApplication.

LandProject is not a separate model — land projects are Project(project_type='LAND').
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView

from apps.core.models import DevelopmentApplication, LandTenure


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

class DevelopmentApplicationListView(LoginRequiredMixin, ListView):
    model = DevelopmentApplication
    template_name = 'development_applications/list.html'
    context_object_name = 'development_applications'
    paginate_by = 50

    def get_queryset(self):
        return DevelopmentApplication.objects.select_related('council').order_by('-created_at')


class DevelopmentApplicationCreateView(LoginRequiredMixin, CreateView):
    model = DevelopmentApplication
    template_name = 'crud/form.html'
    fields = ['council', 'application_type', 'application_reference', 'status',
              'lodged_date', 'decision_date', 'lapsing_date',
              'decision_notice_link', 'conditions', 'notes']
    success_url = reverse_lazy('ui:development_application_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create Development Application'
        ctx['back_url'] = reverse_lazy('ui:development_application_list')
        return ctx


class DevelopmentApplicationDetailView(LoginRequiredMixin, DetailView):
    model = DevelopmentApplication
    template_name = 'development_applications/detail.html'
    context_object_name = 'da'


class DevelopmentApplicationUpdateView(LoginRequiredMixin, UpdateView):
    model = DevelopmentApplication
    template_name = 'crud/form.html'
    fields = ['council', 'application_type', 'application_reference', 'status',
              'lodged_date', 'decision_date', 'lapsing_date',
              'decision_notice_link', 'conditions', 'notes']
    success_url = reverse_lazy('ui:development_application_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit DA: {self.object.application_reference}'
        ctx['back_url'] = reverse_lazy('ui:development_application_list')
        return ctx


class DevelopmentApplicationDeleteView(LoginRequiredMixin, DeleteView):
    model = DevelopmentApplication
    template_name = 'crud/confirm_delete.html'
    success_url = reverse_lazy('ui:development_application_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse_lazy('ui:development_application_list')
        return ctx
