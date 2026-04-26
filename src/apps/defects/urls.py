from django.urls import path
from . import views

app_name = 'defects'

urlpatterns = [
    path('create/<int:project_id>/', views.defect_create, name='defect_create'),
    path('<int:defect_id>/delete/', views.defect_delete, name='defect_delete'),
]
