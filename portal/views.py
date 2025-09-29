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
import logging

from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View
import json
from ricd.models import (
    Project, Program, Council, QuarterlyReport, MonthlyTracker, StageReport,
    FundingSchedule, Address, Work, WorkStep, FundingApproval, WorkType, OutputType, ConstructionMethod, Officer,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement,
    RemoteCapitalProgramFundingAgreement, UserProfile, FieldVisibilitySetting,
    ProjectReportConfiguration,
    SiteConfiguration
)

from .forms import (
    CouncilForm, ProgramForm, ProjectForm, WorkForm, AddressForm,
    WorkTypeForm, OutputTypeForm, ConstructionMethodForm, ProjectStateForm,
    OfficerForm, OfficerAssignmentForm, CouncilUserCreationForm, CouncilUserUpdateForm,
    UserCreationForm, FundingApprovalForm, ForwardRemoteProgramFundingAgreementForm,
    InterimForwardProgramFundingAgreementForm, RemoteCapitalProgramFundingAgreementForm,
    ProjectFieldVisibilityForm, ProjectReportConfigurationForm, SiteConfigurationForm,
    MonthlyTrackerForm, QuarterlyReportForm, Stage1ReportForm, Stage2ReportForm
)



# Project Detail
class ProjectDetailView(DetailView):
    model = Project
    template_name = "portal/project_detail.html"
    context_object_name = "project"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only RICD Staff and RICD Managers can access this view
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view RICD project details.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funding_approvals'] = self.object.funding_approvals.all()

        # Calculate total funding from addresses/works budgets for all users
        from django.db.models import Sum
        calculated_total_funding = self.object.addresses.aggregate(
            total=Sum('budget')
        )['total'] or 0

        # For RICD users, override the stored total_funding with calculated value
        if not hasattr(self.request.user, 'council') or not self.request.user.council:
            # Temporarily override project.total_funding for template display
            self.object.calculated_total_funding = calculated_total_funding
        else:
            # For council users, still provide the calculated amount separately
            context['council_funding_amount'] = calculated_total_funding

        # Add field visibility settings for council users
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            try:
                user_profile = self.request.user.profile
                user_council = user_profile.council
                from ricd.models import get_field_visibility_settings
                context['field_visibility'] = get_field_visibility_settings(user_council, self.request.user)
            except:
                # Default to visible if profile doesn't exist
                context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}
        else:
            # For anonymous users or users without council, show all fields (though they shouldn't reach here)
            context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}

        # Add context variables to help with work display logic
        works_count = self.object.works.count()
        addresses_with_work = self.object.addresses.filter(
            work_type_id__isnull=False,
            output_type_id__isnull=False
        ).count()

        context['has_works'] = works_count > 0
        context['has_addresses_with_work'] = addresses_with_work > 0
        context['has_any_work_content'] = works_count > 0 or addresses_with_work > 0

        return context


# Council Project Detail View
class CouncilProjectDetailView(DetailView):
    model = Project
    template_name = "portal/council_project_detail.html"
    context_object_name = "project"

    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Authentication required.")

        # Only Council Users and Council Managers can access this view
        if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only council users can view council project details.")

        # Check if user has permission to view this project
        project = self.get_object()

        # Council Users and Council Managers can only access their own council's projects
        # Check profile directly to avoid property issues
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if user_council and project.council == user_council:
            return super().dispatch(request, *args, **kwargs)

        # Deny access for all other cases
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to view this project.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        # Add funding agreement information
        context['funding_agreement'] = project.funding_agreement
        context['funding_schedule'] = project.funding_schedule
        context['forward_rpf'] = project.forward_rpf_agreement
        context['interim_frp'] = project.interim_fp_agreement

        # Calculate funding amount (sum of all address budgets - for council view)
        from django.db.models import Sum
        total_budget = project.addresses.aggregate(
            total=Sum('budget')
        )['total'] or 0
        context['funding_amount_less_contingency'] = total_budget

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

        # Add field visibility settings for council users
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            try:
                user_profile = self.request.user.profile
                user_council = user_profile.council
                from ricd.models import get_field_visibility_settings
                context['field_visibility'] = get_field_visibility_settings(user_council, self.request.user)
            except:
                # Default to visible if profile doesn't exist
                context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}
        else:
            # For anonymous users or users without council, show all fields (though they shouldn't reach here)
            context['field_visibility'] = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}

        return context


# Report Form Views
class MonthlyReportView(LoginRequiredMixin, TemplateView):
    template_name = "portal/monthly_report.html"

    def get_context_data(self, **kwargs):
        from .forms import MonthlyTrackerForm
        context = super().get_context_data(**kwargs)
        context['form'] = MonthlyTrackerForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        from .forms import MonthlyTrackerForm
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
        # Allow RICD users and Council users to view councils
        is_ricd = request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_user = request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists()

        if not (is_ricd or is_council_user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")

        # For council users, check if they're viewing their own council
        if is_council_user and not is_ricd:
            council = self.get_object()
            try:
                user_profile = request.user.profile
                user_council = user_profile.council
                if user_council != council:
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden("You can only view your own council.")
            except:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Access denied. No council profile found.")

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
    context_object_name = "council"

    def get_template_names(self):
        # Use council-specific template for council users, general template for RICD users
        if self.request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
            return ["portal/council_detail_council.html", "portal/council_detail.html"]
        return ["portal/council_detail.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if user is council user (not RICD)
        is_council_user = self.request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists()
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        context['is_council_user'] = is_council_user
        context['is_ricd'] = is_ricd

        # For council users, only show their own projects
        if is_council_user and not is_ricd:
            context['projects'] = self.object.projects.filter(council=self.object)
        else:
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
        import logging
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER CREATE VIEW FORM_VALID STARTED ===")

        user = self.request.user
        selected_council = self.council or form.cleaned_data.get('council')
        role = form.cleaned_data.get('role')

        logger.info(f"Current user: {user.username} (ID: {user.pk})")
        logger.info(f"Selected council: {selected_council}")
        logger.info(f"Role: {role}")
        logger.info(f"View council: {self.council}")

        # --- Permission checks ---
        user_council = getattr(user, 'council', None)
        is_ricd = user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_manager = user.groups.filter(name='Council Manager').exists() and user_council == selected_council

        logger.info(f"User council: {user_council}")
        logger.info(f"Is RICD: {is_ricd}")
        logger.info(f"Is Council Manager: {is_council_manager}")
        logger.info(f"User groups: {[g.name for g in user.groups.all()]}")

        if not (is_ricd or is_council_manager):
            logger.warning("❌ Permission denied - user does not have permission to create users for this council")
            messages.error(self.request, 'You do not have permission to create users for this council.')
            return self.form_invalid(form)

        if role == 'council_manager' and not is_ricd:
            logger.warning("❌ Permission denied - only RICD staff can create Council Manager accounts")
            messages.error(self.request, 'Only RICD staff can create Council Manager accounts.')
            return self.form_invalid(form)

        if not selected_council:
            logger.warning("❌ No council selected")
            messages.error(self.request, 'A council must be selected for the user.')
            return self.form_invalid(form)

        logger.info("✅ Permission checks passed")

        try:
            logger.info("Calling form.save(commit=True)")
            # The form's save method handles User creation, UserProfile creation, and group assignment
            # We don't need to call super().form_valid() as the form has already saved everything
            created_user = form.save(commit=True)

            logger.info(f"✅ Form save completed - Created user: {created_user.username} (ID: {created_user.pk})")

            # Confirm success
            group_name = "Council Manager" if role == "council_manager" else "Council User"
            success_msg = f'{group_name} "{created_user.username}" created successfully for {selected_council.name}.'
            messages.success(self.request, success_msg)
            logger.info(f"✅ Success message set: {success_msg}")

            # Get success URL
            success_url = self.get_success_url()
            logger.info(f"Redirecting to: {success_url}")
            logger.info("=== COUNCIL USER CREATE VIEW FORM_VALID COMPLETED ===")

            return redirect(success_url)

        except Exception as e:
            logger.error(f"❌ Error creating user: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            messages.error(self.request, f'Error creating user: {str(e)}')
            return self.form_invalid(form)


class CouncilUserUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing council user - RICD users can modify any user, Council Managers can only modify their own council users"""
    model = User
    form_class = CouncilUserUpdateForm
    template_name = "portal/council_user_form.html"

    def dispatch(self, request, *args, **kwargs):
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        # Permission checks
        current_user = request.user
        user_council = getattr(current_user, 'council', None)
        is_ricd = current_user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_manager = current_user.groups.filter(name='Council Manager').exists() and user_council == user_profile.council

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: CouncilUserUpdateView.dispatch - User: {current_user.username}, Target User: {user_obj.username}, User Council: {user_council}, Target Council: {user_profile.council if user_profile else None}, Is RICD: {is_ricd}, Is Council Manager: {is_council_manager}")

        # Check if user has permission to update this user
        if not (is_ricd or is_council_manager):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have permission to update this user.")

        # Council Managers can only update users in their own council
        if user_profile and user_council and user_profile.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You can only update users in your own council.")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        if user_profile:
            context['council'] = user_profile.council
        context['is_update'] = True
        return context

    def get_success_url(self):
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        if user_profile:
            return reverse_lazy('portal:council_detail', kwargs={'pk': user_profile.council.pk})
        return reverse_lazy('portal:council_list')

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER UPDATE VIEW FORM_VALID STARTED ===")

        user_obj = self.get_object()
        old_role = None
        if user_obj.groups.filter(name='Council Manager').exists():
            old_role = 'council_manager'
        elif user_obj.groups.filter(name='Council User').exists():
            old_role = 'council_user'

        new_role = form.cleaned_data.get('role')

        logger.info(f"Updating user: {user_obj.username} (ID: {user_obj.pk})")
        logger.info(f"Old role: {old_role}, New role: {new_role}")

        # --- Permission checks for role changes ---
        current_user = self.request.user
        user_council = getattr(current_user, 'council', None)
        is_ricd = current_user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_manager = current_user.groups.filter(name='Council Manager').exists()

        if new_role == 'council_manager' and not is_ricd:
            logger.warning("❌ Permission denied - only RICD staff can change users to Council Manager role")
            messages.error(self.request, 'Only RICD staff can change users to Council Manager role.')
            return self.form_invalid(form)

        # Council Managers cannot change roles for other Council Managers
        if not is_ricd and is_council_manager and old_role == 'council_manager' and user_obj != current_user:
            logger.warning("❌ Permission denied - Council Managers cannot modify other Council Managers")
            messages.error(self.request, 'You cannot modify other Council Managers.')
            return self.form_invalid(form)

        response = super().form_valid(form)

        # Log success
        group_name = "Council Manager" if new_role == "council_manager" else "Council User"
        success_msg = f'{group_name} "{user_obj.username}" updated successfully.'
        messages.success(self.request, success_msg)
        logger.info(f"✅ Success message set: {success_msg}")
        logger.info("=== COUNCIL USER UPDATE VIEW FORM_VALID COMPLETED ===")

        return response


class CouncilUserDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a council user - RICD users can delete any user, Council Managers can only delete users in their own council"""
    model = User
    template_name = "portal/council_user_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        # Permission checks
        current_user = request.user
        user_council = getattr(current_user, 'council', None)
        is_ricd = current_user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council_manager = current_user.groups.filter(name='Council Manager').exists() and user_council == user_profile.council

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: CouncilUserDeleteView.dispatch - User: {current_user.username}, Target User: {user_obj.username}, User Council: {user_council}, Target Council: {user_profile.council if user_profile else None}, Is RICD: {is_ricd}, Is Council Manager: {is_council_manager}")

        # Check if user has permission to delete this user
        if not (is_ricd or is_council_manager):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have permission to delete this user.")

        # Council Managers can only delete users in their own council
        if user_profile and user_council and user_profile.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You can only delete users in your own council.")

        # Council Managers cannot delete other Council Managers
        if not is_ricd and is_council_manager and user_obj.groups.filter(name='Council Manager').exists() and user_obj != current_user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You cannot delete other Council Managers.")

        # Users cannot delete themselves
        if user_obj == current_user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You cannot delete your own account.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        if user_profile:
            context['council'] = user_profile.council
        return context

    def get_success_url(self):
        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)

        if user_profile and user_profile.council:
            return reverse_lazy('portal:council_detail', kwargs={'pk': user_profile.council.pk})
        return reverse_lazy('portal:council_list')

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER DELETE VIEW FORM_VALID STARTED ===")

        user_obj = self.get_object()
        user_profile = getattr(user_obj, 'profile', None)
        council_name = user_profile.council.name if user_profile and user_profile.council else "Unknown Council"

        logger.info(f"Deleting user: {user_obj.username} (ID: {user_obj.pk}) from council: {council_name}")

        # Store success message before deletion
        group_name = "Council Manager" if user_obj.groups.filter(name='Council Manager').exists() else "Council User"
        success_msg = f'{group_name} "{user_obj.username}" has been deleted from {council_name}.'

        response = super().form_valid(form)

        messages.success(self.request, success_msg)
        logger.info(f"✅ Success message set: {success_msg}")
        logger.info("=== COUNCIL USER DELETE VIEW FORM_VALID COMPLETED ===")

        return response


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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        user_council = getattr(request.user, 'council', None)

        if not (is_ricd or (user_council and self.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this project.")

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

    def dispatch(self, request, *args, **kwargs):
        address = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this address.")

        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        address = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to delete this address.")

        return super().dispatch(request, *args, **kwargs)

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

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        user_council = getattr(request.user, 'council', None)

        if not (is_ricd or (user_council and self.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this project.")

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

    def dispatch(self, request, *args, **kwargs):
        work = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and work.address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to modify this work.")

        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        work = self.get_object()

        # Check permissions - allow RICD users and council users for their own projects
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None

        if not (is_ricd or (user_council and work.address.project.council == user_council)):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to delete this work.")

        return super().dispatch(request, *args, **kwargs)

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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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


# class Stage1ReportView(LoginRequiredMixin, TemplateView):
#     template_name = "portal/stage1_report.html"
#
#     def dispatch(self, request, *args, **kwargs):
#         # Check if user is authenticated
#         if not request.user.is_authenticated:
#             from django.http import HttpResponseForbidden
#             return HttpResponseForbidden("Authentication required.")
#
#         # Only Council Users and Council Managers can access this view
#         if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
#             from django.http import HttpResponseForbidden
#             return HttpResponseForbidden("Access denied. Only council users can submit Stage 1 reports.")
#
#         # Get user's council
#         try:
#             user_profile = request.user.profile
#             user_council = user_profile.council
#         except:
#             user_council = None
#
#         # If user doesn't have a council profile, deny access
#         if not user_council:
#             from django.http import HttpResponseForbidden
#             return HttpResponseForbidden("Access denied. No council profile found.")
#
#         # Check if user has permission to view this project (if project_pk is provided)
#         project_pk = kwargs.get('project_pk')
#         if project_pk:
#             project = get_object_or_404(Project, pk=project_pk)
#             # Ensure the project belongs to the user's council
#             if project.council != user_council:
#                 from django.http import HttpResponseForbidden
#                 return HttpResponseForbidden("You don't have permission to submit reports for this project.")
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         project_pk = kwargs.get('project_pk')
#         project = None
#
#         if project_pk:
#            project = get_object_or_404(Project, pk=project_pk)
#
#         context['form'] = Stage1ReportForm(user=self.request.user, project=project)
#         context['project'] = project
#         return context
#
#     def post(self, request, *args, **kwargs):
#         form = Stage1ReportForm(request.POST, request.FILES, user=self.request.user)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Stage 1 report submitted successfully!')
#             return redirect('portal:council_dashboard')
#         else:
#             messages.error(request, 'Please correct the errors below.')
#         return self.render_to_response({'form': form})
#
#
# class Stage2ReportView(LoginRequiredMixin, TemplateView):
#     template_name = "portal/stage2_report.html"
#
#     def dispatch(self, request, *args, **kwargs):
#         # Check if user is authenticated
#         if not request.user.is_authenticated:
#             from django.http import HttpResponseForbidden
#             return HttpResponseForbidden("Authentication required.")
#
#         # Only Council Users and Council Managers can access this view
#         if not request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists():
#             from django.http import HttpResponseForbidden
#             return HttpResponseForbidden("Access denied. Only council users can submit Stage 2 reports.")
#
#         # Check if user has permission to view this project (if project_pk is provided)
#         project_pk = kwargs.get('project_pk')
#         if project_pk:
#             project = get_object_or_404(Project, pk=project_pk)
#             try:
#                 user_profile = request.user.profile
#                 user_council = user_profile.council
#             except:
#                 user_council = None
#
#             if user_council and project.council != user_council:
#                 from django.http import HttpResponseForbidden
#                 return HttpResponseForbidden("You don't have permission to submit reports for this project.")
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         project_pk = kwargs.get('project_pk')
#         project = None
#
#         if project_pk:
#             project = get_object_or_404(Project, pk=project_pk)
#
#         context['form'] = Stage2ReportForm(user=self.request.user, project=project)
#         context['project'] = project
#         return context
#
#     def post(self, request, *args, **kwargs):
#         form = Stage2ReportForm(request.POST, request.FILES, user=self.request.user)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Stage 2 report submitted successfully!')
#             return redirect('portal:council_dashboard')
#         else:
#             messages.error(request, 'Please correct the errors below.')

# Enhanced Analytics and Forecasting Views
class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Advanced analytics dashboard with budget forecasting and anomaly detection"""
    template_name = "portal/analytics_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get program filter
        program_filter = self.request.GET.get('program')

        # Filter projects based on user permissions - capture all projects without date restrictions
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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
        """Analyze overdue reports and missing stage reports - only for commenced/under construction projects"""
        alerts = []
        today = analysis_date

        for project in projects:
            # Only require reports for projects that are commenced or under construction
            if project.state not in ['commenced', 'under_construction']:
                continue

            # Check monthly reports - required during construction
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

            # Check quarterly reports - required for commenced and under construction projects
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
                elif project.state in ['commenced', 'under_construction']:
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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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
        # Get the project instance
        project = self.get_object()

        # Store original values for logging
        original_principal = project.principal_officer
        original_senior = project.senior_officer

        # Update the project with form data
        project.principal_officer = form.cleaned_data.get('principal_officer')
        project.senior_officer = form.cleaned_data.get('senior_officer')
        project.save()

        # Set the object for response
        self.object = project

        # Message about changes
        messages.success(self.request, f'Officer assignments for project "{form.instance.name}" updated successfully!')

        # Return a redirect response
        return redirect(self.get_success_url())
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
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
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

        # Only show council filter to RICD users, not council users
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        if is_ricd:
            context['councils'] = Council.objects.all()

        # Get works with defects for the dropdown - always filter by user's council if they have one
        if user_council:
            context['works'] = Work.objects.filter(
                address__project__council=user_council
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
        kwargs['user'] = self.request.user
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

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


class ProjectFieldVisibilityView(LoginRequiredMixin, TemplateView):
    """Configure field visibility settings for a specific project - RICD users only"""
    template_name = "portal/project_field_visibility.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can configure field visibility.")

        self.project = get_object_or_404(Project, pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['form'] = ProjectFieldVisibilityForm(project=self.project)
        return context

    def post(self, request, *args, **kwargs):
        form = ProjectFieldVisibilityForm(request.POST, project=self.project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Field visibility settings for project "{self.project.name}" have been updated successfully!')
            return redirect('portal:project_detail', pk=self.project.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
            return self.render_to_response({'form': form, 'project': self.project})


# Enhanced Reporting Management Views

class MonthlyTrackerItemListView(LoginRequiredMixin, ListView):
    """List all monthly tracker items - RICD users only"""
    model = MonthlyTrackerItem
    template_name = "portal/monthly_tracker_item_list.html"
    context_object_name = "tracker_items"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can view monthly tracker items.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = MonthlyTrackerItem.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('order', 'name')


class MonthlyTrackerItemCreateView(LoginRequiredMixin, CreateView):
    """Create a new monthly tracker item"""
    model = MonthlyTrackerItem
    form_class = MonthlyTrackerItemForm
    template_name = "portal/monthly_tracker_item_form.html"
    success_url = reverse_lazy('portal:monthly_tracker_item_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Monthly tracker item "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class MonthlyTrackerItemUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing monthly tracker item"""
    model = MonthlyTrackerItem
    form_class = MonthlyTrackerItemForm
    template_name = "portal/monthly_tracker_item_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:monthly_tracker_item_list')

    def form_valid(self, form):
        messages.success(self.request, f'Monthly tracker item "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class MonthlyTrackerItemDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a monthly tracker item"""
    model = MonthlyTrackerItem
    template_name = "portal/monthly_tracker_item_confirm_delete.html"
    success_url = reverse_lazy('portal:monthly_tracker_item_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        tracker_item = self.get_object()
        messages.success(self.request, f'Monthly tracker item "{tracker_item.name}" has been deleted.')
        return super().form_valid(form)


class MonthlyTrackerItemGroupListView(LoginRequiredMixin, ListView):
    """List all monthly tracker item groups - RICD users only"""
    model = MonthlyTrackerItemGroup
    template_name = "portal/monthly_tracker_item_group_list.html"
    context_object_name = "tracker_item_groups"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = MonthlyTrackerItemGroup.objects.prefetch_related('tracker_items')
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('name')


class MonthlyTrackerItemGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new monthly tracker item group"""
    model = MonthlyTrackerItemGroup
    form_class = MonthlyTrackerItemGroupForm
    template_name = "portal/monthly_tracker_item_group_form.html"
    success_url = reverse_lazy('portal:monthly_tracker_item_group_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Monthly tracker item group "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class MonthlyTrackerItemGroupUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing monthly tracker item group"""
    model = MonthlyTrackerItemGroup
    form_class = MonthlyTrackerItemGroupForm
    template_name = "portal/monthly_tracker_item_group_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:monthly_tracker_item_group_list')

    def form_valid(self, form):
        messages.success(self.request, f'Monthly tracker item group "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class MonthlyTrackerItemGroupDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a monthly tracker item group"""
    model = MonthlyTrackerItemGroup
    template_name = "portal/monthly_tracker_item_group_confirm_delete.html"
    success_url = reverse_lazy('portal:monthly_tracker_item_group_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        group = self.get_object()
        messages.success(self.request, f'Monthly tracker item group "{group.name}" has been deleted.')
        return super().form_valid(form)


class MonthlyTrackerItemGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new monthly tracker item group"""
    model = MonthlyTrackerItemGroup
    form_class = MonthlyTrackerItemGroupForm
    template_name = "portal/monthly_tracker_item_group_form.html"
    success_url = reverse_lazy('portal:monthly_tracker_item_group_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Monthly tracker item group "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class QuarterlyReportItemListView(LoginRequiredMixin, ListView):
    """List all quarterly report items - RICD users only"""
    model = QuarterlyReportItem
    template_name = "portal/quarterly_report_item_list.html"
    context_object_name = "report_items"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = QuarterlyReportItem.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('order', 'name')


class QuarterlyReportItemCreateView(LoginRequiredMixin, CreateView):
    """Create a new quarterly report item"""
    model = QuarterlyReportItem
    form_class = QuarterlyReportItemForm
    template_name = "portal/quarterly_report_item_form.html"
    success_url = reverse_lazy('portal:quarterly_report_item_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Quarterly report item "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class QuarterlyReportItemUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing quarterly report item"""
    model = QuarterlyReportItem
    form_class = QuarterlyReportItemForm
    template_name = "portal/quarterly_report_item_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:quarterly_report_item_list')

    def form_valid(self, form):
        messages.success(self.request, f'Quarterly report item "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class QuarterlyReportItemDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a quarterly report item"""
    model = QuarterlyReportItem
    template_name = "portal/quarterly_report_item_confirm_delete.html"
    success_url = reverse_lazy('portal:quarterly_report_item_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        item = self.get_object()
        messages.success(self.request, f'Quarterly report item "{item.name}" has been deleted.')
        return super().form_valid(form)


class Stage1StepListView(LoginRequiredMixin, ListView):
    """List all Stage 1 steps - RICD users only"""
    model = Stage1Step
    template_name = "portal/stage1_step_list.html"
    context_object_name = "steps"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Stage1Step.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('order', 'name')


class Stage1StepCreateView(LoginRequiredMixin, CreateView):
    """Create a new Stage 1 step"""
    model = Stage1Step
    form_class = Stage1StepForm
    template_name = "portal/stage1_step_form.html"
    success_url = reverse_lazy('portal:stage1_step_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Stage 1 step "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class Stage1StepUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing Stage 1 step"""
    model = Stage1Step
    form_class = Stage1StepForm
    template_name = "portal/stage1_step_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:stage1_step_list')

    def form_valid(self, form):
        messages.success(self.request, f'Stage 1 step "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class Stage1StepDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a Stage 1 step"""
    model = Stage1Step
    template_name = "portal/stage1_step_confirm_delete.html"
    success_url = reverse_lazy('portal:stage1_step_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        step = self.get_object()
        messages.success(self.request, f'Stage 1 step "{step.name}" has been deleted.')
        return super().form_valid(form)


class Stage2StepListView(LoginRequiredMixin, ListView):
    """List all Stage 2 steps - RICD users only"""
    model = Stage2Step
    template_name = "portal/stage2_step_list.html"
    context_object_name = "steps"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Stage2Step.objects.all()
        search = self.request.GET.get('search')
        active_filter = self.request.GET.get('active')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if active_filter:
            queryset = queryset.filter(is_active=active_filter == 'true')
        return queryset.order_by('order', 'name')


class Stage2StepCreateView(LoginRequiredMixin, CreateView):
    """Create a new Stage 2 step"""
    model = Stage2Step
    form_class = Stage2StepForm
    template_name = "portal/stage2_step_form.html"
    success_url = reverse_lazy('portal:stage2_step_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Stage 2 step "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class Stage2StepUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing Stage 2 step"""
    model = Stage2Step
    form_class = Stage2StepForm
    template_name = "portal/stage2_step_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('portal:stage2_step_list')

    def form_valid(self, form):
        messages.success(self.request, f'Stage 2 step "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class Stage2StepDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a Stage 2 step"""
    model = Stage2Step
    template_name = "portal/stage2_step_confirm_delete.html"
    success_url = reverse_lazy('portal:stage2_step_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        step = self.get_object()
        messages.success(self.request, f'Stage 2 step "{step.name}" has been deleted.')
        return super().form_valid(form)


class ProjectReportConfigurationView(LoginRequiredMixin, UpdateView):
    """Configure report items and groups for a specific project"""

    model = ProjectReportConfiguration
    form_class = ProjectReportConfigurationForm
    template_name = "portal/project_report_configuration.html"

    def dispatch(self, request, *args, **kwargs):
        # Check permissions
        project = Project.objects.get(pk=self.kwargs['pk'])
        user_council = getattr(request.user, 'council', None)

        if user_council and project.council != user_council:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to configure this project.")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        project = Project.objects.get(pk=self.kwargs['pk'])
        obj, created = ProjectReportConfiguration.objects.get_or_create(project=project)
        return obj

    def get_success_url(self):
        return reverse_lazy('portal:project_detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Report configuration for project "{self.object.project.name}" has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context


class EnhancedMonthlyTrackerView(LoginRequiredMixin, TemplateView):
    """
    Enhanced monthly tracker table view with the specific layout requested.

    Key Features:
    - Direct inline editing of tracker cells without opening separate forms
    - Live updates: Council users can update data for any month at any time
    - Dynamic work handling: Automatically adapts to new/removed work addresses each month
    - Submission deadline awareness: Tracks 8th of month deadline but allows continuous updates
    - Batch saving: Save button submits all form data at once
    """

    template_name = "portal/enhanced_monthly_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Add submission deadline information
        context['submission_deadline'] = self.get_submission_deadline_info()

        # Add last submission information
        context['last_submission_info'] = self.get_last_submission_info()

        # Get all active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Group projects by their funding agreements
        funding_agreements_data = self.group_projects_by_funding_agreements(active_projects)

        # Create entry forms for workflow management
        entry_forms = self.create_entry_forms(funding_agreements_data)

        context.update({
            'funding_agreements_data': funding_agreements_data,
            'is_ricd': is_ricd,
            'user_council': user_council,
            'user': self.request.user,  # Add user for template workflow checks
            'entry_forms': entry_forms,  # Add forms for workflow management
        })

        return context

    def group_projects_by_funding_agreements(self, projects):
        """Group projects by their funding agreements and prepare table data"""
        from collections import defaultdict

        # Get all monthly tracker items that are active
        tracker_items = MonthlyTrackerItem.objects.filter(is_active=True).order_by('order')
        tracker_items_list = list(tracker_items)

        # Track active entries for cleanup
        self._active_entry_ids = set()

        funding_groups = defaultdict(list)

        for project in projects:
            # Determine which funding agreement this project belongs to
            funding_agreement_name = self.get_funding_agreement_name(project)

            # Get all addresses for this project
            addresses_with_work = Address.objects.filter(
                project=project
            ).select_related('work_type_id', 'output_type_id')

            # Prepare address work data with tracker items
            work_data = []
            for address in addresses_with_work:
                # Skip addresses without work type information
                if not address.work_type_id or not address.output_type_id:
                    continue

                # Get or create the Work object for this address
                work = Work.objects.filter(address=address).first()
                if not work:
                    # Create Work from address data
                    work = Work.objects.create(
                        address=address,
                        work_type_id=address.work_type_id,
                        output_type_id=address.output_type_id,
                        bedrooms=address.bedrooms,
                        output_quantity=address.output_quantity or 1,
                        estimated_cost=address.budget,
                        actual_cost=None,
                        start_date=project.date_physically_commenced,
                        end_date=None
                    )

                work_info = {
                    'work': work,  # Use the Work object
                    'address': address,
                    'tracker_values': {}
                }

                # For each tracker item, determine if it's applicable and get value
                for item in tracker_items_list:
                    tracker_value = self.get_tracker_value_for_address(address, item, project)
                    work_info['tracker_values'][item.id] = tracker_value

                    # Track active entries for cleanup of removed works
                    if tracker_value.get('entry_id'):
                        self._active_entry_ids.add(tracker_value['entry_id'])

                work_data.append(work_info)

            # Always include the project, even if it has no works (but only if it's active)
            if work_data:
                funding_groups[funding_agreement_name].extend(work_data)
            else:
                # Create a placeholder entry for projects without works
                funding_groups[funding_agreement_name].append({
                    'project': project,
                    'work': None,
                    'address': None,
                    'tracker_values': {}
                })

        # Convert to list format for template
        result = []
        for agreement_name, works_list in funding_groups.items():
            result.append({
                'funding_agreement': agreement_name,
                'works': works_list
            })

        # Clean up orphaned entries for removed works
        self.cleanup_orphaned_entries()

        return {
            'tracker_items': tracker_items_list,
            'funding_groups': result,
            'total_columns': len(tracker_items_list) + 1  # +1 for the work address column
        }

    def get_funding_agreement_name(self, project):
        """Get the funding agreement name for a project"""
        if project.funding_schedule:
            if project.funding_schedule.agreement_type == 'rcpf_agreement':
                return f"Remote Capital Program Funding Agreement - {project.funding_schedule.funding_schedule_number}"
            else:
                return f"Funding Schedule {project.funding_schedule.funding_schedule_number}"
        elif project.forward_rpf_agreement:
            return "Forward Remote Program Funding Agreement"
        elif project.interim_fp_agreement:
            return "Interim Forward Remote Program Funding Agreement"
        else:
            return "No Funding Agreement"

    def get_tracker_value_for_address(self, address, tracker_item, project):
        """Determine the value to display for a specific address and tracker item"""
        from datetime import date
        from django.utils import timezone

        # Check if this tracker item is configured for this project
        try:
            config = project.report_configuration
            # Check if this tracker item is in any of the project's configured groups
            applicable_groups = config.monthly_tracker_groups.all()
            item_in_groups = any(
                tracker_item in group.tracker_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is applicable by default
            # Fall through to check for actual data
            pass

        # Item is applicable, check if there's actual data
        try:
            # Get the Work for this address (should already exist from the main method)
            work = Work.objects.filter(address=address).first()

            if not work:
                # This shouldn't happen, but handle it gracefully
                return {
                    'value': '',
                    'display': '',
                    'applicable': False
                }

            # Get the most recent monthly tracker for this work
            latest_tracker = MonthlyTracker.objects.filter(work=work).order_by('-month').first()

            # If no tracker exists, create one for the current month
            if not latest_tracker:
                # Get current month and year
                current_date = timezone.now().date()
                current_month = date(current_date.year, current_date.month, 1)

                # Check if project has commenced
                if project.state in ['commenced', 'under_construction'] and project.date_physically_commenced:
                    # Create new monthly tracker for current month
                    latest_tracker = MonthlyTracker.objects.create(
                        work=work,
                        month=current_month,
                        # Set other default values as needed
                        total_construction_cost=work.estimated_cost or 0,
                        total_expenditure_council=0,
                        total_expenditure_ricd=0,
                        percentage_works_completed=0
                    )

            if latest_tracker:
                # Try to get the value from the tracker entry
                try:
                    entry = MonthlyTrackerEntry.objects.get(
                        monthly_tracker=latest_tracker,
                        tracker_item=tracker_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_tracker_value(entry.value, tracker_item),
                        'applicable': True,
                        'has_data': True,
                        'entry': entry,
                        'entry_id': entry.id
                    }
                except MonthlyTrackerEntry.DoesNotExist:
                    # Create the entry if it doesn't exist and item is applicable
                    if tracker_item.is_active:
                        entry = MonthlyTrackerEntry.objects.create(
                            monthly_tracker=latest_tracker,
                            tracker_item=tracker_item,
                            value=None,  # Start with no value
                            workflow_status='draft'
                        )
                        return {
                            'value': '',
                            'display': '',
                            'applicable': True,
                            'has_data': False,
                            'entry': entry,
                            'entry_id': entry.id
                        }
        except Exception:
            # Handle any exceptions gracefully
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if tracker_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }

    def create_entry_forms(self, funding_agreements_data):
        """Create MonthlyTrackerEntryForm instances for all tracker entries"""
        entry_forms = {}

        for funding_group in funding_agreements_data['funding_groups']:
            for work_info in funding_group['works']:
                for tracker_id, tracker_value in work_info['tracker_values'].items():
                    if tracker_value.get('entry'):
                        # Create form with existing entry
                        entry = tracker_value['entry']
                        form = MonthlyTrackerEntryForm(instance=entry)
                        entry_forms[entry.id] = form
                    elif tracker_value.get('entry_id'):
                        # Create form for entry with ID
                        try:
                            entry = MonthlyTrackerEntry.objects.get(id=tracker_value['entry_id'])
                            form = MonthlyTrackerEntryForm(instance=entry)
                            entry_forms[entry.id] = form
                        except MonthlyTrackerEntry.DoesNotExist:
                            pass  # Entry was deleted, skip form creation
                    elif tracker_value.get('applicable') and tracker_value.get('has_data') == False:
                        # Create a new entry for applicable items without data
                        try:
                            tracker_item = MonthlyTrackerItem.objects.get(id=tracker_id)
                            work = work_info.get('work')
                            if work and tracker_item.is_active:
                                # Find the monthly tracker for this work
                                latest_tracker = MonthlyTracker.objects.filter(work=work).order_by('-month').first()
                                if latest_tracker:
                                    entry = MonthlyTrackerEntry.objects.create(
                                        monthly_tracker=latest_tracker,
                                        tracker_item=tracker_item,
                                        value=None,
                                        workflow_status='draft'
                                    )
                                    form = MonthlyTrackerEntryForm(instance=entry)
                                    entry_forms[entry.id] = form
                        except (MonthlyTrackerItem.DoesNotExist, Exception):
                            pass  # Skip if there are any issues

        return entry_forms

    def format_tracker_value(self, value, tracker_item):
        """Format the tracker value for display based on data type"""
        if not value:
            return ''

        if tracker_item.data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif tracker_item.data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif tracker_item.data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)

    def post(self, request, *args, **kwargs):
        """Handle form submissions and workflow approvals for tracker entries"""
        action = request.POST.get('action')

        # Handle workflow approval actions
        if action in ['approve_council_manager', 'approve_ricd_officer']:
            return self.handle_workflow_approval(request, action)

        # Handle regular form submissions
        return self.handle_form_submission(request)

    def handle_form_submission(self, request):
        """Handle regular form submissions for tracker entries with submission status tracking"""
        from django.utils import timezone
        logger = logging.getLogger(__name__)

        success_count = 0
        error_count = 0
        entry_forms = {}
        current_time = timezone.now()

        # Process each form entry in the POST data
        for key in request.POST:
            if key.startswith('form-'):
                parts = key.split('-')
                if len(parts) < 3:
                    continue

                entry_id = parts[1]
                field_name = '-'.join(parts[2:])

                # Initialize form data dictionary for this entry
                if entry_id not in entry_forms:
                    entry_forms[entry_id] = {'id': entry_id}

                # Store the field value
                entry_forms[entry_id][field_name] = request.POST[key]

        # Process each entry form
        for entry_id, data in entry_forms.items():
            try:
                # Get existing entry or prepare for new entry
                if entry_id and entry_id != 'new':
                    try:
                        entry = MonthlyTrackerEntry.objects.get(id=entry_id)
                        form = MonthlyTrackerEntryForm(data, instance=entry)
                    except MonthlyTrackerEntry.DoesNotExist:
                        form = MonthlyTrackerEntryForm(data)
                else:
                    form = MonthlyTrackerEntryForm(data)

                if form.is_valid():
                    saved_entry = form.save()
                    # Set initial workflow status for new entries
                    if saved_entry.workflow_status == 'draft':
                        pass  # Keep as draft initially

                    # Update submission timestamp for tracking
                    if hasattr(saved_entry, 'monthly_tracker'):
                        saved_entry.monthly_tracker.submission_date = current_time
                        saved_entry.monthly_tracker.save()

                    success_count += 1
                else:
                    error_count += 1
                    # Log form errors for debugging
                    logger.error(f"Form errors for entry {entry_id}: {form.errors}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing entry {entry_id}: {str(e)}")

        # Check if this submission meets the deadline requirement (informational only)
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
            submission_deadline = self.get_submission_deadline_info()

            if user_council and success_count > 0:
                # Always allow updates to previous months' data (live updates)
                # Just provide informational feedback about deadlines
                current_time = timezone.now()
                if current_time.day <= 8:
                    messages.info(request, f'Data updated. Monthly tracker remains open for live updates until the 8th of each month.')
                else:
                    messages.info(request, f'Data updated. You can continue to make live updates to previous months\' data.')

                # Log the update for tracking purposes
                logger.info(f"Live update: User {request.user.username} updated {success_count} tracker entries on {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass  # Ignore errors in deadline checking

        # Set appropriate messages
        if success_count > 0:
            messages.success(request, f'Successfully updated {success_count} tracker entries.')
        if error_count > 0:
            messages.error(request, f'Failed to update {error_count} tracker entries. Please check the form for errors.')

        # Redirect to prevent form resubmission
        return redirect(request.path)

    def handle_workflow_approval(self, request, action):
        """Handle workflow approval actions"""
        entry_id = request.POST.get('entry_id')
        comments = request.POST.get('comments', '')

        if not entry_id:
            messages.error(request, 'No entry specified for approval.')
            return redirect(request.path)

        try:
            entry = MonthlyTrackerEntry.objects.get(id=entry_id)

            if action == 'approve_council_manager':
                entry.approve_council_manager(request.user, comments)
                messages.success(request, f'Tracker entry approved as Council Manager.')
            elif action == 'approve_ricd_officer':
                entry.approve_ricd_officer(request.user, comments)
                messages.success(request, f'Tracker entry approved as RICD Officer.')

        except MonthlyTrackerEntry.DoesNotExist:
            messages.error(request, 'Tracker entry not found.')
        except Exception as e:
            messages.error(request, f'Error processing approval: {str(e)}')

        return redirect(request.path)

    def get_submission_deadline_info(self):
        """Get information about the submission deadline for the current month"""
        from django.utils import timezone
        today = timezone.now().date()
        current_day = today.day

        # Calculate the deadline for the previous month (should be submitted by 8th of current month)
        previous_month = today.replace(day=1) - timezone.timedelta(days=1)
        deadline_date = today.replace(day=8)

        # Check if we're past the 8th (deadline has passed for previous month)
        is_past_deadline = current_day > 8

        days_until_deadline = (deadline_date - today).days if not is_past_deadline else 0

        return {
            'deadline_date': deadline_date,
            'is_past_deadline': is_past_deadline,
            'days_until_deadline': days_until_deadline,
            'previous_month': previous_month,
            'current_day': current_day,
            'deadline_day': 8
        }

    def get_last_submission_info(self):
        """Get information about the last submission for the user's council"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council:
                # Get the most recent monthly tracker submission for this council
                last_submission = MonthlyTracker.objects.filter(
                    work__address__project__council=user_council
                ).order_by('-submission_date').first()

                if last_submission:
                    return {
                        'date': last_submission.submission_date,
                        'month': last_submission.month.strftime('%B %Y'),
                        'has_submission': True
                    }
        except:
            pass

        return {
            'date': None,
            'month': None,
            'has_submission': False
        }

    def cleanup_orphaned_entries(self):
        """Clean up MonthlyTrackerEntry objects for removed works"""
        logger = logging.getLogger(__name__)
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council and hasattr(self, '_active_entry_ids'):
                # Get all entries for this council's works
                all_entries = MonthlyTrackerEntry.objects.filter(
                    monthly_tracker__work__address__project__council=user_council
                ).values_list('id', flat=True)

                # Find orphaned entries (entries that exist but aren't in active entries)
                orphaned_entry_ids = set(all_entries) - self._active_entry_ids

                if orphaned_entry_ids:
                    # Mark orphaned entries as inactive rather than deleting them
                    # This preserves data integrity and allows for recovery if needed
                    MonthlyTrackerEntry.objects.filter(id__in=orphaned_entry_ids).update(
                        workflow_status='archived'
                    )
                    logger.info(f"Archived {len(orphaned_entry_ids)} orphaned tracker entries for council {user_council.name}")

        except Exception as e:
            # Log but don't fail the request if cleanup fails
            logger.error(f"Error during orphaned entry cleanup: {str(e)}")
            pass


class EnhancedQuarterlyTrackerView(LoginRequiredMixin, TemplateView):
    """
    Enhanced quarterly tracker table view with the specific layout requested.
    Similar to EnhancedMonthlyTrackerView but for quarterly tracking with editing capabilities.

    Key Features:
    - Direct inline editing of tracker cells without opening separate forms
    - Live updates: Council users can update data for any quarter at any time
    - Dynamic work handling: Automatically adapts to new/removed work addresses each quarter
    - Submission deadline awareness: Tracks quarterly deadlines but allows continuous updates
    - Batch saving: Save button submits all form data at once
    - Workflow management for approvals
    """

    template_name = "portal/enhanced_quarterly_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Add submission deadline information
        context['submission_deadline'] = self.get_submission_deadline_info()

        # Add last submission information
        context['last_submission_info'] = self.get_last_submission_info()

        # Get all active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Group projects by their funding agreements
        funding_agreements_data = self.group_projects_by_funding_agreements(active_projects)

        # Create entry forms for workflow management
        entry_forms = self.create_entry_forms(funding_agreements_data)

        context.update({
            'funding_agreements_data': funding_agreements_data,
            'is_ricd': is_ricd,
            'user_council': user_council,
            'user': self.request.user,  # Add user for template workflow checks
            'entry_forms': entry_forms,  # Add forms for workflow management
        })

        return context

    def group_projects_by_funding_agreements(self, projects):
        """Group projects by their funding agreements and prepare table data"""
        from collections import defaultdict

        # Get all quarterly tracker items that are active
        tracker_items = QuarterlyReportItem.objects.filter(is_active=True).order_by('order')
        tracker_items_list = list(tracker_items)

        # Track active entries for cleanup
        self._active_entry_ids = set()

        funding_groups = defaultdict(list)

        for project in projects:
            # Determine which funding agreement this project belongs to
            funding_agreement_name = self.get_funding_agreement_name(project)

            # Get all addresses for this project
            addresses_with_work = Address.objects.filter(
                project=project
            ).select_related('work_type_id', 'output_type_id')

            # Prepare address work data with tracker items
            work_data = []
            for address in addresses_with_work:
                # Skip addresses without work type information
                if not address.work_type_id or not address.output_type_id:
                    continue

                # Get or create the Work object for this address
                work = Work.objects.filter(address=address).first()
                if not work:
                    # Create Work from address data
                    work = Work.objects.create(
                        address=address,
                        work_type_id=address.work_type_id,
                        output_type_id=address.output_type_id,
                        bedrooms=address.bedrooms,
                        output_quantity=address.output_quantity or 1,
                        estimated_cost=address.budget,
                        actual_cost=None,
                        start_date=project.date_physically_commenced,
                        end_date=None
                    )

                work_info = {
                    'work': work,  # Use the Work object
                    'address': address,
                    'tracker_values': {}
                }

                # For each tracker item, determine if it's applicable and get value
                for item in tracker_items_list:
                    tracker_value = self.get_tracker_value_for_address(address, item, project)
                    work_info['tracker_values'][item.id] = tracker_value

                    # Track active entries for cleanup of removed works
                    if tracker_value.get('entry_id'):
                        self._active_entry_ids.add(tracker_value['entry_id'])

                work_data.append(work_info)

            # Always include the project, even if it has no works (but only if it's active)
            if work_data:
                funding_groups[funding_agreement_name].extend(work_data)
            else:
                # Create a placeholder entry for projects without works
                funding_groups[funding_agreement_name].append({
                    'project': project,
                    'work': None,
                    'address': None,
                    'tracker_values': {}
                })

        # Convert to list format for template
        result = []
        for agreement_name, works_list in funding_groups.items():
            result.append({
                'funding_agreement': agreement_name,
                'works': works_list
            })

        # Clean up orphaned entries for removed works
        self.cleanup_orphaned_entries()

        return {
            'tracker_items': tracker_items_list,
            'funding_groups': result,
            'total_columns': len(tracker_items_list) + 1  # +1 for the work address column
        }

    def get_funding_agreement_name(self, project):
        """Get the funding agreement name for a project"""
        if project.funding_schedule:
            if project.funding_schedule.agreement_type == 'rcpf_agreement':
                return f"Remote Capital Program Funding Agreement - {project.funding_schedule.funding_schedule_number}"
            else:
                return f"Funding Schedule {project.funding_schedule.funding_schedule_number}"
        elif project.forward_rpf_agreement:
            return "Forward Remote Program Funding Agreement"
        elif project.interim_fp_agreement:
            return "Interim Forward Remote Program Funding Agreement"
        else:
            return "No Funding Agreement"

    def get_tracker_value_for_address(self, address, tracker_item, project):
        """Determine the value to display for a specific address and tracker item"""
        from datetime import date
        from django.utils import timezone

        # Check if this tracker item is configured for this project
        try:
            config = project.report_configuration
            # Check if this tracker item is in any of the project's configured groups
            applicable_groups = config.quarterly_report_groups.all()
            item_in_groups = any(
                tracker_item in group.report_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is applicable by default
            # Fall through to check for actual data
            pass

        # Item is applicable, check if there's actual data
        try:
            # Get the Work for this address (should already exist from the main method)
            work = Work.objects.filter(address=address).first()

            if not work:
                # This shouldn't happen, but handle it gracefully
                return {
                    'value': '',
                    'display': '',
                    'applicable': False
                }

            # Get the most recent quarterly tracker for this work
            latest_tracker = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()

            # If no tracker exists, create one for the current quarter
            if not latest_tracker:
                # Get current date and determine current quarter
                current_date = timezone.now().date()
                current_quarter_start = self.get_quarter_start(current_date)

                # Check if project has commenced
                if project.state in ['commenced', 'under_construction'] and project.date_physically_commenced:
                    # Create new quarterly tracker for current quarter
                    latest_tracker = QuarterlyReport.objects.create(
                        work=work,
                        submission_date=current_quarter_start,
                        # Set other default values as needed
                        total_expenditure_council=0,
                        total_expenditure_ricd=0,
                        percentage_works_completed=0
                    )

            if latest_tracker:
                # Try to get the value from the tracker entry
                try:
                    entry = QuarterlyReportItemEntry.objects.get(
                        quarterly_report=latest_tracker,
                        report_item=tracker_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_tracker_value(entry.value, tracker_item),
                        'applicable': True,
                        'has_data': True,
                        'entry': entry,
                        'entry_id': entry.id
                    }
                except QuarterlyReportItemEntry.DoesNotExist:
                    # Create the entry if it doesn't exist and item is applicable
                    if tracker_item.is_active:
                        entry = QuarterlyReportItemEntry.objects.create(
                            quarterly_report=latest_tracker,
                            report_item=tracker_item,
                            value=None,  # Start with no value
                            workflow_status='draft'
                        )
                        return {
                            'value': '',
                            'display': '',
                            'applicable': True,
                            'has_data': False,
                            'entry': entry,
                            'entry_id': entry.id
                        }
        except Exception:
            # Handle any exceptions gracefully
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if hasattr(tracker_item, 'na_acceptable') and tracker_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }

    def get_quarter_start(self, date):
        """Get the start date of the quarter for a given date"""
        quarter = (date.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        return date.replace(month=quarter_start_month, day=1)

    def create_entry_forms(self, funding_agreements_data):
        """Create QuarterlyReportItemEntryForm instances for all tracker entries"""
        entry_forms = {}

        for funding_group in funding_agreements_data['funding_groups']:
            for work_info in funding_group['works']:
                for tracker_id, tracker_value in work_info['tracker_values'].items():
                    if tracker_value.get('entry'):
                        # Create form with existing entry
                        entry = tracker_value['entry']
                        form = QuarterlyReportItemEntryForm(instance=entry)
                        entry_forms[entry.id] = form
                    elif tracker_value.get('entry_id'):
                        # Create form for entry with ID
                        try:
                            entry = QuarterlyReportItemEntry.objects.get(id=tracker_value['entry_id'])
                            form = QuarterlyReportItemEntryForm(instance=entry)
                            entry_forms[entry.id] = form
                        except QuarterlyReportItemEntry.DoesNotExist:
                            pass  # Entry was deleted, skip form creation
                    elif tracker_value.get('applicable') and tracker_value.get('has_data') == False:
                        # Create a new entry for applicable items without data
                        try:
                            tracker_item = QuarterlyReportItem.objects.get(id=tracker_id)
                            work = work_info.get('work')
                            if work and tracker_item.is_active:
                                # Find the quarterly report for this work
                                latest_report = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()
                                if latest_report:
                                    entry = QuarterlyReportItemEntry.objects.create(
                                        quarterly_report=latest_report,
                                        report_item=tracker_item,
                                        value=None,
                                        workflow_status='draft'
                                    )
                                    form = QuarterlyReportItemEntryForm(instance=entry)
                                    entry_forms[entry.id] = form
                        except (QuarterlyReportItem.DoesNotExist, Exception):
                            pass  # Skip if there are any issues

        return entry_forms

    def format_tracker_value(self, value, tracker_item):
        """Format the tracker value for display based on data type"""
        if not value:
            return ''

        if hasattr(tracker_item, 'data_type'):
            data_type = tracker_item.data_type
        else:
            data_type = 'text'  # Default fallback

        if data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)

    def post(self, request, *args, **kwargs):
        """Handle form submissions and workflow approvals for tracker entries"""
        action = request.POST.get('action')

        # Handle workflow approval actions
        if action in ['approve_council_manager', 'approve_ricd_officer']:
            return self.handle_workflow_approval(request, action)

        # Handle regular form submissions
        return self.handle_form_submission(request)

    def handle_form_submission(self, request):
        """Handle regular form submissions for tracker entries with submission status tracking"""
        from django.utils import timezone

        success_count = 0
        error_count = 0
        entry_forms = {}
        current_time = timezone.now()

        # Process each form entry in the POST data
        for key in request.POST:
            if key.startswith('form-'):
                parts = key.split('-')
                if len(parts) < 3:
                    continue

                entry_id = parts[1]
                field_name = '-'.join(parts[2:])

                # Initialize form data dictionary for this entry
                if entry_id not in entry_forms:
                    entry_forms[entry_id] = {'id': entry_id}

                # Store the field value
                entry_forms[entry_id][field_name] = request.POST[key]

        # Process each entry form
        for entry_id, data in entry_forms.items():
            try:
                # Get existing entry or prepare for new entry
                if entry_id and entry_id != 'new':
                    try:
                        entry = QuarterlyReportItemEntry.objects.get(id=entry_id)
                        form = QuarterlyReportItemEntryForm(data, instance=entry)
                    except QuarterlyReportItemEntry.DoesNotExist:
                        form = QuarterlyReportItemEntryForm(data)
                else:
                    form = QuarterlyReportItemEntryForm(data)

                if form.is_valid():
                    saved_entry = form.save()
                    # Set initial workflow status for new entries
                    if saved_entry.workflow_status == 'draft':
                        pass  # Keep as draft initially

                    # Update submission timestamp for tracking
                    if hasattr(saved_entry, 'quarterly_report'):
                        saved_entry.quarterly_report.submission_date = current_time
                        saved_entry.quarterly_report.save()

                    success_count += 1
                else:
                    error_count += 1
                    # Log form errors for debugging
                    print(f"Form errors for entry {entry_id}: {form.errors}")

            except Exception as e:
                error_count += 1
                print(f"Error processing entry {entry_id}: {str(e)}")

        # Check if this submission meets the deadline requirement (informational only)
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
            submission_deadline = self.get_submission_deadline_info()

            if user_council and success_count > 0:
                # Always allow updates to previous quarters' data (live updates)
                # Just provide informational feedback about deadlines
                current_time = timezone.now()
                messages.info(request, f'Data updated. Quarterly tracker remains open for live updates throughout each quarter.')

                # Log the update for tracking purposes
                print(f"Live update: User {request.user.username} updated {success_count} quarterly tracker entries on {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass  # Ignore errors in deadline checking

        # Set appropriate messages
        if success_count > 0:
            messages.success(request, f'Successfully updated {success_count} quarterly tracker entries.')
        if error_count > 0:
            messages.error(request, f'Failed to update {error_count} quarterly tracker entries. Please check the form for errors.')

        # Redirect to prevent form resubmission
        return redirect(request.path)

    def handle_workflow_approval(self, request, action):
        """Handle workflow approval actions"""
        entry_id = request.POST.get('entry_id')
        comments = request.POST.get('comments', '')

        if not entry_id:
            messages.error(request, 'No entry specified for approval.')
            return redirect(request.path)

        try:
            entry = QuarterlyReportItemEntry.objects.get(id=entry_id)

            if action == 'approve_council_manager':
                entry.approve_council_manager(request.user, comments)
                messages.success(request, f'Quarterly tracker entry approved as Council Manager.')
            elif action == 'approve_ricd_officer':
                entry.approve_ricd_officer(request.user, comments)
                messages.success(request, f'Quarterly tracker entry approved as RICD Officer.')

        except QuarterlyReportItemEntry.DoesNotExist:
            messages.error(request, 'Quarterly tracker entry not found.')
        except Exception as e:
            messages.error(request, f'Error processing approval: {str(e)}')

        return redirect(request.path)

    def get_submission_deadline_info(self):
        """Get information about the submission deadline for the current quarter"""
        from django.utils import timezone
        today = timezone.now().date()

        # Calculate the end of the current quarter for deadline
        current_quarter = (today.month - 1) // 3 + 1
        quarter_end_month = current_quarter * 3
        if quarter_end_month > 12:
            quarter_end_month = 12

        # Last day of the quarter
        from calendar import monthrange
        _, last_day = monthrange(today.year, quarter_end_month)
        quarter_end = today.replace(month=quarter_end_month, day=last_day)

        # Calculate days until end of quarter
        days_until_deadline = (quarter_end - today).days + 1  # +1 to include today

        return {
            'deadline_date': quarter_end,
            'days_until_deadline': days_until_deadline,
            'current_quarter': current_quarter,
            'quarter_end_month': quarter_end_month,
            'quarter_year': today.year
        }

    def get_last_submission_info(self):
        """Get information about the last submission for the user's council"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council:
                # Get the most recent quarterly report submission for this council
                last_submission = QuarterlyReport.objects.filter(
                    work__address__project__council=user_council
                ).order_by('-submission_date').first()

                if last_submission:
                    # Calculate which quarter this was
                    quarter = (last_submission.submission_date.month - 1) // 3 + 1
                    quarter_name = f"Q{quarter} {last_submission.submission_date.year}"

                    return {
                        'date': last_submission.submission_date,
                        'quarter': quarter_name,
                        'has_submission': True
                    }
        except:
            pass

        return {
            'date': None,
            'quarter': None,
            'has_submission': False
        }

    def cleanup_orphaned_entries(self):
        """Clean up QuarterlyReportItemEntry objects for removed works"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council and hasattr(self, '_active_entry_ids'):
                # Get all entries for this council's works
                all_entries = QuarterlyReportItemEntry.objects.filter(
                    quarterly_report__work__address__project__council=user_council
                ).values_list('id', flat=True)

                # Find orphaned entries (entries that exist but aren't in active entries)
                orphaned_entry_ids = set(all_entries) - self._active_entry_ids

                if orphaned_entry_ids:
                    # Mark orphaned entries as inactive rather than deleting them
                    # This preserves data integrity and allows for recovery if needed
                    QuarterlyReportItemEntry.objects.filter(id__in=orphaned_entry_ids).update(
                        workflow_status='archived'
                    )
                    print(f"Archived {len(orphaned_entry_ids)} orphaned quarterly tracker entries for council {user_council.name}")

        except Exception as e:
            # Log but don't fail the request if cleanup fails
            print(f"Error during orphaned entry cleanup: {str(e)}")
            pass


class EnhancedQuarterlyReportView(LoginRequiredMixin, TemplateView):
    """Enhanced quarterly report view with configurable items"""

    template_name = "portal/enhanced_quarterly_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Get active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Get quarterly report items
        quarterly_items = QuarterlyReportItem.objects.filter(is_active=True).order_by('order')

        # Prepare data for enhanced table view
        quarterly_data = self.prepare_quarterly_data(active_projects, quarterly_items)

        context.update({
            'quarterly_data': quarterly_data,
            'quarterly_items': quarterly_items,
            'total_columns': len(quarterly_items) + 1,  # +1 for work address column
            'is_ricd': is_ricd,
            'user_council': user_council,
        })

        return context

    def prepare_quarterly_data(self, projects, quarterly_items):
        """Prepare quarterly data for enhanced table display"""
        from collections import defaultdict

        project_groups = []

        for project in projects:
            # Get all works for this project
            works = Work.objects.filter(address__project=project).select_related(
                'address', 'work_type_id', 'output_type_id'
            )

            # Prepare work data with quarterly report items
            work_data = []
            for work in works:
                work_info = {
                    'work': work,
                    'address': work.address,
                    'report_values': {}
                }

                # For each quarterly report item, determine if it's applicable and get value
                for item in quarterly_items:
                    work_info['report_values'][item.id] = self.get_quarterly_value_for_work(work, item, project)

                work_data.append(work_info)

            if work_data:  # Only add if there are works
                project_groups.append({
                    'project': project,
                    'works': work_data
                })

        return project_groups

    def get_quarterly_value_for_work(self, work, quarterly_item, project):
        """Determine the value to display for a specific work and quarterly report item"""
        # Check if this quarterly item is configured for this project
        try:
            config = project.report_configuration
            # Check if this quarterly item is in any of the project's configured groups
            applicable_groups = config.quarterly_report_groups.all()
            item_in_groups = any(
                quarterly_item in group.report_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is not applicable
            return {'value': '', 'display': '', 'applicable': False}

        # Item is applicable, check if there's actual data
        try:
            # Get the most recent quarterly report for this work
            latest_quarterly = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()
            if latest_quarterly:
                # Try to get the value from the quarterly report item entry
                try:
                    entry = QuarterlyReportItemEntry.objects.get(
                        quarterly_report=latest_quarterly,
                        report_item=quarterly_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_quarterly_value(entry.value, quarterly_item),
                        'applicable': True,
                        'has_data': True
                    }
                except QuarterlyReportItemEntry.DoesNotExist:
                    pass
        except QuarterlyReport.DoesNotExist:
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if quarterly_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False
            }

    def format_quarterly_value(self, value, quarterly_item):
        """Format the quarterly report value for display based on data type"""
        if not value:
            return ''

        if quarterly_item.data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif quarterly_item.data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif quarterly_item.data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)


class EnhancedStage1ReportView(LoginRequiredMixin, TemplateView):
    """Enhanced Stage 1 report view with configurable steps"""

    template_name = "portal/enhanced_stage1_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Get projects (for stage 1, we show all projects, not just active ones)
        if user_council:
            projects = Project.objects.filter(council=user_council).prefetch_related('addresses__works')
        else:
            projects = Project.objects.all().prefetch_related('addresses__works')

        # Get Stage 1 steps
        stage1_steps = Stage1Step.objects.filter(is_active=True).order_by('order')

        # Prepare data for enhanced table view
        stage1_data = self.prepare_stage1_data(projects, stage1_steps)

        context.update({
            'stage1_data': stage1_data,
            'stage1_steps': stage1_steps,
            'total_columns': len(stage1_steps) + 1,  # +1 for work address column
            'is_ricd': is_ricd,
            'user_council': user_council,
        })

        return context

    def prepare_stage1_data(self, projects, stage1_steps):
        """Prepare Stage 1 data for enhanced table display"""
        from collections import defaultdict

        project_groups = []

        for project in projects:
            # Get all works for this project
            works = Work.objects.filter(address__project=project).select_related(
                'address', 'work_type_id', 'output_type_id'
            )

            # Prepare work data with stage 1 steps
            work_data = []
            for work in works:
                work_info = {
                    'work': work,
                    'address': work.address,
                    'step_values': {}
                }

                # For each stage 1 step, determine completion status
                for step in stage1_steps:
                    work_info['step_values'][step.id] = self.get_stage1_value_for_work(work, step, project)

                work_data.append(work_info)

            if work_data:  # Only add if there are works
                project_groups.append({
                    'project': project,
                    'works': work_data
                })

        return project_groups

    def get_stage1_value_for_work(self, work, stage1_step, project):
        """Determine the completion status for a specific work and stage 1 step"""
        # Check if this stage 1 step is configured for this project
        try:
            config = project.report_configuration
            # Check if this stage 1 step is in any of the project's configured groups
            applicable_groups = config.stage1_step_groups.all()
            step_in_groups = any(
                stage1_step in group.steps.all()
                for group in applicable_groups
            )

            if not step_in_groups:
                # Step is not configured for this project
                return {'completed': False, 'completion_date': None, 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so step is not applicable
            return {'completed': False, 'completion_date': None, 'applicable': False}

        # Step is applicable, check if there's completion data
        try:
            # Get the completion status for this step and work
            completion = Stage1StepCompletion.objects.get(
                work=work,
                step=stage1_step
            )
            return {
                'completed': completion.completed,
                'completion_date': completion.completion_date,
                'applicable': True
            }
        except Stage1StepCompletion.DoesNotExist:
            # No completion record exists
            return {
                'completed': False,
                'completion_date': None,
                'applicable': True
            }


class EnhancedStage2ReportView(LoginRequiredMixin, TemplateView):
    """Enhanced Stage 2 report view with configurable steps"""

    template_name = "portal/enhanced_stage2_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Get projects (for stage 2, we show commenced, under construction, and completed projects)
        if user_council:
            projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction', 'completed']
            ).prefetch_related('addresses__works')
        else:
            projects = Project.objects.filter(
                state__in=['commenced', 'under_construction', 'completed']
            ).prefetch_related('addresses__works')

        # Get Stage 2 steps
        stage2_steps = Stage2Step.objects.filter(is_active=True).order_by('order')

        # Prepare data for enhanced table view
        stage2_data = self.prepare_stage2_data(projects, stage2_steps)

        context.update({
            'stage2_data': stage2_data,
            'stage2_steps': stage2_steps,
            'total_columns': len(stage2_steps) + 1,  # +1 for work address column
            'is_ricd': is_ricd,
            'user_council': user_council,
        })

        return context

    def prepare_stage2_data(self, projects, stage2_steps):
        """Prepare Stage 2 data for enhanced table display"""
        from collections import defaultdict

        project_groups = []

        for project in projects:
            # Get all works for this project
            works = Work.objects.filter(address__project=project).select_related(
                'address', 'work_type_id', 'output_type_id'
            )

            # Prepare work data with stage 2 steps
            work_data = []
            for work in works:
                work_info = {
                    'work': work,
                    'address': work.address,
                    'step_values': {}
                }

                # For each stage 2 step, determine completion status
                for step in stage2_steps:
                    work_info['step_values'][step.id] = self.get_stage2_value_for_work(work, step, project)

                work_data.append(work_info)

            if work_data:  # Only add if there are works
                project_groups.append({
                    'project': project,
                    'works': work_data
                })

        return project_groups

    def get_stage2_value_for_work(self, work, stage2_step, project):
        """Determine the completion status for a specific work and stage 2 step"""
        # Check if this stage 2 step is configured for this project
        try:
            config = project.report_configuration
            # Check if this stage 2 step is in any of the project's configured groups
            applicable_groups = config.stage2_step_groups.all()
            step_in_groups = any(
                stage2_step in group.steps.all()
                for group in applicable_groups
            )

            if not step_in_groups:
                # Step is not configured for this project
                return {'completed': False, 'completion_date': None, 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so step is not applicable
            return {'completed': False, 'completion_date': None, 'applicable': False}

        # Step is applicable, check if there's completion data
        try:
            # Get the completion status for this step and work
            completion = Stage2StepCompletion.objects.get(
                work=work,
                step=stage2_step
            )
            return {
                'completed': completion.completed,
                'completion_date': completion.completion_date,
                'applicable': True
            }
        except Stage2StepCompletion.DoesNotExist:
            # No completion record exists
            return {
                'completed': False,
                'completion_date': None,
                'applicable': True
            }


class SiteConfigurationView(LoginRequiredMixin, UpdateView):
    """View for site-wide configuration settings - RICD users only"""
    model = SiteConfiguration
    form_class = SiteConfigurationForm
    template_name = "portal/site_configuration.html"
    success_url = reverse_lazy('portal:site_configuration')

    def dispatch(self, request, *args, **kwargs):
        # Restrict access to RICD users only
        if not request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Only RICD staff can configure site settings.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Return the singleton instance
        return SiteConfiguration.get_instance()

    def form_valid(self, form):
        messages.success(self.request, 'Site configuration updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_config'] = self.get_object()
        return context