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
        from apps.works.models import NotionalCost
        
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
        from apps.works.models import NotionalCost
        
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

    class ProjectType(models.TextChoices):
        DWELLING = 'DWELLING', 'Dwelling/Construction'
        LAND = 'LAND', 'Land/Infrastructure'

    address = models.ForeignKey('addresses.Address', related_name='works', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey('projects.Project', related_name='works', on_delete=models.CASCADE, null=True, blank=True)
    land_project = models.ForeignKey('land_infra.LandProject', related_name='works', on_delete=models.CASCADE, null=True, blank=True)
    project_type = models.CharField(max_length=10, choices=ProjectType.choices, default=ProjectType.DWELLING)
    work_type = models.ForeignKey(WorkType, related_name='works', on_delete=models.PROTECT, null=True, blank=True)
    work_type_other = models.CharField(max_length=100, blank=True)
    bedrooms = models.PositiveIntegerField(default=0, help_text="Number of bedrooms (0 if not applicable)")
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    is_notional_cost = models.BooleanField(default=True, help_text="If True, cost is calculated from notional rates. If False, use actual_cost.")
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Actual cost (manual override)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        work_type_display = self.work_type.name if self.work_type else self.work_type_other
        project_name = self.project.name if self.project else (self.land_project.name if self.land_project else 'No Project')
        bedroom_str = f", {self.bedrooms}BR" if self.bedrooms else ""
        return f"{work_type_display}{bedroom_str} x {self.quantity} for {project_name}"

    @property
    def linked_project(self):
        """Returns the linked project (either dwelling or land)"""
        if self.project_type == self.ProjectType.DWELLING:
            return self.project
        return self.land_project

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
        
        project = self.project or self.land_project
        financial_year = None
        
        if project:
            financial_year = getattr(project, 'financial_year', None)
        
        if not financial_year:
            from apps.works.models import NotionalCostSettings
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