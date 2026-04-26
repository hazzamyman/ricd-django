from django.contrib import admin
from .models import Project
from apps.works.models import Work


class WorkInline(admin.TabularInline):
    model = Work
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'council', 'program', 'state', 'status_flag', 'start_date', 'completion_date', 'warranty_end_date')
    list_filter = ('state', 'status_flag')
    search_fields = ('name',)
    inlines = [WorkInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'council', 'program', 'funding_schedule', 'financial_year')
        }),
        ('Dates', {
            'fields': ('start_date', 'stage1_target_date', 'stage2_target_date', 'stage1_sunset_date', 'stage2_sunset_date', 'completion_date')
        }),
        ('Status', {
            'fields': ('state', 'status_flag')
        }),
        ('Post-Completion', {
            'fields': ('warranty_end_date', 'handover_checklist_link')
        }),
    )