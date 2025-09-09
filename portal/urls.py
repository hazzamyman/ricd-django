from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboard URLs
    path('ricd/', views.RICDDashboardView.as_view(), name='ricd_dashboard'),
    path('council/', views.CouncilDashboardView.as_view(), name='council_dashboard'),

    # Project detail
    path('project/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),

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
    path('projects/<int:project_pk>/addresses/create/', views.AddressCreateView.as_view(), name='address_create'),
    path('projects/<int:project_pk>/addresses/<int:pk>/update/', views.AddressUpdateView.as_view(), name='address_update'),
    path('projects/<int:project_pk>/addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
    path('projects/<int:project_pk>/works/create/', views.WorkCreateView.as_view(), name='work_create'),
    path('projects/<int:project_pk>/works/<int:pk>/update/', views.WorkUpdateView.as_view(), name='work_update'),
    path('projects/<int:project_pk>/works/<int:pk>/delete/', views.WorkDeleteView.as_view(), name='work_delete'),

    # Analytics Dashboard
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),

    # Funding Related URLs
    path('projects/<int:pk>/add-to-funding-schedule/', views.AddProjectToFundingScheduleView.as_view(), name='add_project_to_funding_schedule'),

    # Funding Approval URLs
    path('funding-approvals/', views.FundingApprovalListView.as_view(), name='funding_approval_list'),
    path('funding-approvals/create/', views.FundingApprovalCreateView.as_view(), name='funding_approval_create'),
    path('funding-approvals/<int:pk>/', views.FundingApprovalDetailView.as_view(), name='funding_approval_detail'),
    path('funding-approvals/<int:pk>/update/', views.FundingApprovalUpdateView.as_view(), name='funding_approval_update'),
]
