from django.urls import path
from . import views

app_name = 'addresses'

urlpatterns = [
    path('create/<int:project_id>/', views.address_create, name='address_create'),
    path('<int:address_id>/delete/', views.address_delete, name='address_delete'),
]
