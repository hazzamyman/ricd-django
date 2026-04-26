from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # Dashboard
    path('', views.maintenance_dashboard, name='dashboard'),
    
    # Councils
    path('councils/', views.council_list, name='council_list'),
    path('councils/create/', views.council_create, name='council_create'),
    path('councils/<int:pk>/edit/', views.council_edit, name='council_edit'),
    path('councils/<int:pk>/delete/', views.council_delete, name='council_delete'),
    
    # Council Contacts
    path('council-contacts/', views.councilcontact_list, name='councilcontact_list'),
    path('council-contacts/create/', views.councilcontact_create, name='councilcontact_create'),
    path('council-contacts/<int:pk>/edit/', views.councilcontact_edit, name='councilcontact_edit'),
    
    # Programs
    path('programs/', views.program_list, name='program_list'),
    path('programs/create/', views.program_create, name='program_create'),
    path('programs/<int:pk>/edit/', views.program_edit, name='program_edit'),
    path('programs/<int:pk>/delete/', views.program_delete, name='program_delete'),
    
    # Program Budgets
    path('program-budgets/', views.programbudget_list, name='programbudget_list'),
    path('program-budgets/create/', views.programbudget_create, name='programbudget_create'),
    path('program-budgets/<int:pk>/edit/', views.programbudget_edit, name='programbudget_edit'),
    path('program-budgets/<int:pk>/delete/', views.programbudget_delete, name='programbudget_delete'),
    
    # Work Types
    path('work-types/', views.worktype_list, name='worktype_list'),
    path('work-types/create/', views.worktype_create, name='worktype_create'),
    path('work-types/<int:pk>/edit/', views.worktype_edit, name='worktype_edit'),
    path('work-types/<int:pk>/delete/', views.worktype_delete, name='worktype_delete'),
    
    # Work Step Templates
    path('work-step-templates/', views.worksteptemplate_list, name='worksteptemplate_list'),
    path('work-step-templates/create/', views.worksteptemplate_create, name='worksteptemplate_create'),
    path('work-step-templates/<int:pk>/edit/', views.worksteptemplate_edit, name='worksteptemplate_edit'),
    path('work-step-templates/<int:pk>/delete/', views.worksteptemplate_delete, name='worksteptemplate_delete'),
    
    # Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/create/', views.address_create, name='address_create'),
    path('addresses/<int:pk>/edit/', views.address_edit, name='address_edit'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    
    # Works
    path('works/', views.work_list, name='work_list'),
    path('works/create/', views.work_create, name='work_create'),
    path('works/<int:pk>/edit/', views.work_edit, name='work_edit'),
    path('works/<int:pk>/delete/', views.work_delete, name='work_delete'),
    
    # Funding Approvals
    path('funding-approvals/', views.fundingapproval_list, name='fundingapproval_list'),
    path('funding-approvals/create/', views.fundingapproval_create, name='fundingapproval_create'),
    path('funding-approvals/<int:pk>/edit/', views.fundingapproval_edit, name='fundingapproval_edit'),
    
    # Delegations
    path('delegations/', views.delegation_list, name='delegation_list'),
    path('delegations/create/', views.delegation_create, name='delegation_create'),
    path('delegations/<int:pk>/edit/', views.delegation_edit, name='delegation_edit'),
    path('delegations/<int:pk>/delete/', views.delegation_delete, name='delegation_delete'),
    
    # Funding Schedules
    path('funding-schedules/', views.fundingschedule_list, name='fundingschedule_list'),
    path('funding-schedules/create/', views.fundingschedule_create, name='fundingschedule_create'),
    path('funding-schedules/<int:pk>/edit/', views.fundingschedule_edit, name='fundingschedule_edit'),
    path('funding-schedules/<int:pk>/delete/', views.fundingschedule_delete, name='fundingschedule_delete'),
    
    # Contractors
    path('contractors/', views.contractor_list, name='contractor_list'),
    path('contractors/create/', views.contractor_create, name='contractor_create'),
    path('contractors/<int:pk>/edit/', views.contractor_edit, name='contractor_edit'),
    path('contractors/<int:pk>/delete/', views.contractor_delete, name='contractor_delete'),
    
    # Document Types
    path('document-types/', views.documenttype_list, name='documenttype_list'),
    path('document-types/create/', views.documenttype_create, name='documenttype_create'),
    path('document-types/<int:pk>/edit/', views.documenttype_edit, name='documenttype_edit'),
    path('document-types/<int:pk>/delete/', views.documenttype_delete, name='documenttype_delete'),
    
    # Notional Costs
    path('notional-costs/', views.notionalcost_list, name='notionalcost_list'),
    path('notional-costs/create/', views.notionalcost_create, name='notionalcost_create'),
    path('notional-costs/<int:pk>/edit/', views.notionalcost_edit, name='notionalcost_edit'),
    path('notional-costs/bulk-update/', views.notionalcost_bulk_update, name='notionalcost_bulk_update'),
]
