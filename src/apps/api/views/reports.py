"""ViewSets for StageReport and QuarterlyReport."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import StageReport, QuarterlyReport
from apps.api.serializers.reports import StageReportSerializer, QuarterlyReportSerializer
from apps.api.permissions import FNCOnlyPermission, WriteOrReadOnlyPermission, COUNCIL_ROLES, _get_role


def _council_qs(qs, request, field):
    role = _get_role(request)
    if role in COUNCIL_ROLES:
        try:
            council = request.user.profile.council
            qs = qs.filter(**{field: council})
        except Exception:
            qs = qs.none()
    return qs


class StageReportViewSet(viewsets.ModelViewSet):
    queryset = StageReport.objects.select_related('project', 'funding_schedule').all()
    serializer_class = StageReportSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        return _council_qs(super().get_queryset(), self.request, 'project__council')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        obj = self.get_object()
        if obj.status != StageReport.Status.DRAFT:
            return Response({'detail': 'Only DRAFT reports can be submitted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = StageReport.Status.SUBMITTED
        obj.submitted_by = request.user
        obj.submitted_at = timezone.now()
        obj.save(update_fields=['status', 'submitted_by', 'submitted_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def endorse(self, request, pk=None):
        obj = self.get_object()
        if obj.status != StageReport.Status.SUBMITTED:
            return Response({'detail': 'Only SUBMITTED reports can be endorsed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = StageReport.Status.ENDORSED
        obj.endorsed_by = request.user
        obj.endorsed_at = timezone.now()
        obj.save(update_fields=['status', 'endorsed_by', 'endorsed_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def assess(self, request, pk=None):
        obj = self.get_object()
        if obj.status != StageReport.Status.ENDORSED:
            return Response({'detail': 'Only ENDORSED reports can be assessed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = StageReport.Status.ASSESSED
        obj.assessed_by = request.user
        obj.assessed_at = timezone.now()
        obj.save(update_fields=['status', 'assessed_by', 'assessed_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def approve(self, request, pk=None):
        """Approve — may unlock next payment via signal."""
        obj = self.get_object()
        if obj.status != StageReport.Status.ASSESSED:
            return Response({'detail': 'Only ASSESSED reports can be approved.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = StageReport.Status.APPROVED
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class QuarterlyReportViewSet(viewsets.ModelViewSet):
    queryset = QuarterlyReport.objects.select_related('project').all()
    serializer_class = QuarterlyReportSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        return _council_qs(super().get_queryset(), self.request, 'project__council')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        obj = self.get_object()
        if obj.status != QuarterlyReport.Status.DRAFT:
            return Response({'detail': 'Only DRAFT reports can be submitted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = QuarterlyReport.Status.SUBMITTED
        obj.submitted_by = request.user
        obj.submitted_at = timezone.now()
        obj.save(update_fields=['status', 'submitted_by', 'submitted_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def approve(self, request, pk=None):
        obj = self.get_object()
        if obj.status not in (QuarterlyReport.Status.ENDORSED, QuarterlyReport.Status.ASSESSED):
            return Response({'detail': 'Report must be ENDORSED or ASSESSED to approve.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        obj.status = QuarterlyReport.Status.APPROVED
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(self.get_serializer(obj).data)
