from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Sum, Count
from django.utils import timezone
from django.utils.dateformat import format
from django import forms
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from collections import defaultdict
import calendar

from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View
import json
from ricd.models import (
    Project, Program, Council, QuarterlyReport, MonthlyTracker, Stage1Report, Stage2Report,
    FundingSchedule, Address, Work, WorkStep, FundingApproval, WorkType, OutputType, ConstructionMethod, Officer,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement,
    RemoteCapitalProgramFundingAgreement, Defect
)
from .forms import (
    MonthlyTrackerForm, QuarterlyReportForm, Stage1ReportForm, Stage2ReportForm,
    CouncilForm, ProgramForm, ProjectForm, ProjectStateForm, AddressForm, WorkForm,
    WorkTypeForm, OutputTypeForm, ConstructionMethodForm, ForwardRemoteProgramFundingAgreementForm,
    InterimForwardProgramFundingAgreementForm, RemoteCapitalProgramFundingAgreementForm,
    UserCreationForm, OfficerForm, OfficerAssignmentForm, FundingApprovalForm,
    CustomExcelExportForm, DefectForm, CouncilUserCreationForm
)

# RICD Dashboard
class RICDDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/ricd_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view RICD dashboard.")
        return super().dispatch(request, *args, **kwargs)

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
        from django.db.models import Exists, OuterRef
        from ricd.models import Work, Address

        # Updated query to use address relationship since Work no longer has direct project FK
        latest_reports = QuarterlyReport.objects.filter(
            work__address__project=project
        ).order_by('-submission_date')
        if latest_reports.exists():
            avg_progress = latest_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
            return avg_progress or 0
        return 0

    def get_budget_vs_spent(self, project):
        """Calculate budget vs spent as 'Budget - Spent' or show remaining"""
        total_budget = 0
        total_spent = 0

        # Get total budget from funding schedule or commitments
        if project.funding_agreement and hasattr(project.funding_agreement, 'total_funding'):
            total_budget = project.funding_agreement.total_funding or 0
        elif hasattr(project.funding_schedule, 'total_funding'):
            total_budget = project.funding_schedule.total_funding or 0
        else:
            total_budget = project.commitments or 0

        # Sum total expenditures from quarterly reports
        expenditures = QuarterlyReport.objects.filter(
            work__address__project=project
        ).aggregate(
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

        # Apply stage filter if provided
        stage_filter = self.request.GET.get('stage')
        if stage_filter:
            user_projects = user_projects.filter(state=stage_filter)

        # Enhance projects with calculated data
        enhanced_projects = []
        for project in user_projects.select_related('council', 'program', 'funding_schedule'):
            # Get latest monthly report through works relationship
            latest_monthly = MonthlyTracker.objects.filter(work__address__project=project).order_by('-month').first()
            # Get latest quarterly report through works relationship
            latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()

            # Calculate progress from quarterly reports through works relationship
            quarterly_reports = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date')
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

        # Add only stage filter options
        context['stages'] = [{'value': choice[0], 'display': choice[1]} for choice in Project.STATE_CHOICES]
        context['current_stage'] = stage_filter

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
                work__address__project=project,
                month__year=last_month.year,
                month__month=last_month.month
            ).first()
            if not latest_monthly:
                overdue_reports.append('Monthly Report')

        # Check for quarterly reports
        latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()
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

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to view this project
        project = self.get_object()
        user_council = getattr(request.user, 'council', None)

        # If user has a council (council user), they can only view their own council's projects
        if user_council and project.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to view this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funding_approvals'] = self.object.funding_approvals.all()
        return context


# Council Project Detail View
class CouncilProjectDetailView(DetailView):
    model = Project
    template_name = "portal/council_project_detail.html"
    context_object_name = "project"

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to view this project
        project = self.get_object()
        user_council = getattr(request.user, 'council', None)

        # Only council users and managers can access this view
        if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only council users can view council project details.")

        # If user has a council, they can only view their own council's projects
        if user_council and project.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to view this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        # Add funding agreement information
        context['funding_agreement'] = project.funding_agreement
        context['funding_schedule'] = project.funding_schedule
        context['forward_rpf'] = project.forward_rpf_agreement
        context['interim_frp'] = project.interim_fp_agreement

        # Calculate funding amount (less contingency)
        if project.funding_agreement and hasattr(project.funding_agreement, 'funding_amount'):
            total_funding = project.funding_agreement.funding_amount or 0
            contingency = project.funding_agreement.contingency_amount or 0
            context['funding_amount_less_contingency'] = total_funding - contingency
        else:
            context['funding_amount_less_contingency'] = 0

        # Get overall progress from latest quarterly reports
        from django.db.models import Avg
        latest_reports = QuarterlyReport.objects.filter(
            work__address__project=project
        ).order_by('-submission_date')[:5]  # Last 5 reports

        if latest_reports.exists():
            avg_progress = latest_reports.aggregate(avg_progress=Avg('percentage_works_completed'))['avg_progress']
            context['overall_progress'] = avg_progress or 0
        else:
            context['overall_progress'] = 0

        # Get defects for this project
        context['defects'] = Defect.objects.filter(work__address__project=project).select_related('work__address')

        return context


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
    """List all councils - accessible by RICD users only"""
    model = Council
    template_name = "portal/council_list.html"
    context_object_name = "councils"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view council list.")
        return super().dispatch(request, *args, **kwargs)

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

    def form_valid(self, form):
        council = self.get_object()
        messages.success(self.request, f'Council "{council.name}" has been deleted.')
        return super().form_valid(form)


class CouncilDetailView(LoginRequiredMixin, DetailView):
    """Display council details"""
    model = Council
    template_name = "portal/council_detail.html"
    context_object_name = "council"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        context['funding_schedules'] = self.object.funding_schedules.all()

        # Add council users with role information (only Council User and Council Manager groups)
        council_users = []
        for profile in self.object.users.all().select_related('user'):
            user = profile.user
            # Only include users who are in Council User or Council Manager groups
            if user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
                # Add role information to user for template use
                user.council_role = None
                for group in user.groups.all():
                    if group.name == 'Council Manager':
                        user.council_role = 'manager'
                        break
                    elif group.name == 'Council User':
                        user.council_role = 'user'
                        break
                council_users.append(user)

        context['council_users'] = council_users
        return context


class CouncilUserCreateView(LoginRequiredMixin, CreateView):
    """Create a new council user - RICD users can select council, Council Managers create for their own council"""
    model = User
    form_class = CouncilUserCreationForm
    template_name = "portal/council_user_form.html"

    def dispatch(self, request, *args, **kwargs):
        # Only get council from URL if it's a council-specific URL (for Council Managers)
        if 'council_pk' in self.kwargs:
            self.council = get_object_or_404(Council, pk=self.kwargs['council_pk'])
        else:
            self.council = None
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.council:
            kwargs['council'] = self.council
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.council:
            context['council'] = self.council
        return context

    def get_success_url(self):
        # If we have a specific council, go back to it
        if self.council:
            return reverse_lazy('portal:council_detail', kwargs={'pk': self.council.pk})
        # Otherwise, go to council list
        return reverse_lazy('portal:council_list')

    def form_valid(self, form):
        # Check permissions before saving
        user = self.request.user
        selected_council = form.cleaned_data.get('council') or self.council

        # Only RICD users or Council Managers of this council can create users
        user_council = getattr(user, 'council', None)
        is_ricd = user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_manager = user.groups.filter(name='Council Manager').exists() and user_council == selected_council

        if not (is_ricd or is_council_manager):
            messages.error(self.request, 'You do not have permission to create users for this council.')
            return self.form_invalid(form)

        # Additional check: only RICD users can create Council Manager roles
        role = form.cleaned_data.get('role')
        if role == 'council_manager' and not is_ricd:
            messages.error(self.request, 'Only RICD staff can create Council Manager accounts.')
            return self.form_invalid(form)

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: CouncilUserCreateView.form_valid - Creating user: {form.cleaned_data.get('username')}, Council: {selected_council}, Role: {role}")

        try:
            response = super().form_valid(form)

            # Verify user was created and has profile
            created_user = form.instance
            logger.info(f"DEBUG: User created - ID: {created_user.pk}, Username: {created_user.username}")

            # Check if profile was created
            if hasattr(created_user, 'profile'):
                logger.info(f"DEBUG: UserProfile exists - Council: {created_user.profile.council}")
            else:
                logger.error(f"DEBUG: UserProfile NOT created for user {created_user.username}")

            # Check groups
            user_groups = list(created_user.groups.values_list('name', flat=True))
            logger.info(f"DEBUG: User groups: {user_groups}")

            role_display = "Council Manager" if role == 'council_manager' else "Council User"
            council_name = selected_council.name if selected_council else "Unknown Council"
            messages.success(self.request, f'{role_display} "{created_user.username}" created successfully for {council_name}.')
            return response

        except Exception as e:
            logger.error(f"DEBUG: Error creating user: {str(e)}")
            messages.error(self.request, f'Error creating user: {str(e)}')
            return self.form_invalid(form)


# Program CRUD Views
class ProgramListView(LoginRequiredMixin, ListView):
    """List all programs - RICD users only"""
    model = Program
    template_name = "portal/program_list.html"
    context_object_name = "programs"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view programs.")
        return super().dispatch(request, *args, **kwargs)

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

    def form_valid(self, form):
        program = self.get_object()
        messages.success(self.request, f'Program "{program.name}" has been deleted.')
        return super().form_valid(form)


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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectListView - User: {self.request.user.username}, User Council: {user_council}, Is Staff: {self.request.user.is_staff}, Groups: {[g.name for g in self.request.user.groups.all()]}")

        if user_council:
            queryset = queryset.filter(council=user_council)
            logger.info(f"DEBUG: ProjectListView - Filtering by council: {user_council.name}")

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
            logger.info(f"DEBUG: ProjectListView - Additional council filter applied: {council_filter}")
        if state_filter:
            queryset = queryset.filter(state=state_filter)

        final_queryset = queryset.order_by('name')
        logger.info(f"DEBUG: ProjectListView - Final queryset count: {final_queryset.count()}")
        return final_queryset

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
        # Check if user is in Council groups
        if self.request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            form.instance.state = 'prospective'
        messages.success(self.request, f'Project "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectForm
    template_name = "portal/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to update this project
        project = self.get_object()
        user_council = getattr(request.user, 'council', None)

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectUpdateView.dispatch - User: {request.user.username}, User Council: {user_council}, Project ID: {kwargs.get('pk')}, Project Council: {project.council}")

        # If user has a council (council user), they can only update their own council's projects
        if user_council and project.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to update this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: ProjectUpdateView.form_valid - User: {self.request.user.username}, Project: {form.instance.name}, Council: {form.instance.council}")
        messages.success(self.request, f'Project "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project"""
    model = Project
    template_name = "portal/project_confirm_delete.html"
    success_url = reverse_lazy('portal:project_list')

    def form_valid(self, form):
        project = self.get_object()
        messages.success(self.request, f'Project "{project.name}" has been deleted.')
        return super().form_valid(form)


class ProjectStateUpdateView(LoginRequiredMixin, UpdateView):
    """Update project state only"""
    model = Project
    form_class = ProjectStateForm
    template_name = "portal/project_state_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # Check if user is in RICD groups (only RICD officers can change project state)
        if not self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            messages.error(self.request, 'Only RICD officers can change project state.')
            return self.form_invalid(form)

        old_state = self.get_object().state
        response = super().form_valid(form)
        new_state = self.object.state
        if old_state != new_state:
            messages.success(self.request, f'Project state changed from {dict(Project.STATE_CHOICES)[old_state]} to {dict(Project.STATE_CHOICES)[new_state]}.')
        return response


# Custom Login View for role-based redirection
class CustomLoginView(auth_views.LoginView):
    """Custom login view that redirects based on user role"""
    template_name = 'portal/login.html'

    def get_success_url(self):
        """Determine redirect URL based on user role"""
        user = self.request.user

        import logging
        logger = logging.getLogger(__name__)
        user_council = getattr(user, 'council', None)
        logger.info(f"DEBUG: CustomLoginView.get_success_url - User: {user.username}, Groups: {[g.name for g in user.groups.all()]}, User Council: {user_council}")

        # Check if user is in RICD groups
        if user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            logger.info("DEBUG: CustomLoginView.get_success_url - Redirecting to RICD dashboard")
            return '/portal/ricd/'

        # Check if user is in Council groups
        if user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            logger.info("DEBUG: CustomLoginView.get_success_url - Redirecting to Council dashboard")
            return '/portal/council/'

        # Check if user has a council (council user - fallback)
        if user_council:
            logger.info("DEBUG: CustomLoginView.get_success_url - Redirecting to Council dashboard (fallback)")
            return '/portal/council/'

        # Default fallback
        logger.info("DEBUG: CustomLoginView.get_success_url - Redirecting to RICD dashboard (default)")
        return '/portal/ricd/'


# Help Pages Views
class RICDSHelpView(LoginRequiredMixin, TemplateView):
    """RICD Staff Help Page"""
    template_name = "portal/help_ricd.html"


class CouncilHelpView(LoginRequiredMixin, TemplateView):
    """Council Help Page"""
    template_name = "portal/help_council.html"


# Export Views
class AddressWorkExportView(LoginRequiredMixin, View):
    """Export all addresses and works data to Excel format"""

    def get(self, request, *args, **kwargs):
        import pandas as pd
        from django.http import HttpResponse

        # Get all addresses with related data
        addresses = Address.objects.select_related(
            'project', 'project__council', 'project__program',
            'work_type_id', 'output_type_id'
        ).all()

        selected_fields = request.GET.getlist('fields')

        # Default fields if none selected
        if not selected_fields:
            selected_fields = [
                'State', 'Project', 'Council', 'Program', 'Street', 'Suburb',
                'Postcode', 'Work Type', 'Output Type', 'Bedrooms',
                'Output Quantity', 'Estimated Cost', 'Actual Cost',
                'Start Date', 'End Date'
            ]

        # Prepare data for export
        data = []
        for address in addresses:
            # Get associated works for this address
            works = Work.objects.filter(address=address).select_related('work_type_id', 'output_type_id')

            if works.exists():
                # Create a row for each work at this address
                for work in works:
                    full_row = {
                        'State': address.state or '',
                        'Project': address.project.name,
                        'Council': address.project.council.name if address.project.council else '',
                        'Program': address.project.program.name if address.project.program else '',
                        'Street': address.street,
                        'Suburb': address.suburb or '',
                        'Postcode': address.postcode or '',
                        'Work Type': work.work_type_id.name if work.work_type_id else '',
                        'Output Type': work.output_type_id.name if work.output_type_id else '',
                        'Bedrooms': work.bedrooms or '',
                        'Output Quantity': work.output_quantity or 1,
                        'Estimated Cost': work.estimated_cost or '',
                        'Actual Cost': work.actual_cost or '',
                        'Start Date': work.start_date.strftime('%Y-%m-%d') if work.start_date else '',
                        'End Date': work.end_date.strftime('%Y-%m-%d') if work.end_date else '',
                        'Land Status': work.land_status or '',
                        'Floor Method': work.floor_method or '',
                        'Frame Method': work.frame_method or '',
                        'External Wall Method': work.external_wall_method or '',
                        'Roof Method': work.roof_method or '',
                        'Car Accommodation': work.car_accommodation or '',
                        'Additional Facilities': work.additional_facilities or '',
                        'Extension High Low': work.extension_high_low or '',
                        'Bathrooms': work.bathrooms or '',
                        'Kitchens': work.kitchens or '',
                        'Dwellings Count': work.dwellings_count or '',
                        'Lot Number': address.lot_number or '',
                        'Plan Number': address.plan_number or '',
                        'Title Reference': address.title_reference or '',
                    }
                    # Filter to only selected fields
                    row = {field: full_row[field] for field in selected_fields if field in full_row}
                    data.append(row)
            else:
                # Address without work data
                full_row = {
                    'State': address.state or '',
                    'Project': address.project.name,
                    'Council': address.project.council.name if address.project.council else '',
                    'Program': address.project.program.name if address.project.program else '',
                    'Street': address.street,
                    'Suburb': address.suburb or '',
                    'Postcode': address.postcode or '',
                    'Work Type': '',
                    'Output Type': '',
                    'Bedrooms': '',
                    'Output Quantity': '',
                    'Estimated Cost': '',
                    'Actual Cost': '',
                    'Start Date': '',
                    'End Date': '',
                    'Land Status': '',
                    'Floor Method': '',
                    'Frame Method': '',
                    'External Wall Method': '',
                    'Roof Method': '',
                    'Car Accommodation': '',
                    'Additional Facilities': '',
                    'Extension High Low': '',
                    'Bathrooms': '',
                    'Kitchens': '',
                    'Dwellings Count': '',
                    'Lot Number': address.lot_number or '',
                    'Plan Number': address.plan_number or '',
                    'Title Reference': address.title_reference or '',
                }
                # Filter to only selected fields
                row = {field: full_row[field] for field in selected_fields if field in full_row}
                data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data)

        # Create Excel file
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="addresses_and_works_export.xlsx"'

        try:
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Addresses and Works', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Addresses and Works']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Max width of 50
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        except ImportError:
            # Fallback without pandas if not available
            response = HttpResponse("Excel export requires pandas and openpyxl libraries to be installed.", content_type='text/plain')

        return response


class CustomExportView(LoginRequiredMixin, TemplateView):
    """View for configuring custom Excel export with field selection"""
    template_name = 'portal/custom_export.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomExcelExportForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CustomExcelExportForm(request.POST)
        if form.is_valid():
            selected_fields = form.cleaned_data['fields']
            # Redirect to export view with selected fields as URL parameters
            from django.shortcuts import redirect
            from urllib.parse import urlencode

            query_string = urlencode({'fields': selected_fields}, doseq=True)
            return redirect(f'/analytics/export/addresses-works/?{query_string}')
        else:
            return self.render_to_response({'form': form})


# Work Type CRUD Views
class WorkTypeListView(LoginRequiredMixin, ListView):
    """List work types - RICD users only"""
    model = WorkType
    template_name = "portal/work_type_list.html"
    context_object_name = "work_types"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view work types.")
        return super().dispatch(request, *args, **kwargs)

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

    def form_valid(self, form):
        work_type = self.get_object()
        # Check if work type is in use
        if work_type.get_usage_count() > 0:
            messages.error(self.request, f'Cannot delete work type "{work_type.name}" as it is currently in use by {work_type.get_usage_count()} items.')
            return redirect(reverse_lazy('portal:work_type_list'))
        messages.success(self.request, f'Work type "{work_type.name}" has been deleted.')
        return super().form_valid(form)


# Output Type CRUD Views
class OutputTypeListView(LoginRequiredMixin, ListView):
    """List output types - RICD users only"""
    model = OutputType
    template_name = "portal/output_type_list.html"
    context_object_name = "output_types"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view output types.")
        return super().dispatch(request, *args, **kwargs)

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

    def form_valid(self, form):
        output_type = self.get_object()
        # Check if output type is in use
        if output_type.get_usage_count() > 0:
            messages.error(self.request, f'Cannot delete output type "{output_type.name}" as it is currently in use by {output_type.get_usage_count()} items.')
            return redirect(reverse_lazy('portal:output_type_list'))
        messages.success(self.request, f'Output type "{output_type.name}" has been deleted.')
        return super().form_valid(form)


# Construction Method CRUD Views
class ConstructionMethodListView(LoginRequiredMixin, ListView):
    """List construction methods - RICD users only"""
    model = ConstructionMethod
    template_name = "portal/construction_method_list.html"
    context_object_name = "construction_methods"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view construction methods.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ConstructionMethod.objects.all()
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


class ConstructionMethodCreateView(LoginRequiredMixin, CreateView):
    """Create a new construction method"""
    model = ConstructionMethod
    form_class = ConstructionMethodForm
    template_name = "portal/construction_method_form.html"
    success_url = reverse_lazy('portal:construction_method_list')

    def form_valid(self, form):
        messages.success(self.request, f'Construction method "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ConstructionMethodUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing construction method"""
    model = ConstructionMethod
    form_class = ConstructionMethodForm
    template_name = "portal/construction_method_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:construction_method_list')

    def form_valid(self, form):
        messages.success(self.request, f'Construction method "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ConstructionMethodDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a construction method"""
    model = ConstructionMethod
    template_name = "portal/construction_method_confirm_delete.html"
    success_url = reverse_lazy('portal:construction_method_list')

    def form_valid(self, form):
        construction_method = self.get_object()
        # Check if construction method is in use
        if construction_method.get_usage_count() > 0:
            messages.error(self.request, f'Cannot delete construction method "{construction_method.name}" as it is currently in use by {construction_method.get_usage_count()} items.')
            return redirect(reverse_lazy('portal:construction_method_list'))
        messages.success(self.request, f'Construction method "{construction_method.name}" has been deleted.')
        return super().form_valid(form)


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
        kwargs['project'] = self.project  # Pass project for budget validation
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

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

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

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

        return context


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an address"""
    model = Address
    template_name = "portal/address_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        address = self.get_object()
        project = address.project
        messages.success(self.request, f'Address "{address}" has been deleted.')
        return super().form_valid(form)


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
        kwargs['project'] = self.project
        return kwargs

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Work "{form.instance}" created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.object.project  # Pass project for budget validation
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project

        # Add work type to output type mappings for JavaScript
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[work_type.id] = [ot.id for ot in work_type.allowed_output_types.all()]
        context['work_type_output_types_json'] = json.dumps(work_type_mappings)

        return context


class WorkDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a work"""
    model = Work
    template_name = "portal/work_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        work = self.get_object()
        project = work.project
        messages.success(self.request, f'Work "{work}" has been deleted.')
        return super().form_valid(form)


# Work List View
class WorkListView(LoginRequiredMixin, ListView):
    """List all works with filtering and templating features"""
    model = Work
    template_name = "portal/work_list.html"
    context_object_name = "works"
    paginate_by = 25

    def get_queryset(self):
        queryset = Work.objects.select_related(
            'address__project__council',
            'address__project__program',
            'work_type_id',
            'output_type_id'
        )

        # Apply user-specific filtering (council users see only their works)
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            queryset = queryset.filter(address__project__council=user_council)

        # Apply search/filtering
        search = self.request.GET.get('search')
        construction_filter = self.request.GET.get('construction_type')
        output_filter = self.request.GET.get('output_type')
        project_filter = self.request.GET.get('project')
        status_filter = self.request.GET.get('status')  # completed/pending/all

        if search:
            queryset = queryset.filter(
                Q(address__street__icontains=search) |
                Q(address__project__name__icontains=search) |
                Q(work_type_id__name__icontains=search) |
                Q(output_type_id__name__icontains=search)
            )
        if construction_filter:
            queryset = queryset.filter(work_type_id__code=construction_filter)
        if output_filter:
            queryset = queryset.filter(output_type_id__code=output_filter)
        if project_filter:
            queryset = queryset.filter(address__project_id=project_filter)
        if status_filter == 'completed':
            queryset = queryset.exclude(end_date__isnull=True)
        elif status_filter == 'pending':
            queryset = queryset.filter(end_date__isnull=True)

        # Allow reordering
        order_by = self.request.GET.get('order_by', '-start_date')
        if order_by in ['start_date', '-start_date', 'estimated_cost', '-estimated_cost', 'end_date', '-end_date']:
            queryset = queryset.order_by(order_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter options
        user_council = getattr(self.request.user, 'council', None)
        projects = Project.objects.select_related('council', 'program')
        if user_council:
            projects = projects.filter(council=user_council)

        context.update({
            'projects': projects,
            'work_types': WorkType.objects.filter(is_active=True),
            'output_types': OutputType.objects.filter(is_active=True),
            'order_options': [
                ('-start_date', 'Recent Start First'),
                ('start_date', 'Oldest Start First'),
                ('-estimated_cost', 'Highest Cost First'),
                ('estimated_cost', 'Lowest Cost First'),
                ('-end_date', 'Recently Completed'),
                ('end_date', 'Oldest Completed'),
            ]
        })

        # Add current filters for form pre-population
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'construction_type': self.request.GET.get('construction_type', ''),
            'output_type': self.request.GET.get('output_type', ''),
            'project': self.request.GET.get('project', ''),
            'status': self.request.GET.get('status', ''),
            'order_by': self.request.GET.get('order_by', '-start_date'),
        }

        return context


# Work Step Management Views
class WorkStepListView(LoginRequiredMixin, DetailView):
    """View to list and manage work steps (stages/tasks) for a specific work"""
    model = Work
    template_name = "portal/work_step_list.html"
    context_object_name = "work"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.work_steps.order_by('order')
        return context


class WorkStepReorderView(LoginRequiredMixin, View):
    """View to reorder work steps"""

    def post(self, request, work_pk):
        work = get_object_or_404(Work, pk=work_pk)

        # Check permissions
        if not (request.user.is_staff or (
            hasattr(request.user, 'council') and
            request.user.council == work.address.project.council
        )):
            messages.error(request, "You don't have permission to modify this work.")
            return redirect('portal:work_detail', pk=work_pk)

        step_orders = request.POST.getlist('step_order[]')
        for i, step_id in enumerate(step_orders):
            try:
                step = WorkStep.objects.get(pk=step_id, work=work)
                step.order = i + 1
                step.save()
            except WorkStep.DoesNotExist:
                continue

        messages.success(request, 'Work steps reordered successfully!')
        return redirect('portal:work_step_list', work_pk=work_pk)


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

        # Get program filter
        program_filter = self.request.GET.get('program')

        # Filter projects based on user permissions - capture all projects without date restrictions
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            projects = Project.objects.filter(council=user_council)
        else:
            projects = Project.objects.all()

        # Apply program filter if specified
        if program_filter:
            projects = projects.filter(program_id=program_filter)

        # Get works data for output analytics - capture all without date restrictions
        works_queryset = Work.objects.filter(address__project__in=projects)

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
            'address__project__council__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_program = works_queryset.values(
            'address__project__program__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        # 2. Project Status Tracking - capture all without date restrictions
        commenced_projects = projects.filter(
            date_physically_commenced__isnull=False
        ).count()

        completed_projects = projects.filter(
            actual_completion__isnull=False
        ).count()

        # Addresses/Projects commenced - capture all without date restrictions
        addresses_commenced = Address.objects.filter(
            project__in=projects,
            project__date_physically_commenced__isnull=False
        ).count()

        # 3. Budget Forecasting and Anomaly Detection - use current date for analysis
        budget_analytics = self.analyze_budget_forecasting(projects, timezone.now().date())

        # 4. Report overdue alerts - check all projects without date restrictions
        report_alerts = self.analyze_report_alerts(projects, timezone.now().date())

        # Combine all alerts
        all_alerts = budget_analytics.get('alerts', []) + report_alerts

        context.update({
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
                work__address__project__in=projects
            ).values(
                'work__address__project__council__name',
                'work__output_type_id',
                'work__bedrooms'
            ).annotate(
                total_spent=Sum('total_expenditure_council'),
                project_count=Count('work__address__project', distinct=True)
            )

            for entry in quarterly_spending:
                council_name = entry['work__address__project__council__name'] or 'Unknown Council'
                # Group by similar project types for better comparison
                group_key = f"{council_name}_{entry.get('work__output_type_id', 'unknown')}_{entry.get('work__bedrooms', 'unknown')}"

                analytics['spending_groups'][group_key] = analytics['spending_groups'].get(group_key, [])
                analytics['spending_groups'][group_key].append(float(entry['total_spent'] or 0))

            # Also maintain council-level summary for backwards compatibility
            for entry in quarterly_spending:
                council_name = entry['work__address__project__council__name'] or 'Unknown Council'
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
                    work__address__project=project,
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
            latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()

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
    """List funding approvals - RICD users only"""
    model = FundingApproval
    template_name = "portal/funding_approval_list.html"
    context_object_name = "funding_approvals"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view funding approvals.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = FundingApproval.objects.select_related().prefetch_related('projects')
        search = self.request.GET.get('search')
        council_filter = self.request.GET.get('council')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if search:
            queryset = queryset.filter(
                Q(mincor_reference__icontains=search) |
                Q(approved_by_position__icontains=search)
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
    form_class = FundingApprovalForm
    template_name = "portal/funding_approval_form.html"
    success_url = reverse_lazy('portal:funding_approval_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Check for project parameter in query string
        project_id = self.request.GET.get('project')
        if project_id:
            try:
                project = Project.objects.get(pk=project_id)
                kwargs['initial_project'] = project
            except Project.DoesNotExist:
                pass  # Ignore if project doesn't exist
        return kwargs

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


# Remote Capital Program Funding Agreement CRUD Views
class RemoteCapitalProgramListView(LoginRequiredMixin, ListView):
    """List Remote Capital Program Funding Agreements - RICD users only"""
    model = RemoteCapitalProgramFundingAgreement
    template_name = "portal/remote_capital_program_list.html"
    context_object_name = "agreements"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view remote capital program agreements.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = RemoteCapitalProgramFundingAgreement.objects.select_related('council')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(council__name__icontains=search) |
                Q(date_council_signed__icontains=search) |
                Q(date_delegate_signed__icontains=search)
            )
        return queryset.order_by('-date_council_signed')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link_project = self.request.GET.get('link_project')
        unlink_project = self.request.GET.get('unlink_project')

        if link_project:
            try:
                project = Project.objects.get(pk=link_project)
                context['link_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show link functionality

        if unlink_project:
            try:
                project = Project.objects.get(pk=unlink_project)
                context['unlink_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show unlink functionality

        return context

    def post(self, request, *args, **kwargs):
        """Handle linking/unlinking projects to agreements"""
        project_id = request.POST.get('project_id')
        agreement_id = request.POST.get('agreement_id')
        action = request.POST.get('action')

        if not project_id:
            messages.error(request, 'Project ID is required.')
            return self.get(request)

        try:
            project = Project.objects.get(pk=project_id)

            # Check permissions
            if not (request.user.is_staff or (hasattr(request.user, 'council') and request.user.council == project.council)):
                messages.error(request, "You don't have permission to modify this project.")
                return redirect('portal:project_detail', pk=project_id)

            if action == 'link' and agreement_id:
                agreement = RemoteCapitalProgramFundingAgreement.objects.get(pk=agreement_id)

                # Ensure project is not already linked to another agreement type
                if project.tuition_agreement or project.forward_rpf_agreement or project.funding_schedule:
                    messages.error(request,
                       'Project is already linked to another funding agreement. Remove existing link first.')
                    return redirect('portal:project_detail', pk=project_id)

                # For remote capital programs, we link through the funding schedule
                agreement.funding_schedules.create(
                    council=project.council,
                    program=project.program,
                    funding_schedule_number=f"RCP-{project.council.abn}-{agreement.pk}",
                    funding_amount=0,  # To be set later
                    remote_capital_program=agreement,
                    agreement_type='rcpf_agreement'
                )

                messages.success(request, f'Project "{project.name}" linked to Remote Capital Program "{agreement}".')

            elif action == 'unlink':
                if not project.funding_agreement or project.funding_agreement.agreement_type != 'rcpf_agreement':
                    messages.warning(request, 'Project is not linked to any Remote Capital Program.')
                else:
                    agreement_name = str(project.funding_agreement)
                    # Remove the project from its funding schedule and delete the schedule
                    if hasattr(project.funding_agreement, 'funding_schedules'):
                        project.funding_agreement.funding_schedules.clear()
                    project.funding_schedule = None
                    project.save()
                    messages.success(request, f'Project "{project.name}" unlinked from Remote Capital Program "{agreement_name}".')

        except Project.DoesNotExist:
            messages.error(request, 'Project not found.')
        except RemoteCapitalProgramFundingAgreement.DoesNotExist:
            messages.error(request, 'Remote Capital Program Agreement not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

        return redirect('portal:project_detail', pk=project_id)


class RemoteCapitalProgramCreateView(LoginRequiredMixin, CreateView):
    """Create a new Remote Capital Program Funding Agreement"""
    model = RemoteCapitalProgramFundingAgreement
    form_class = RemoteCapitalProgramFundingAgreementForm
    template_name = "portal/remote_capital_program_form.html"
    success_url = reverse_lazy('portal:remote_capital_program_list')

    def form_valid(self, form):
        messages.success(self.request, f'Remote Capital Program Agreement for {form.instance.council.name} created successfully!')
        return super().form_valid(form)


class RemoteCapitalProgramUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing Remote Capital Program Funding Agreement"""
    model = RemoteCapitalProgramFundingAgreement
    form_class = RemoteCapitalProgramFundingAgreementForm
    template_name = "portal/remote_capital_program_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:remote_capital_program_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Remote Capital Program Agreement updated successfully!')
        return super().form_valid(form)


class RemoteCapitalProgramDetailView(LoginRequiredMixin, DetailView):
    """Display Remote Capital Program Funding Agreement details"""
    model = RemoteCapitalProgramFundingAgreement
    template_name = "portal/remote_capital_program_detail.html"
    context_object_name = "agreement"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funding_schedules'] = self.object.funding_schedules.all()
        return context


class RemoteCapitalProgramDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a Remote Capital Program Funding Agreement"""
    model = RemoteCapitalProgramFundingAgreement
    template_name = "portal/remote_capital_program_confirm_delete.html"
    success_url = reverse_lazy('portal:remote_capital_program_list')

    def form_valid(self, form):
        agreement = self.get_object()
        messages.success(self.request, f'Remote Capital Program Agreement for {agreement.council.name} has been deleted.')
        return super().form_valid(form)


# Forward Remote Program Funding Agreement CRUD Views
class ForwardRPFListView(LoginRequiredMixin, ListView):
    """List Forward Remote Program Funding Agreements - RICD users only"""
    model = ForwardRemoteProgramFundingAgreement
    template_name = "portal/forward_rpf_list.html"
    context_object_name = "agreements"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view forward RPF agreements.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ForwardRemoteProgramFundingAgreement.objects.select_related('council')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(council__name__icontains=search) |
                Q(date_council_signed__icontains=search) |
                Q(date_delegate_signed__icontains=search)
            )
        return queryset.order_by('-date_council_signed')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link_project = self.request.GET.get('link_project')
        unlink_project = self.request.GET.get('unlink_project')

        if link_project:
            try:
                project = Project.objects.get(pk=link_project)
                context['link_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show link functionality

        if unlink_project:
            try:
                project = Project.objects.get(pk=unlink_project)
                context['unlink_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show unlink functionality

        return context

    def post(self, request, *args, **kwargs):
        """Handle linking/unlinking projects to agreements"""
        project_id = request.POST.get('project_id')
        agreement_id = request.POST.get('agreement_id')
        action = request.POST.get('action')

        if not project_id:
            messages.error(request, 'Project ID is required.')
            return self.get(request)

        try:
            project = Project.objects.get(pk=project_id)

            # Check permissions
            if not (request.user.is_staff or (hasattr(request.user, 'council') and request.user.council == project.council)):
                messages.error(request, "You don't have permission to modify this project.")
                return redirect('portal:project_detail', pk=project_id)

            if action == 'link' and agreement_id:
                agreement = ForwardRemoteProgramFundingAgreement.objects.get(pk=agreement_id)

                # Ensure project is not already linked to another agreement type
                if project.funding_agreement or project.interim_fp_agreement or project.funding_schedule:
                    messages.error(request,
                       'Project is already linked to another funding agreement. Remove existing link first.')
                    return redirect('portal:project_detail', pk=project_id)

                # Link the project
                project.forward_rpf_agreement = agreement
                project.save()
                messages.success(request, f'Project "{project.name}" linked to Forward RPF Agreement "{agreement}".')

            elif action == 'unlink':
                if not project.forward_rpf_agreement:
                    messages.warning(request, 'Project is not linked to any Forward RPF Agreement.')
                else:
                    agreement_name = str(project.forward_rpf_agreement)
                    project.forward_rpf_agreement = None
                    project.save()
                    messages.success(request, f'Project "{project.name}" unlinked from Forward RPF Agreement "{agreement_name}".')

        except Project.DoesNotExist:
            messages.error(request, 'Project not found.')
        except ForwardRemoteProgramFundingAgreement.DoesNotExist:
            messages.error(request, 'Forward RPF Agreement not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

        return redirect('portal:project_detail', pk=project_id)


class ForwardRFPCreateView(LoginRequiredMixin, CreateView):
    """Create a new Forward Remote Program Funding Agreement"""
    model = ForwardRemoteProgramFundingAgreement
    form_class = ForwardRemoteProgramFundingAgreementForm
    template_name = "portal/forward_rpf_form.html"
    success_url = reverse_lazy('portal:forward_rpf_list')

    def form_valid(self, form):
        messages.success(self.request, f'Forward RPF Agreement for {form.instance.council.name} created successfully!')
        return super().form_valid(form)


class ForwardRPFUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing Forward Remote Program Funding Agreement"""
    model = ForwardRemoteProgramFundingAgreement
    form_class = ForwardRemoteProgramFundingAgreementForm
    template_name = "portal/forward_rpf_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:forward_rpf_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Forward RPF Agreement updated successfully!')
        return super().form_valid(form)


class ForwardRPFDetailView(LoginRequiredMixin, DetailView):
    """Display Forward Remote Program Funding Agreement details"""
    model = ForwardRemoteProgramFundingAgreement
    template_name = "portal/forward_rpf_detail.html"
    context_object_name = "agreement"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        return context


class ForwardRPFDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a Forward Remote Program Funding Agreement"""
    model = ForwardRemoteProgramFundingAgreement
    template_name = "portal/forward_rpf_confirm_delete.html"
    success_url = reverse_lazy('portal:forward_rpf_list')

    def form_valid(self, form):
        agreement = self.get_object()
        messages.success(self.request, f'Forward RPF Agreement for {agreement.council.name} has been deleted.')
        return super().form_valid(form)


# Interim Forward Program Funding Agreement CRUD Views
class InterimFRPFListView(LoginRequiredMixin, ListView):
    """List Interim Forward Remote Program Funding Agreements - RICD users only"""
    model = InterimForwardProgramFundingAgreement
    template_name = "portal/interim_frp_list.html"
    context_object_name = "agreements"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view interim FRP agreements.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = InterimForwardProgramFundingAgreement.objects.select_related('council')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(council__name__icontains=search) |
                Q(date_council_signed__icontains=search) |
                Q(date_delegate_signed__icontains=search)
            )
        return queryset.order_by('-date_council_signed')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link_project = self.request.GET.get('link_project')
        unlink_project = self.request.GET.get('unlink_project')

        if link_project:
            try:
                project = Project.objects.get(pk=link_project)
                context['link_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show link functionality

        if unlink_project:
            try:
                project = Project.objects.get(pk=unlink_project)
                context['unlink_project'] = project
                # Check permissions - user should have access to this project
                if not (self.request.user.is_staff or (hasattr(self.request.user, 'council') and self.request.user.council == project.council)):
                    raise PermissionError("You don't have permission to modify this project.")
            except Project.DoesNotExist:
                pass  # Project doesn't exist, just don't show unlink functionality

        return context

    def post(self, request, *args, **kwargs):
        """Handle linking/unlinking projects to agreements"""
        project_id = request.POST.get('project_id')
        agreement_id = request.POST.get('agreement_id')
        action = request.POST.get('action')

        if not project_id:
            messages.error(request, 'Project ID is required.')
            return self.get(request)

        try:
            project = Project.objects.get(pk=project_id)

            # Check permissions
            if not (request.user.is_staff or (hasattr(request.user, 'council') and request.user.council == project.council)):
                messages.error(request, "You don't have permission to modify this project.")
                return redirect('portal:project_detail', pk=project_id)

            if action == 'link' and agreement_id:
                agreement = InterimForwardProgramFundingAgreement.objects.get(pk=agreement_id)

                # Ensure project is not already linked to another agreement type
                if project.funding_agreement or project.forward_rpf_agreement or project.funding_schedule:
                    messages.error(request,
                       'Project is already linked to another funding agreement. Remove existing link first.')
                    return redirect('portal:project_detail', pk=project_id)

                # Link the project
                project.interim_fp_agreement = agreement
                project.save()
                messages.success(request, f'Project "{project.name}" linked to Interim FRP Agreement "{agreement}".')

            elif action == 'unlink':
                if not project.interim_fp_agreement:
                    messages.warning(request, 'Project is not linked to any Interim FRP Agreement.')
                else:
                    agreement_name = str(project.interim_fp_agreement)
                    project.interim_fp_agreement = None
                    project.save()
                    messages.success(request, f'Project "{project.name}" unlinked from Interim FRP Agreement "{agreement_name}".')

        except Project.DoesNotExist:
            messages.error(request, 'Project not found.')
        except InterimForwardProgramFundingAgreement.DoesNotExist:
            messages.error(request, 'Interim FRP Agreement not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

        return redirect('portal:project_detail', pk=project_id)


class InterimFRPFCreateView(LoginRequiredMixin, CreateView):
    """Create a new Interim Forward Remote Program Funding Agreement"""
    model = InterimForwardProgramFundingAgreement
    form_class = InterimForwardProgramFundingAgreementForm
    template_name = "portal/interim_frp_form.html"
    success_url = reverse_lazy('portal:interim_frp_list')

    def form_valid(self, form):
        messages.success(self.request, f'Interim FRP Agreement for {form.instance.council.name} created successfully!')
        return super().form_valid(form)


class InterimFRPFUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing Interim Forward Remote Program Funding Agreement"""
    model = InterimForwardProgramFundingAgreement
    form_class = InterimForwardProgramFundingAgreementForm
    template_name = "portal/interim_frp_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:interim_frp_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Interim FRP Agreement updated successfully!')
        return super().form_valid(form)


class InterimFRPFDetailView(LoginRequiredMixin, DetailView):
    """Display Interim Forward Remote Program Funding Agreement details"""
    model = InterimForwardProgramFundingAgreement
    template_name = "portal/interim_frp_detail.html"
    context_object_name = "agreement"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        return context


class InterimFRPFDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an Interim Forward Remote Program Funding Agreement"""
    model = InterimForwardProgramFundingAgreement
    template_name = "portal/interim_frp_confirm_delete.html"
    success_url = reverse_lazy('portal:interim_frp_list')

    def form_valid(self, form):
        agreement = self.get_object()
        messages.success(self.request, f'Interim FRP Agreement for {agreement.council.name} has been deleted.')
        return super().form_valid(form)


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

        # Set the program from the project (if not in form)
        if not getattr(form.instance, 'program', None):
            form.instance.program = self.project.program

        response = super().form_valid(form)

        # Link the project to this funding schedule
        # Project has a foreign key to FundingSchedule, so we set it the other way around
        self.project.funding_schedule = self.object
        self.project.funding_schedule_amount = self.object.funding_amount
        if self.object.contingency_amount:
            self.project.contingency_amount = self.object.contingency_amount

        # Update project state to funded
        if self.project.state == 'prospective':
            self.project.state = 'funded'

        self.project.save()

        messages.success(self.request,
            f'Project "{self.project.name}" has been added to funding schedule and state updated to "Funded".')

        return response


class FundingApprovalUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing funding approval"""
    model = FundingApproval
    form_class = FundingApprovalForm
    template_name = "portal/funding_approval_form.html"

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


# User and Officer Management Views
class UserListView(LoginRequiredMixin, ListView):
    """List users with filtering"""
    model = User
    template_name = "portal/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.select_related().all()

        # Filter users by council for council users
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            queryset = queryset.filter(profile__council=user_council)

        search = self.request.GET.get('search')
        group_filter = self.request.GET.get('group')
        active_filter = self.request.GET.get('active')

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        if group_filter and not user_council:  # Only allow group filter for RICD users
            queryset = queryset.filter(groups__name=group_filter)
        if active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif active_filter == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('username')


class UserCreateView(LoginRequiredMixin, CreateView):
    """Create a new user"""
    model = User
    form_class = UserCreationForm
    template_name = "portal/user_form.html"
    success_url = reverse_lazy('portal:user_list')

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.instance.username}" created successfully!')
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing user"""
    model = User
    template_name = "portal/user_form.html"

    def get_form_class(self):
        # For updates, use a simpler user form
        if self.object:
            class UserUpdateForm(forms.ModelForm):
                groups = forms.ModelMultipleChoiceField(
                    queryset=Group.objects.all(),
                    required=False,
                    widget=forms.SelectMultiple(attrs={'class': 'form-select'})
                )

                class Meta:
                    model = User
                    fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
                    widgets = {
                        'username': forms.TextInput(attrs={'class': 'form-control'}),
                        'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                        'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                        'email': forms.EmailInput(attrs={'class': 'form-control'}),
                        'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                        'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                    }

                def save(self, commit=True):
                    user = super().save(commit=False)
                    if commit:
                        user.save()
                        if self.cleaned_data.get('groups'):
                            user.groups.set(self.cleaned_data['groups'])
                    return user
            return UserUpdateForm
        return UserCreationForm

    def get_success_url(self):
        return reverse_lazy('portal:user_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.instance.username}" updated successfully!')
        return super().form_valid(form)


class UserDetailView(LoginRequiredMixin, DetailView):
    """Display user details"""
    model = User
    template_name = "portal/user_detail.html"
    context_object_name = "user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_groups'] = self.object.groups.all()
        return context


# Officer Management Views
class OfficerListView(LoginRequiredMixin, ListView):
    """List officers with filtering"""
    model = Officer
    template_name = "portal/officer_list.html"
    context_object_name = "officers"
    paginate_by = 20

    def get_queryset(self):
        queryset = Officer.objects.select_related('user').all()

        # Filter officers by user's council for council users
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            queryset = queryset.filter(user__profile__council=user_council)

        search = self.request.GET.get('search')
        council_filter = self.request.GET.get('council')
        active_filter = self.request.GET.get('active')
        role_filter = self.request.GET.get('role')

        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(position__icontains=search)
            )
        if council_filter and not user_council:  # Only allow council filter for RICD users
            queryset = queryset.filter(user__profile__council_id=council_filter)
        if active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif active_filter == 'false':
            queryset = queryset.filter(is_active=False)
        if role_filter:
            if role_filter == 'principal':
                queryset = queryset.filter(is_principal=True)
            elif role_filter == 'senior':
                queryset = queryset.filter(is_senior=True)
            elif role_filter == 'both':
                queryset = queryset.filter(is_principal=True, is_senior=True)

        return queryset.order_by('user__last_name', 'user__first_name')


class OfficerCreateView(LoginRequiredMixin, CreateView):
    """Create a new officer"""
    model = Officer
    form_class = OfficerForm
    template_name = "portal/officer_form.html"
    success_url = reverse_lazy('portal:officer_list')

    def form_valid(self, form):
        officer_name = form.instance.user.get_full_name() or form.instance.user.username
        messages.success(self.request, f'Officer for {officer_name} created successfully!')
        return super().form_valid(form)


class OfficerUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing officer"""
    model = Officer
    form_class = OfficerForm
    template_name = "portal/officer_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:officer_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        officer_name = form.instance.user.get_full_name() or form.instance.user.username
        messages.success(self.request, f'Officer for {officer_name} updated successfully!')
        return super().form_valid(form)


class OfficerDetailView(LoginRequiredMixin, DetailView):
    """Display officer details"""
    model = Officer
    template_name = "portal/officer_detail.html"
    context_object_name = "officer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Show projects where this officer is assigned
        principal_projects = self.object.principal_projects.all()
        senior_projects = self.object.senior_projects.all()
        context['principal_projects'] = principal_projects
        context['senior_projects'] = senior_projects
        # Combine unique projects
        all_projects = set(list(principal_projects) + list(senior_projects))
        context['projects'] = all_projects
        return context


# Officer Assignment to Projects
class OfficerAssignmentView(LoginRequiredMixin, UpdateView):
    """View for assigning officers to projects"""
    model = Project
    form_class = OfficerAssignmentForm
    template_name = "portal/officer_assignment_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        original_principal = self.get_object().principal_officer
        original_senior = self.get_object().senior_officer

        response = super().form_valid(form)

        # Message about changes
        messages.success(self.request, f'Officer assignments for project "{form.instance.name}" updated successfully!')
# Defect CRUD Views
class DefectListView(LoginRequiredMixin, ListView):
    """List all defects with filtering"""
    model = Defect
    template_name = "portal/defect_list.html"
    context_object_name = "defects"
    paginate_by = 20

    def get_queryset(self):
        queryset = Defect.objects.select_related(
            'work__address__project__council',
            'work__address__project__program',
            'work__work_type_id',
            'work__output_type_id'
        )

        # Apply user-specific filtering (council users see only their defects)
        user_council = getattr(self.request.user, 'council', None)
        if user_council:
            queryset = queryset.filter(work__address__project__council=user_council)

        # Apply search/filtering
        search = self.request.GET.get('search')
        council_filter = self.request.GET.get('council')
        status_filter = self.request.GET.get('status')  # rectified/unrectified/all
        work_filter = self.request.GET.get('work')

        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(work__address__street__icontains=search)
            )
        if council_filter:
            queryset = queryset.filter(work__address__project__council_id=council_filter)
        if work_filter:
            queryset = queryset.filter(work_id=work_filter)
        if status_filter == 'rectified':
            queryset = queryset.exclude(rectified_date__isnull=True)
        elif status_filter == 'unrectified':
            queryset = queryset.filter(rectified_date__isnull=True)

        return queryset.order_by('-identified_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['councils'] = Council.objects.all()
        # Get works with defects for the dropdown
        if hasattr(self.request.user, 'council') and self.request.user.council:
            context['works'] = Work.objects.filter(
                address__project__council=self.request.user.council
            ).select_related('address', 'work_type_id', 'output_type_id')
        else:
            context['works'] = Work.objects.select_related('address', 'work_type_id', 'output_type_id')[:100]  # Limit for performance
        return context


class DefectCreateView(LoginRequiredMixin, CreateView):
    """Create a new defect"""
    model = Defect
    form_class = DefectForm
    template_name = "portal/defect_form.html"

    def dispatch(self, request, *args, **kwargs):
        work_pk = self.kwargs.get('work_pk')
        if work_pk:
            self.work = get_object_or_404(Work, pk=work_pk)
        else:
            self.work = None
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.work:
            kwargs['initial'] = {'work': self.work}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.work:
            context['work'] = self.work
        return context

    def get_success_url(self):
        if self.work and hasattr(self, 'object') and self.object:
            # If we have a work and the object was created, return to the work detail
            return reverse_lazy('portal:project_detail', kwargs={'pk': self.work.address.project.pk})
        return reverse_lazy('portal:defect_list')

    def form_valid(self, form):
        if self.work:
            form.instance.work = self.work
        messages.success(self.request, f'Defect identified successfully!')
        return super().form_valid(form)


class DefectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing defect"""
    model = Defect
    form_class = DefectForm
    template_name = "portal/defect_form.html"

    def get_success_url(self):
        return reverse_lazy('portal:defect_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work'] = self.object.work
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Defect updated successfully!')
        return super().form_valid(form)


class DefectDetailView(LoginRequiredMixin, DetailView):
    """Display defect details"""
    model = Defect
    template_name = "portal/defect_detail.html"
    context_object_name = "defect"


class DefectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a defect"""
    model = Defect
    template_name = "portal/defect_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('portal:defect_list')

    def form_valid(self, form):
        defect = self.get_object()
        messages.success(self.request, f'Defect has been deleted.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work'] = self.object.work
        return context


# Defect rectification view
class DefectRectifyView(LoginRequiredMixin, UpdateView):
    """Mark a defect as rectified (set rectified_date)"""
    model = Defect
    fields = ['rectified_date']
    template_name = "portal/defect_rectify.html"

    def get_initial(self):
        initial = super().get_initial()
        if not self.object.rectified_date:
            initial['rectified_date'] = timezone.now().date()
        return initial

    def get_success_url(self):
        return reverse_lazy('portal:defect_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Defect marked as rectified on {form.instance.rectified_date}!')
        return super().form_valid(form)


class MoveAddressesWorksView(LoginRequiredMixin, DetailView):
    """View for moving addresses and works from one project to another"""
    model = Project
    template_name = "portal/move_addresses_works.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get addresses and works for this project
        addresses = self.object.addresses.select_related(
            'work_type_id', 'output_type_id'
        ).prefetch_related('works__work_type_id', 'works__output_type_id')

        context['addresses'] = addresses

        # Get existing projects with same council for dropdown
        existing_projects = Project.objects.filter(
            council=self.object.council
        ).exclude(pk=self.object.pk).select_related('council', 'program')

        context['existing_projects'] = existing_projects
        context['total_addresses'] = addresses.count()
        context['total_works'] = sum(address.works.count() for address in addresses)

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')

        # Check permissions
        if not (request.user.is_staff or (hasattr(request.user, 'council') and request.user.council == self.object.council)):
            messages.error(request, "You don't have permission to modify this project.")
            return redirect('portal:project_detail', pk=self.object.pk)

        if action == 'move_to_existing':
            return self.move_to_existing(request)
        elif action == 'move_to_new':
            return self.move_to_new(request)
        else:
            messages.error(request, 'Invalid action specified.')
            return redirect('portal:project_detail', pk=self.object.pk)

    def move_to_existing(self, request):
        """Move selected addresses and works to an existing project"""
        target_project_id = request.POST.get('target_project')
        selected_address_ids = request.POST.getlist('selected_addresses')

        if not target_project_id or not selected_address_ids:
            messages.error(request, 'Please select a target project and at least one address.')
            return redirect('portal:project_detail', pk=self.object.pk)

        try:
            target_project = Project.objects.get(pk=target_project_id, council=self.object.council)

            # Move selected addresses and their works
            for address_id in selected_address_ids:
                address = Address.objects.get(pk=address_id, project=self.object)

                # Update project reference
                address.project = target_project
                address.save()

                # Move all associated works (they should already be linked to address)
                for work in address.works.all():
                    # Update work.project through the address reference
                    work.save()  # This triggers any signals

            # Update funding amounts with notices
            self.update_funding_amounts(target_project)

            messages.success(request, f'Successfully moved {len(selected_address_ids)} addresses and their associated works to "{target_project.name}". Please review and update funding amounts as needed.')
            return redirect('portal:project_detail', pk=self.object.pk)

        except Project.DoesNotExist:
            messages.error(request, 'Target project not found.')
        except Address.DoesNotExist:
            messages.error(request, 'Selected address not found.')

        return redirect('portal:project_detail', pk=self.object.pk)

    def move_to_new(self, request):
        """Move selected addresses and works to a new project"""
        project_name = request.POST.get('new_project_name')
        selected_address_ids = request.POST.getlist('selected_addresses')

        if not project_name or not selected_address_ids:
            messages.error(request, 'Please provide a name for the new project and select at least one address.')
            return redirect('portal:project_detail', pk=self.object.pk)

        try:
            # Create new project with same program and council
            new_project = Project.objects.create(
                name=project_name,
                council=self.object.council,
                program=self.object.program,
                state='prospective',  # Start as prospective
            )

            # Copy some basic fields from original project
            if self.object.principal_officer:
                new_project.principal_officer = self.object.principal_officer
            if self.object.senior_officer:
                new_project.senior_officer = self.object.senior_officer
            new_project.save()

            # Move selected addresses and their works
            total_budget_moved = 0
            for address_id in selected_address_ids:
                address = Address.objects.get(pk=address_id, project=self.object)
                total_budget_moved += address.budget or 0

                # Update project reference
                address.project = new_project
                address.save()

            # Set funding amount based on moved budget
            if total_budget_moved > 0:
                new_project.funding_schedule_amount = Decimal(str(total_budget_moved))
                new_project.contingency_amount = new_project.funding_schedule_amount * new_project.contingency_percentage
                new_project.save()

            messages.success(request, f'Successfully created new project "{new_project.name}" and moved {len(selected_address_ids)} addresses and their associated works. Please review funding amounts and contingency amounts.')
            return redirect('portal:project_detail', pk=self.object.pk)

        except Exception as e:
            messages.error(request, f'Error creating new project: {str(e)}')

        return redirect('portal:project_detail', pk=self.object.pk)

    def update_funding_amounts(self, project):
        """Update funding amounts after moving addresses/works and add warning messages"""
        total_budget = sum(
            address.budget or 0
            for address in project.addresses.all()
        )

        current_funding = project.funding_schedule_amount or 0

        if current_funding > 0 and abs(total_budget - current_funding) > 1:  # Allow for small differences
            messages.warning(self.request,
                f'Project "{project.name}": Current funding amount (${current_funding:,.0f}) may need adjustment. '
                f'Total budget of addresses is now ${total_budget:,.0f}. Please review funding schedule and contingency amounts.')

            # Recalculate contingency if needed
            if project.contingency_percentage:
                recommended_contingency = (project.funding_schedule_amount or total_budget) * project.contingency_percentage
                if abs((project.contingency_amount or 0) - recommended_contingency) > 1:
                    messages.info(self.request,
                        f'Recommended contingency amount: ${recommended_contingency:,.0f} (based on {project.contingency_percentage:.1%} contingency rate).')


# Work Type/Output Type Configuration View
class WorkOutputTypeConfigView(LoginRequiredMixin, TemplateView):
    """Configuration page for managing work type and output type relationships - RICD users only"""
    template_name = "portal/work_output_type_config.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can access work/output type configuration.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all work types and output types
        work_types = WorkType.objects.filter(is_active=True).prefetch_related('allowed_output_types')
        output_types = OutputType.objects.filter(is_active=True)

        context['work_types'] = work_types
        context['output_types'] = output_types

        # Create mapping for JavaScript
        work_type_mappings = {}
        for work_type in work_types:
            work_type_mappings[str(work_type.id)] = list(work_type.allowed_output_types.values_list('id', flat=True))

        context['work_type_mappings'] = json.dumps(work_type_mappings)

        return context

    def post(self, request, *args, **kwargs):
        """Handle drag and drop updates"""
        action = request.POST.get('action')
        work_type_id = request.POST.get('work_type_id')
        output_type_id = request.POST.get('output_type_id')

        if not work_type_id or not output_type_id:
            messages.error(request, 'Invalid request data.')
            return redirect('portal:work_output_type_config')

        try:
            work_type = WorkType.objects.get(pk=work_type_id)
            output_type = OutputType.objects.get(pk=output_type_id)

            if action == 'add':
                work_type.allowed_output_types.add(output_type)
                messages.success(request, f'Added {output_type.name} to {work_type.name}')
            elif action == 'remove':
                work_type.allowed_output_types.remove(output_type)
                messages.success(request, f'Removed {output_type.name} from {work_type.name}')
            else:
                messages.error(request, 'Invalid action specified.')

        except (WorkType.DoesNotExist, OutputType.DoesNotExist):
            messages.error(request, 'Work type or output type not found.')

        return redirect('portal:work_output_type_config')