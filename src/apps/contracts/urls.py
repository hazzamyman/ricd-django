from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('', views.contract_list, name='contract_list'),
    path('create/', views.contract_create, name='contract_create'),
    path('<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('<int:contract_id>/edit/', views.contract_edit, name='contract_edit'),
    path('<int:contract_id>/delete/', views.contract_delete, name='contract_delete'),
    path('<int:contract_id>/meeting/create/', views.contract_meeting_create, name='contract_meeting_create'),
]