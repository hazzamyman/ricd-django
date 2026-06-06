from django.urls import path
from . import views

app_name = 'ui'

urlpatterns = [
    # Dashboard views
    path('dashboard/', views.dashboard_views.dashboard_view, name='dashboard'),
    path('cashflow/', views.dashboard_views.cashflow_view, name='cashflow'),
    path('aggregate/', views.dashboard_views.aggregate_outputs_view, name='aggregate_outputs'),
    path('dashboard/projects/', views.dashboard_views.projects_board_view, name='projects_board'),
    path('dashboard/traceability/', views.dashboard_views.traceability_view, name='traceability'),
    path('help/', views.dashboard_views.help_view, name='help'),

    # Maintenance
    path('maintenance/', views.crud_views.MaintenanceView.as_view(), name='maintenance'),
    path('maintenance/site-settings/', views.crud_views.SiteSettingsView.as_view(), name='site_settings'),

    # Planning views
    path('planning/', views.planning_views.planning_list, name='planning_list'),

    # Project management views (existing list + new CRUD)
    path('projects/', views.projects_views.projects_list_view, name='projects_list'),
    path('projects/create/', views.crud_views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.crud_views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', views.crud_views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:pk>/delete/', views.crud_views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/set-completion-dates/', views.crud_views.ProjectSetCompletionDatesView.as_view(), name='project_set_completion_dates'),

    # Payments (nested under project)
    path('projects/<int:project_pk>/payments/', views.crud_views.PaymentListView.as_view(), name='payment_list'),
    path('projects/<int:project_pk>/payments/create/', views.crud_views.PaymentCreateView.as_view(), name='payment_create'),
    path('projects/<int:project_pk>/payments/<int:pk>/', views.crud_views.PaymentDetailView.as_view(), name='payment_detail'),
    path('projects/<int:project_pk>/payments/<int:pk>/edit/', views.crud_views.PaymentUpdateView.as_view(), name='payment_edit'),
    path('projects/<int:project_pk>/payments/<int:pk>/delete/', views.crud_views.PaymentDeleteView.as_view(), name='payment_delete'),
    path('projects/<int:project_pk>/payments/<int:pk>/recommend/', views.crud_views.PaymentRecommendView.as_view(), name='payment_recommend'),
    path('projects/<int:project_pk>/payments/<int:pk>/approve/', views.crud_views.PaymentApproveView.as_view(), name='payment_approve'),
    path('projects/<int:project_pk>/payments/<int:pk>/release/', views.crud_views.PaymentReleaseView.as_view(), name='payment_release'),
    path('projects/<int:project_pk>/payments/<int:pk>/reconcile/', views.crud_views.PaymentReconcileView.as_view(), name='payment_reconcile'),
    path('projects/<int:project_pk>/payments/<int:pk>/reject/', views.crud_views.PaymentRejectView.as_view(), name='payment_reject'),

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
    # Council Contacts (nested under Council)
    path('councils/<int:council_pk>/contacts/add/', views.crud_views.CouncilContactCreateView.as_view(), name='council_contact_create'),
    path('council-contacts/<int:pk>/edit/', views.crud_views.CouncilContactUpdateView.as_view(), name='council_contact_edit'),
    path('council-contacts/<int:pk>/delete/', views.crud_views.CouncilContactDeleteView.as_view(), name='council_contact_delete'),

    # Programs CRUD
    path('programs/', views.crud_views.ProgramListView.as_view(), name='program_list'),
    path('programs/create/', views.crud_views.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/', views.crud_views.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/<int:pk>/edit/', views.crud_views.ProgramUpdateView.as_view(), name='program_edit'),
    path('programs/<int:pk>/delete/', views.crud_views.ProgramDeleteView.as_view(), name='program_delete'),
    # Program Budgets (per FY, nested under Program)
    path('programs/<int:program_pk>/budgets/add/', views.crud_views.ProgramBudgetCreateView.as_view(), name='program_budget_create'),
    path('program-budgets/<int:pk>/edit/', views.crud_views.ProgramBudgetUpdateView.as_view(), name='program_budget_edit'),
    path('program-budgets/<int:pk>/delete/', views.crud_views.ProgramBudgetDeleteView.as_view(), name='program_budget_delete'),

    # Work Types CRUD
    path('work-types/', views.crud_views.WorkTypeListView.as_view(), name='work_type_list'),
    path('work-types/create/', views.crud_views.WorkTypeCreateView.as_view(), name='work_type_create'),
    path('work-types/<int:pk>/', views.crud_views.WorkTypeDetailView.as_view(), name='work_type_detail'),
    path('work-types/<int:pk>/edit/', views.crud_views.WorkTypeUpdateView.as_view(), name='work_type_edit'),
    path('work-types/<int:pk>/delete/', views.crud_views.WorkTypeDeleteView.as_view(), name='work_type_delete'),

    # Notional Costs — global list + bulk update (maintenance)
    path('notional-costs/', views.crud_views.NotionalCostListView.as_view(), name='notional_cost_list'),
    path('notional-costs/bulk-update/', views.crud_views.NotionalCostBulkUpdateView.as_view(), name='notional_cost_bulk_update'),
    # Notional Costs (nested under WorkType)
    path('work-types/<int:wt_pk>/costs/create/', views.crud_views.NotionalCostCreateView.as_view(), name='notional_cost_create'),
    path('work-types/<int:wt_pk>/costs/<int:pk>/edit/', views.crud_views.NotionalCostUpdateView.as_view(), name='notional_cost_edit'),
    path('work-types/<int:wt_pk>/costs/<int:pk>/delete/', views.crud_views.NotionalCostDeleteView.as_view(), name='notional_cost_delete'),

    # Suburbs CRUD
    path('suburbs/', views.crud_views.SuburbListView.as_view(), name='suburb_list'),
    path('suburbs/create/', views.crud_views.SuburbCreateView.as_view(), name='suburb_create'),
    path('suburbs/<int:pk>/edit/', views.crud_views.SuburbUpdateView.as_view(), name='suburb_edit'),
    path('suburbs/<int:pk>/delete/', views.crud_views.SuburbDeleteView.as_view(), name='suburb_delete'),

    # WorkStepDefinition CRUD (global catalogue)
    path('work-step-definitions/', views.crud_views.WorkStepDefinitionListView.as_view(), name='work_step_definition_list'),
    path('work-step-definitions/create/', views.crud_views.WorkStepDefinitionCreateView.as_view(), name='work_step_definition_create'),
    path('work-step-definitions/<int:pk>/edit/', views.crud_views.WorkStepDefinitionUpdateView.as_view(), name='work_step_definition_edit'),
    path('work-step-definitions/<int:pk>/delete/', views.crud_views.WorkStepDefinitionDeleteView.as_view(), name='work_step_definition_delete'),

    # WorkStepGroup CRUD (central — under Maintenance)
    path('maintenance/work-step-groups/', views.crud_views.WorkStepGroupListView.as_view(), name='work_step_group_list'),
    path('maintenance/work-step-groups/create/', views.crud_views.WorkStepGroupCreateView.as_view(), name='work_step_group_create'),
    path('maintenance/work-step-groups/<int:pk>/', views.crud_views.WorkStepGroupDetailView.as_view(), name='work_step_group_detail'),
    path('maintenance/work-step-groups/<int:pk>/edit/', views.crud_views.WorkStepGroupUpdateView.as_view(), name='work_step_group_edit'),
    path('maintenance/work-step-groups/<int:pk>/delete/', views.crud_views.WorkStepGroupDeleteView.as_view(), name='work_step_group_delete'),
    path('maintenance/work-step-groups/<int:pk>/clone/', views.crud_views.WorkStepGroupCloneView.as_view(), name='work_step_group_clone'),
    # Legacy nested route — preserved so the WorkType detail "+ Add group" link still works.
    # It pre-selects the work type on the central form.
    path('work-types/<int:wt_pk>/step-groups/create/', views.crud_views.WorkStepGroupCreateView.as_view(), name='work_step_group_create_for_work_type'),

    # WorkStepGroupItem CRUD (nested under WorkStepGroup)
    path('step-groups/<int:group_pk>/items/create/', views.crud_views.WorkStepGroupItemCreateView.as_view(), name='work_step_group_item_create'),
    path('step-groups/<int:group_pk>/items/<int:pk>/edit/', views.crud_views.WorkStepGroupItemUpdateView.as_view(), name='work_step_group_item_edit'),
    path('step-groups/<int:group_pk>/items/<int:pk>/delete/', views.crud_views.WorkStepGroupItemDeleteView.as_view(), name='work_step_group_item_delete'),

    # Payment Milestone Schedules (Maintenance — when payments are timed)
    path('maintenance/payment-milestones/', views.crud_views.PaymentMilestoneScheduleListView.as_view(), name='payment_milestone_schedule_list'),
    path('maintenance/payment-milestones/create/', views.crud_views.PaymentMilestoneScheduleCreateView.as_view(), name='payment_milestone_schedule_create'),
    path('maintenance/payment-milestones/<int:pk>/', views.crud_views.PaymentMilestoneScheduleDetailView.as_view(), name='payment_milestone_schedule_detail'),
    path('maintenance/payment-milestones/<int:pk>/edit/', views.crud_views.PaymentMilestoneScheduleUpdateView.as_view(), name='payment_milestone_schedule_edit'),
    path('maintenance/payment-milestones/<int:pk>/delete/', views.crud_views.PaymentMilestoneScheduleDeleteView.as_view(), name='payment_milestone_schedule_delete'),

    # Funding Schedules CRUD + lifecycle actions
    path('funding-schedules/', views.crud_views.FundingScheduleListView.as_view(), name='funding_schedule_list'),
    path('funding-schedules/create/', views.crud_views.FundingScheduleCreateView.as_view(), name='funding_schedule_create'),
    path('funding-schedules/<int:pk>/', views.crud_views.FundingScheduleDetailView.as_view(), name='funding_schedule_detail'),
    path('funding-schedules/<int:pk>/contract-report/', views.crud_views.FundingScheduleContractReportView.as_view(), name='funding_schedule_contract_report'),
    path('funding-schedules/<int:pk>/edit/', views.crud_views.FundingScheduleUpdateView.as_view(), name='funding_schedule_edit'),
    path('funding-schedules/<int:pk>/delete/', views.crud_views.FundingScheduleDeleteView.as_view(), name='funding_schedule_delete'),
    path('funding-schedules/<int:pk>/mark-ready/', views.crud_views.FundingScheduleMarkReadyView.as_view(), name='funding_schedule_mark_ready'),
    path('funding-schedules/<int:pk>/complete/', views.crud_views.FundingScheduleCompleteView.as_view(), name='funding_schedule_complete'),
    path('funding-schedules/<int:pk>/supersede/', views.crud_views.FundingScheduleSupersededView.as_view(), name='funding_schedule_supersede'),
    path('funding-schedules/<int:pk>/cancel/', views.crud_views.FundingScheduleCancelView.as_view(), name='funding_schedule_cancel'),
    path('funding-schedules/<int:pk>/generate-instalments/', views.crud_views.FundingScheduleGenerateInstalmentsView.as_view(), name='funding_schedule_generate_instalments'),

    # Funding Notices CRUD + close action
    path('funding-notices/', views.crud_views.FundingNoticeListView.as_view(), name='funding_notice_list'),
    path('funding-notices/create/', views.crud_views.FundingNoticeCreateView.as_view(), name='funding_notice_create'),
    path('funding-notices/<int:pk>/', views.crud_views.FundingNoticeDetailView.as_view(), name='funding_notice_detail'),
    path('funding-notices/<int:pk>/edit/', views.crud_views.FundingNoticeUpdateView.as_view(), name='funding_notice_edit'),
    path('funding-notices/<int:pk>/delete/', views.crud_views.FundingNoticeDeleteView.as_view(), name='funding_notice_delete'),
    path('funding-notices/<int:pk>/close/', views.crud_views.FundingNoticeCloseView.as_view(), name='funding_notice_close'),

    # Expense Claims (nested under FundingNotice; standalone detail with attachments)
    path('funding-notices/<int:notice_pk>/claims/create/', views.crud_views.ExpenseClaimCreateView.as_view(), name='expense_claim_create'),
    path('expense-claims/<int:pk>/', views.crud_views.ExpenseClaimDetailView.as_view(), name='expense_claim_detail'),
    path('expense-claims/<int:pk>/edit/', views.crud_views.ExpenseClaimUpdateView.as_view(), name='expense_claim_edit'),
    path('expense-claims/<int:pk>/delete/', views.crud_views.ExpenseClaimDeleteView.as_view(), name='expense_claim_delete'),
    path('expense-claims/<int:pk>/submit/', views.crud_views.ExpenseClaimSubmitView.as_view(), name='expense_claim_submit'),
    path('expense-claims/<int:pk>/approve/', views.crud_views.ExpenseClaimApproveView.as_view(), name='expense_claim_approve'),
    path('expense-claims/<int:pk>/reject/', views.crud_views.ExpenseClaimRejectView.as_view(), name='expense_claim_reject'),
    # Expense claim attachments
    path('expense-claims/<int:claim_pk>/attachments/add/', views.crud_views.ExpenseClaimAttachmentAddView.as_view(), name='expense_claim_attachment_add'),
    path('expense-claim-attachments/<int:pk>/delete/', views.crud_views.ExpenseClaimAttachmentDeleteView.as_view(), name='expense_claim_attachment_delete'),

    # Funding Agreements CRUD
    path('funding-agreements/', views.crud_views.FundingAgreementListView.as_view(), name='funding_agreement_list'),
    path('funding-agreements/create/', views.crud_views.FundingAgreementCreateView.as_view(), name='funding_agreement_create'),
    path('funding-agreements/<int:pk>/', views.crud_views.FundingAgreementDetailView.as_view(), name='funding_agreement_detail'),
    path('funding-agreements/<int:pk>/edit/', views.crud_views.FundingAgreementUpdateView.as_view(), name='funding_agreement_edit'),
    path('funding-agreements/<int:pk>/delete/', views.crud_views.FundingAgreementDeleteView.as_view(), name='funding_agreement_delete'),

    # StageReport lifecycle actions
    path('projects/<int:project_pk>/stage-reports/<int:pk>/submit/', views.crud_views.StageReportSubmitView.as_view(), name='stage_report_submit'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/endorse/', views.crud_views.StageReportEndorseView.as_view(), name='stage_report_endorse'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/assess/', views.crud_views.StageReportAssessView.as_view(), name='stage_report_assess'),
    path('projects/<int:project_pk>/stage-reports/<int:pk>/approve/', views.crud_views.StageReportApproveView.as_view(), name='stage_report_approve'),

    # VariationItems (nested under Variation)
    path('variations/<int:variation_pk>/items/create/', views.crud_views.VariationItemCreateView.as_view(), name='variation_item_create'),
    path('variations/<int:variation_pk>/items/<int:pk>/edit/', views.crud_views.VariationItemUpdateView.as_view(), name='variation_item_edit'),
    path('variations/<int:variation_pk>/items/<int:pk>/delete/', views.crud_views.VariationItemDeleteView.as_view(), name='variation_item_delete'),
    path('variations/<int:pk>/execute/', views.crud_views.VariationExecuteView.as_view(), name='variation_execute'),

    # Allocations (WorkFunding)
    path('allocations/', views.crud_views.WorkFundingListView.as_view(), name='allocation_list'),
    path('allocations/create/', views.crud_views.WorkFundingCreateView.as_view(), name='allocation_create'),
    path('allocations/<int:pk>/', views.crud_views.WorkFundingDetailView.as_view(), name='allocation_detail'),
    path('allocations/<int:pk>/edit/', views.crud_views.WorkFundingUpdateView.as_view(), name='allocation_edit'),
    path('allocations/<int:pk>/delete/', views.crud_views.WorkFundingDeleteView.as_view(), name='allocation_delete'),

    # Brief Financial Approvals (un-nested — header may cover multiple projects)
    path('bfa/', views.crud_views.BriefFinancialApprovalGlobalListView.as_view(), name='bfa_global_list'),
    path('bfa/create/', views.crud_views.BriefFinancialApprovalCreateView.as_view(), name='bfa_create_global'),
    path('bfa/<int:pk>/', views.crud_views.BriefFinancialApprovalDetailView.as_view(), name='bfa_detail'),
    path('bfa/<int:pk>/edit/', views.crud_views.BriefFinancialApprovalUpdateView.as_view(), name='bfa_edit'),
    path('bfa/<int:pk>/delete/', views.crud_views.BriefFinancialApprovalDeleteView.as_view(), name='bfa_delete'),
    path('bfa/<int:pk>/approve/', views.crud_views.BriefFinancialApprovalApproveView.as_view(), name='bfa_approve'),
    path('bfa/<int:pk>/reject/', views.crud_views.BriefFinancialApprovalRejectView.as_view(), name='bfa_reject'),
    # Legacy per-project BFA list (project-detail page links here to see BFAs containing this project)
    path('projects/<int:project_pk>/bfa/', views.crud_views.BriefFinancialApprovalListView.as_view(), name='bfa_list'),
    # Compat alias: old per-project create URL -> global create form
    path('projects/<int:project_pk>/bfa/create/', views.crud_views.BriefFinancialApprovalCreateView.as_view(), name='bfa_create'),

    # Land Pre-Conditions (traffic-light flags for land development projects)
    path('projects/<int:project_pk>/pre-conditions/', views.crud_views.LandPreConditionEditView.as_view(), name='land_pre_condition_edit'),

    # Land Tenures CRUD
    path('land-tenures/', views.land_crud_views.LandTenureListView.as_view(), name='land_tenure_list'),
    path('land-tenures/create/', views.land_crud_views.LandTenureCreateView.as_view(), name='land_tenure_create'),
    path('land-tenures/<int:pk>/', views.land_crud_views.LandTenureDetailView.as_view(), name='land_tenure_detail'),
    path('land-tenures/<int:pk>/edit/', views.land_crud_views.LandTenureUpdateView.as_view(), name='land_tenure_edit'),
    path('land-tenures/<int:pk>/delete/', views.land_crud_views.LandTenureDeleteView.as_view(), name='land_tenure_delete'),

    # Development Applications CRUD
    path('development-applications/', views.land_crud_views.DevelopmentApplicationListView.as_view(), name='development_application_list'),
    path('development-applications/create/', views.land_crud_views.DevelopmentApplicationCreateView.as_view(), name='development_application_create'),
    path('development-applications/<int:pk>/', views.land_crud_views.DevelopmentApplicationDetailView.as_view(), name='development_application_detail'),
    path('development-applications/<int:pk>/edit/', views.land_crud_views.DevelopmentApplicationUpdateView.as_view(), name='development_application_edit'),
    path('development-applications/<int:pk>/delete/', views.land_crud_views.DevelopmentApplicationDeleteView.as_view(), name='development_application_delete'),

    # PaymentRule CRUD + nested milestone rows
    path('payment-rules/', views.crud_views.PaymentRuleListView.as_view(), name='payment_rule_list'),
    path('payment-rules/create/', views.crud_views.PaymentRuleCreateView.as_view(), name='payment_rule_create'),
    path('payment-rules/<int:pk>/', views.crud_views.PaymentRuleDetailView.as_view(), name='payment_rule_detail'),
    path('payment-rules/<int:pk>/edit/', views.crud_views.PaymentRuleUpdateView.as_view(), name='payment_rule_edit'),
    path('payment-rules/<int:pk>/delete/', views.crud_views.PaymentRuleDeleteView.as_view(), name='payment_rule_delete'),
    path('payment-rules/<int:rule_pk>/milestones/add/', views.crud_views.PaymentRuleMilestoneCreateView.as_view(), name='payment_rule_milestone_add'),
    path('payment-rule-milestones/<int:pk>/update/', views.crud_views.PaymentRuleMilestoneUpdateView.as_view(), name='payment_rule_milestone_update'),
    path('payment-rule-milestones/<int:pk>/delete/', views.crud_views.PaymentRuleMilestoneDeleteView.as_view(), name='payment_rule_milestone_delete'),

    # Approvals (issue #15)
    path('approvals/', views.crud_views.ApprovalListView.as_view(), name='approval_list'),
    path('approvals/<int:pk>/', views.crud_views.ApprovalDetailView.as_view(), name='approval_detail'),
    path('approvals/<int:pk>/approve/', views.crud_views.ApprovalApproveView.as_view(), name='approval_approve'),
    path('approvals/<int:pk>/reject/', views.crud_views.ApprovalRejectView.as_view(), name='approval_reject'),

    # Works (nested under project — issue #18)
    path('projects/<int:project_pk>/works/', views.crud_views.WorkListView.as_view(), name='work_list'),
    path('projects/<int:project_pk>/works/create/', views.crud_views.WorkCreateView.as_view(), name='work_create'),
    path('projects/<int:project_pk>/works/<int:pk>/', views.crud_views.WorkDetailView.as_view(), name='work_detail'),
    path('projects/<int:project_pk>/works/<int:pk>/edit/', views.crud_views.WorkUpdateView.as_view(), name='work_edit'),
    path('projects/<int:project_pk>/works/<int:pk>/delete/', views.crud_views.WorkDeleteView.as_view(), name='work_delete'),
    path('projects/<int:project_pk>/works/<int:pk>/apply-group/', views.crud_views.WorkStepApplyGroupView.as_view(), name='work_step_apply_group'),
    path('projects/<int:project_pk>/works/<int:work_pk>/steps/<int:pk>/edit/', views.crud_views.WorkStepUpdateView.as_view(), name='work_step_edit'),

    # Addresses & Works combined page
    path('projects/<int:pk>/addresses-works/', views.crud_views.ProjectAddressesWorksView.as_view(), name='project_addresses_works'),

    # Addresses (nested under project — issue #18)
    path('projects/<int:project_pk>/addresses/', views.crud_views.AddressListView.as_view(), name='address_list'),
    path('projects/<int:project_pk>/addresses/create/', views.crud_views.AddressCreateView.as_view(), name='address_create'),
    path('projects/<int:project_pk>/addresses/<int:pk>/', views.crud_views.AddressDetailView.as_view(), name='address_detail'),
    path('projects/<int:project_pk>/addresses/<int:pk>/edit/', views.crud_views.AddressUpdateView.as_view(), name='address_edit'),
    path('projects/<int:project_pk>/addresses/<int:pk>/delete/', views.crud_views.AddressDeleteView.as_view(), name='address_delete'),

    # Comments (generic — works for any entity via ContentType)
    path('comments/add/', views.comment_views.add_comment, name='comment_add'),
    path('comments/<int:pk>/edit/', views.comment_views.edit_comment, name='comment_edit'),
    path('comments/<int:pk>/delete/', views.comment_views.delete_comment, name='comment_delete'),

    # Notices (broadcast to multiple objects)
    path('notices/', views.notice_views.notice_list, name='notice_list'),
    path('notices/create/', views.notice_views.notice_create, name='notice_create'),
    path('notices/<int:pk>/delete/', views.notice_views.notice_delete, name='notice_delete'),
    path('notices/<int:pk>/remove-target/', views.notice_views.notice_remove_target, name='notice_remove_target'),

    # Construction Methods CRUD (Maintenance)
    path('construction-methods/', views.crud_views.ConstructionMethodListView.as_view(), name='construction_method_list'),
    path('construction-methods/create/', views.crud_views.ConstructionMethodCreateView.as_view(), name='construction_method_create'),
    path('construction-methods/<int:pk>/edit/', views.crud_views.ConstructionMethodUpdateView.as_view(), name='construction_method_edit'),
    path('construction-methods/<int:pk>/delete/', views.crud_views.ConstructionMethodDeleteView.as_view(), name='construction_method_delete'),

    # Forward RPF Agreements CRUD
    path('agreements/forward-rpf/', views.crud_views.ForwardRPFListView.as_view(), name='forward_rpf_list'),
    path('agreements/forward-rpf/create/', views.crud_views.ForwardRPFCreateView.as_view(), name='forward_rpf_create'),
    path('agreements/forward-rpf/<int:pk>/', views.crud_views.ForwardRPFDetailView.as_view(), name='forward_rpf_detail'),
    path('agreements/forward-rpf/<int:pk>/edit/', views.crud_views.ForwardRPFUpdateView.as_view(), name='forward_rpf_edit'),
    path('agreements/forward-rpf/<int:pk>/delete/', views.crud_views.ForwardRPFDeleteView.as_view(), name='forward_rpf_delete'),

    # Interim FRP Agreements CRUD
    path('agreements/interim-frp/', views.crud_views.InterimFRPListView.as_view(), name='interim_frp_list'),
    path('agreements/interim-frp/create/', views.crud_views.InterimFRPCreateView.as_view(), name='interim_frp_create'),
    path('agreements/interim-frp/<int:pk>/', views.crud_views.InterimFRPDetailView.as_view(), name='interim_frp_detail'),
    path('agreements/interim-frp/<int:pk>/edit/', views.crud_views.InterimFRPUpdateView.as_view(), name='interim_frp_edit'),
    path('agreements/interim-frp/<int:pk>/delete/', views.crud_views.InterimFRPDeleteView.as_view(), name='interim_frp_delete'),

    # Monthly Tracker (per-council)
    path('monthly-trackers/', views.tracker_views.MonthlyTrackerListView.as_view(), name='monthly_tracker_list'),
    path('monthly-trackers/council/<int:council_pk>/open/', views.tracker_views.MonthlyTrackerOpenOrCreateView.as_view(), name='monthly_tracker_open'),
    path('monthly-trackers/<int:pk>/', views.tracker_views.MonthlyTrackerDetailView.as_view(), name='monthly_tracker_detail'),
    path('monthly-trackers/<int:pk>/submit/', views.tracker_views.MonthlyTrackerSubmitView.as_view(), name='monthly_tracker_submit'),
    path('monthly-trackers/<int:pk>/review/', views.tracker_views.MonthlyTrackerReviewView.as_view(), name='monthly_tracker_review'),

    # Quarterly Report (per-council)
    path('quarterly-reports/', views.tracker_views.QuarterlyReportListView.as_view(), name='quarterly_report_global_list'),
    path('quarterly-reports/council/<int:council_pk>/open/', views.tracker_views.QuarterlyReportOpenOrCreateView.as_view(), name='quarterly_report_open'),
    path('quarterly-reports/<int:pk>/', views.tracker_views.QuarterlyReportDetailView.as_view(), name='quarterly_report_detail'),
    path('quarterly-reports/<int:pk>/submit/', views.tracker_views.QuarterlyReportSubmitView.as_view(), name='quarterly_report_submit'),
    path('quarterly-reports/<int:pk>/approve/', views.tracker_views.QuarterlyReportApproveView.as_view(), name='quarterly_report_approve'),

    # Tracker config (maintenance)
    path('maintenance/tracker-config/', views.tracker_views.CouncilTrackerConfigListView.as_view(), name='tracker_config_list'),
    path('maintenance/tracker-config/<int:council_pk>/edit/', views.tracker_views.CouncilTrackerConfigUpdateView.as_view(), name='tracker_config_edit'),

    # Electorate / Region lookup tables (Maintenance)
    path('maintenance/state-electorates/', views.crud_views.StateElectorateListView.as_view(), name='state_electorate_list'),
    path('maintenance/state-electorates/create/', views.crud_views.StateElectorateCreateView.as_view(), name='state_electorate_create'),
    path('maintenance/state-electorates/<int:pk>/edit/', views.crud_views.StateElectorateUpdateView.as_view(), name='state_electorate_edit'),
    path('maintenance/state-electorates/<int:pk>/delete/', views.crud_views.StateElectorateDeleteView.as_view(), name='state_electorate_delete'),

    path('maintenance/federal-electorates/', views.crud_views.FederalElectorateListView.as_view(), name='federal_electorate_list'),
    path('maintenance/federal-electorates/create/', views.crud_views.FederalElectorateCreateView.as_view(), name='federal_electorate_create'),
    path('maintenance/federal-electorates/<int:pk>/edit/', views.crud_views.FederalElectorateUpdateView.as_view(), name='federal_electorate_edit'),
    path('maintenance/federal-electorates/<int:pk>/delete/', views.crud_views.FederalElectorateDeleteView.as_view(), name='federal_electorate_delete'),

    path('maintenance/qhigi-regions/', views.crud_views.QhigiRegionListView.as_view(), name='qhigi_region_list'),
    path('maintenance/qhigi-regions/create/', views.crud_views.QhigiRegionCreateView.as_view(), name='qhigi_region_create'),
    path('maintenance/qhigi-regions/<int:pk>/edit/', views.crud_views.QhigiRegionUpdateView.as_view(), name='qhigi_region_edit'),
    path('maintenance/qhigi-regions/<int:pk>/delete/', views.crud_views.QhigiRegionDeleteView.as_view(), name='qhigi_region_delete'),

    # Stage Item Definitions (Maintenance)
    path('maintenance/stage-items/', views.stage_views.StageItemDefinitionListView.as_view(), name='stage_item_definition_list'),
    path('maintenance/stage-items/create/', views.stage_views.StageItemDefinitionCreateView.as_view(), name='stage_item_definition_create'),
    path('maintenance/stage-items/<int:pk>/edit/', views.stage_views.StageItemDefinitionUpdateView.as_view(), name='stage_item_definition_edit'),
    path('maintenance/stage-items/<int:pk>/delete/', views.stage_views.StageItemDefinitionDeleteView.as_view(), name='stage_item_definition_delete'),

    # Stage Item Groups (Maintenance)
    path('maintenance/stage-groups/', views.stage_views.StageItemGroupListView.as_view(), name='stage_item_group_list'),
    path('maintenance/stage-groups/create/', views.stage_views.StageItemGroupCreateView.as_view(), name='stage_item_group_create'),
    path('maintenance/stage-groups/<int:pk>/', views.stage_views.StageItemGroupDetailView.as_view(), name='stage_item_group_detail'),
    path('maintenance/stage-groups/<int:pk>/edit/', views.stage_views.StageItemGroupUpdateView.as_view(), name='stage_item_group_edit'),
    path('maintenance/stage-groups/<int:pk>/clone/', views.stage_views.StageItemGroupCloneView.as_view(), name='stage_item_group_clone'),
    path('maintenance/stage-groups/<int:pk>/delete/', views.stage_views.StageItemGroupDeleteView.as_view(), name='stage_item_group_delete'),
    path('maintenance/stage-groups/<int:group_pk>/items/add/', views.stage_views.StageItemGroupItemCreateView.as_view(), name='stage_item_group_item_create'),
    path('maintenance/stage-group-items/<int:pk>/edit/', views.stage_views.StageItemGroupItemUpdateView.as_view(), name='stage_item_group_item_edit'),
    path('maintenance/stage-group-items/<int:pk>/delete/', views.stage_views.StageItemGroupItemDeleteView.as_view(), name='stage_item_group_item_delete'),

    # Stage Report flow (per-FundingSchedule; legacy per-project URL redirects)
    path('funding-schedules/<int:fs_pk>/stage-reports/<str:stage_type>/open/', views.stage_views.StageReportOpenOrCreateView.as_view(), name='stage_report_open'),
    path('projects/<int:project_pk>/stage-reports/<str:stage_type>/open/', views.stage_views.LegacyProjectStageOpenRedirectView.as_view(), name='stage_report_open_legacy_project'),
    path('stage-reports/<int:pk>/', views.stage_views.StageReportGridView.as_view(), name='stage_report_grid'),
    path('stage-reports/<int:pk>/submit/', views.stage_views.StageReportSubmitView.as_view(), name='stage_report_submit'),
    path('stage-reports/<int:pk>/endorse/', views.stage_views.StageReportEndorseView.as_view(), name='stage_report_endorse'),
    path('stage-reports/<int:pk>/assess/', views.stage_views.StageReportAssessView.as_view(), name='stage_report_assess'),
    path('stage-reports/<int:pk>/approve/', views.stage_views.StageReportApproveView.as_view(), name='stage_report_approve'),
    path('stage-reports/<int:pk>/reject/', views.stage_views.StageReportRejectView.as_view(), name='stage_report_reject'),
    path('stage-reports/items/<int:item_pk>/attachments/add/', views.stage_views.StageReportAttachmentAddView.as_view(), name='stage_report_attachment_add'),
    path('stage-reports/attachments/<int:pk>/delete/', views.stage_views.StageReportAttachmentDeleteView.as_view(), name='stage_report_attachment_delete'),

    # Other existing views
    path('reports/', views.reports_views.reports_dashboard_view, name='reports_dashboard'),
    path('reports/monthly/', views.reports_views.monthly_report_council_select, name='monthly_report_select'),
    path('reports/monthly/<int:council_pk>/', views.reports_views.monthly_report_view, name='monthly_report'),
    path('reports/eom-reconciliation/', views.reports_views.eom_reconciliation_view, name='eom_reconciliation'),
    path('reports/eom-reconciliation/export.csv', views.reports_views.eom_reconciliation_export, name='eom_reconciliation_export'),
    path('reports/construction-creation-list/', views.reports_views.construction_creation_list_view, name='construction_creation_list'),
    path('reports/construction-creation-list/export.csv', views.reports_views.construction_creation_list_export, name='construction_creation_list_export'),
    path('land-infra/', views.land_infra_views.land_projects_list_view, name='land_projects_list'),
    path('documents/', views.documents_views.documents_list_view, name='documents_list'),
]
