from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# Import Project for proper FK resolution
from .project import Project


class WorkType(models.Model):
    """Manage work types independently from code choices"""
    code = models.CharField(max_length=50, unique=True, help_text="Internal code for work type")
    name = models.CharField(max_length=255, help_text="Display name for work type")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Many-to-many relationship with OutputType to define allowed output types
    allowed_output_types = models.ManyToManyField(
        'OutputType',
        blank=True,
        related_name='work_types',
        help_text="Output types that are allowed for this work type"
    )

    def __str__(self):
        return self.name

    def get_usage_count(self):
        """Count how many addresses/works use this work type"""
        return (
            self.address_set.filter(project__isnull=False).count() +
            self.work_set.filter(address__project__isnull=False).count()
        )

    def get_allowed_output_types(self):
        """Get queryset of allowed output types for this work type"""
        return self.allowed_output_types.filter(is_active=True)

    def clean(self):
        """Validate WorkType fields"""
        if not self.code.strip():
            raise ValidationError({'code': 'Work type code is required'})

        if not self.name.strip():
            raise ValidationError({'name': 'Work type name is required'})

    class Meta:
        ordering = ['name']


class OutputType(models.Model):
    """Manage output types independently from code choices"""
    code = models.CharField(max_length=50, unique=True, help_text="Internal code for output type")
    name = models.CharField(max_length=255, help_text="Display name for output type")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        """Validate OutputType fields"""
        if not self.code.strip():
            raise ValidationError({'code': 'Output type code is required'})

        if not self.name.strip():
            raise ValidationError({'name': 'Output type name is required'})

    def __str__(self):
        return self.name

    def get_usage_count(self):
        """Count how many addresses/works use this output type"""
        return (
            self.address_set.filter(project__isnull=False).count() +
            self.work_set.filter(address__project__isnull=False).count()
        )

    class Meta:
        ordering = ['name']


class ConstructionMethod(models.Model):
    """Manage construction methods independently from code choices"""
    code = models.CharField(max_length=50, unique=True, help_text="Internal code for construction method")
    name = models.CharField(max_length=255, help_text="Display name for construction method")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        """Validate ConstructionMethod fields"""
        if not self.code.strip():
            raise ValidationError({'code': 'Construction method code is required'})

        if not self.name.strip():
            raise ValidationError({'name': 'Construction method name is required'})

    def __str__(self):
        return self.name

    def get_usage_count(self):
        """Count how many addresses/works use this construction method"""
        return (
            self.address_set.filter(project__isnull=False).count() +
            self.work_set.filter(address__project__isnull=False).count()
        )

    class Meta:
        ordering = ['name']


class DefaultWorkStep(models.Model):
    program = models.ForeignKey('core.Program', on_delete=models.CASCADE, related_name="default_work_steps")
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.CASCADE,
        related_name='default_steps'
    )
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_offset_days = models.PositiveIntegerField(default=0)

    def clean(self):
        """Validate DefaultWorkStep fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Step name is required'})

        if self.order <= 0:
            raise ValidationError({'order': 'Order must be a positive integer'})

        if self.due_offset_days < 0:
            raise ValidationError({'due_offset_days': 'Due offset days cannot be negative'})

        # Check for unique order per program
        if DefaultWorkStep.objects.filter(
            program=self.program,
            order=self.order
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'order': 'Order must be unique within the program'})

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.program} ({self.work_type_id.name if self.work_type_id else 'No work type'})"


class Address(models.Model):
    # Retained if not merged; but per plan, could be merged
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=255, help_text="Street address")

    # These will default to council's defaults when creating
    suburb = models.CharField(max_length=255, help_text="Suburb/Town")
    postcode = models.CharField(max_length=4, validators=[RegexValidator(r'^\d{4}$', 'Postcode must be exactly 4 digits')], help_text="4-digit postcode")
    state = models.CharField(max_length=3, default="QLD")

    # New fields for address-specific work details
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Type of work at this address"
    )

    output_type_id = models.ForeignKey(
        OutputType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Type of output at this address"
    )

    bedrooms = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of bedrooms"
    )

    output_quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of outputs (e.g., houses, units) at this address"
    )

    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Budget allocated for this address"
    )

    # Property reference fields for land tenure information
    lot_number = models.CharField(max_length=50, blank=True, null=True)
    plan_number = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., RP3435")
    title_reference = models.CharField(max_length=50, blank=True, null=True, validators=[RegexValidator(r'^\d*$', 'Title reference must be numeric')], help_text="e.g., 5456565")

    # Construction method field for cost analysis
    construction_method = models.ForeignKey(
        ConstructionMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Construction method used for this address"
    )

    def clean(self):
        """Validate Address fields"""
        if not self.street.strip():
            raise ValidationError({'street': 'Street address is required'})

        if not self.suburb.strip():
            raise ValidationError({'suburb': 'Suburb is required'})

        if self.postcode:
            if not self.postcode.isdigit() or len(self.postcode) != 4:
                raise ValidationError({'postcode': 'Postcode must be exactly 4 digits'})

        if self.state != 'QLD':
            raise ValidationError({'state': 'State must be QLD'})

        if self.bedrooms is not None and self.bedrooms < 0:
            raise ValidationError({'bedrooms': 'Bedrooms cannot be negative'})

        if self.output_quantity <= 0:
            raise ValidationError({'output_quantity': 'Output quantity must be positive'})

        if self.budget is not None and self.budget <= 0:
            raise ValidationError({'budget': 'Budget must be a positive amount'})

        # Title reference format validation
        if self.title_reference and not self.title_reference.isdigit():
            raise ValidationError({'title_reference': 'Title reference must be numeric'})

        # Work type and output type compatibility check
        if self.work_type_id and self.output_type_id:
            if not self.work_type_id.allowed_output_types.filter(pk=self.output_type_id.pk).exists():
                raise ValidationError({
                    'output_type_id': f'Output type "{self.output_type_id.name}" is not allowed for work type "{self.work_type_id.name}"'
                })

    class Meta:
        ordering = ['street']

    def __str__(self):
        addr_parts = [self.street, self.suburb]
        if self.state and self.postcode:
            addr_parts.append(f"{self.state} {self.postcode}")

        # Add work type and output info if available
        work_info = []
        if self.work_type_id:
            work_info.append(self.work_type_id.name)
        if self.output_type_id:
            work_info.append(self.output_type_id.name)
        if self.bedrooms:
            work_info.append(f"{self.bedrooms}BR")
        if self.output_quantity and self.output_quantity > 1:
            work_info.append(f"×{self.output_quantity}")

        if work_info:
            addr_parts.append(" • ".join(work_info))

        property_refs = []
        if self.lot_number:
            property_refs.append(f"Lot {self.lot_number}")
        if self.plan_number:
            property_refs.append(self.plan_number)
        if self.title_reference:
            property_refs.append(f"Title {self.title_reference}")

        if property_refs:
            addr_parts.append(" ".join(property_refs))

        return ", ".join(addr_parts)


class Work(models.Model):
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="works")
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        null=False,
        help_text="Type of work to be performed"
    )
    output_type_id = models.ForeignKey(
        OutputType,
        on_delete=models.PROTECT,
        null=False,
        help_text="Type of output/tenure to be produced"
    )
    output_quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    bedrooms = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    bathrooms = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    kitchens = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])

    # Land status field (for work items)
    land_status = models.CharField(max_length=255, blank=True, null=True)

    # Construction method fields
    floor_method = models.CharField(max_length=255, blank=True, null=True, help_text="Concrete Slab/Timber Frame/Steel Frame")
    frame_method = models.CharField(max_length=255, blank=True, null=True, help_text="Timber Frame/Steel Frame/Block/FC Panel")
    external_wall_method = models.CharField(max_length=255, blank=True, null=True, help_text="Timber/Sheeting/Block/Brick")
    roof_method = models.CharField(max_length=255, blank=True, null=True, help_text="Metal Sheeting/Tiles/Galv.Sheeting/Colourbond")
    car_accommodation = models.CharField(max_length=255, blank=True, null=True, help_text="Carport/Garage/Under House")
    additional_facilities = models.CharField(max_length=255, blank=True, null=True, help_text="Additional WC/BATHROOM")

    # Extension fields
    extension_high_low = models.CharField(max_length=50, blank=True, null=True, help_text="High set/Low set for extensions")

    dwellings_count = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0.01'))])
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0.01'))])
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    # Construction method field for cost analysis
    construction_method = models.ForeignKey(
        ConstructionMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Construction method used for this work"
    )

    # Progress field
    progress_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Progress percentage for this work")

    def clean(self):
        """Validate Work fields"""
        if self.output_quantity <= 0:
            raise ValidationError({'output_quantity': 'Output quantity must be positive'})

        if self.bedrooms is not None and self.bedrooms < 0:
            raise ValidationError({'bedrooms': 'Bedrooms cannot be negative'})

        if self.bathrooms is not None and self.bathrooms < 0:
            raise ValidationError({'bathrooms': 'Bathrooms cannot be negative'})

        if self.kitchens is not None and self.kitchens < 0:
            raise ValidationError({'kitchens': 'Kitchens cannot be negative'})

        # Cost validations
        if self.estimated_cost is not None and self.estimated_cost <= 0:
            raise ValidationError({'estimated_cost': 'Estimated cost must be positive'})

        if self.actual_cost is not None and self.actual_cost <= 0:
            raise ValidationError({'actual_cost': 'Actual cost must be positive'})

        # Date logic validation
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'End date cannot be before start date'})

        # Progress validation
        if self.progress_percentage < 0 or self.progress_percentage > 100:
            raise ValidationError({'progress_percentage': 'Progress percentage must be between 0 and 100'})

        # Work type and output type compatibility check
        if self.work_type_id and self.output_type_id:
            if not self.work_type_id.allowed_output_types.filter(pk=self.output_type_id.pk).exists():
                raise ValidationError({
                    'output_type_id': f'Output type "{self.output_type_id.name}" is not allowed for work type "{self.work_type_id.name}"'
                })

        # Dwelling count validation
        if self.dwellings_count <= 0:
            raise ValidationError({'dwellings_count': 'Dwellings count must be positive'})

    @property
    def total_dwellings(self):
        # Simplified: for duplex/triplex, multiply
        multiplier = 1
        if self.output_type_id and self.output_type_id.code in ["duplex"]:
            multiplier = 2
        elif self.output_type_id and self.output_type_id.code == "triplex":
            multiplier = 3
        return self.output_quantity * multiplier

    @property
    def total_bedrooms(self):
        return (self.bedrooms or 0) * self.total_dwellings

    def get_practical_completion_date(self):
        # Get practical completion from project's practical completions
        practical_completion = self.project.practical_completions.first()
        if practical_completion and practical_completion.completion_date:
            return practical_completion.completion_date
        # Fallback to quarterly reports
        quarterly_reports = self.quarterly_reports.filter(practical_completion_actual_date__isnull=False).order_by('-submission_date')
        if quarterly_reports.exists():
            return quarterly_reports.first().practical_completion_actual_date
        # Another fallback: Stage2Report
        stage2_reports = self.project.stage2_reports.filter(practical_completion_date__isnull=False).order_by('-submission_date')
        if stage2_reports.exists():
            return stage2_reports.first().practical_completion_date
        return None

    @property
    def is_within_defect_liability_period(self):
        pc_date = self.get_practical_completion_date()
        if pc_date:
            expiry = pc_date + relativedelta(months=12)
            today = timezone.now().date()
            return today <= expiry
        return False

    @property
    def project(self):
        """Get project through associated address"""
        return self.address.project

    def get_progress_class(self):
        """Return CSS class for progress bar color based on progress percentage"""
        if self.progress_percentage >= 75:
            return 'progress-bar-success'
        elif self.progress_percentage >= 50:
            return 'progress-bar-info'
        elif self.progress_percentage >= 25:
            return 'progress-bar-warning'
        else:
            return 'progress-bar-danger'

    def __str__(self):
        return f"{self.work_type_id.name if self.work_type_id else 'No work type'} - {self.output_type_id.name if self.output_type_id else 'No output type'} ({self.address})"


class Defect(models.Model):
    """Defects identified during construction or within defect liability period"""
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='defects')
    description = models.TextField(help_text="Description of the defect")
    identified_date = models.DateField(default=timezone.now, help_text="Date defect was identified")
    rectified_date = models.DateField(blank=True, null=True, help_text="Date defect was rectified")

    def clean(self):
        """Validate Defect fields"""
        if not self.description.strip():
            raise ValidationError({'description': 'Defect description is required'})

        if self.rectified_date and self.rectified_date < self.identified_date:
            raise ValidationError({'rectified_date': 'Rectified date cannot be before identified date'})

        if self.rectified_date and self.rectified_date > timezone.now().date():
            raise ValidationError({'rectified_date': 'Rectified date cannot be in the future'})

    def __str__(self):
        return f"Defect for {self.work} - {self.description[:50]}..."


class WorkStep(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="work_steps")
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(blank=True, null=True)

    def clean(self):
        """Validate WorkStep fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Step name is required'})

        if self.order <= 0:
            raise ValidationError({'order': 'Order must be a positive integer'})

        # Check for unique order per work
        if WorkStep.objects.filter(
            work=self.work,
            order=self.order
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'order': 'Order must be unique within the work'})

        # Due date validation
        if self.due_date and self.work.start_date and self.due_date < self.work.start_date:
            raise ValidationError({'due_date': 'Due date cannot be before work start date'})

        # Completion validation logic
        if self.completed and not self.due_date:
            raise ValidationError({'completed': 'Cannot mark as completed without a due date'})

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.work}"


# Signals for automation
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Work)
def copy_default_work_steps(sender, instance, created, **kwargs):
    if created:
        defaults = DefaultWorkStep.objects.filter(program=instance.project.program, work_type_id=instance.work_type_id)
        for default in defaults:
            due_date = None
            if instance.start_date:
                due_date = instance.start_date + timezone.timedelta(days=default.due_offset_days)
            WorkStep.objects.create(
                work=instance,
                order=default.order,
                name=default.name,
                description=default.description,
                due_date=due_date,
                completed=False
            )