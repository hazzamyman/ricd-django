"""
RICD API v1 router.

State-transition actions (POST only):
  /api/v1/funding-schedules/{id}/approve/   execute/   complete/
  /api/v1/funding-agreements/{id}/activate/  cease/
  /api/v1/brief-financial-approvals/{id}/approve/  reject/
  /api/v1/payments/{id}/release/
  /api/v1/approvals/{id}/approve/  reject/
  /api/v1/funding-notices/{id}/close/
  /api/v1/expense-claims/{id}/submit/  approve/  reject/
  /api/v1/variations/{id}/sign/  execute/  cancel/
  /api/v1/stage-reports/{id}/submit/  endorse/  assess/  approve/
  /api/v1/quarterly-reports/{id}/submit/  approve/

OpenAPI:
  GET /api/v1/schema/   → OpenAPI 3 YAML
  GET /api/v1/docs/     → Swagger UI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.api.views.funding import (
    PaymentRuleViewSet, FundingAgreementViewSet, FundingScheduleViewSet,
    BriefFinancialApprovalViewSet, PaymentViewSet, ApprovalViewSet,
    FundingNoticeViewSet, ExpenseClaimViewSet, WorkflowActionViewSet,
    AuditLogViewSet,
)
from apps.api.views.councils import CouncilViewSet, ProgramViewSet, ProjectViewSet
from apps.api.views.works import WorkViewSet, WorkFundingViewSet
from apps.api.views.variations import VariationViewSet, VariationItemViewSet
from apps.api.views.reports import StageReportViewSet, QuarterlyReportViewSet

router = DefaultRouter()

# Funding domain
router.register(r'payment-rules', PaymentRuleViewSet, basename='paymentrule')
router.register(r'funding-agreements', FundingAgreementViewSet, basename='fundingagreement')
router.register(r'funding-schedules', FundingScheduleViewSet, basename='fundingschedule')
router.register(r'brief-financial-approvals', BriefFinancialApprovalViewSet, basename='brieffinancialapproval')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'approvals', ApprovalViewSet, basename='approval')
router.register(r'funding-notices', FundingNoticeViewSet, basename='fundingnotice')
router.register(r'expense-claims', ExpenseClaimViewSet, basename='expenseclaim')
router.register(r'workflow-actions', WorkflowActionViewSet, basename='workflowaction')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

# Councils / Programs / Projects
router.register(r'councils', CouncilViewSet, basename='council')
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'projects', ProjectViewSet, basename='project')

# Works
router.register(r'works', WorkViewSet, basename='work')
router.register(r'work-funding', WorkFundingViewSet, basename='workfunding')

# Variations
router.register(r'variations', VariationViewSet, basename='variation')
router.register(r'variation-items', VariationItemViewSet, basename='variationitem')

# Reports
router.register(r'stage-reports', StageReportViewSet, basename='stagereport')
router.register(r'quarterly-reports', QuarterlyReportViewSet, basename='quarterlyreport')

urlpatterns = [
    path('', include(router.urls)),
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
]
