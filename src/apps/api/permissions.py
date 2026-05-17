"""
DRF permission classes for the RICD API.

Mirrors the mixin-based RBAC from apps.core.mixins but as DRF BasePermission
subclasses so they work with ViewSets rather than class-based views.

Role hierarchy (Profile.OfficerRole):
  OFFICER        — FNC frontline staff, full CRUD
  MANAGER        — FNC senior staff, full CRUD + approval authority
  COUNCIL_USER   — Council staff, own-council read + submit reports/claims
  COUNCIL_MANAGER— Senior council staff, same scope as Council User
  READ_ONLY      — Internal audit/finance, read everything no writes

Approval delegation:
  MANAGER  → up to Delegation.threshold_1
  DIRECTOR → up to Delegation.threshold_2 (maps to MANAGER role in Profile)
  GM       → unlimited (maps to higher roles)
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})
FNC_ROLES = frozenset({'OFFICER', 'MANAGER'})
WRITE_ROLES = frozenset({'OFFICER', 'MANAGER'})
ALL_ROLES = frozenset({'OFFICER', 'MANAGER', 'COUNCIL_USER', 'COUNCIL_MANAGER', 'READ_ONLY'})


def _get_role(request):
    try:
        return request.user.profile.officer_role
    except Exception:
        return None


class IsAuthenticatedWithRole(BasePermission):
    """
    Default permission: must be logged in and have any recognised role.
    Superusers bypass all checks.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _get_role(request) in ALL_ROLES


class FNCOnlyPermission(BasePermission):
    """Only FNC staff (OFFICER or MANAGER) — council-side users get 403."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _get_role(request) in FNC_ROLES


class WriteOrReadOnlyPermission(BasePermission):
    """
    OFFICER/MANAGER: full access.
    COUNCIL_USER/COUNCIL_MANAGER/READ_ONLY: read-only (safe methods).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = _get_role(request)
        if role not in ALL_ROLES:
            return False
        if request.method in SAFE_METHODS:
            return True
        return role in WRITE_ROLES


class CouncilScopedPermission(BasePermission):
    """
    Object-level council scoping for council-side roles.
    Combine with a viewset that overrides get_queryset() to pre-filter by council.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        role = _get_role(request)
        if role not in COUNCIL_ROLES:
            return True  # FNC and READ_ONLY are not council-scoped
        try:
            council = request.user.profile.council
            field_path = getattr(view, 'council_filter_field', 'council')
            val = obj
            for part in field_path.split('__'):
                val = getattr(val, part, None)
            return val == council
        except Exception:
            return False


class CouncilSubmitPermission(BasePermission):
    """Only council-side roles (COUNCIL_USER, COUNCIL_MANAGER) may submit."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _get_role(request) in COUNCIL_ROLES


class ApprovalPermission(BasePermission):
    """
    FNC staff only; approval actions require MANAGER role or above.
    Used on approve/reject @action endpoints.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _get_role(request) in FNC_ROLES
