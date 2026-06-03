from django.db import models
from django.utils import timezone

from apps.core.utils import CURRENT_FINANCIAL_YEAR, FINANCIAL_YEAR_CHOICES



class ConstructionMethod(models.Model):
    """
    Configurable construction method types (e.g. On-site, Flatpack, Offsite).
    Managed via Maintenance UI. Used to analyse cost variances across methods.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True, help_text="Short code e.g. on_site, flatpack")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Construction Method"

    def __str__(self):
        return self.name


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
    min_bedrooms = models.PositiveIntegerField(
        default=0,
        help_text="Typical lowest bedroom count (e.g. 3). Bulk-update notional costs uses this range."
    )
    max_bedrooms = models.PositiveIntegerField(
        default=0,
        help_text="Typical highest bedroom count (e.g. 5). Costs outside the range are still allowed but flagged."
    )
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
    def typical_bedroom_range(self):
        """Return the inclusive [min, max] range as a list, or [] when not bedroom-driven."""
        if not self.has_bedrooms:
            return []
        lo = self.min_bedrooms or self.default_bedrooms or 0
        hi = self.max_bedrooms or self.default_bedrooms or lo
        if hi < lo:
            hi = lo
        return list(range(lo, hi + 1)) if lo > 0 else []

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

    class LivableHousingLevel(models.TextChoices):
        SILVER = 'SILVER', 'Silver'
        GOLD = 'GOLD', 'Gold'
        PLATINUM = 'PLATINUM', 'Platinum'

    class UsageType(models.TextChoices):
        PUBLIC_HOUSING = 'PH', 'Public Housing'
        AFFORDABLE = 'AH', 'Affordable Housing'
        COMMUNITY = 'CH', 'Community Housing'
        MIXED = 'MX', 'Mixed Use'

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
    actual_start_date = models.DateField(
        null=True, blank=True,
        help_text="Date construction actually started — anchors the rolling step forecast"
    )

    # Practical Completion + Handover — operational truth, separate from contract
    # (Stage 1/2 Target/Sunset). PC = when the work can be counted as complete;
    # Handover = when the asset is delivered to the council/department. Both
    # have a forecast (rolling estimate, adjusted by Monthly Tracker) and an
    # actual (set on Stage 2 PC/Handover item approval, or manually).
    forecast_practical_completion_date = models.DateField(
        null=True, blank=True, db_index=True,
        help_text="Rolling estimate of Practical Completion. Driven by Monthly "
                  "Tracker progress; can be manually overridden.",
    )
    practical_completion_date = models.DateField(
        null=True, blank=True, db_index=True,
        help_text="Actual Practical Completion date. Set when the Stage 2 PC item "
                  "is approved (or entered manually).",
    )
    forecast_handover_date = models.DateField(
        null=True, blank=True, db_index=True,
        help_text="Rolling estimate of when the asset will be handed to the "
                  "council/department.",
    )
    handover_date = models.DateField(
        null=True, blank=True, db_index=True,
        help_text="Actual Handover date — when the asset has been delivered.",
    )

    is_notional_cost = models.BooleanField(default=True, help_text="If True, cost is calculated from notional rates. If False, use actual_cost.")
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Actual cost (manual override)")
    forecast_final_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Latest forecast of the final cost for this work item",
    )
    costs_finalised = models.BooleanField(default=False, help_text="All costs for this work item have been finalised")

    # Contractor
    contractor = models.ForeignKey(
        'Contractor', related_name='works', on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    # Physical characteristics
    floor_area = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Floor area in m²",
    )
    drawing_no = models.CharField(max_length=100, blank=True, help_text="Construction drawing reference")

    # As-built dwelling characteristics (the dwelling produced by this work item,
    # not the land parcel — those stay on Address).
    floor_number = models.CharField(max_length=10, blank=True, help_text="Floor number for apartments (e.g. '3', 'G')")
    livable_housing_level = models.CharField(
        max_length=8, choices=LivableHousingLevel.choices, blank=True, default='',
        help_text="Livable Housing Design guideline level (Silver / Gold / Platinum)",
    )
    usage_type = models.CharField(max_length=2, choices=UsageType.choices, blank=True, default='')

    floor_material = models.CharField(max_length=100, blank=True)
    frame_material = models.CharField(max_length=100, blank=True)
    wall_material = models.CharField(max_length=100, blank=True)
    roof_material = models.CharField(max_length=100, blank=True)
    car_accommodation = models.CharField(max_length=100, blank=True)

    bathrooms_count = models.PositiveIntegerField(null=True, blank=True)
    kitchens_count = models.PositiveIntegerField(null=True, blank=True)
    living_rooms_count = models.PositiveIntegerField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Handover usually happens the same day as PC (occasionally up to ~15
        # days later, in which case the user enters it explicitly). Default
        # blank handover dates to the matching PC date so the typical case is
        # zero-input.
        if self.forecast_practical_completion_date and not self.forecast_handover_date:
            self.forecast_handover_date = self.forecast_practical_completion_date
        if self.practical_completion_date and not self.handover_date:
            self.handover_date = self.practical_completion_date
        super().save(*args, **kwargs)

    @property
    def pc_breaches_sunset(self):
        """True when forecast PC is >30 days past the project's Stage 2 sunset.

        Triggers an amber warning badge on the work + project detail pages —
        no hard validation, just a heads-up that this work is expected to
        breach the contract sunset.
        """
        from datetime import timedelta
        sunset = getattr(self.project, 'stage2_sunset_date', None)
        forecast = self.forecast_practical_completion_date
        if sunset is None or forecast is None:
            return False
        return forecast > sunset + timedelta(days=30)

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
    """Named package of ordered work steps reusable across many work types.

    A single group (e.g. "Standard New Residential Construction") can be
    linked to House, Duplex, Townhouse, Unit and Attached at once via the
    work_types M2M. Use Clone to make a near-identical variant and tweak.
    """
    work_types = models.ManyToManyField(
        WorkType, related_name='step_groups', blank=True,
        help_text="Work types this group applies to — many-to-many so one group "
                  "can serve all residential types that share a workflow.",
    )
    name = models.CharField(
        max_length=200,
        help_text="e.g. 'Standard New Residential Construction', 'Land Subdivision'",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Work Step Group'
        verbose_name_plural = 'Work Step Groups'

    def __str__(self):
        return self.name

    def total_cost_percentage(self):
        return sum(item.cost_percentage for item in self.items.all())

    def clone(self, new_name=None):
        """Create a deep copy of this group + its items. Returns the new group.

        work_types links are NOT copied (the clone is intended for "similar but
        different" — caller assigns its own work types).
        """
        from django.db import transaction
        with transaction.atomic():
            new = WorkStepGroup.objects.create(
                name=new_name or f"{self.name} (copy)",
                description=self.description,
                is_active=self.is_active,
            )
            for it in self.items.all():
                WorkStepGroupItem.objects.create(
                    group=new, step=it.step, order=it.order,
                    cost_percentage=it.cost_percentage,
                    expected_duration_days=it.expected_duration_days,
                    stage_gate=it.stage_gate,
                    is_monthly_tracker_column=it.is_monthly_tracker_column,
                )
            # Copy the payment milestone schedule (if any) so the clone keeps the
            # same payment timing until the user tweaks it.
            sched = getattr(self, 'payment_schedule', None)
            if sched is not None:
                sched.clone_for_group(new, new_name=f"{new.name} payments")
            return new


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
    is_monthly_tracker_column = models.BooleanField(
        default=False,
        help_text="Show this step as a column in the monthly tracker grid"
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


# ============================================================================
# Stage Item template models (for Stage 1 / Stage 2 Reports)
# ============================================================================
# StageItemDefinition: global catalogue of step names (stage-agnostic).
# StageItemGroup: a templated set of items with a stage_type (Stage 1 OR Stage 2)
#   -- the same StageItemDefinition can appear in BOTH a Stage 1 group (e.g. for
#   Land projects) and a Stage 2 group (e.g. for Construction).
# StageItemGroupItem: ordered membership of items in a group, with field_type
#   (DATE / CHECKBOX / YES_NO / etc.) and attachment requirement.
# Projects pre-assign one StageItemGroup per stage (Project.stage1_item_group,
# Project.stage2_item_group) which seeds the StageReportItems when a council
# opens that stage report.


class StageItemDefinition(models.Model):
    """Global catalogue of stage report items (steps).

    Not stage-typed -- the same item can appear in a Stage 1 group OR a Stage 2 group
    depending on the project work type (e.g. site preparation is Stage 1 for
    construction but might be Stage 2 for land lot development).
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Stage Item Definition'
        verbose_name_plural = 'Stage Item Definitions'

    def __str__(self):
        return self.name


class StageItemGroup(models.Model):
    """Templated checklist of stage items for one stage and one work-type context.

    Example groups:
      - "Stage 1 - Construction"
      - "Stage 1 - Extension"
      - "Stage 1 - Land"
      - "Stage 2 - Construction"
      - "Stage 2 - Demolition"
    Pre-assigned to a Project via Project.stage1_item_group / stage2_item_group.
    """

    class StageType(models.TextChoices):
        STAGE1 = 'STAGE1', 'Stage 1'
        STAGE2 = 'STAGE2', 'Stage 2'

    stage_type = models.CharField(max_length=10, choices=StageType.choices, db_index=True)
    name = models.CharField(max_length=255, help_text="e.g. 'Construction', 'Extension', 'Demolition', 'Land'")
    description = models.TextField(blank=True)
    work_types = models.ManyToManyField(
        WorkType, related_name='stage_item_groups', blank=True,
        help_text="Optional — work types this group typically applies to. "
                  "Drives the picker filter on the Funding Schedule form.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['stage_type', 'name']
        unique_together = ('stage_type', 'name')
        verbose_name = 'Stage Item Group'
        verbose_name_plural = 'Stage Item Groups'

    def __str__(self):
        return f"{self.get_stage_type_display()} -- {self.name}"

    def clone(self, new_name=None):
        """Deep copy this group + its items. work_types links NOT copied."""
        from django.db import transaction
        with transaction.atomic():
            new = StageItemGroup.objects.create(
                stage_type=self.stage_type,
                name=new_name or f"{self.name} (copy)",
                description=self.description,
                is_active=self.is_active,
            )
            for it in self.items.all():
                StageItemGroupItem.objects.create(
                    group=new, item=it.item, order=it.order,
                    field_type=it.field_type, is_required=it.is_required,
                    requires_attachment=it.requires_attachment,
                    help_text=it.help_text,
                )
            return new


class StageItemGroupItem(models.Model):
    """Ordered membership of a StageItemDefinition in a StageItemGroup, with field type."""

    class FieldType(models.TextChoices):
        DATE = 'DATE', 'Date'
        DATE_NA = 'DATE_NA', 'Date or N/A'
        NUMBER = 'NUMBER', 'Number'
        CURRENCY = 'CURRENCY', 'Currency'
        TEXT = 'TEXT', 'Text'
        CHECKBOX = 'CHECKBOX', 'Checkbox'
        YES_NO = 'YES_NO', 'Yes/No'
        YES_NO_NA = 'YES_NO_NA', 'Yes/No/N/A'

    group = models.ForeignKey(StageItemGroup, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(StageItemDefinition, related_name='group_memberships', on_delete=models.PROTECT)
    order = models.PositiveIntegerField(default=0)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.CHECKBOX)
    is_required = models.BooleanField(default=True)
    requires_attachment = models.BooleanField(default=True, help_text="Council must upload at least one document URI")
    help_text = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('group', 'order')
        verbose_name = 'Stage Item Group Item'
        verbose_name_plural = 'Stage Item Group Items'

    def __str__(self):
        return f"{self.group.name} [{self.order}] {self.item.name}"
