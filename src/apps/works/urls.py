from django.urls import path
from . import views

app_name = 'works'

urlpatterns = [
    path('create/<int:project_id>/', views.work_create, name='work_create'),
    path('create/land/<int:land_project_id>/', views.work_create_land, name='work_create_land'),
    path('<int:work_id>/delete/', views.work_delete, name='work_delete'),
]
