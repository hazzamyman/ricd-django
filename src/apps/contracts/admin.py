from django.contrib import admin
from .models import Contract, ContractMeeting


class ContractMeetingInline(admin.TabularInline):
    model = ContractMeeting
    extra = 1


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'execution_date', 'start_date', 'end_date')
    search_fields = ('title', 'project__name')
    list_filter = ('execution_date',)
    inlines = [ContractMeetingInline]


@admin.register(ContractMeeting)
class ContractMeetingAdmin(admin.ModelAdmin):
    list_display = ('contract', 'meeting_type', 'meeting_date', 'location')
    search_fields = ('contract__project__name', 'notes')
    list_filter = ('meeting_type', 'meeting_date')
    date_hierarchy = 'meeting_date'
