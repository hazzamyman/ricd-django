from django.urls import path
from . import views

app_name = 'councils'

urlpatterns = [
    path('', views.council_list, name='council_list'),
    path('create/', views.council_create, name='council_create'),
]
