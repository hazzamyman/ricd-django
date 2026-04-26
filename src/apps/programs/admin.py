from django.contrib import admin
from .models import Program, ProgramBudget


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'funding_source', 'budget', 'gl_code', 'is_active')
    list_filter = ('funding_source', 'is_active')
    search_fields = ('name', 'funding_source')
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'funding_source', 'funding_source_other', 'description')
        }),
        ('Budget', {
            'fields': ('budget', 'gl_code', 'business_case_reference')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ProgramBudget)
class ProgramBudgetAdmin(admin.ModelAdmin):
    list_display = ('program', 'financial_year', 'allocated', 'spent', 'remaining', 'percent_used')
    list_filter = ('financial_year', 'program')
    search_fields = ('program__name',)
    ordering = ('-financial_year',)