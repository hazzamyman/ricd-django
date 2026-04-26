from django.contrib import admin
from .models import VariationType, Variation, VariationItem


class VariationItemInline(admin.TabularInline):
    model = VariationItem
    extra = 1


@admin.register(VariationType)
class VariationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('is_active',)


@admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    list_display = ('id', 'funding_schedule', 'get_status_display', 'council_signed_date', 'department_executed_date', 'created_at')
    list_filter = ('status', 'council_signed_date', 'department_executed_date')
    search_fields = ('funding_schedule__project__name', 'description')
    inlines = [VariationItemInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('funding_schedule', 'funding_schedules', 'projects', 'variation_type', 'description')
        }),
        ('Dates', {
            'fields': ('council_signed_date', 'department_executed_date')
        }),
        ('Document', {
            'fields': ('document_link',)
        }),
        ('Status', {
            'fields': ('status', 'created_by')
        }),
    )
    readonly_fields = ('created_by', 'created_at', 'updated_at')


@admin.register(VariationItem)
class VariationItemAdmin(admin.ModelAdmin):
    list_display = ('variation', 'option', 'description')
    list_filter = ('option',)
    search_fields = ('variation__funding_schedule__project__name', 'description')
