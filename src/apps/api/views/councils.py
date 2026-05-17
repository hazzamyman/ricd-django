"""ViewSets for Council, Program, and Project."""
from rest_framework import viewsets
from apps.core.models import Council, Program, Project
from apps.api.serializers.councils import CouncilSerializer, ProgramSerializer, ProjectSerializer
from apps.api.permissions import WriteOrReadOnlyPermission, COUNCIL_ROLES, _get_role


class CouncilViewSet(viewsets.ModelViewSet):
    queryset = Council.objects.all()
    serializer_class = CouncilSerializer
    permission_classes = [WriteOrReadOnlyPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        role = _get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                qs = qs.filter(pk=council.pk) if council else qs.none()
            except Exception:
                qs = qs.none()
        return qs


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [WriteOrReadOnlyPermission]


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('council', 'program').all()
    serializer_class = ProjectSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = _get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                qs = qs.filter(council=council)
            except Exception:
                qs = qs.none()
        return qs
