from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = 'portal'

urlpatterns = [
    # Root URL redirect to login
    path('', RedirectView.as_view(url='accounts/login/'), name='root_redirect'),
    
    # Dashboard URLs
    path('ricd/', views.RICDDashboardView.as_view(), name='ricd_dashboard'),
    path('council/', views.CouncilDashboardView.as_view(), name='council_dashboard'),

    # Project detail
    path('project/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('council/projects/<int:pk>/detail/', views.CouncilProjectDetailView.as_view(), name='council_project_detail'),

    # Report submission URLs
    path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    path('reports/quarterly/', views.QuarterlyReportView.as_view(), name='quarterly_report'),
    path('reports/stage1/', views.Stage1ReportView.as_view(), name='stage1_report'),
    path('reports/stage2/', views.Stage2ReportView.as_view(), name='stage2_report'),

    # Council CRUD URLs
    path('councils/', views.CouncilListView.as_view(), name='council_list'),
    path('councils/create/', views.CouncilCreateView.as_view(), name='council_create'),
    path('councils/<int:pk>/', views.CouncilDetailView.as_view(), name='council_detail'),
    path('councils/<int:pk>/update/', views.CouncilUpdateView.as_view(), name='council_update'),
    path('councils/<int:pk>/delete/', views.CouncilDeleteView.as_view(), name='council_delete'),
    path('councils/<int:council_pk>/add-user/', views.CouncilUserCreateView.as_view(), name='council_add_user'),
    path('councils/users/<int:pk>/update/', views.CouncilUserUpdateView.as_view(), name='council_user_update'),
    path('councils/users/<int:pk>/delete/', views.CouncilUserDeleteView.as_view(), name='council_user_delete'),

    # Program CRUD URLs
    path('programs/', views.ProgramListView.as_view(), name='program_list'),
    path('programs/create/', views.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/<int:pk>/update/', views.ProgramUpdateView.as_view(), name='program_update'),
    path('programs/<int:pk>/delete/', views.ProgramDeleteView.as_view(), name='program_delete'),

    # Project CRUD URLs
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/detail/', views.ProjectDetailView.as_view(), name='project_detail'),  # Updated to match existing
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/update-state/', views.ProjectStateUpdateView.as_view(), name='project_update_state'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Address and Work CRUD URLs
    path('works/', views.WorkListView.as_view(), name='work_list'),
    path('projects/<int:project_pk>/addresses/create/', views.AddressCreateView.as_view(), name='address_create'),
    path('projects/<int:project_pk>/addresses/<int:pk>/update/', views.AddressUpdateView.as_view(), name='address_update'),
    path('projects/<int:project_pk>/addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
    path('projects/<int:project_pk>/works/create/', views.WorkCreateView.as_view(), name='work_create'),
    path('projects/<int:project_pk>/works/<int:pk>/update/', views.WorkUpdateView.as_view(), name='work_update'),
    path('projects/<int:project_pk>/works/<int:pk>/delete/', views.WorkDeleteView.as_view(), name='work_delete'),
    
    # Work Step Management (for ordering stages/tasks)
    path('works/<int:work_pk>/steps/', views.WorkStepListView.as_view(), name='work_step_list'),
    path('works/<int:work_pk>/steps/reorder/', views.WorkStepReorderView.as_view(), name='work_step_reorder'),
    
    # Analytics Dashboard
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('analytics/export/custom/', views.CustomExportView.as_view(), name='custom_export'),
    path('analytics/export/addresses-works/', views.AddressWorkExportView.as_view(), name='export_addresses_works'),

    # Help Pages
    path('help/ricd/', views.RICDSHelpView.as_view(), name='help_ricd'),
    path('help/council/', views.CouncilHelpView.as_view(), name='help_council'),

    # Funding Related URLs
    path('projects/<int:pk>/add-to-funding-schedule/', views.AddProjectToFundingScheduleView.as_view(), name='add_project_to_funding_schedule'),

    # Funding Approval URLs
    path('funding-approvals/', views.FundingApprovalListView.as_view(), name='funding_approval_list'),
    path('funding-approvals/create/', views.FundingApprovalCreateView.as_view(), name='funding_approval_create'),
    path('funding-approvals/<int:pk>/', views.FundingApprovalDetailView.as_view(), name='funding_approval_detail'),
    path('funding-approvals/<int:pk>/update/', views.FundingApprovalUpdateView.as_view(), name='funding_approval_update'),

    # Work Type Management URLs
    path('work-types/', views.WorkTypeListView.as_view(), name='work_type_list'),
    path('work-types/create/', views.WorkTypeCreateView.as_view(), name='work_type_create'),
    path('work-types/<int:pk>/update/', views.WorkTypeUpdateView.as_view(), name='work_type_update'),
    path('work-types/<int:pk>/delete/', views.WorkTypeDeleteView.as_view(), name='work_type_delete'),

    # Output Type Management URLs
    path('output-types/', views.OutputTypeListView.as_view(), name='output_type_list'),
    path('output-types/create/', views.OutputTypeCreateView.as_view(), name='output_type_create'),
    path('output-types/<int:pk>/update/', views.OutputTypeUpdateView.as_view(), name='output_type_update'),
    path('output-types/<int:pk>/delete/', views.OutputTypeDeleteView.as_view(), name='output_type_delete'),
    
    # Construction Method Management URLs
    path('maintenance/construction-methods/', views.ConstructionMethodListView.as_view(), name='construction_method_list'),
    path('maintenance/construction-methods/create/', views.ConstructionMethodCreateView.as_view(), name='construction_method_create'),
    path('maintenance/construction-methods/<int:pk>/update/', views.ConstructionMethodUpdateView.as_view(), name='construction_method_update'),
    path('maintenance/construction-methods/<int:pk>/delete/', views.ConstructionMethodDeleteView.as_view(), name='construction_method_delete'),
    
    # Work Type/Output Type Configuration
    path('maintenance/work-output-config/', views.WorkOutputTypeConfigView.as_view(), name='work_output_type_config'),

    # Agreement URLs
    path('agreements/remote-capital/', views.RemoteCapitalProgramListView.as_view(), name='remote_capital_program_list'),
    path('agreements/remote-capital/create/', views.RemoteCapitalProgramCreateView.as_view(), name='remote_capital_program_create'),
    path('agreements/remote-capital/<int:pk>/', views.RemoteCapitalProgramDetailView.as_view(), name='remote_capital_program_detail'),
    path('agreements/remote-capital/<int:pk>/update/', views.RemoteCapitalProgramUpdateView.as_view(), name='remote_capital_program_update'),
    path('agreements/remote-capital/<int:pk>/delete/', views.RemoteCapitalProgramDeleteView.as_view(), name='remote_capital_program_delete'),

    path('agreements/forward-rpf/', views.ForwardRPFListView.as_view(), name='forward_rpf_list'),
    path('agreements/forward-rpf/create/', views.ForwardRFPCreateView.as_view(), name='forward_rpf_create'),
    path('agreements/forward-rpf/<int:pk>/', views.ForwardRPFDetailView.as_view(), name='forward_rpf_detail'),
    path('agreements/forward-rpf/<int:pk>/update/', views.ForwardRPFUpdateView.as_view(), name='forward_rpf_update'),
    path('agreements/forward-rpf/<int:pk>/delete/', views.ForwardRPFDeleteView.as_view(), name='forward_rpf_delete'),

    path('agreements/interim-frp/', views.InterimFRPFListView.as_view(), name='interim_frp_list'),
    path('agreements/interim-frp/create/', views.InterimFRPFCreateView.as_view(), name='interim_frp_create'),
    path('agreements/interim-frp/<int:pk>/', views.InterimFRPFDetailView.as_view(), name='interim_frp_detail'),
    path('agreements/interim-frp/<int:pk>/update/', views.InterimFRPFUpdateView.as_view(), name='interim_frp_update'),
    path('agreements/interim-frp/<int:pk>/delete/', views.InterimFRPFDeleteView.as_view(), name='interim_frp_delete'),

    # User and Officer Management URLs
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),

    path('officers/', views.OfficerListView.as_view(), name='officer_list'),
    path('officers/create/', views.OfficerCreateView.as_view(), name='officer_create'),
    path('officers/<int:pk>/', views.OfficerDetailView.as_view(), name='officer_detail'),
    path('officers/<int:pk>/update/', views.OfficerUpdateView.as_view(), name='officer_update'),

    # Defect URLs
    path('defects/', views.DefectListView.as_view(), name='defect_list'),
    path('defects/create/', views.DefectCreateView.as_view(), name='defect_create'),
    path('defects/<int:pk>/', views.DefectDetailView.as_view(), name='defect_detail'),
    path('defects/<int:pk>/update/', views.DefectUpdateView.as_view(), name='defect_update'),
    path('defects/<int:pk>/delete/', views.DefectDeleteView.as_view(), name='defect_delete'),
    path('defects/<int:pk>/rectify/', views.DefectRectifyView.as_view(), name='defect_rectify'),

    # Defect creation URL for specific works
    path('works/<int:work_pk>/defects/create/', views.DefectCreateView.as_view(), name='work_defect_create'),

    path('projects/<int:pk>/assign-officers/', views.OfficerAssignmentView.as_view(), name='officer_assignment'),

    # Move addresses and works functionality
    path('projects/<int:pk>/move-addresses-works/', views.MoveAddressesWorksView.as_view(), name='move_addresses_works'),
]
