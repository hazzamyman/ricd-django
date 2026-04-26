from django.urls import path
from . import views
from django.http import JsonResponse

app_name = 'variations'

urlpatterns = [
    path('', views.variations_list, name='variations_list'),
    path('create/', views.variation_create, name='variation_create'),
    path('<int:variation_id>/', views.variation_detail, name='variation_detail'),
    path('<int:variation_id>/status/', views.variation_update_status, name='variation_update_status'),
    path('<int:variation_id>/status/<str:new_status>/', views.variation_update_status, name='variation_update_status'),
    path('<int:variation_id>/item/', views.variation_item_create, name='variation_item_create'),
    path('<int:variation_id>/projects/', views.variation_projects, name='variation_projects'),
    path('<int:variation_id>/add-funding-change/', views.add_funding_change, name='add_funding_change'),
    path('funding-change/<int:change_id>/delete/', views.funding_change_delete, name='funding_change_delete'),
    path('land-change/<int:change_id>/delete/', views.land_change_delete, name='land_change_delete'),
    path('scope-change/<int:change_id>/delete/', views.scope_change_delete, name='scope_change_delete'),
    path('date-change/<int:change_id>/delete/', views.date_change_delete, name='date_change_delete'),
    path('by-council/', views.variations_by_council, name='variations_by_council'),
    path('by-project/', views.variations_by_project, name='variations_by_project'),
    
    # API endpoints
    path('api/active-projects/', views.api_active_projects, name='api_active_projects'),
    path('api/project-payments/', views.api_project_payments, name='api_project_payments'),
    path('api/project-addresses/', views.api_project_addresses, name='api_project_addresses'),
    path('api/project-works/', views.api_project_works, name='api_project_works'),
    path('api/funding-details/', views.api_funding_details, name='api_funding_details'),
]
