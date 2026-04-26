from django.contrib import admin
from .models import (
    MonthlyTrackerItemGroup, MonthlyTrackerItem, MonthlyTracker, MonthlyTrackerEntry,
    QuarterlyReportItemGroup, QuarterlyReportItem, QuarterlyReport, QuarterlyReportEntry, QuarterlyReportAttachment,
    StageReport, StageReportItem, StageReportAttachment
)


@admin.register(MonthlyTrackerItemGroup)
class MonthlyTrackerItemGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(MonthlyTrackerItem)
class MonthlyTrackerItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'field_type', 'order', 'is_required')
    list_filter = ('group', 'field_type')
    search_fields = ('name',)
    ordering = ('group', 'order')


@admin.register(MonthlyTracker)
class MonthlyTrackerAdmin(admin.ModelAdmin):
    list_display = ('funding_schedule', 'year', 'month', 'status', 'submitted_at')
    list_filter = ('status', 'year', 'month')
    search_fields = ('funding_schedule__project__name',)


@admin.register(QuarterlyReportItemGroup)
class QuarterlyReportItemGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(QuarterlyReportItem)
class QuarterlyReportItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'field_type', 'order', 'is_required')
    list_filter = ('group', 'field_type')
    search_fields = ('name',)
    ordering = ('group', 'order')


@admin.register(QuarterlyReport)
class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'year', 'quarter', 'status', 'submitted_at')
    list_filter = ('status', 'year', 'quarter')
    search_fields = ('project__name',)


@admin.register(QuarterlyReportAttachment)
class QuarterlyReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ('report', 'work', 'uploaded_at')
    search_fields = ('report__project__name',)


@admin.register(StageReport)
class StageReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'stage_type', 'status', 'submitted_at')
    list_filter = ('status', 'stage_type')
    search_fields = ('project__name',)


@admin.register(StageReportItem)
class StageReportItemAdmin(admin.ModelAdmin):
    list_display = ('report', 'step_name', 'step_order', 'is_completed')
    list_filter = ('is_completed',)
    search_fields = ('step_name',)


@admin.register(StageReportAttachment)
class StageReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ('item', 'uploaded_at')
    search_fields = ('item__step_name',)
