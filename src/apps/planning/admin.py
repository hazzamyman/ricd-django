from django.contrib import admin
from .models import StrategicPlan


@admin.register(StrategicPlan)
class StrategicPlanAdmin(admin.ModelAdmin):
    list_display = ('council', 'year', 'housing_application_count', 'overcrowded_households', 'additional_bedrooms_needed')
    list_filter = ('year', 'council')
    search_fields = ('council__name',)
    ordering = ('-year', 'council')
