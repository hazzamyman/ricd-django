from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('cashflow/', views.cashflow_view, name='dashboard_cashflow'),
    path('outputs/', views.aggregate_outputs_view, name='dashboard_outputs'),
]
