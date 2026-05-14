from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import (
    PaymentRule, FundingAgreement, FundingSchedule, BriefFinancialApproval,
    FundingNotice, ExpenseClaim, Approval, WorkflowAction, AuditLog
)
from apps.core.models import Payment
from apps.api.serializers.funding import (
    PaymentRuleSerializer, FundingAgreementSerializer, FundingScheduleSerializer,
    BriefFinancialApprovalSerializer, PaymentSerializer, ApprovalSerializer,
    FundingNoticeSerializer, ExpenseClaimSerializer, WorkflowActionSerializer,
    AuditLogSerializer
)


class PaymentRuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentRule.objects.all()
    serializer_class = PaymentRuleSerializer


class FundingAgreementViewSet(viewsets.ModelViewSet):
    queryset = FundingAgreement.objects.all()
    serializer_class = FundingAgreementSerializer


class FundingScheduleViewSet(viewsets.ModelViewSet):
    queryset = FundingSchedule.objects.all()
    serializer_class = FundingScheduleSerializer


class BriefFinancialApprovalViewSet(viewsets.ModelViewSet):
    queryset = BriefFinancialApproval.objects.all()
    serializer_class = BriefFinancialApprovalSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer


class FundingNoticeViewSet(viewsets.ModelViewSet):
    queryset = FundingNotice.objects.all()
    serializer_class = FundingNoticeSerializer


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    queryset = ExpenseClaim.objects.all()
    serializer_class = ExpenseClaimSerializer


class WorkflowActionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowAction.objects.all()
    serializer_class = WorkflowActionSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
