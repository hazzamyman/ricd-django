"""ViewSets for Work and WorkFunding."""
from rest_framework import viewsets
from apps.core.models import Work, WorkFunding
from apps.api.serializers.works import WorkSerializer, WorkFundingSerializer
from apps.api.permissions import WriteOrReadOnlyPermission, COUNCIL_ROLES, _get_role


class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.select_related('project', 'work_type').all()
    serializer_class = WorkSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = _get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                qs = qs.filter(project__council=council)
            except Exception:
                qs = qs.none()
        return qs


class WorkFundingViewSet(viewsets.ModelViewSet):
    queryset = WorkFunding.objects.select_related('funding_schedule', 'project', 'work').all()
    serializer_class = WorkFundingSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = _get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                qs = qs.filter(project__council=council)
            except Exception:
                qs = qs.none()
        return qs
