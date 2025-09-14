from django.urls import path, include
from . import views

app_name = 'ricd'

urlpatterns = [
    path('portal/', include('portal.urls')),
    path('council/<int:council_id>/monthly/<str:period>/', views.monthly_report_form, name='monthly_report_form'),
    path('council/<int:council_id>/quarterly/<str:period>/', views.quarterly_report_form, name='quarterly_report_form'),
    path('ricd/review/<int:report_id>/', views.ricd_review_report, name='ricd_review_report'),
]