from django.urls import path
from . import views

app_name = 'ui'

urlpatterns = [
    # Dashboard views
    path('dashboard/', views.dashboard_views.dashboard_view, name='dashboard'),
    path('cashflow/', views.dashboard_views.cashflow_view, name='cashflow'),
    path('aggregate/', views.dashboard_views.aggregate_outputs_view, name='aggregate_outputs'),

    # Maintenance views
    # path('maintenance/', views.maintenance_views.maintenance_list, name='maintenance_list'),

    # Planning views
    path('planning/', views.planning_views.planning_list, name='planning_list'),

    # Project management views (existing list + new CRUD)
    path('projects/', views.projects_views.projects_list_view, name='projects_list'),
    path('projects/create/', views.crud_views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.crud_views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', views.crud_views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:pk>/delete/', views.crud_views.ProjectDeleteView.as_view(), name='project_delete'),

    # Payments (nested under project)
    path('projects/<int:project_pk>/payments/', views.crud_views.PaymentListView.as_view(), name='payment_list'),
    path('projects/<int:project_pk>/payments/create/', views.crud_views.PaymentCreateView.as_view(), name='payment_create'),
    path('projects/<int:project_pk>/payments/<int:pk>/', views.crud_views.PaymentDetailView.as_view(), name='payment_detail'),
    path('projects/<int:project_pk>/payments/<int:pk>/edit/', views.crud_views.PaymentUpdateView.as_view(), name='payment_edit'),
    path('projects/<int:project_pk>/payments/<int:pk>/delete/', views.crud_views.PaymentDeleteView.as_view(), name='payment_delete'),

    # Stage Reports (nested under project)
    path('projects/<int:project_pk>/stage-reports/', views.crud_views.StageReportListView.as_view(), name='stage_report_list'),
    path('projects/<int:project_pk>/stage-reports/create/', views.crud_views.StageReportCreateView.as_view(), name='stage_report_create'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/', views.crud_views.StageReportDetailView.as_view(), name='stage_report_detail'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/edit/', views.crud_views.StageReportUpdateView.as_view(), name='stage_report_edit'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/delete/', views.crud_views.StageReportDeleteView.as_view(), name='stage_report_delete'),

    # Quarterly Reports (nested under project)
    path('projects/<int:project_pk>/quarterly-reports/', views.crud_views.QuarterlyReportListView.as_view(), name='quarterly_report_list'),
    path('projects/<int:project_pk>/quarterly-reports/create/', views.crud_views.QuarterlyReportCreateView.as_view(), name='quarterly_report_create'),
    path('projects/<int:project_pk>/quarterly-reports/<int:pk>/', views.crud_views.QuarterlyReportDetailView.as_view(), name='quarterly_report_detail'),
    path('projects/<int:project_pk>/quarterly-reports/<int:pk>/edit/', views.crud_views.QuarterlyReportUpdateView.as_view(), name='quarterly_report_edit'),
    path('projects/<int:project_pk>/quarterly-reports/<int:pk>/delete/', views.crud_views.QuarterlyReportDeleteView.as_view(), name='quarterly_report_delete'),

    # Variations (existing list + new CRUD)
    path('variations/', views.variations_views.variations_list_view, name='variations_list'),
    path('variations/create/', views.crud_views.VariationCreateView.as_view(), name='variation_create'),
    path('variations/<int:pk>/', views.crud_views.VariationDetailView.as_view(), name='variation_detail'),
    path('variations/<int:pk>/edit/', views.crud_views.VariationUpdateView.as_view(), name='variation_edit'),
    path('variations/<int:pk>/delete/', views.crud_views.VariationDeleteView.as_view(), name='variation_delete'),

    # Councils CRUD
    path('councils/', views.crud_views.CouncilListView.as_view(), name='council_list'),
    path('councils/create/', views.crud_views.CouncilCreateView.as_view(), name='council_create'),
    path('councils/<int:pk>/', views.crud_views.CouncilDetailView.as_view(), name='council_detail'),
    path('councils/<int:pk>/edit/', views.crud_views.CouncilUpdateView.as_view(), name='council_edit'),
    path('councils/<int:pk>/delete/', views.crud_views.CouncilDeleteView.as_view(), name='council_delete'),

    # Programs CRUD
    path('programs/', views.crud_views.ProgramListView.as_view(), name='program_list'),
    path('programs/create/', views.crud_views.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/', views.crud_views.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/<int:pk>/edit/', views.crud_views.ProgramUpdateView.as_view(), name='program_edit'),
    path('programs/<int:pk>/delete/', views.crud_views.ProgramDeleteView.as_view(), name='program_delete'),

    # Work Types CRUD
    path('work-types/', views.crud_views.WorkTypeListView.as_view(), name='work_type_list'),
    path('work-types/create/', views.crud_views.WorkTypeCreateView.as_view(), name='work_type_create'),
    path('work-types/<int:pk>/', views.crud_views.WorkTypeDetailView.as_view(), name='work_type_detail'),
    path('work-types/<int:pk>/edit/', views.crud_views.WorkTypeUpdateView.as_view(), name='work_type_edit'),
    path('work-types/<int:pk>/delete/', views.crud_views.WorkTypeDeleteView.as_view(), name='work_type_delete'),

    # Funding Schedules CRUD
    path('funding-schedules/', views.crud_views.FundingScheduleListView.as_view(), name='funding_schedule_list'),
    path('funding-schedules/create/', views.crud_views.FundingScheduleCreateView.as_view(), name='funding_schedule_create'),
    path('funding-schedules/<int:pk>/', views.crud_views.FundingScheduleDetailView.as_view(), name='funding_schedule_detail'),
    path('funding-schedules/<int:pk>/edit/', views.crud_views.FundingScheduleUpdateView.as_view(), name='funding_schedule_edit'),
    path('funding-schedules/<int:pk>/delete/', views.crud_views.FundingScheduleDeleteView.as_view(), name='funding_schedule_delete'),

    # Funding Notices CRUD + close action
    path('funding-notices/', views.crud_views.FundingNoticeListView.as_view(), name='funding_notice_list'),
    path('funding-notices/create/', views.crud_views.FundingNoticeCreateView.as_view(), name='funding_notice_create'),
    path('funding-notices/<int:pk>/', views.crud_views.FundingNoticeDetailView.as_view(), name='funding_notice_detail'),
    path('funding-notices/<int:pk>/edit/', views.crud_views.FundingNoticeUpdateView.as_view(), name='funding_notice_edit'),
    path('funding-notices/<int:pk>/delete/', views.crud_views.FundingNoticeDeleteView.as_view(), name='funding_notice_delete'),
    path('funding-notices/<int:pk>/close/', views.crud_views.FundingNoticeCloseView.as_view(), name='funding_notice_close'),

    # Expense Claims (nested under FundingNotice)
    path('funding-notices/<int:notice_pk>/claims/create/', views.crud_views.ExpenseClaimCreateView.as_view(), name='expense_claim_create'),
    path('expense-claims/<int:pk>/edit/', views.crud_views.ExpenseClaimUpdateView.as_view(), name='expense_claim_edit'),
    path('expense-claims/<int:pk>/delete/', views.crud_views.ExpenseClaimDeleteView.as_view(), name='expense_claim_delete'),
    path('expense-claims/<int:pk>/approve/', views.crud_views.ExpenseClaimApproveView.as_view(), name='expense_claim_approve'),
    path('expense-claims/<int:pk>/reject/', views.crud_views.ExpenseClaimRejectView.as_view(), name='expense_claim_reject'),

    # Funding Agreements CRUD
    path('funding-agreements/', views.crud_views.FundingAgreementListView.as_view(), name='funding_agreement_list'),
    path('funding-agreements/create/', views.crud_views.FundingAgreementCreateView.as_view(), name='funding_agreement_create'),
    path('funding-agreements/<int:pk>/', views.crud_views.FundingAgreementDetailView.as_view(), name='funding_agreement_detail'),
    path('funding-agreements/<int:pk>/edit/', views.crud_views.FundingAgreementUpdateView.as_view(), name='funding_agreement_edit'),
    path('funding-agreements/<int:pk>/delete/', views.crud_views.FundingAgreementDeleteView.as_view(), name='funding_agreement_delete'),

    # Brief Financial Approvals (nested under project)
    path('projects/<int:project_pk>/bfa/', views.crud_views.BriefFinancialApprovalListView.as_view(), name='bfa_list'),
    path('projects/<int:project_pk>/bfa/create/', views.crud_views.BriefFinancialApprovalCreateView.as_view(), name='bfa_create'),
    path('projects/<int:project_pk>/bfa/<int:pk>/', views.crud_views.BriefFinancialApprovalDetailView.as_view(), name='bfa_detail'),
    path('projects/<int:project_pk>/bfa/<int:pk>/edit/', views.crud_views.BriefFinancialApprovalUpdateView.as_view(), name='bfa_edit'),
    path('projects/<int:project_pk>/bfa/<int:pk>/delete/', views.crud_views.BriefFinancialApprovalDeleteView.as_view(), name='bfa_delete'),
    path('projects/<int:project_pk>/bfa/<int:pk>/approve/', views.crud_views.BriefFinancialApprovalApproveView.as_view(), name='bfa_approve'),
    path('projects/<int:project_pk>/bfa/<int:pk>/reject/', views.crud_views.BriefFinancialApprovalRejectView.as_view(), name='bfa_reject'),

    # Other existing views
    path('reports/', views.reports_views.reports_dashboard_view, name='reports_dashboard'),
    path('land-infra/', views.land_infra_views.land_projects_list_view, name='land_projects_list'),
    path('documents/', views.documents_views.documents_list_view, name='documents_list'),
]
