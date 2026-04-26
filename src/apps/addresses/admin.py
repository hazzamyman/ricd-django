from django.contrib import admin
from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'lot', 'plan', 'project', 'created_at')
    search_fields = ('street', 'lot', 'plan', 'project__name')
    list_filter = ('project',)
