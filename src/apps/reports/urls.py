from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Monthly Tracker
    path('monthly/', views.monthly_tracker_list, name='monthly_tracker_list'),
    path('monthly/create/', views.monthly_tracker_create, name='monthly_tracker_create'),
    path('monthly/<int:tracker_id>/', views.monthly_tracker_detail, name='monthly_tracker_detail'),
    path('monthly/<int:tracker_id>/submit/', views.monthly_tracker_submit, name='monthly_tracker_submit'),
    path('monthly/entry/<int:entry_id>/', views.monthly_tracker_update_entry, name='monthly_tracker_update_entry'),
    
    # Quarterly Reports
    path('quarterly/', views.quarterly_report_list, name='quarterly_report_list'),
    path('quarterly/create/', views.quarterly_report_create, name='quarterly_report_create'),
    path('quarterly/<int:report_id>/', views.quarterly_report_detail, name='quarterly_report_detail'),
    path('quarterly/<int:report_id>/upload/', views.quarterly_report_upload_attachment, name='quarterly_report_upload'),
    
    # Stage Reports
    path('stage/', views.stage_report_list, name='stage_report_list'),
    path('stage/create/', views.stage_report_create, name='stage_report_create'),
    path('stage/<int:report_id>/', views.stage_report_detail, name='stage_report_detail'),
    path('stage/<int:report_id>/submit/', views.stage_report_submit, name='stage_report_submit'),
    path('stage/<int:report_id>/endorse/', views.stage_report_endorse, name='stage_report_endorse'),
    path('stage/<int:report_id>/assess/', views.stage_report_assess, name='stage_report_assess'),
    path('stage/<int:report_id>/approve/', views.stage_report_approve, name='stage_report_approve'),
    path('stage/item/<int:item_id>/', views.stage_report_update_item, name='stage_report_update_item'),
    path('stage/item/<int:item_id>/upload/', views.stage_report_upload_attachment, name='stage_report_upload_attachment'),
    
    # Maintenance
    path('maintenance/monthly/groups/', views.monthly_item_groups, name='monthly_item_groups'),
    path('maintenance/monthly/groups/create/', views.monthly_item_group_create, name='monthly_item_group_create'),
    path('maintenance/monthly/groups/<int:group_id>/edit/', views.monthly_item_group_edit, name='monthly_item_group_edit'),
    path('maintenance/monthly/groups/<int:group_id>/delete/', views.monthly_item_group_delete, name='monthly_item_group_delete'),
    
    path('maintenance/quarterly/groups/', views.quarterly_item_groups, name='quarterly_item_groups'),
    path('maintenance/quarterly/groups/create/', views.quarterly_item_group_create, name='quarterly_item_group_create'),
    path('maintenance/quarterly/groups/<int:group_id>/edit/', views.quarterly_item_group_edit, name='quarterly_item_group_edit'),
    
    path('maintenance/stage/templates/', views.stage_templates, name='stage_templates'),
]
