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
    Council, UserProfile, FieldVisibilitySetting
)
from .forms import (
    CouncilForm, CouncilUserCreationForm, CouncilUserUpdateForm
)


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