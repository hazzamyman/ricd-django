from django.contrib import admin
from .models import FundingSchedule, ProjectStateLog


class FundingScheduleInline(admin.TabularInline):
    model = FundingSchedule
    extra = 1


@admin.register(FundingSchedule)
class FundingScheduleAdmin(admin.ModelAdmin):
    list_display = ('project', 'amount', 'contingency', 'total_funding', 'payment_split', 'created_at')
    search_fields = ('project__name',)
    list_filter = ('project', 'payment_split')
    readonly_fields = ('total_funding',)


@admin.register(ProjectStateLog)
class ProjectStateLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'previous_state', 'new_state', 'changed_by', 'change_date')
    search_fields = ('project__name',)
    list_filter = ('project', 'change_date')
    date_hierarchy = 'change_date'
    readonly_fields = ('previous_state', 'new_state', 'changed_by', 'change_date')
