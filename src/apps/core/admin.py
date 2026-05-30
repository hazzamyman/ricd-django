"""
Admin registrations for the core domain models.

AuditLog and WorkflowAction are read-only (no add/change/delete) to preserve
their integrity as the system audit trail.
"""
from django.contrib import admin

from apps.core.models import (
    # Council & Program
    Council, CouncilContact, Program, ProgramBudget,
    # Funding & Payment
    PaymentRule, FundingAgreement, BriefFinancialApproval,
    FundingNotice, ExpenseClaim, Delegation, FundingSchedule, WorkFunding,
    Approval, WorkflowAction, AuditLog, Payment,
    ForwardRPFAgreement, InterimFRPAgreement,
    # Reports
    MonthlyTracker, MonthlyTrackerWorkEntry, CouncilTrackerConfig,
    QuarterlyReport, QuarterlyReportItem, QuarterlyReportItemGroup,
    QuarterlyReportEntry, QuarterlyReportAttachment,
    StageReport, StageReportItem, StageReportAttachment,
    StageItemDefinition, StageItemGroup, StageItemGroupItem,
    # Land
    LandPreCondition,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Base for audit/event tables — block add/change/delete."""
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Audit trail (read-only)
# ---------------------------------------------------------------------------

@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ('timestamp', 'entity_type', 'entity_id', 'action', 'user')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_type', 'entity_id', 'user__username')
    readonly_fields = ('user', 'timestamp', 'entity_type', 'entity_id',
                       'action', 'before_json', 'after_json')
    ordering = ('-timestamp',)


@admin.register(WorkflowAction)
class WorkflowActionAdmin(ReadOnlyAdmin):
    list_display = ('performed_at', 'entity_type', 'entity_id', 'action_type', 'performed_by')
    list_filter = ('action_type', 'entity_type')
    search_fields = ('entity_type', 'entity_id', 'performed_by__username')
    ordering = ('-performed_at',)


# ---------------------------------------------------------------------------
# Council & Program
# ---------------------------------------------------------------------------

@admin.register(Council)
class CouncilAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'is_registered_housing_provider')
    list_filter = ('is_registered_housing_provider',)
    search_fields = ('name', 'region')


@admin.register(CouncilContact)
class CouncilContactAdmin(admin.ModelAdmin):
    list_display = ('council', 'name', 'role', 'email')
    search_fields = ('name', 'email', 'council__name')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'funding_source', 'budget', 'is_active')
    list_filter = ('funding_source', 'is_active')
    search_fields = ('name', 'gl_code')


@admin.register(ProgramBudget)
class ProgramBudgetAdmin(admin.ModelAdmin):
    list_display = ('program', 'financial_year', 'allocated')
    list_filter = ('financial_year',)
    search_fields = ('program__name',)


# ---------------------------------------------------------------------------
# Funding & Payment
# ---------------------------------------------------------------------------

@admin.register(PaymentRule)
class PaymentRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'rule_type', 'is_active')
    list_filter = ('rule_type', 'is_active')
    search_fields = ('name',)


@admin.register(FundingAgreement)
class FundingAgreementAdmin(admin.ModelAdmin):
    list_display = ('name', 'council', 'status', 'execution_date')
    list_filter = ('status',)
    search_fields = ('name', 'council__name')


class BriefFinancialApprovalItemInline(admin.TabularInline):
    from apps.core.models import BriefFinancialApprovalItem
    model = BriefFinancialApprovalItem
    extra = 0
    fields = ('project', 'funding_amount', 'contingency_amount', 'cost_centre', 'gl_code')
    readonly_fields = ('cost_centre', 'gl_code')


@admin.register(BriefFinancialApproval)
class BriefFinancialApprovalAdmin(admin.ModelAdmin):
    list_display = ('mincor_reference', 'project_count_col', 'total_amount_col', 'status', 'delegate_level')
    list_filter = ('status', 'delegate_level')
    search_fields = ('mincor_reference', 'document_uri')
    inlines = [BriefFinancialApprovalItemInline]

    @admin.display(description='Total')
    def total_amount_col(self, obj):
        return f"${obj.total_amount:,.0f}"

    @admin.display(description='Projects')
    def project_count_col(self, obj):
        return obj.project_count


@admin.register(FundingNotice)
class FundingNoticeAdmin(admin.ModelAdmin):
    list_display = ('project', 'capped_amount', 'issued_date', 'status')
    list_filter = ('status',)
    search_fields = ('project__name',)


@admin.register(ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ('funding_notice', 'amount', 'date_submitted', 'status')
    list_filter = ('status',)


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ('position', 'threshold_amount', 'is_active')
    list_filter = ('is_active', 'position')


@admin.register(FundingSchedule)
class FundingScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'schedule_number', 'status', 'payment_rule')
    list_filter = ('status',)
    search_fields = ('project__name',)


@admin.register(WorkFunding)
class WorkFundingAdmin(admin.ModelAdmin):
    list_display = ('funding_schedule', 'project', 'work', 'amount', 'cost_centre', 'gl_code')
    search_fields = ('cost_centre', 'gl_code')


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('approval_type', 'entity_type', 'entity_id', 'required_role', 'status', 'approved_by')
    list_filter = ('approval_type', 'required_role', 'status')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('project', 'payment_type', 'amount', 'status', 'release_date')
    list_filter = ('status', 'payment_type', 'payment_split')
    search_fields = ('project__name', 'reference')


# ---------------------------------------------------------------------------
# Legacy agreements
# ---------------------------------------------------------------------------

@admin.register(ForwardRPFAgreement)
class ForwardRPFAgreementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'council', 'status', 'executed_date')
    list_filter = ('status',)
    search_fields = ('reference', 'council__name')


@admin.register(InterimFRPAgreement)
class InterimFRPAgreementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'council', 'status', 'executed_date')
    list_filter = ('status',)
    search_fields = ('reference', 'council__name')


# ---------------------------------------------------------------------------
# Monthly tracker
# ---------------------------------------------------------------------------

@admin.register(CouncilTrackerConfig)
class CouncilTrackerConfigAdmin(admin.ModelAdmin):
    list_display = ('council', 'council_submission_enabled', 'submission_due_day')
    list_filter = ('council_submission_enabled',)
    search_fields = ('council__name',)


class MonthlyTrackerWorkEntryInline(admin.TabularInline):
    model = MonthlyTrackerWorkEntry
    extra = 0
    fields = ('work_step', 'actual_completion_date', 'forecast_completion_date', 'notes')


@admin.register(MonthlyTracker)
class MonthlyTrackerAdmin(admin.ModelAdmin):
    list_display = ('council', 'year', 'month', 'status', 'submitted_at')
    list_filter = ('status', 'year', 'month')
    search_fields = ('council__name',)
    inlines = [MonthlyTrackerWorkEntryInline]


@admin.register(MonthlyTrackerWorkEntry)
class MonthlyTrackerWorkEntryAdmin(admin.ModelAdmin):
    list_display = ('tracker', 'work_step', 'actual_completion_date', 'forecast_completion_date')
    search_fields = ('tracker__council__name',)


# ---------------------------------------------------------------------------
# Quarterly report
# ---------------------------------------------------------------------------

class QuarterlyReportItemInline(admin.TabularInline):
    model = QuarterlyReportItem
    extra = 0
    fields = ('name', 'field_type', 'order', 'is_required', 'is_active', 'help_text')


@admin.register(QuarterlyReportItemGroup)
class QuarterlyReportItemGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [QuarterlyReportItemInline]


@admin.register(QuarterlyReportItem)
class QuarterlyReportItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'field_type', 'order', 'is_active', 'is_required')
    list_filter = ('field_type', 'is_active', 'is_required')
    search_fields = ('name', 'group__name')


class QuarterlyReportEntryInline(admin.TabularInline):
    model = QuarterlyReportEntry
    extra = 0
    fields = ('work', 'item', 'date_value', 'number_value', 'text_value', 'boolean_value', 'is_na')


class QuarterlyReportAttachmentInline(admin.TabularInline):
    model = QuarterlyReportAttachment
    extra = 0
    fields = ('work', 'document_uri', 'description')


@admin.register(QuarterlyReport)
class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ('council', 'year', 'quarter', 'status', 'submitted_at')
    list_filter = ('status', 'year', 'quarter')
    search_fields = ('council__name',)
    inlines = [QuarterlyReportEntryInline, QuarterlyReportAttachmentInline]


# ---------------------------------------------------------------------------
# Stage report + templates
# ---------------------------------------------------------------------------

@admin.register(StageItemDefinition)
class StageItemDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


class StageItemGroupItemInline(admin.TabularInline):
    model = StageItemGroupItem
    extra = 0
    fields = ('order', 'item', 'field_type', 'is_required', 'requires_attachment', 'help_text')
    autocomplete_fields = ('item',)


@admin.register(StageItemGroup)
class StageItemGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'stage_type', 'is_active')
    list_filter = ('stage_type', 'is_active')
    search_fields = ('name',)
    inlines = [StageItemGroupItemInline]


@admin.register(StageItemGroupItem)
class StageItemGroupItemAdmin(admin.ModelAdmin):
    list_display = ('group', 'order', 'item', 'field_type', 'requires_attachment')
    list_filter = ('field_type', 'requires_attachment', 'group__stage_type')
    search_fields = ('item__name', 'group__name')


class StageReportItemInline(admin.TabularInline):
    model = StageReportItem
    extra = 0
    fields = ('group_item', 'is_completed', 'date_value', 'number_value',
              'text_value', 'boolean_value', 'is_na', 'notes')
    readonly_fields = ('group_item',)


@admin.register(StageReport)
class StageReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'stage_type', 'status', 'agreement_type', 'submitted_at')
    list_filter = ('stage_type', 'status')
    search_fields = ('project__name',)
    inlines = [StageReportItemInline]


@admin.register(StageReportItem)
class StageReportItemAdmin(admin.ModelAdmin):
    list_display = ('report', 'group_item', 'is_completed', 'is_na', 'updated_at')
    list_filter = ('is_completed', 'is_na')


@admin.register(StageReportAttachment)
class StageReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ('item', 'description', 'uploaded_at')
    search_fields = ('description',)


@admin.register(LandPreCondition)
class LandPreConditionAdmin(admin.ModelAdmin):
    list_display = ('project', 'category', 'status', 'native_title_type', 'completed_date')
    list_filter = ('category', 'status')
    search_fields = ('project__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
