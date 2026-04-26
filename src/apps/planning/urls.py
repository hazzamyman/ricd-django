from django.urls import path
from . import views

app_name = 'planning'

urlpatterns = [
    path('', views.planning_list, name='planning_list'),
]
