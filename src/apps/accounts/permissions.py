from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from apps.councils.models import Council


class FNCMixin:
    """
    Mixin that requires user to be in FNC User or FNC Manager group.
    FNC users have access to all projects across all councils.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not (request.user.groups.filter(name__startswith='FNC').exists() or request.user.is_superuser):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class FNCManagerMixin:
    """
    Mixin that requires user to be in FNC Manager group.
    FNC Managers can approve state changes and stage reports.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not (request.user.groups.filter(name='FNC Manager').exists() or request.user.is_superuser):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class CouncilUserMixin:
    """
    Mixin that requires user to be in a Council User group.
    Council Users can only view and submit reports for their assigned councils.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.groups.filter(name__endswith='Council User').exists():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)