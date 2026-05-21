from django.db import models
from django.utils import timezone

from apps.core.utils import CURRENT_FINANCIAL_YEAR, FINANCIAL_YEAR_CHOICES


class WorkType(models.Model):
    class Category(models.TextChoices):
        RESIDENTIAL = 'RESIDENTIAL', 'Residential'
        EXTENSION = 'EXTENSION', 'Extension'
        DEMOLITION = 'DEMOLITION', 'Demolition'
        LAND_DEV = 'LAND_DEV', 'Land Development'
        INFRASTRUCTURE = 'INFRASTRUCTURE', 'Infrastructure'
        PLANNING = 'PLANNING', 'Plan and Prepare/Consultant'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    has_bedrooms = models.BooleanField(default=False, help_text="Does this work type use bedroom counts?")
    default_bedrooms = models.PositiveIntegerField(default=0, help_text="Default bedrooms for this work type")
    description = models.TextField(blank=True)
    short_code = models.CharField(max_length=10, blank=True, help_text="Abbreviation for reports, e.g. DH, TRI, EXT")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Work Types'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        if self.has_bedrooms and self.default_bedrooms == 0:
            if 'House' in self.name or 'Triplex' in self.name:
                self.default_bedrooms = 4
            elif 'Duplex' in self.name:
                self.default_bedrooms = 3
            elif 'Unit' in self.name or 'Extension' in self.name:
                self.default_bedrooms = 2
            elif 'Townhouse' in self.name:
                self.default_bedrooms = 3
        super().save(*args, **kwargs)

    @property
    def notional_cost(self):
        """Get the default notional cost for this work type for current financial year"""
        from apps.core.models import NotionalCost
        
        cost = NotionalCost.objects.filter(
            work_type=self,
            financial_year=CURRENT_FINANCIAL_YEAR,
            bedrooms=self.default_bedrooms or 1
        ).first()
        
        if cost:
            return cost.cost_per_unit
        return None

    @property
    def get_notional_cost_for_bedrooms(self, bedrooms):
        """Get notional cost for specific bedroom count"""
        from apps.core.models import NotionalCost
        
        cost = NotionalCost.objects.filter(
            work_type=self,
            financial_year=CURRENT_FINANCIAL_YEAR,
            bedrooms=bedrooms
        ).first()
        
        if cost:
            return cost.cost_per_unit
        return None


class NotionalCost(models.Model):
    """Notional cost per financial year for each work type"""
    work_type = models.ForeignKey(WorkType, related_name='costs', on_delete=models.CASCADE)
    financial_year = models.CharField(max_length=9, choices=FINANCIAL_YEAR_CHOICES, default=CURRENT_FINANCIAL_YEAR, help_text="Financial year")
    cost_per_unit = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Cost per unit/lot/bedroom")
    bedrooms = models.PositiveIntegerField(null=True, blank=True, help_text="Number of bedrooms (null/0 for work types without bedrooms)")
    is_default = models.BooleanField(default=False, help_text="Mark as the default for this work type")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notional Cost'
        verbose_name_plural = 'Notional Costs'
        unique_together = ['work_type', 'financial_year', 'bedrooms']
        ordering = ['financial_year', 'work_type__category', 'work_type__name']

    def __str__(self):
        bedroom_str = f" ({self.bedrooms}BR)" if self.bedrooms else ""
        return f"{self.work_type.name}{bedroom_str} - {self.financial_year}: ${self.cost_per_unit:,.2f}"

    @classmethod
    def get_for_type(cls, work_type, financial_year, bedrooms=None):
        """Get notional cost for a work type, year, and bedroom count"""
        return cls.objects.filter(
            work_type=work_type,
            financial_year=financial_year,
            bedrooms=bedrooms
        ).first()


class NotionalCostSettings(models.Model):
    """Global settings for notional costs"""
    default_inflation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00, help_text="Default inflation rate percentage for bulk updates")
    current_financial_year = models.CharField(max_length=9, choices=FINANCIAL_YEAR_CHOICES, default=CURRENT_FINANCIAL_YEAR, help_text="Current active financial year")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notional Cost Settings'
        verbose_name_plural = 'Notional Cost Settings'

    def __str__(self):
        return f"Settings: {self.current_financial_year}, Inflation: {self.default_inflation_rate}%"

    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class Work(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    address = models.ForeignKey('Address', related_name='works', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey('Project', related_name='works', on_delete=models.CASCADE)
    work_type = models.ForeignKey(WorkType, related_name='works', on_delete=models.PROTECT, null=True, blank=True)
    work_type_other = models.CharField(max_length=100, blank=True)
    bedrooms = models.PositiveIntegerField(default=0, help_text="Number of bedrooms (0 if not applicable)")
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    class CashflowMethod(models.TextChoices):
        PAYMENT_MILESTONE = 'MILESTONE', 'Capital Grants (Payment Milestone)'
        WORKSTEP_PROGRESSIVE = 'WORKSTEP', 'Capital Works (WorkStep Progressive)'

    cashflow_method = models.CharField(
        max_length=10, choices=CashflowMethod.choices,
        default=CashflowMethod.PAYMENT_MILESTONE,
        help_text="How cashflow is forecast for this work item"
    )
    step_group = models.ForeignKey(
        'WorkStepGroup', related_name='works', on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Required when cashflow_method = WORKSTEP"
    )

    is_notional_cost = models.BooleanField(default=True, help_text="If True, cost is calculated from notional rates. If False, use actual_cost.")
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Actual cost (manual override)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        work_type_display = self.work_type.name if self.work_type else self.work_type_other
        bedroom_str = f", {self.bedrooms}BR" if self.bedrooms else ""
        return f"{work_type_display}{bedroom_str} x {self.quantity} for {self.project.name}"

    @property
    def total_estimated_cost(self):
        return self.estimated_cost * self.quantity

    @property
    def cost_source(self):
        """Returns 'Notional' or 'Actual' depending on what's being used"""
        if self.is_notional_cost:
            return 'Notional'
        return 'Actual'

    @property
    def effective_cost(self):
        """Returns the effective cost (actual if set, otherwise estimated)"""
        if not self.is_notional_cost and self.actual_cost:
            return self.actual_cost
        return self.estimated_cost

    @property
    def total_effective_cost(self):
        """Returns the total effective cost"""
        return self.effective_cost * self.quantity

    def calculate_notional_cost(self):
        """Calculate cost based on notional rates for the project's financial year"""
        if not self.work_type:
            return None
        
        financial_year = None
        
        if self.project:
            financial_year = getattr(self.project, 'financial_year', None)
        
        if not financial_year:
            from apps.core.models import NotionalCostSettings
            financial_year = NotionalCostSettings.get_settings().current_financial_year

        if not financial_year:
            return None
        
        bedrooms = self.bedrooms if self.bedrooms else (self.work_type.default_bedrooms or 1)
        
        cost = NotionalCost.get_for_type(
            self.work_type,
            financial_year,
            bedrooms
        )
        
        if cost:
            return cost.cost_per_unit
        
        cost = NotionalCost.get_for_type(
            self.work_type,
            financial_year,
            None
        )
        
        if cost:
            return cost.cost_per_unit
        
        return None


class WorkStepTemplate(models.Model):
    work_type = models.ForeignKey(WorkType, related_name='step_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.work_type.name} - {self.name}"


# ============================================================================
# WorkStep catalogue + grouping (Capital Works cashflow)
# ============================================================================

class WorkStepDefinition(models.Model):
    """Global catalogue of named work steps. Not tied to any work type."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Work Step Definition'
        verbose_name_plural = 'Work Step Definitions'

    def __str__(self):
        return self.name


class WorkStepGroup(models.Model):
    """Named package of ordered work steps for a specific work type."""
    work_type = models.ForeignKey(WorkType, related_name='step_groups', on_delete=models.PROTECT)
    name = models.CharField(max_length=200, help_text="e.g. Standard 3BR New House, Minor Extension")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['work_type', 'name']
        verbose_name = 'Work Step Group'
        verbose_name_plural = 'Work Step Groups'

    def __str__(self):
        return f"{self.work_type.name} — {self.name}"

    def total_cost_percentage(self):
        return sum(item.cost_percentage for item in self.items.all())


class WorkStepGroupItem(models.Model):
    """Ordered step within a WorkStepGroup, with cost % and duration."""

    class StageGate(models.TextChoices):
        NONE = '', 'No gate'
        STAGE_1 = 'STAGE1', 'Stage 1 completion'
        STAGE_2 = 'STAGE2', 'Stage 2 completion'

    group = models.ForeignKey(WorkStepGroup, related_name='items', on_delete=models.CASCADE)
    step = models.ForeignKey(WorkStepDefinition, related_name='group_items', on_delete=models.PROTECT)
    order = models.PositiveIntegerField()
    cost_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expected_duration_days = models.PositiveIntegerField(default=0)
    stage_gate = models.CharField(
        max_length=10, choices=StageGate.choices, blank=True, default='',
        help_text="Mark this step as the completion point for Stage 1 or Stage 2 works"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['group', 'order']
        verbose_name = 'Work Step Group Item'
        verbose_name_plural = 'Work Step Group Items'

    def __str__(self):
        return f"{self.group.name} [{self.order}] {self.step.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.stage_gate:
            qs = WorkStepGroupItem.objects.filter(
                group=self.group, stage_gate=self.stage_gate
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    f"A {self.get_stage_gate_display()} gate already exists in this group."
                )