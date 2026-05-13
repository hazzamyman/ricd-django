from django.urls import path
from . import views

app_name = 'ui'

urlpatterns = [
    # Dashboard views
    path('dashboard/', views.dashboard_views.dashboard_view, name='dashboard'),
    path('cashflow/', views.dashboard_views.cashflow_view, name='cashflow'),
    path('aggregate/', views.dashboard_views.aggregate_outputs_view, name='aggregate_outputs'),

    # Maintenance views
    # path('maintenance/', views.maintenance_views.maintenance_list, name='maintenance_list'),

    # Planning views
    # path('planning/', views.planning_views.planning_list, name='planning_list'),
]
