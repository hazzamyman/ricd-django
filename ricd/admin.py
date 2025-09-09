from django.contrib import admin
from django.contrib.admin import TabularInline

# Register your models here.
from .models import Council, Program, Project, Address, Work, FundingSchedule, Instalment, MonthlyTracker, QuarterlyReport, Stage1Report, Stage2Report, WorkProgress, Defect, Contact, StageReport, WorkStep, DefaultWorkStep, ReportAttachment, StepTask, StepTaskCompletion, WorkSchedule, PracticalCompletion, FundingApproval, MonthlyReport, CouncilQuarterlyReport

class AddressInline(TabularInline):
    model = Address
    extra = 0

class WorkInline(TabularInline):
    model = Work
    extra = 0

class WorkStepInline(TabularInline):
    model = WorkStep
    extra = 0

class DefectAdmin(admin.ModelAdmin):
    readonly_fields = ('expiry_date',)

class WorkAdmin(admin.ModelAdmin):
    inlines = [WorkStepInline]
    readonly_fields = ('is_within_defect_liability_period',)
    list_display = ('get_work_type', 'get_project', 'get_address', 'get_council', 'get_funding_agreement', 'get_progress_percentage', 'get_budget_vs_spent', 'get_late_overdue_status', 'start_date', 'end_date')
    list_filter = ('work_type_id__name', 'address__project__council', 'address__project__funding_schedule', 'start_date')
    search_fields = ('address__project__name', 'address__project__council__name', 'address__street', 'address__suburb')
    ordering = ('start_date',)

    def get_work_type(self, obj):
        return obj.work_type_id.name
    get_work_type.short_description = 'Work Type'

    def get_project(self, obj):
        return obj.project.name
    get_project.short_description = 'Project'
    get_project.admin_order_field = 'address__project__name'

    def get_address(self, obj):
        return str(obj.address)
    get_address.short_description = 'Address'

    def get_council(self, obj):
        return obj.project.council.name
    get_council.short_description = 'Council'
    get_council.admin_order_field = 'address__project__council__name'

    def get_funding_agreement(self, obj):
        return obj.project.funding_agreement or "No Funding Agreement"
    get_funding_agreement.short_description = 'Funding Agreement'

    def get_progress_percentage(self, obj):
        latest_report = obj.quarterly_reports.order_by('-submission_date').first()
        if latest_report and latest_report.percentage_works_completed:
            return f"{latest_report.percentage_works_completed}%"
        return "Not Reported"
    get_progress_percentage.short_description = 'Progress %'

    def get_budget_vs_spent(self, obj):
        budget = obj.estimated_cost or 0
        spent = obj.actual_cost or 0
        if budget:
            percentage_spent = (spent / budget) * 100 if spent else 0
            return ".2f"
        return f"{spent} spent (No budget)"
    get_budget_vs_spent.short_description = 'Budget vs Spent'

    def get_late_overdue_status(self, obj):
        project = obj.project
        if project.is_overdue:
            return "Overdue"
        elif project.is_late:
            return "Late"
        else:
            return "On Time"
    get_late_overdue_status.short_description = 'Status'

class ProjectAdmin(admin.ModelAdmin):
    inlines = [AddressInline]
    readonly_fields = ('state', 'is_late', 'is_overdue', 'is_on_time')

admin.site.register(Council)
admin.site.register(Program)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Address)
admin.site.register(Work, WorkAdmin)
class InstalmentInline(TabularInline):
    model = Instalment
    extra = 0

class FundingScheduleAdmin(admin.ModelAdmin):
    inlines = [InstalmentInline]

admin.site.register(FundingSchedule, FundingScheduleAdmin)
admin.site.register(Instalment)
admin.site.register(MonthlyTracker)
admin.site.register(QuarterlyReport)
admin.site.register(Stage1Report)
admin.site.register(Stage2Report)
admin.site.register(WorkProgress)
admin.site.register(Defect, DefectAdmin)
admin.site.register(Contact)
admin.site.register(StageReport)
admin.site.register(DefaultWorkStep)
admin.site.register(ReportAttachment)
admin.site.register(StepTask)
admin.site.register(StepTaskCompletion)
admin.site.register(WorkSchedule)
admin.site.register(PracticalCompletion)

class FundingApprovalAdmin(admin.ModelAdmin):
    list_display = ('mincor_reference', 'amount', 'approved_date')


class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('council', 'period', 'ricd_status')


class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ('council', 'period', 'ricd_status')


admin.site.register(FundingApproval, FundingApprovalAdmin)
admin.site.register(MonthlyReport, MonthlyReportAdmin)
admin.site.register(CouncilQuarterlyReport, QuarterlyReportAdmin)