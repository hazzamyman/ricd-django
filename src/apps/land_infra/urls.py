from django.urls import path
from . import views

app_name = 'land_infra'

urlpatterns = [
    path('land-projects/', views.land_project_list, name='land_project_list'),
    path('land-projects/create/', views.land_project_create, name='land_project_create'),
    path('land-projects/<int:project_id>/', views.land_project_detail, name='land_project_detail'),
    path('land-projects/<int:project_id>/update/', views.land_project_edit, name='land_project_edit'),
    path('land-projects/<int:project_id>/delete/', views.land_project_delete, name='land_project_delete'),
    path('land-tenures/', views.land_tenure_list, name='land_tenure_list'),
    path('land-tenures/create/', views.land_tenure_create, name='land_tenure_create'),
    path('land-tenures/<int:tenure_id>/', views.land_tenure_detail, name='land_tenure_detail'),
    path('land-tenures/<int:tenure_id>/update/', views.land_tenure_edit, name='land_tenure_edit'),
    path('land-tenures/<int:tenure_id>/delete/', views.land_tenure_delete, name='land_tenure_delete'),
    path('development-applications/', views.development_application_list, name='development_application_list'),
    path('development-applications/create/', views.development_application_create, name='development_application_create'),
    path('development-applications/<int:application_id>/', views.development_application_detail, name='development_application_detail'),
    path('development-applications/<int:application_id>/update/', views.development_application_edit, name='development_application_edit'),
    path('development-applications/<int:application_id>/delete/', views.development_application_delete, name='development_application_delete'),
]