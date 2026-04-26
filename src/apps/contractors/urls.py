from django.urls import path
from . import views

app_name = 'contractors'

urlpatterns = [
    path('', views.contractor_list, name='contractor_list'),
    path('create/', views.contractor_create, name='contractor_create'),
]
