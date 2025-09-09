from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Sum, Count
from django.utils import timezone
from django.utils.dateformat import format
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from collections import defaultdict
import calendar

from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from ricd.models import Project, Program, Council, QuarterlyReport, MonthlyTracker, Stage1Report, Stage2Report, FundingSchedule, Address, Work, FundingApproval, WorkType, OutputType
from .forms import (
    MonthlyTrackerForm, QuarterlyReportForm, Stage1ReportForm, Stage2ReportForm,
    CouncilForm, ProgramForm, ProjectForm, ProjectStateForm, AddressForm, WorkForm,
    WorkTypeForm, OutputTypeForm
)

# RICD Dashboard
class RICDDashboardView(TemplateView):
    template_name = "portal/ricd_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build filter queryset
        projects_queryset = Project.objects.select_related('council', 'program', 'funding_schedule')

        # Apply filters from GET parameters
        program_filter = self.request.GET.get('program')
        council_filter = self.request.GET.get('council')
        stage_filter = self.request.GET.get('stage')

        if program_filter:
            projects_queryset = projects_queryset.filter(program_id=program_filter)
        if council_filter:
            projects_queryset = projects_queryset.filter(council_id=council_filter)
        if stage_filter:
            projects_queryset = projects_queryset.filter(state=stage_filter)

        projects = projects_queryset.all()

        # Store current filters for template use
        context['current_filters'] = {
            'program': program_filter,
            'council': council_filter,
            'stage': stage_filter,
        }

        # Enhance projects with calculated data
        enhanced_projects = []
        for project in projects:
            enhanced_project = {
                'project': project,
                'progress_percentage': self.get_project_progress(project),
                'budget_vs_spent': self.get_budget_vs_spent(project),
                'stage1_status': self.get_stage1_status(project),
                'stage2_status': self.get_stage2_status(project),
                'late_flag': project.is_late,
                'overdue_flag': project.is_overdue,
                'funding_schedule_number': project.funding_schedule.funding_schedule_number if project.funding_schedule else 'N/A',
            }
            enhanced_projects.append(enhanced_project)

        context['projects'] = enhanced_projects
        context['programs'] = Program.objects.all()
        context['councils'] = Council.objects.all()
        context['stages'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]

        return context

    def get_project_progress(self, project):
        """Calculate average progress percentage from most recent quarterly reports"""
        latest_reports = QuarterlyReport.objects.filter(work__project=project).order_by('-submission_date')
        if latest_reports.exists():
            avg_progress = latest_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
            return avg_progress or 0
        return 0

    def get_budget_vs_spent(self, project):
        """Calculate budget vs spent as 'Budget - Spent' or show remaining"""
        total_budget = 0
        total_spent = 0

        # Get total budget from funding schedule or commitments
        if project.funding_schedule:
            total_budget = project.funding_schedule.total_funding or 0
        else:
            total_budget = project.commitments or 0

        # Sum total expenditures from quarterly reports
        expenditures = QuarterlyReport.objects.filter(work__project=project).aggregate(
            total_spent=Sum('total_expenditure_council')
        )['total_spent'] or 0

        total_spent = expenditures
        remaining = total_budget - total_spent

        if total_budget > 0:
            return f"${remaining:,.0f} / ${total_budget:,.0f}"
        return "N/A"

    def get_stage1_status(self, project):
        """Get stage 1 report status"""
        from ricd.models import Stage1Report
        stage1_reports = Stage1Report.objects.filter(project=project).order_by('-submission_date')
        if stage1_reports.exists():
            report = stage1_reports.first()
            if report.state_accepted:
                return "Complete"
            return "Pending Acceptance"
        return "Not Submitted"

    def get_stage2_status(self, project):
        """Get stage 2 report status"""
        from ricd.models import Stage2Report
        stage2_reports = Stage2Report.objects.filter(project=project).order_by('-submission_date')
        if stage2_reports.exists():
            report = stage2_reports.first()
            if report.is_complete:
                return "Complete"
            return "In Progress"
        return "Not Submitted"

# Council Dashboard
class CouncilDashboardView(TemplateView):
    template_name = "portal/council_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter projects by logged-in user's council
        user_council = getattr(self.request.user, 'council', None) if self.request.user.is_authenticated else None
        if user_council:
            user_projects = Project.objects.filter(council=user_council)
        else:
            user_projects = Project.objects.none()

        # Enhance projects with calculated data
        enhanced_projects = []
        for project in user_projects.select_related('council', 'program', 'funding_schedule'):
            # Get latest monthly report through works relationship
            latest_monthly = MonthlyTracker.objects.filter(work__project=project).order_by('-month').first()
            # Get latest quarterly report through works relationship
            latest_quarterly = QuarterlyReport.objects.filter(work__project=project).order_by('-submission_date').first()

            # Calculate progress from quarterly reports through works relationship
            quarterly_reports = QuarterlyReport.objects.filter(work__project=project).order_by('-submission_date')
            progress_percentage = 0
            if quarterly_reports.exists():
                avg_progress = quarterly_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
                progress_percentage = avg_progress or 0

            enhanced_project = {
                'project': project,
                'funding_schedule_number': project.funding_schedule.funding_schedule_number if project.funding_schedule else 'N/A',
                'progress_percentage': progress_percentage,
                'is_overdue': project.is_overdue,
                'latest_monthly_report': latest_monthly,
                'latest_quarterly_report': latest_quarterly,
                'required_reports_overdue': self.get_required_reports_status(project),
            }
            enhanced_projects.append(enhanced_project)

        context['projects'] = enhanced_projects
        context['user_council'] = getattr(self.request.user, 'council', None) if self.request.user.is_authenticated else None
        return context

    def get_required_reports_status(self, project):
        """Check if required reports are overdue"""
        from django.utils import timezone
        today = timezone.now().date()

        overdue_reports = []

        # Check for monthly reports (typically monthly during construction)
        if project.state == 'under_construction':
            last_month = today.replace(day=1) - timezone.timedelta(days=1)
            latest_monthly = MonthlyTracker.objects.filter(
                work__project=project,
                month__year=last_month.year,
                month__month=last_month.month
            ).first()
            if not latest_monthly:
                overdue_reports.append('Monthly Report')

        # Check for quarterly reports
        latest_quarterly = QuarterlyReport.objects.filter(work__project=project).order_by('-submission_date').first()
        if not latest_quarterly:
            overdue_reports.append('Quarterly Report')
        else:
            # Check if quarterly report is less than 3 months old
            months_since_last = (today - latest_quarterly.submission_date).days / 30
            if months_since_last > 3:
                overdue_reports.append('Quarterly Report')

        return overdue_reports

# Project Detail
class ProjectDetailView(DetailView):
    model = Project
    template_name = "portal/project_detail.html"
    context_object_name = "project"


# Report Form Views
class MonthlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/monthly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MonthlyTrackerForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = MonthlyTrackerForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Monthly report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


# Council CRUD Views
class CouncilListView(LoginRequiredMixin, ListView):
    """List all councils - accessible by RICD users primarily"""
    model = Council
    template_name = "portal/council_list.html"
    context_object_name = "councils"
    paginate_by = 20

    def get_queryset(self):
        queryset = Council.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(abn__icontains=search) |
                Q(default_suburb__icontains=search)
            )
        return queryset.order_by('name')


class CouncilCreateView(LoginRequiredMixin, CreateView):
    """Create a new council"""
    model = Council
    form_class = CouncilForm
    template_name = "portal/council_form.html"
    success_url = reverse_lazy('portal:council_list')

    def form_valid(self, form):
        messages.success(self.request, f'Council "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class CouncilUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing council"""
    model = Council
    form_class = CouncilForm
    template_name = "portal/council_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:council_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Council "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class CouncilDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a council"""
    model = Council
    template_name = "portal/council_confirm_delete.html"
    success_url = reverse_lazy('portal:council_list')

    def delete(self, request, *args, **kwargs):
        council = self.get_object()
        messages.success(request, f'Council "{council.name}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class CouncilDetailView(LoginRequiredMixin, DetailView):
    """Display council details"""
    model = Council
    template_name = "portal/council_detail.html"
    context_object_name = "council"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        context['funding_schedules'] = self.object.funding_schedules.all()
        return context


# Program CRUD Views
class ProgramListView(LoginRequiredMixin, ListView):
    """List all programs"""
    model = Program
    template_name = "portal/program_list.html"
    context_object_name = "programs"
    paginate_by = 20

    def get_queryset(self):
        queryset = Program.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset.order_by('name')


class ProgramCreateView(LoginRequiredMixin, CreateView):
    """Create a new program"""
    model = Program
    form_class = ProgramForm
    template_name = "portal/program_form.html"
    success_url = reverse_lazy('portal:program_list')

    def form_valid(self, form):
        messages.success(self.request, f'Program "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ProgramUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing program"""
    model = Program
    form_class = ProgramForm
    template_name = "portal/program_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:program_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Program "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ProgramDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a program"""
    model = Program
    template_name = "portal/program_confirm_delete.html"
    success_url = reverse_lazy('portal:program_list')

    def delete(self, request, *args, **kwargs):
        program = self.get_object()
        messages.success(request, f'Program "{program.name}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class ProgramDetailView(LoginRequiredMixin, DetailView):
    """Display program details"""
    model = Program
    template_name = "portal/program_detail.html"
    context_object_name = "program"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        context['funding_schedules'] = self.object.funding_schedules.all()
        context['default_work_steps'] = self.object.default_work_steps.all()
        return context


# Project CRUD Views
class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects with filtering"""
    model = Project
    template_name = "portal/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        queryset = Project.objects.select_related('council', 'program', 'funding_schedule')

        # Apply user-specific filtering (council users see only their projects)
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            queryset = queryset.filter(council=user_council)

        # Apply search/filtering
        search = self.request.GET.get('search')
        program_filter = self.request.GET.get('program')
        council_filter = self.request.GET.get('council')
        state_filter = self.request.GET.get('state')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sap_project__icontains=search)
            )
        if program_filter:
            queryset = queryset.filter(program_id=program_filter)
        if council_filter:
            queryset = queryset.filter(council_id=council_filter)
        if state_filter:
            queryset = queryset.filter(state=state_filter)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.all()
        context['councils'] = Council.objects.all()
        context['states'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project"""
    model = Project
    form_class = ProjectForm
    template_name = "portal/project_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Project "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectForm
    template_name = "portal/project_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Project "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project"""
    model = Project
    template_name = "portal/project_confirm_delete.html"
    success_url = reverse_lazy('portal:project_list')

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(self.request, f'Project "{project.name}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class ProjectStateUpdateView(LoginRequiredMixin, UpdateView):
    """Update project state only"""
    model = Project
    form_class = ProjectStateForm
    template_name = "portal/project_state_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        old_state = self.get_object().state
        response = super().form_valid(form)
        new_state = self.object.state
        if old_state != new_state:
            messages.success(self.request, f'Project state changed from {dict(Project.STATE_CHOICES)[old_state]} to {dict(Project.STATE_CHOICES)[new_state]}.')
        return response


# Work Type CRUD Views
class WorkTypeListView(LoginRequiredMixin, ListView):
    """List all work types"""
    model = WorkType
    template_name = "portal/work_type_list.html"
    context_object_name = "work_types"
    paginate_by = 20

    def get_queryset(self):
        queryset = WorkType.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('name')


class WorkTypeCreateView(LoginRequiredMixin, CreateView):
    """Create a new work type"""
    model = WorkType
    form_class = WorkTypeForm
    template_name = "portal/work_type_form.html"
    success_url = reverse_lazy('portal:work_type_list')

    def form_valid(self, form):
        messages.success(self.request, f'Work type "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class WorkTypeUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing work type"""
    model = WorkType
    form_class = WorkTypeForm
    template_name = "portal/work_type_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:work_type_list')

    def form_valid(self, form):
        messages.success(self.request, f'Work type "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class WorkTypeDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a work type"""
    model = WorkType
    template_name = "portal/work_type_confirm_delete.html"
    success_url = reverse_lazy('portal:work_type_list')

    def delete(self, request, *args, **kwargs):
        work_type = self.get_object()
        # Check if work type is in use
        if work_type.get_usage_count() > 0:
            messages.error(request, f'Cannot delete work type "{work_type.name}" as it is currently in use by {work_type.get_usage_count()} items.')
            return redirect(reverse_lazy('portal:work_type_list'))
        messages.success(request, f'Work type "{work_type.name}" has been deleted.')
        return super().delete(request, *args, **kwargs)


# Output Type CRUD Views
class OutputTypeListView(LoginRequiredMixin, ListView):
    """List all output types"""
    model = OutputType
    template_name = "portal/output_type_list.html"
    context_object_name = "output_types"
    paginate_by = 20

    def get_queryset(self):
        queryset = OutputType.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('name')


class OutputTypeCreateView(LoginRequiredMixin, CreateView):
    """Create a new output type"""
    model = OutputType
    form_class = OutputTypeForm
    template_name = "portal/output_type_form.html"
    success_url = reverse_lazy('portal:output_type_list')

    def form_valid(self, form):
        messages.success(self.request, f'Output type "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class OutputTypeUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing output type"""
    model = OutputType
    form_class = OutputTypeForm
    template_name = "portal/output_type_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:output_type_list')

    def form_valid(self, form):
        messages.success(self.request, f'Output type "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class OutputTypeDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an output type"""
    model = OutputType
    template_name = "portal/output_type_confirm_delete.html"
    success_url = reverse_lazy('portal:output_type_list')

    def delete(self, request, *args, **kwargs):
        output_type = self.get_object()
        # Check if output type is in use
        if output_type.get_usage_count() > 0:
            messages.error(request, f'Cannot delete output type "{output_type.name}" as it is currently in use by {output_type.get_usage_count()} items.')
            return redirect(reverse_lazy('portal:output_type_list'))
        messages.success(request, f'Output type "{output_type.name}" has been deleted.')
        return super().delete(request, *args, **kwargs)


# Address CRUD Views
class AddressCreateView(LoginRequiredMixin, CreateView):
    """Create a new address for a project"""
    model = Address
    form_class = AddressForm
    template_name = "portal/address_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Address(project=self.project)
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
        return context


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing address"""
    model = Address
    form_class = AddressForm
    template_name = "portal/address_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Address "{form.instance}" updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an address"""
    model = Address
    template_name = "portal/address_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def delete(self, request, *args, **kwargs):
        address = self.get_object()
        project = address.project
        messages.success(request, f'Address "{address}" has been deleted.')
        return super().delete(request, *args, **kwargs)


# Work CRUD Views
class WorkCreateView(LoginRequiredMixin, CreateView):
    """Create a new work for a project"""
    model = Work
    form_class = WorkForm
    template_name = "portal/work_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Work(project=self.project)
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.project.pk})

    def form_valid(self, form):
        form.instance.project = self.project
        messages.success(self.request, f'Work "{form.instance}" created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing work"""
    model = Work
    form_class = WorkForm
    template_name = "portal/work_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Work "{form.instance}" updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context


class WorkDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a work"""
    model = Work
    template_name = "portal/work_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def delete(self, request, *args, **kwargs):
        work = self.get_object()
        project = work.project
        messages.success(request, f'Work "{work}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class QuarterlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/quarterly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = QuarterlyReportForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = QuarterlyReportForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quarterly report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


class Stage1ReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/stage1_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = Stage1ReportForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = Stage1ReportForm(request.POST, request.FILES, user=self.request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stage 1 report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.render_to_response({'form': form})


class Stage2ReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/stage2_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = Stage2ReportForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = Stage2ReportForm(request.POST, request.FILES, user=self.request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stage 2 report submitted successfully!')
            return redirect('portal:council_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')

# Enhanced Analytics and Forecasting Views
class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Advanced analytics dashboard with budget forecasting and anomaly detection"""
    template_name = "portal/analytics_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        # Get program filter
        program_filter = self.request.GET.get('program')

        if not start_date:
            start_date = timezone.now().date().replace(day=1)  # First day of current month
        if not end_date:
            end_date = timezone.now().date()

        # Convert to date objects
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = timezone.now().date().replace(day=1)
            end_date = timezone.now().date()

        # Filter projects based on user permissions
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            projects = Project.objects.filter(council=user_council)
        else:
            projects = Project.objects.all()

        # Apply program filter if specified
        if program_filter:
            projects = projects.filter(program_id=program_filter)

        # Get works data for output analytics
        works_queryset = Work.objects.filter(project__in=projects)

        # 1. Enhanced Outputs Analysis
        outputs_by_type = works_queryset.values('output_type_id').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        # Enhanced groupings
        outputs_by_work_type = works_queryset.values('work_type_id').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_bedrooms = works_queryset.values('bedrooms').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_council = works_queryset.values(
            'project__council__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_program = works_queryset.values(
            'project__program__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        # 2. Project Status Tracking
        commenced_projects = projects.filter(
            date_physically_commenced__range=[start_date, end_date]
        ).count()

        completed_projects = projects.filter(
            actual_completion__range=[start_date, end_date]
        ).count()

        # Addresses/Projects commenced in period
        addresses_commenced = Address.objects.filter(
            project__in=projects,
            project__date_physically_commenced__range=[start_date, end_date]
        ).count()

        # 3. Budget Forecasting and Anomaly Detection
        budget_analytics = self.analyze_budget_forecasting(projects, end_date)

        # 4. Report overdue alerts
        report_alerts = self.analyze_report_alerts(projects, end_date)

        # Combine all alerts
        all_alerts = budget_analytics.get('alerts', []) + report_alerts

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'program_filter': program_filter,
            'programs': Program.objects.all(),
            'outputs_by_type': outputs_by_type,
            'outputs_by_work_type': outputs_by_work_type,
            'outputs_by_bedrooms': outputs_by_bedrooms,
            'outputs_by_council': outputs_by_council,
            'outputs_by_program': outputs_by_program,
            'commenced_projects': commenced_projects,
            'completed_projects': completed_projects,
            'addresses_commenced': addresses_commenced,
            'budget_analytics': budget_analytics,
            'alerts': all_alerts,
            'report_alerts': report_alerts,
            'forecast_summary': budget_analytics.get('forecast_summary', {})
        })

        return context

    def analyze_budget_forecasting(self, projects, analysis_date):
        """Analyze budget spending patterns and detect anomalies"""
        try:
            import numpy as np
        except ImportError:
            np = None

        analytics = {
            'alerts': [],
            'forecast_summary': {},
            'council_spending': [],
            'spending_groups': defaultdict(list)
        }

        # Minimum sample size for confident analysis
        MIN_SAMPLES = 3

        # Get quarterly spending data for the last 6 quarters
        quarters = []
        for i in range(6):
            # Calculate quarter start (first month of quarter)
            quarter_start_month = ((analysis_date.month-1)//3)*3+1
            quarter_start = analysis_date.replace(month=quarter_start_month, day=1)

            # Calculate quarter end (last day of third month in quarter)
            quarter_end_month = min(quarter_start_month + 2, 12)
            _, last_day = calendar.monthrange(analysis_date.year, quarter_end_month)
            quarter_end = quarter_start.replace(month=quarter_end_month, day=last_day)

            quarters.append((quarter_start, quarter_end))

            # Move to previous quarter
            if quarter_start_month == 1:
                analysis_date = analysis_date.replace(year=analysis_date.year-1, month=12)
            else:
                analysis_date = analysis_date.replace(month=quarter_start_month-1)

        quarters.reverse()

        # Analyze spending by council
        council_spending = defaultdict(list)

        # Enhanced like-for-like comparison
        for quarter_start, quarter_end in quarters:
            quarterly_spending = QuarterlyReport.objects.filter(
                submission_date__range=[quarter_start, quarter_end],
                work__project__in=projects
            ).values(
                'work__project__council__name',
                'work__output_type_id',
                'work__bedrooms'
            ).annotate(
                total_spent=Sum('total_expenditure_council'),
                project_count=Count('work__project', distinct=True)
            )

            for entry in quarterly_spending:
                council_name = entry['work__project__council__name'] or 'Unknown Council'
                # Group by similar project types for better comparison
                group_key = f"{council_name}_{entry.get('work__output_type_id', 'unknown')}_{entry.get('work__bedrooms', 'unknown')}"

                analytics['spending_groups'][group_key] = analytics['spending_groups'].get(group_key, [])
                analytics['spending_groups'][group_key].append(float(entry['total_spent'] or 0))

            # Also maintain council-level summary for backwards compatibility
            for entry in quarterly_spending:
                council_name = entry['work__project__council__name'] or 'Unknown Council'
                council_spending[council_name].append(float(entry['total_spent'] or 0))

        # Enhanced anomaly detection with like-for-like comparison and sample size validation
        if np:
            # Analyze grouped spending (like-for-like comparison)
            for group_key, group_spending in analytics['spending_groups'].items():
                if len(group_spending) >= MIN_SAMPLES:  # Require minimum sample size
                    spending_array = np.array(group_spending)

                    if spending_array.std() > 0:  # Check if there's variance
                        mean_spend = spending_array.mean()
                        std_spend = spending_array.std()

                        current_trend = spending_array[-1]  # Most recent value
                        deviation = abs(current_trend - mean_spend)

                        # Split group key to extract metadata
                        parts = group_key.split('_', 2)
                        council = parts[0]
                        output_type = parts[1] if len(parts) > 1 else 'unknown'
                        bedrooms = parts[2] if len(parts) > 2 else 'unknown'

                        if deviation > 2 * std_spend:  # 2 standard deviations
                            trend = "over-spending" if current_trend > mean_spend else "under-spending"
                            analytics['alerts'].append({
                                'council': council,
                                'group_key': group_key,
                                'output_type': output_type,
                                'bedrooms': bedrooms,
                                'type': trend,
                                'deviation': deviation,
                                'mean': mean_spend,
                                'std': std_spend,
                                'current': current_trend,
                                'severity': 'high',
                                'sample_size': len(group_spending)
                            })

                        elif deviation > std_spend:  # 1 standard deviation
                            trend = "elevated spending" if current_trend > mean_spend else "reduced spending"
                            analytics['alerts'].append({
                                'council': council,
                                'group_key': group_key,
                                'output_type': output_type,
                                'bedrooms': bedrooms,
                                'type': trend,
                                'deviation': deviation,
                                'mean': mean_spend,
                                'current': current_trend,
                                'severity': 'medium',
                                'sample_size': len(group_spending)
                            })

            # Fallback to council-level analysis if no grouped data
            for council, spending_history in council_spending.items():
                if len(spending_history) >= MIN_SAMPLES:
                    spending_array = np.array(spending_history)

                    if spending_array.std() > 0:
                        mean_spend = spending_array.mean()

                        # Forecast next quarter spending
                        if len(spending_history) >= 2:
                            trend_slope = np.polyfit(range(len(spending_history)), spending_history, 1)[0]
                            next_quarter_forecast = spending_history[-1] + trend_slope
                            analytics['forecast_summary'][council] = {
                                'current_avg': mean_spend,
                                'next_forecast': max(0, next_quarter_forecast),
                                'trend': 'increasing' if trend_slope > 0 else 'decreasing',
                                'sample_size': len(spending_history)
                            }

        # Sort alerts by severity
        analytics['alerts'].sort(key=lambda x: ['high', 'medium', 'low'].index(x['severity']))

        return analytics

    def analyze_report_alerts(self, projects, analysis_date):
        """Analyze overdue reports and missing stage reports"""
        alerts = []
        today = analysis_date

        for project in projects:
            # Check monthly reports - required for under construction projects
            if project.state == 'under_construction':
                last_month = today.replace(day=1) - timezone.timedelta(days=1)
                latest_monthly = MonthlyTracker.objects.filter(
                    work__project=project,
                    month__year=last_month.year,
                    month__month=last_month.month
                ).first()

                if not latest_monthly:
                    # Check how many days past due
                    days_overdue = (today - last_month.replace(day=1)).days
                    severity = 'high' if days_overdue >= 14 else 'medium'

                    alerts.append({
                        'type': 'Overdue Monthly Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'days_overdue': days_overdue,
                        'due_month': last_month.strftime('%B %Y'),
                        'project_id': project.id
                    })

            # Check quarterly reports - required for all active projects
            latest_quarterly = QuarterlyReport.objects.filter(work__project=project).order_by('-submission_date').first()

            if not latest_quarterly:
                # Check how many months have passed since project started
                if project.date_physically_commenced:
                    months_since_start = ((today.year - project.date_physically_commenced.year) * 12 +
                                        (today.month - project.date_physically_commenced.month))

                    if months_since_start >= 3:  # At least 3 months passed
                        # Check when last quarterly was due
                        # Assume quarterly reports are due at end of each quarter
                        current_quarter_start_month = ((today.month-1)//3)*3+1
                        if today.month > current_quarter_start_month:
                            # We're past quarter start, check if quarter ended
                            if today.month > current_quarter_start_month + 2:
                                days_overdue = (today - project.date_physically_commenced).days
                                severity = 'high'

                                alerts.append({
                                    'type': 'Missing Initial Quarterly Report',
                                    'council': project.council.name,
                                    'project': project.name,
                                    'severity': severity,
                                    'months_since_start': months_since_start,
                                    'project_id': project.id
                                })
                elif project.state in ['funded', 'commenced', 'under_construction']:
                    # Project is active but has no quarterly report ever
                    if project.date_physically_commenced:
                        days_since_start = (today - project.date_physically_commenced).days
                        if days_since_start > 90:  # More than 3 months active
                            alerts.append({
                                'type': 'Missing Quarterly Report',
                                'council': project.council.name,
                                'project': project.name,
                                'severity': 'high',
                                'days_since_start': days_since_start,
                                'project_id': project.id
                            })
            else:
                # Check if quarterly report is overdue (more than 3 months old)
                months_since_last_report = ((today.year - latest_quarterly.submission_date.year) * 12 +
                                          (today.month - latest_quarterly.submission_date.month))
                if months_since_last_report > 3:
                    days_overdue = (today - latest_quarterly.submission_date).days - 90  # 3 months
                    severity = 'high' if months_since_last_report >= 4 else 'medium'

                    alerts.append({
                        'type': 'Overdue Quarterly Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'days_overdue': max(0, days_overdue),
                        'last_report_date': latest_quarterly.submission_date.strftime('%d/%m/%Y'),
                        'project_id': project.id
                    })

            # Check Stage 1 reports - required when past target date but no report submitted
            if project.stage1_target and today > project.stage1_target:
                stage1_reports = Stage1Report.objects.filter(project=project)
                if not stage1_reports.exists():
                    days_overdue = (today - project.stage1_target).days
                    severity = 'high' if days_overdue >= 14 else 'medium'

                    alerts.append({
                        'type': 'Missing Stage 1 Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'target_date': project.stage1_target.strftime('%d/%m/%Y'),
                        'days_past_target': days_overdue,
                        'project_id': project.id
                    })

            # Check Stage 2 reports - required when past target date but no report submitted
            if project.stage2_target and today > project.stage2_target:
                stage2_reports = Stage2Report.objects.filter(project=project)
                if not stage2_reports.exists() or not stage2_reports.first().is_complete:
                    days_overdue = (today - project.stage2_target).days
                    severity = 'high' if days_overdue >= 14 else 'medium'
                    report_status = 'Not Submitted' if not stage2_reports.exists() else 'Incomplete'

                    alerts.append({
                        'type': f'Stage 2 Report {report_status}',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'target_date': project.stage2_target.strftime('%d/%m/%Y'),
                        'days_past_target': days_overdue,
                        'project_id': project.id
                    })

            # Check Stage sunset dates
            if project.stage1_sunset and today > project.stage1_sunset:
                stage1_reports = Stage1Report.objects.filter(project=project)
                if not stage1_reports.exists() or not stage1_reports.first().state_accepted:
                    days_overdue = (today - project.stage1_sunset).days
                    severity = 'critical'

                    alerts.append({
                        'type': 'Stage 1 Sunset Date Passed',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'sunset_date': project.stage1_sunset.strftime('%d/%m/%Y'),
                        'days_past_sunset': days_overdue,
                        'project_id': project.id
                    })

            if project.stage2_sunset and today > project.stage2_sunset:
                stage2_reports = Stage2Report.objects.filter(project=project)
                if not stage2_reports.exists() or not stage2_reports.first().is_complete:
                    days_overdue = (today - project.stage2_sunset).days
                    severity = 'critical'

                    alerts.append({
                        'type': 'Stage 2 Sunset Date Passed',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'sunset_date': project.stage2_sunset.strftime('%d/%m/%Y'),
                        'days_past_sunset': days_overdue,
                        'project_id': project.id
                    })

        # Sort alerts by severity (critical > high > medium)
        def get_severity_order(severity):
            order = {'critical': 0, 'high': 1, 'medium': 2}
            return order.get(severity, 3)

        alerts.sort(key=lambda x: get_severity_order(x['severity']))

        return alerts


# Funding Approval Views
class FundingApprovalListView(LoginRequiredMixin, ListView):
    """List all funding approvals with filtering and management capabilities"""
    model = FundingApproval
    template_name = "portal/funding_approval_list.html"
    context_object_name = "funding_approvals"
    paginate_by = 20

    def get_queryset(self):
        queryset = FundingApproval.objects.select_related().prefetch_related('projects')
        search = self.request.GET.get('search')
        council_filter = self.request.GET.get('council')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if search:
            queryset = queryset.filter(
                Q(mincor_reference__icontains=search) |
                Q(approved_by__icontains=search)
            )
        if council_filter:
            queryset = queryset.filter(projects__council_id=council_filter)
        if date_from:
            queryset = queryset.filter(approved_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(approved_date__lte=date_to)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['councils'] = Council.objects.all()
        return context


class FundingApprovalDetailView(LoginRequiredMixin, DetailView):
    """Display funding approval details and associated projects"""
    model = FundingApproval
    template_name = "portal/funding_approval_detail.html"
    context_object_name = "funding_approval"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['associated_projects'] = self.object.projects.all().select_related('council', 'program')
        return context


class FundingApprovalCreateView(LoginRequiredMixin, CreateView):
    """Create a new funding approval"""
    model = FundingApproval
    template_name = "portal/funding_approval_form.html"
    fields = ['mincor_reference', 'amount', 'approved_by', 'approved_date', 'projects']
    success_url = reverse_lazy('portal:funding_approval_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Update project states when funding is approved
        for project in self.object.projects.all():
            if project.state == 'prospective':
                project.state = 'funded'
                project.save()
                messages.success(self.request,
                    f'Project "{project.name}" state updated to "Funded" due to funding approval.')
        return response


# Funding Schedule Views for Projects
class AddProjectToFundingScheduleView(LoginRequiredMixin, CreateView):
    """View to add a project to an existing or new funding schedule"""
    model = FundingSchedule
    template_name = "portal/add_project_funding_schedule.html"
    fields = ['funding_schedule_number', 'program', 'funding_amount', 'contingency_amount']

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['pk'])

        # Check permissions - user should have council access or be staff
        if not (request.user.is_staff or (hasattr(request.user, 'council') and request.user.council == self.project.council)):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to modify this project's funding.")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-populate form with council and program from project
        initial = {
            'council': self.project.council,
            'program': self.project.program,
        }
        kwargs['initial'] = initial
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['existing_schedules'] = FundingSchedule.objects.filter(
            council=self.project.council,
            program=self.project.program
        ).exclude(projects=self.project)
        return context

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.project.pk})

    def form_valid(self, form):
        # Set the council from the project
        form.instance.council = self.project.council

        response = super().form_valid(form)

        # Add the project to this funding schedule
        self.object.projects.add(self.project)

        # Update project state to funded
        if self.project.state == 'prospective':
            self.project.state = 'funded'
            self.project.funding_schedule_amount = self.object.funding_amount
            if self.object.contingency_amount:
                self.project.contingency_amount = self.object.contingency_amount
            self.project.save()

            messages.success(self.request,
                f'Project "{self.project.name}" has been added to funding schedule and state updated to "Funded".')

        return response


class FundingApprovalUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing funding approval"""
    model = FundingApproval
    template_name = "portal/funding_approval_form.html"
    fields = ['mincor_reference', 'amount', 'approved_by', 'approved_date', 'projects']

    def get_success_url(self):
        return reverse_lazy('portal:funding_approval_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        # Update project states when funding is approved
        for project in self.object.projects.all():
            if project.state == 'prospective':
                project.state = 'funded'
                project.save()
                messages.success(self.request,
                    f'Project "{project.name}" state updated to "Funded" due to funding approval.')
        return response