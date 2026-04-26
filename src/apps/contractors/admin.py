from django.contrib import admin
from .models import Contractor


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'council', 'trade_type', 'contact_name', 'licence_expiry', 'is_active')
    list_filter = ('trade_type', 'council', 'is_active')
    search_fields = ('company_name', 'contact_name', 'council__name')
    ordering = ('council', 'company_name')
    list_editable = ('is_active',)
