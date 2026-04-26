from django.contrib import admin
from .models import Stage, WorkStep


class WorkStepInline(admin.TabularInline):
    model = WorkStep
    extra = 1


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ('project', 'stage_name', 'start_date', 'end_date', 'status')
    search_fields = ('project__name', 'stage_name')
    list_filter = ('project', 'stage_name', 'status')


@admin.register(WorkStep)
class WorkStepAdmin(admin.ModelAdmin):
    list_display = ('work', 'step_name', 'expected_duration_days', 'expected_cost_percentage', 'actual_start_date', 'actual_end_date', 'completed')
    search_fields = ('work__work_type', 'step_name')
    list_filter = ('completed',)
