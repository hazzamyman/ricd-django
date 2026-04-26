from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('create/', views.payment_create, name='payment_create'),
    path('<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('<int:payment_id>/edit/', views.payment_edit, name='payment_edit'),
    path('<int:payment_id>/delete/', views.payment_delete, name='payment_delete'),
    path('<int:payment_id>/recommend/', views.payment_recommend, name='payment_recommend'),
    path('<int:payment_id>/approve/', views.payment_approve, name='payment_approve'),
    path('<int:payment_id>/release/', views.payment_release, name='payment_release'),
    path('<int:payment_id>/reject/', views.payment_reject, name='payment_reject'),
    path('<int:payment_id>/add-document/', views.payment_add_document, name='payment_add_document'),
]