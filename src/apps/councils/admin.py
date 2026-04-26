from django.contrib import admin
from .models import Council, CouncilContact

@admin.register(Council)
class CouncilAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'is_registered_housing_provider', 'created_at')
    search_fields = ('name', 'region')

@admin.register(CouncilContact)
class CouncilContactAdmin(admin.ModelAdmin):
    list_display = ('council', 'role', 'name', 'email')
    search_fields = ('name', 'role')