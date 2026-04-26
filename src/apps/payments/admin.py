from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('project', 'payment_type', 'payment_split', 'amount', 'status', 'release_date', 'reference')
    search_fields = ('project__name', 'reference')
    list_filter = ('status', 'payment_type', 'payment_split')
    date_hierarchy = 'release_date'
    readonly_fields = ('created_at', 'updated_at')
