from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.api.views.funding import (
    PaymentRuleViewSet, FundingAgreementViewSet, FundingScheduleViewSet,
    BriefFinancialApprovalViewSet, PaymentViewSet, ApprovalViewSet,
    FundingNoticeViewSet, ExpenseClaimViewSet, WorkflowActionViewSet,
    AuditLogViewSet
)

router = DefaultRouter()
router.register(r'payment-rules', PaymentRuleViewSet, basename='paymentrule')
router.register(r'funding-agreements', FundingAgreementViewSet, basename='fundingagreement')
router.register(r'funding-schedules', FundingScheduleViewSet, basename='fundingschedule')
router.register(r'brief-financial-approvals', BriefFinancialApprovalViewSet, basename='brieffinancialpproval')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'approvals', ApprovalViewSet, basename='approval')
router.register(r'funding-notices', FundingNoticeViewSet, basename='fundingnotice')
router.register(r'expense-claims', ExpenseClaimViewSet, basename='expenseclaim')
router.register(r'workflow-actions', WorkflowActionViewSet, basename='workflowaction')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
]
