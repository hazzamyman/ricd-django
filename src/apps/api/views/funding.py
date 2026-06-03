"""
ViewSets for the funding domain.

State-transition actions follow the pattern:
  POST /api/v1/<resource>/{id}/<action>/
  Body: {} (or {"comments": "..."} for approve/reject)
  Returns the updated serialized object.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import (
    PaymentRule, FundingAgreement, FundingSchedule, BriefFinancialApproval,
    FundingNotice, ExpenseClaim, Approval, WorkflowAction, AuditLog, Payment,
)
from apps.api.serializers.funding import (
    PaymentRuleSerializer, FundingAgreementSerializer, FundingScheduleSerializer,
    BriefFinancialApprovalSerializer, PaymentSerializer, ApprovalSerializer,
    FundingNoticeSerializer, ExpenseClaimSerializer, WorkflowActionSerializer,
    AuditLogSerializer,
)
from apps.api.permissions import (
    FNCOnlyPermission, WriteOrReadOnlyPermission, ApprovalPermission,
    COUNCIL_ROLES, _get_role,
)


def _council_scope(qs, request, filter_field):
    """Filter queryset to own council for council-side roles."""
    role = _get_role(request)
    if role in COUNCIL_ROLES:
        try:
            council = request.user.profile.council
            qs = qs.filter(**{filter_field: council})
        except Exception:
            qs = qs.none()
    return qs


class PaymentRuleViewSet(viewsets.ReadOnlyModelViewSet):
    """PaymentRules are immutable once used — list/retrieve only."""
    queryset = PaymentRule.objects.all()
    serializer_class = PaymentRuleSerializer


class FundingAgreementViewSet(viewsets.ModelViewSet):
    queryset = FundingAgreement.objects.select_related('council').all()
    serializer_class = FundingAgreementSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'council'

    def get_queryset(self):
        return _council_scope(super().get_queryset(), self.request, 'council')

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.status = FundingAgreement.Status.ACTIVE
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def cease(self, request, pk=None):
        obj = self.get_object()
        obj.status = FundingAgreement.Status.CEASED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class FundingScheduleViewSet(viewsets.ModelViewSet):
    queryset = FundingSchedule.objects.select_related('project', 'funding_agreement', 'payment_rule').order_by('-id')
    serializer_class = FundingScheduleSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        return _council_scope(super().get_queryset(), self.request, 'project__council')

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def approve(self, request, pk=None):
        """Advance to READY_FOR_EXECUTION (financial approval gate)."""
        obj = self.get_object()
        if obj.status != FundingSchedule.Status.DRAFT:
            return Response({'detail': 'Only DRAFT schedules can be approved.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = FundingSchedule.Status.READY_FOR_EXECUTION
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def execute(self, request, pk=None):
        """Advance to EXECUTED (variation deed executed)."""
        obj = self.get_object()
        if obj.status != FundingSchedule.Status.READY_FOR_EXECUTION:
            return Response({'detail': 'Schedule must be READY_FOR_EXECUTION to execute.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = FundingSchedule.Status.EXECUTED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def complete(self, request, pk=None):
        """Mark ACTIVE schedule as COMPLETED."""
        obj = self.get_object()
        if obj.status != FundingSchedule.Status.ACTIVE:
            return Response({'detail': 'Only ACTIVE schedules can be completed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = FundingSchedule.Status.COMPLETED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class BriefFinancialApprovalViewSet(viewsets.ModelViewSet):
    queryset = BriefFinancialApproval.objects.prefetch_related('items__project__council').all()
    serializer_class = BriefFinancialApprovalSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    # Council scoping walks via items -> project -> council (BFA may span multiple councils)
    council_filter_field = 'items__project__council'

    def get_queryset(self):
        return _council_scope(super().get_queryset(), self.request, 'items__project__council').distinct()

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def approve(self, request, pk=None):
        from django.utils import timezone
        obj = self.get_object()
        obj.status = BriefFinancialApproval.Status.APPROVED
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = BriefFinancialApproval.Status.REJECTED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('project', 'funding_schedule').order_by('-id')
    serializer_class = PaymentSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        return _council_scope(super().get_queryset(), self.request, 'project__council')

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def release(self, request, pk=None):
        """Release an APPROVED payment."""
        obj = self.get_object()
        if obj.status != Payment.Status.APPROVED:
            return Response({'detail': 'Only APPROVED payments can be released.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from datetime import date
        obj.status = Payment.Status.RELEASED
        obj.release_date = obj.release_date or date.today()
        obj.save(update_fields=['status', 'release_date', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [WriteOrReadOnlyPermission]

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def approve(self, request, pk=None):
        """Approve — triggers downstream signal (e.g. Payment → APPROVED)."""
        obj = self.get_object()
        if obj.status != Approval.Status.PENDING:
            return Response({'detail': 'Only PENDING approvals can be approved.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = Approval.Status.APPROVED
        obj.approved_by = request.user
        obj.comments = request.data.get('comments', obj.comments)
        obj.save(update_fields=['status', 'approved_by', 'approved_at', 'comments'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def reject(self, request, pk=None):
        obj = self.get_object()
        if obj.status != Approval.Status.PENDING:
            return Response({'detail': 'Only PENDING approvals can be rejected.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = Approval.Status.REJECTED
        obj.comments = request.data.get('comments', obj.comments)
        obj.save(update_fields=['status', 'comments', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class FundingNoticeViewSet(viewsets.ModelViewSet):
    queryset = FundingNotice.objects.select_related('project').all()
    serializer_class = FundingNoticeSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'project__council'

    def get_queryset(self):
        return _council_scope(super().get_queryset(), self.request, 'project__council')

    @action(detail=True, methods=['post'], permission_classes=[FNCOnlyPermission])
    def close(self, request, pk=None):
        obj = self.get_object()
        obj.status = FundingNotice.Status.CLOSED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    queryset = ExpenseClaim.objects.select_related('funding_notice__project').all()
    serializer_class = ExpenseClaimSerializer
    permission_classes = [WriteOrReadOnlyPermission]
    council_filter_field = 'funding_notice__project__council'

    def get_queryset(self):
        return _council_scope(
            super().get_queryset(), self.request, 'funding_notice__project__council'
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a DRAFT claim."""
        obj = self.get_object()
        if obj.status != ExpenseClaim.Status.DRAFT:
            return Response({'detail': 'Only DRAFT claims can be submitted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = ExpenseClaim.Status.SUBMITTED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def approve(self, request, pk=None):
        """Approve a submitted claim — cap enforced via serializer."""
        obj = self.get_object()
        if obj.status != ExpenseClaim.Status.SUBMITTED:
            return Response({'detail': 'Only SUBMITTED claims can be approved.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(obj, data={'status': ExpenseClaim.Status.APPROVED}, partial=True)
        serializer.is_valid(raise_exception=True)
        from datetime import date
        obj.status = ExpenseClaim.Status.APPROVED
        obj.approved_by = request.user
        obj.approved_date = date.today()
        obj.save(update_fields=['status', 'approved_by', 'approved_date', 'updated_at'])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[ApprovalPermission])
    def reject(self, request, pk=None):
        obj = self.get_object()
        if obj.status != ExpenseClaim.Status.SUBMITTED:
            return Response({'detail': 'Only SUBMITTED claims can be rejected.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = ExpenseClaim.Status.REJECTED
        obj.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(obj).data)


class WorkflowActionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowAction.objects.all()
    serializer_class = WorkflowActionSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [FNCOnlyPermission]
