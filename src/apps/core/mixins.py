"""
RBAC mixins for view-level access control.

Five roles:
  OFFICER        — FNC frontline staff, full CRUD on all records
  MANAGER        — FNC senior staff, same access as Officer (trust-based)
  COUNCIL_USER   — Council staff, own-council data only, can submit reports/claims
  COUNCIL_MANAGER— Senior council staff, same scope as Council User
  READ_ONLY      — Internal audit/finance/executives, read everything, no writes

Council scoping: COUNCIL_USER and COUNCIL_MANAGER see only records belonging
to their own council. The CouncilScopedMixin enforces this at the queryset level.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})
FNC_ROLES = frozenset({'OFFICER', 'MANAGER'})
WRITE_ROLES = frozenset({'OFFICER', 'MANAGER'})
# Internal staff = FNC frontline/managers + read-only audit/finance/executives.
# Mirrors the `is_fnc` context flag: everyone EXCEPT council roles.
INTERNAL_ROLES = frozenset({'OFFICER', 'MANAGER', 'READ_ONLY'})
ALL_ROLES = frozenset({'OFFICER', 'MANAGER', 'COUNCIL_USER', 'COUNCIL_MANAGER', 'READ_ONLY'})


def get_role(request):
    """Return the officer_role string for the current user, or None."""
    try:
        return request.user.profile.officer_role
    except Exception:
        return None


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Base mixin. Subclasses set `required_roles` to a frozenset of allowed role strings.
    Raises 403 (not redirect) on role violation.
    """
    required_roles = ALL_ROLES

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response
        role = get_role(request)
        if role not in self.required_roles and not request.user.is_superuser:
            raise PermissionDenied
        return response


class FNCOnlyMixin(RoleRequiredMixin):
    """Only FNC staff (Officer or Manager) can access this view."""
    required_roles = FNC_ROLES


class InternalOnlyMixin(RoleRequiredMixin):
    """Internal staff only (FNC + read-only audit/finance/exec). Council roles get 403.

    Used for records councils must never inspect in detail — e.g. Brief Financial
    Approvals, where the contingency hold-back and delegate/cost-centre internals
    are FNC-team-only. Councils learn only *whether* funding was approved via their
    own project/schedule pages, never the BFA itself.
    """
    required_roles = INTERNAL_ROLES


class WriteRequiredMixin(RoleRequiredMixin):
    """Write access: Officer or Manager only. Council and Read-Only roles get 403."""
    required_roles = WRITE_ROLES


class CouncilOrFNCMixin(RoleRequiredMixin):
    """Any authenticated user with a valid role can access (all 5 roles)."""
    required_roles = ALL_ROLES


class ReadOnlyExcludedMixin(RoleRequiredMixin):
    """All roles except READ_ONLY — for action views that change state."""
    required_roles = frozenset({'OFFICER', 'MANAGER', 'COUNCIL_USER', 'COUNCIL_MANAGER'})


class CouncilScopedMixin:
    """
    Filters list/detail querysets to own council for COUNCIL_USER and COUNCIL_MANAGER.
    Must be combined with a RoleRequiredMixin subclass.

    Set `council_filter_field` to the queryset lookup path that reaches the council
    FK (e.g. 'council', 'project__council', 'funding_schedule__project__council').
    """
    council_filter_field = 'council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                if council is None:
                    return qs.none()
                return qs.filter(**{self.council_filter_field: council})
            except Exception:
                return qs.none()
        return qs

    def get_object(self):
        obj = super().get_object()
        role = get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                parts = self.council_filter_field.split('__')
                val = obj
                for part in parts:
                    val = getattr(val, part, None)
                if val != council:
                    raise PermissionDenied
            except PermissionDenied:
                raise
            except Exception:
                raise PermissionDenied
        return obj


class CouncilSubmitMixin(RoleRequiredMixin):
    """Only council-side roles may submit reports or expense claims."""
    required_roles = COUNCIL_ROLES
