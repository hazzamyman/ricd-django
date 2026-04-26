from django.urls import path
from . import views

app_name = 'funding'

urlpatterns = [
    path('schedule/create/<int:project_id>/', views.funding_schedule_create, name='funding_schedule_create'),
    path('schedule/create/land/<int:land_project_id>/', views.funding_schedule_create_land, name='funding_schedule_create_land'),
    path('schedule/<int:fs_id>/delete/', views.funding_schedule_delete, name='funding_schedule_delete'),
    path('approval/create/<int:project_id>/', views.funding_approval_create, name='funding_approval_create'),
    path('approval/<int:fa_id>/delete/', views.funding_approval_delete, name='funding_approval_delete'),
]
