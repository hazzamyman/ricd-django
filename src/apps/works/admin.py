from django.contrib import admin
from .models import Work, WorkType, NotionalCost, NotionalCostSettings, WorkStepTemplate


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'has_bedrooms', 'default_bedrooms', 'is_active')
    list_filter = ('category', 'is_active', 'has_bedrooms')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'has_bedrooms', 'default_bedrooms')


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ('get_work_type', 'bedrooms', 'quantity', 'project', 'address')
    list_filter = ('work_type', 'project', 'status')
    search_fields = ('work_type__name', 'work_type_other', 'project__name')

    @admin.display(description='Work Type')
    def get_work_type(self, obj):
        return obj.work_type.name if obj.work_type else obj.work_type_other


@admin.register(NotionalCost)
class NotionalCostAdmin(admin.ModelAdmin):
    list_display = ('work_type', 'bedrooms', 'financial_year', 'cost_per_unit')
    list_filter = ('financial_year', 'work_type')
    search_fields = ('work_type__name',)


@admin.register(NotionalCostSettings)
class NotionalCostSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(WorkStepTemplate)
class WorkStepTemplateAdmin(admin.ModelAdmin):
    list_display = ('work_type', 'name', 'order')
    list_filter = ('work_type',)
    search_fields = ('work_type__name', 'name')
