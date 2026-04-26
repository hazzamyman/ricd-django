from django.contrib import admin
from .models import Defect


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'identified_date', 'rectified_date', 'defects_liability_expiry', 'warranty_expiry')
    search_fields = ('description', 'project__name')
    list_filter = ('project', 'identified_date')
    date_hierarchy = 'identified_date'
