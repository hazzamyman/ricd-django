"""ViewSets for Variation and VariationItem."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import Variation, VariationItem
from apps.api.serializers.variations import VariationSerializer, VariationItemSerializer
from apps.api.permissions import FNCOnlyPermission, WriteOrReadOnlyPermission, COUNCIL_ROLES, _get_role


class VariationViewSet(viewsets.ModelViewSet):
    queryset = Variation.objects.select_related('funding_schedule').prefetch_related('items').all()
    serializer_class = VariationSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'funding_schedule__project__council'

    def get_queryset(self):
        qs = super().get_queryset()
        role = _get_role(self.request)
        if role in COUNCIL_ROLES:
            try:
                council = self.request.user.profile.council
                qs = qs.filter(funding_schedule__project__council=council)
            except Exception:
                qs = qs.none()
        return qs

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def sign(self, request, pk=None):
        """Advance Variation to COUNCIL_SIGNED."""
        obj = self.get_object()
        if obj.status != Variation.Status.DRAFT:
            return Response({'detail': 'Only DRAFT variations can be signed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = Variation.Status.COUNCIL_SIGNED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def execute(self, request, pk=None):
        """Execute a COUNCIL_SIGNED variation — triggers FundingSchedule lifecycle signals."""
        obj = self.get_object()
        if obj.status != Variation.Status.COUNCIL_SIGNED:
            return Response({'detail': 'Only COUNCIL_SIGNED variations can be executed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from datetime import date
        obj.status = Variation.Status.EXECUTED
        obj.department_executed_date = date.today()
        obj.save(update_fields=['status', 'department_executed_date', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def cancel(self, request, pk=None):
        obj = self.get_object()
        if obj.status == Variation.Status.EXECUTED:
            return Response({'detail': 'EXECUTED variations cannot be cancelled.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = Variation.Status.CANCELLED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class VariationItemViewSet(viewsets.ModelViewSet):
    queryset = VariationItem.objects.select_related('variation').all()
    serializer_class = VariationItemSerializer
    permission_classes = [FNCOnlyPermission]
