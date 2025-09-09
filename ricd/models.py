from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from decimal import Decimal


class UserProfile(models.Model):
    """User profile to extend Django's base User model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    council = models.ForeignKey('Council', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def __str__(self):
        return f"{self.user.username} - {self.council.name if self.council else 'No Council'}"

    @property
    def get_council(self):
        return self.council


class Contact(models.Model):
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True, help_text="Physical address")
    postal_address = models.TextField(blank=True, null=True, help_text="Postal address (optional)")

    def __str__(self):
        return f"{self.name} ({self.position})"


class Council(models.Model):
    name = models.CharField(max_length=255)
    abn = models.CharField(max_length=11, blank=True, null=True)
    default_suburb = models.CharField(max_length=255, blank=True, null=True)
    default_postcode = models.CharField(max_length=4, blank=True, null=True)
    default_state = models.CharField(max_length=3, default='QLD')

    # Geographic fields - council-level specifics (don't change per project)
    federal_electorate = models.CharField(max_length=255, blank=True, null=True)
    state_electorate = models.CharField(max_length=255, blank=True, null=True)
    qhigi_region = models.CharField(max_length=255, blank=True, null=True)

    # Housing provider status for requirements determination
    is_registered_housing_provider = models.BooleanField(
        default=False,
        help_text="Whether or not the Council is a Registered Housing Provider. "
                 "This affects whether or not we require leases where council is NOT a registered provider."
    )

    def __str__(self):
        return self.name


class WorkType(models.Model):
    """Manage work types independently from code choices"""
    code = models.CharField(max_length=50, unique=True, help_text="Internal code for work type")
    name = models.CharField(max_length=255, help_text="Display name for work type")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_usage_count(self):
        """Count how many addresses/works use this work type"""
        return (
            self.addresses.filter(project__isnull=False).count() +
            self.works.filter(project__isnull=False).count()
        )

    class Meta:
        ordering = ['name']


class OutputType(models.Model):
    """Manage output types independently from code choices"""
    code = models.CharField(max_length=50, unique=True, help_text="Internal code for output type")
    name = models.CharField(max_length=255, help_text="Display name for output type")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_usage_count(self):
        """Count how many addresses/works use this output type"""
        return (
            self.addresses.filter(project__isnull=False).count() +
            self.works.filter(project__isnull=False).count()
        )

    class Meta:
        ordering = ['name']


class Program(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    funding_source = models.CharField(max_length=50, choices=[
        ("Commonwealth", "Commonwealth"),
        ("State", "State"),
    ], blank=True, null=True)

    def __str__(self):
        return self.name

class DefaultWorkStep(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="default_work_steps")
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.CASCADE,
        related_name='default_steps'
    )
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_offset_days = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.program} ({self.work_type_id.name if self.work_type_id else 'No work type'})"
    

class FundingSchedule(models.Model):
    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name="funding_schedules", null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="funding_schedules", null=True, blank=True)
    funding_schedule_number = models.IntegerField()
    # Simplified funding structure
    funding_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total funding amount allocated")
    contingency_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Contingency amount (calculated or manual)")

    # Simplified payment tracking
    first_payment_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    first_release_date = models.DateField(blank=True, null=True)
    first_reference_number = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ('council', 'funding_schedule_number')

    @property
    def total_funding(self):
        return self.funding_amount + (self.contingency_amount or 0)

    def save(self, *args, **kwargs):
        # Auto-set first payment if funding is allocated but payment details blank
        if self.funding_amount and not self.first_payment_amount:
            # Calculate contingency portion from commitment percentage if project exists
            project = self.projects.first()
            if project and project.contingency_percentage:
                contingency_portion = self.funding_amount * project.contingency_percentage
                payment_amount = self.funding_amount - contingency_portion + (self.contingency_amount or 0)
                self.first_payment_amount = payment_amount.quantize(Decimal('0.01'))
            else:
                # Default: 90% of total as first payment
                self.first_payment_amount = (self.funding_amount * Decimal('0.9')).quantize(Decimal('0.01'))

            # Set release date and reference
            if not self.first_release_date:
                self.first_release_date = timezone.now().date() + timezone.timedelta(days=30)
            if not self.first_reference_number:
                self.first_reference_number = f"FS-{self.funding_schedule_number}-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.council} - {self.funding_schedule_number}"


class Project(models.Model):
    STATE_CHOICES = [
        ("prospective", "Prospective"),
        ("programmed", "Programmed"),
        ("funded", "Funded"),
        ("commenced", "Commenced"),
        ("under_construction", "Under Construction"),
        ("completed", "Completed"),
    ]

    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name="projects")
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="projects")
    funding_schedule = models.ForeignKey(FundingSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    funding_schedule_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    contingency_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    principal_officer = models.CharField(max_length=255, blank=True, null=True)
    senior_officer = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    stage1_target = models.DateField(blank=True, null=True)
    stage1_sunset = models.DateField(blank=True, null=True)
    stage2_target = models.DateField(blank=True, null=True)
    stage2_sunset = models.DateField(blank=True, null=True)
    state = models.CharField(max_length=30, choices=STATE_CHOICES, default="prospective")

    # Essential project fields based on master data requirements
    sap_project = models.CharField(max_length=255, blank=True, null=True)
    cli_no = models.CharField(max_length=255, blank=True, null=True, help_text="CLI Number")
    sap_master_project = models.CharField(max_length=255, blank=True, null=True)

    # Management and contractor fields
    PROJECT_MANAGER_CHOICES = [
        ('council', 'Council'),
        ('qbuild', 'QBuild'),
        ('external', 'External Project Manager'),
    ]
    CONTRACTOR_CHOICES = [
        ('council', 'Council'),
        ('qbuild', 'QBuild'),
        ('third_party', 'Third Party Contractor'),
    ]
    project_manager = models.CharField(max_length=50, choices=PROJECT_MANAGER_CHOICES, blank=True, null=True)
    contractor = models.CharField(max_length=50, choices=CONTRACTOR_CHOICES, blank=True, null=True)
    contractor_address = models.TextField(blank=True, null=True)

    # Financial fields
    commitments = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Total funding obtained")
    contingency_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.10'), help_text="Contingency percentage (default 10%)")
    external_manager_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of external project manager")
    contractor_organisation = models.CharField(max_length=255, blank=True, null=True, help_text="Name of third party contractor organisation")
    forecast_final_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    final_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    costs_finalised = models.BooleanField(default=False, help_text="Yes/No for finalised costs")

    # Temporal fields
    handover_forecast = models.DateField(blank=True, null=True)
    handover_actual = models.DateField(blank=True, null=True)
    commencement_loa_forecast = models.DateField(blank=True, null=True)
    commencement_loa_actual = models.DateField(blank=True, null=True)
    date_physically_commenced = models.DateField(blank=True, null=True)
    estimated_completion = models.DateField(blank=True, null=True)
    actual_completion = models.DateField(blank=True, null=True)

    # Indexes for performance
    class Meta:
        indexes = [
            models.Index(fields=['sap_project']),
            models.Index(fields=['contractor']),
        ]

    @property
    def total_funding(self):
        return (self.funding_schedule_amount or 0) + (self.contingency_amount or 0)

    @property
    def calculated_commitments(self):
        """Calculate commitments from funding schedule or estimated amounts"""
        if self.funding_schedule:
            return self.funding_schedule.funding_amount
        return self.contingency_amount or 0  # Fallback to contingency if no funding schedule

    @property
    def calculated_contingency(self):
        """Calculate contingency from commitments and percentage"""
        if self.commitments and self.contingency_percentage:
            return (self.commitments * self.contingency_percentage).quantize(Decimal('0.01'))
        return self.contingency_amount or 0

    @property
    def is_late(self):
        today = timezone.now().date()
        if self.state == 'commenced' and self.stage1_target and today > self.stage1_target:
            return True
        if self.state == 'under_construction' and self.stage2_target and today > self.stage2_target:
            return True
        return False

    @property
    def is_overdue(self):
        today = timezone.now().date()
        if self.state == 'commenced' and self.stage1_sunset and today > self.stage1_sunset:
            return True
        if self.state == 'under_construction' and self.stage2_sunset and today > self.stage2_sunset:
            return True
        return False

    @property
    def is_on_time(self):
        return not self.is_late and not self.is_overdue

    @property
    def program_year(self):
        """Auto-calculate program year from funding schedule first release date"""
        if self.funding_schedule and self.funding_schedule.first_release_date:
            return str(self.funding_schedule.first_release_date.year)
        return str(timezone.now().year)

    def __str__(self):
        return f"{self.name} ({self.council})"


class Address(models.Model):
    # Retained if not merged; but per plan, could be merged
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=255, help_text="Street address")

    # These will default to council's defaults when creating
    suburb = models.CharField(max_length=255, help_text="Suburb/Town")
    postcode = models.CharField(max_length=4, help_text="4-digit postcode")
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
        help_text="Number of outputs (e.g., houses, units) at this address"
    )

    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Budget allocated for this address"
    )

    # Property reference fields for land tenure information
    lot_number = models.CharField(max_length=50, blank=True, null=True)
    plan_number = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., RP3435")
    title_reference = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 5456565")

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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="works")
    address_line = models.CharField(max_length=500, blank=True, null=True)  # Full address
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
    output_quantity = models.IntegerField(default=1)
    bedrooms = models.IntegerField(blank=True, null=True)
    bathrooms = models.IntegerField(blank=True, null=True)
    kitchens = models.IntegerField(blank=True, null=True)

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

    dwellings_count = models.IntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

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
            from dateutil.relativedelta import relativedelta
            expiry = pc_date + relativedelta(months=12)
            today = timezone.now().date()
            return today <= expiry
        return False

    def __str__(self):
        return f"{self.work_type_id.name if self.work_type_id else 'No work type'} - {self.output_type_id.name if self.output_type_id else 'No output type'} ({self.project})"


class WorkStep(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="work_steps")
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name} - {self.work}"


class StageReport(models.Model):
    funding_schedule = models.ForeignKey(FundingSchedule, on_delete=models.CASCADE, related_name="stage_reports")
    stage = models.IntegerField(choices=[(1, "Stage 1"), (2, "Stage 2")])
    submission_date = models.DateField()
    acceptance_date = models.DateField(blank=True, null=True)
    report_file = models.FileField(upload_to="reports/", blank=True, null=True)
    checklist = models.JSONField(default=dict)

    def __str__(self):
        return f"Stage {self.stage} Report for {self.funding_schedule}"


# Existing models retained where still useful
class Instalment(models.Model):
    funding_schedule = models.ForeignKey(FundingSchedule, on_delete=models.CASCADE, related_name="instalments")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid = models.BooleanField(default=False)
    release_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Instalment {self.amount} due {self.due_date} - {self.payment_reference or 'No ref'}"


class MonthlyTracker(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="monthly_trackers", null=True, blank=True)
    month = models.DateField(default=timezone.now)
    progress_notes = models.TextField(blank=True, null=True)

    # Design Phase
    design_tender_date = models.DateField(blank=True, null=True)
    design_award_date = models.DateField(blank=True, null=True)

    # Tender and Award Phase
    construction_tender_date = models.DateField(blank=True, null=True)
    construction_award_date = models.DateField(blank=True, null=True)

    # Utilities and Services
    ergon_connection_application_date = models.DateField(blank=True, null=True)
    ergon_connection_date = models.DateField(blank=True, null=True)

    # Site Preparation
    site_establishment_date = models.DateField(blank=True, null=True)
    earthworks_date = models.DateField(blank=True, null=True)
    slab_date = models.DateField(blank=True, null=True)
    underground_services_date = models.DateField(blank=True, null=True)

    # Foundation and Structure
    termite_prevention_date = models.DateField(blank=True, null=True)
    sub_floor_framing_concrete_date = models.DateField(blank=True, null=True)
    end_of_year_shutdown = models.DateField(blank=True, null=True)
    wall_frames_masonry_date = models.DateField(blank=True, null=True)

    # Roof Structure
    roof_framing_battens_date = models.DateField(blank=True, null=True)
    roof_sheeting_date = models.DateField(blank=True, null=True)
    fascia_gutter_date = models.DateField(blank=True, null=True)
    soffit_linings_gables_date = models.DateField(blank=True, null=True)

    # Services Rough-in
    plumbing_electrical_rough_in_date = models.DateField(blank=True, null=True)

    # Internal Finishes
    internal_wall_ceiling_linings_date = models.DateField(blank=True, null=True)
    internal_floor_coverings_date = models.DateField(blank=True, null=True)
    carpentry_2nd_fix_date = models.DateField(blank=True, null=True)
    wet_area_wall_linings_date = models.DateField(blank=True, null=True)
    joinery_install_date = models.DateField(blank=True, null=True)
    internal_painting_date = models.DateField(blank=True, null=True)

    # Exterior Elements
    external_doors_windows_date = models.DateField(blank=True, null=True)
    external_decks_stairs_balustrade_date = models.DateField(blank=True, null=True)

    # Waterproofing
    waterproofing_date = models.DateField(blank=True, null=True)

    # Final Touches
    external_painting_date = models.DateField(blank=True, null=True)
    electrical_fit_off_date = models.DateField(blank=True, null=True)
    plumbing_fit_off_date = models.DateField(blank=True, null=True)
    carpentry_3rd_fix_date = models.DateField(blank=True, null=True)

    # Site Completion
    fencing_gates_date = models.DateField(blank=True, null=True)
    clothesline_date = models.DateField(blank=True, null=True)
    driveway_paths_date = models.DateField(blank=True, null=True)
    shed_date = models.DateField(blank=True, null=True)
    site_clean_date = models.DateField(blank=True, null=True)
    final_internal_clean_handover_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.work} - {self.month.strftime('%B %Y')}"

    @property
    def month_display(self):
        """Auto-generate month display like 'August 2024'"""
        return self.month.strftime('%B %Y')

    def copy_from_previous(self):
        """Copy data from the previous month's report for this work"""
        previous_month = self.month - timezone.timedelta(days=30)
        try:
            previous_report = MonthlyTracker.objects.get(
                work=self.work,
                month__year=previous_month.year,
                month__month=previous_month.month
            )
            # Copy all the date fields from previous report
            date_fields = [
                'design_tender_date', 'design_award_date', 'construction_tender_date',
                'construction_award_date', 'ergon_connection_application_date',
                'ergon_connection_date', 'site_establishment_date', 'earthworks_date',
                'slab_date', 'underground_services_date', 'termite_prevention_date',
                'sub_floor_framing_concrete_date', 'end_of_year_shutdown',
                'wall_frames_masonry_date', 'roof_framing_battens_date',
                'roof_sheeting_date', 'fascia_gutter_date', 'soffit_linings_gables_date',
                'plumbing_electrical_rough_in_date', 'internal_wall_ceiling_linings_date',
                'internal_floor_coverings_date', 'carpentry_2nd_fix_date',
                'wet_area_wall_linings_date', 'joinery_install_date', 'internal_painting_date',
                'external_doors_windows_date', 'external_decks_stairs_balustrade_date',
                'waterproofing_date', 'external_painting_date', 'electrical_fit_off_date',
                'plumbing_fit_off_date', 'carpentry_3rd_fix_date', 'fencing_gates_date',
                'clothesline_date', 'driveway_paths_date', 'shed_date', 'site_clean_date',
                'final_internal_clean_handover_date'
            ]
            for field_name in date_fields:
                if hasattr(previous_report, field_name):
                    setattr(self, field_name, getattr(previous_report, field_name))
            return True
        except MonthlyTracker.DoesNotExist:
            return False


class QuarterlyReport(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="quarterly_reports", null=True, blank=True)
    quarter = models.CharField(max_length=20, default="")  # Auto-generated like "Jan-Mar 2024"
    submission_date = models.DateField(default=timezone.now)

    # Progress Tracking
    percentage_works_completed = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    total_expenditure_council = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    unspent_funding_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # Employment Statistics
    total_employed_people = models.PositiveIntegerField(blank=True, null=True)
    total_indigenous_employed = models.PositiveIntegerField(blank=True, null=True)
    comments_indigenous_employment = models.TextField(blank=True, null=True)

    # Project Status
    practical_completion_forecast_date = models.DateField(blank=True, null=True)
    practical_completion_actual_date = models.DateField(blank=True, null=True)

    # Issues and Contributions
    adverse_matters = models.TextField(blank=True, null=True)
    council_contributions_details = models.TextField(blank=True, null=True)
    other_contributions_details = models.TextField(blank=True, null=True)
    council_contributions_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    other_contributions_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # Additional summary/notes
    # Additional summary/notes
    summary_notes = models.TextField(blank=True, null=True)

    # Supporting documents
    supporting_document_1 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 1")
    supporting_document_2 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 2")
    supporting_document_3 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 3")
    supporting_document_description = models.TextField(blank=True, null=True, help_text="Description of supporting documents")
    summary_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Auto-generate quarter field"""
        if not self.quarter:
            date = self.submission_date or timezone.now()
            year = date.year
            month = date.month
            if 1 <= month <= 3:
                self.quarter = f"Jan-Mar {year}"
            elif 4 <= month <= 6:
                self.quarter = f"Apr-Jun {year}"
            elif 7 <= month <= 9:
                self.quarter = f"Jul-Sep {year}"
            elif 10 <= month <= 12:
                self.quarter = f"Oct-Dec {year}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.work} - {self.quarter}"

    @property
    def total_contributions(self):
        contributions = Decimal('0.00')
        if self.council_contributions_amount:
            contributions += self.council_contributions_amount
        if self.other_contributions_amount:
            contributions += self.other_contributions_amount
        return contributions

    @property
    def unspent_funding(self):
        """Calculate unspent funding for this work"""
        if self.work.estimated_cost and self.total_expenditure_council:
            return self.work.estimated_cost - self.total_expenditure_council
        return None

    # Project-level aggregation properties for summary reporting
    @classmethod
    def get_project_quarterly_summary(cls, project, quarter_str):
        """Get aggregated summary for all works in a project for a specific quarter"""
        reports = cls.objects.filter(work__project=project, quarter=quarter_str)

        if not reports:
            return {}

        summary = {
            'works_completed_avg': reports.aggregate(avg=models.Avg('percentage_works_completed'))['avg'] or 0,
            'total_budget': sum(report.work.estimated_cost or 0 for report in reports),
            'total_expenditure': reports.aggregate(total=models.Sum('total_expenditure_council'))['total'] or 0,
            'total_unspent': sum((report.unspent_funding or 0) for report in reports),
            'total_employed': reports.aggregate(total=models.Sum('total_employed_people'))['total'] or 0,
            'total_indigenous': reports.aggregate(total=models.Sum('total_indigenous_employed'))['total'] or 0,
            'work_reports': reports
        }

        return summary

    @property
    def project(self):
        """Convenience property to get the project"""
        return self.work.project


class ReportAttachment(models.Model):
    # Generic attachment model that can be linked to various reports and tasks
    quarterly_report = models.ForeignKey('QuarterlyReport', on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    monthly_tracker = models.ForeignKey('MonthlyTracker', on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    step_completion = models.ForeignKey('StepTaskCompletion', on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    # Can add more report type foreign keys as needed

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="reports/attachments/%Y/%m/")
    description = models.TextField(blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.file.name}"


class StepTask(models.Model):
    # Generic step task for stage 1 and stage 2 reports
    TASK_TYPES = [
        ('construction_stage1', 'Construction Stage 1'),
        ('land_stage1', 'Land Stage 1'),
        ('construction_stage2', 'Construction Stage 2'),
        ('land_stage2', 'Land Stage 2'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    order = models.PositiveIntegerField(default=1)
    required_evidence = models.TextField(blank=True, null=True)  # Describes what evidence is needed
    completed = models.BooleanField(default=False)
    completion_date = models.DateField(blank=True, null=True)
    state_accepted = models.BooleanField(default=False)
    state_acceptance_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['task_type', 'order']

    def __str__(self):
        return f"{self.task_type}: {self.name}"


class StepTaskCompletion(models.Model):
    # Tracks completion of step tasks by projects, with evidence
    step_task = models.ForeignKey(StepTask, on_delete=models.CASCADE, related_name="completions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="step_completions")
    completed_date = models.DateField(blank=True, null=True)
    evidence_notes = models.TextField(blank=True, null=True)
    # Evidence attachments will be handled through separate attachment model

    def __str__(self):
        return f"{self.project} - {self.step_task.name}"


class WorkSchedule(models.Model):
    # Schedule of Works for Stage 2 Construction
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="work_schedules")
    stage_name = models.CharField(max_length=255)  # e.g., "Site preparation", "Base/slab", "Framing", etc.
    planned_start_date = models.DateField(blank=True, null=True)
    planned_end_date = models.DateField(blank=True, null=True)
    actual_start_date = models.DateField(blank=True, null=True)
    actual_end_date = models.DateField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project} - {self.stage_name}"


class PracticalCompletion(models.Model):
    # Practical Completion tracking
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="practical_completions")
    completion_date = models.DateField(blank=True, null=True)
    notified_to_state = models.BooleanField(default=False)
    notification_date = models.DateField(blank=True, null=True)
    state_acknowledged = models.BooleanField(default=False)
    acknowledgment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Practical Completion - {self.project}"


class Stage2Report(models.Model):
    REPORT_TYPES = [
        ('construction', 'Construction'),
        ('land', 'Land'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stage2_reports")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='construction')
    submission_date = models.DateField()
    state_accepted = models.BooleanField(default=False)
    acceptance_date = models.DateField(blank=True, null=True)

    # For Construction projects - Schedule of Works
    schedule_provided = models.BooleanField(default=False)
    schedule_provided_date = models.DateField(blank=True, null=True)

    # Reporting compliance
    quarterly_reports_provided = models.BooleanField(default=False)
    monthly_trackers_provided = models.BooleanField(default=False)

    # Practical Completion
    practical_completion_achieved = models.BooleanField(default=False)
    practical_completion_date = models.DateField(blank=True, null=True)
    practical_completion_notification_sent = models.BooleanField(default=False)
    notification_date = models.DateField(blank=True, null=True)

    # Handover requirements
    handover_requirements_met = models.BooleanField(default=False)
    handover_checklist_completed = models.BooleanField(default=False)
    handover_checklist_document = models.FileField(upload_to="reports/stage2/handover/", blank=True, null=True)
    warranties_provided = models.BooleanField(default=False)
    warranties_document = models.FileField(upload_to="reports/stage2/warranties/", blank=True, null=True)
    final_plans_provided = models.BooleanField(default=False)
    final_plans_document = models.FileField(upload_to="reports/stage2/plans/", blank=True, null=True)
    joint_inspection_completed = models.BooleanField(default=False)
    joint_inspection_date = models.DateField(blank=True, null=True)

    # Land works completion
    land_works_completed = models.BooleanField(default=False)

    # Additional documentation and notes
    completion_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Stage 2 Report ({self.get_report_type_display()}) - {self.project}"

    @property
    def is_complete(self):
        if self.report_type == 'construction':
            return (self.schedule_provided and
                    self.quarterly_reports_provided and
                    self.monthly_trackers_provided and
                    self.practical_completion_achieved and
                    self.handover_requirements_met and
                    self.handover_checklist_completed)
        else:  # land
            return (self.quarterly_reports_provided and
                    self.monthly_trackers_provided and
                    self.practical_completion_achieved and
                    self.handover_requirements_met and
                    self.land_works_completed)


class Stage1Report(models.Model):
    REPORT_TYPES = [
        ('construction', 'Construction'),
        ('land', 'Land'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stage1_reports")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='construction')
    submission_date = models.DateField()
    state_accepted = models.BooleanField(default=False)
    acceptance_date = models.DateField(blank=True, null=True)

    # Administrative fields
    expenditure_records_maintained = models.BooleanField(default=False)
    quarterly_reports_provided = models.BooleanField(default=False)

    # Land and Works Documentation
    land_description_document = models.FileField(upload_to="reports/stage1/land/", blank=True, null=True)
    works_description_document = models.FileField(upload_to="reports/stage1/works/", blank=True, null=True)
    land_title_document = models.FileField(upload_to="reports/stage1/land_title/", blank=True, null=True)

    # Legal and Compliance
    native_title_addressed = models.BooleanField(default=False)
    native_title_documentation = models.FileField(upload_to="reports/stage1/native_title/", blank=True, null=True)
    heritage_matters_addressed = models.BooleanField(default=False)
    heritage_documentation = models.FileField(upload_to="reports/stage1/heritage/", blank=True, null=True)

    # Approvals and Permits
    development_approval_obtained = models.BooleanField(default=False)
    development_approval_document = models.FileField(upload_to="reports/stage1/dev_approval/", blank=True, null=True)
    tenure_obtained = models.BooleanField(default=False)
    tenure_document = models.FileField(upload_to="reports/stage1/tenure/", blank=True, null=True)
    land_surveyed = models.BooleanField(default=False)
    survey_document = models.FileField(upload_to="reports/stage1/survey/", blank=True, null=True)

    # Subdivision (for land projects)
    subdivision_required = models.BooleanField(default=False)
    subdivision_plan_prepared = models.BooleanField(default=False)
    subdivision_plan_document = models.FileField(upload_to="reports/stage1/subdivision/", blank=True, null=True)

    # Design
    design_approved = models.BooleanField(default=False)
    design_document_proposed = models.FileField(upload_to="reports/stage1/design/", blank=True, null=True)
    design_document_approved = models.FileField(upload_to="reports/stage1/design/", blank=True, null=True)
    structural_certification_obtained = models.BooleanField(default=False)
    structural_certification_document = models.FileField(upload_to="reports/stage1/structural/", blank=True, null=True)

    # Tenders and Contractors
    tenders_called = models.BooleanField(default=False)
    contractor_appointed = models.BooleanField(default=False)
    contractor_details = models.TextField(blank=True, null=True)
    council_contractors_used = models.BooleanField(default=False)

    # Building and Infrastructure Approvals
    building_approval_obtained = models.BooleanField(default=False)
    building_approval_document = models.FileField(upload_to="reports/stage1/building_approval/", blank=True, null=True)
    infrastructure_approvals_obtained = models.BooleanField(default=False)
    infrastructure_documentation = models.FileField(upload_to="reports/stage1/infrastructure/", blank=True, null=True)

    # Additional notes
    completion_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Stage 1 Report ({self.get_report_type_display()}) - {self.project}"

    @property
    def is_complete(self):
        if self.report_type == 'construction':
            return (self.expenditure_records_maintained and
                    self.native_title_addressed and
                    self.development_approval_obtained and
                    self.tenure_obtained and
                    self.design_approved and
                    self.contractors_appointed and
                    self.building_approval_obtained)
        else:  # land
            return (self.expenditure_records_maintained and
                    self.native_title_addressed and
                    self.tenure_obtained and
                    self.subdivision_plan_prepared and
                    self.design_approved and
                    self.contractors_appointed and
                    self.infrastructure_approvals_obtained)


class WorkProgress(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="progress")
    date = models.DateField()
    status = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.work} - {self.status}"


class Defect(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="defects")
    description = models.TextField()
    identified_date = models.DateField()
    rectified_date = models.DateField(blank=True, null=True)

    def get_practical_completion_date(self):
        # Get practical completion from project's practical completions
        practical_completion = self.work.project.practical_completions.first()
        if practical_completion and practical_completion.completion_date:
            return practical_completion.completion_date
        # Fallback to quarterly reports
        quarterly_reports = self.work.quarterly_reports.filter(practical_completion_actual_date__isnull=False).order_by('-submission_date')
        if quarterly_reports.exists():
            return quarterly_reports.first().practical_completion_actual_date
        # Another fallback: Stage2Report
        stage2_reports = self.work.project.stage2_reports.filter(practical_completion_date__isnull=False).order_by('-submission_date')
        if stage2_reports.exists():
            return stage2_reports.first().practical_completion_date
        return None

    @property
    def expiry_date(self):
        from dateutil.relativedelta import relativedelta
        pc_date = self.get_practical_completion_date()
        if pc_date:
            return pc_date + relativedelta(months=12)
        return None

class FundingApproval(models.Model):
    mincor_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    approved_by = models.CharField(max_length=255)  # Position/role
    approved_date = models.DateField()
    projects = models.ManyToManyField('Project', related_name='funding_approvals')

    def __str__(self):
        return f"Approval {self.mincor_reference} - ${self.amount}"

    class Meta:
        ordering = ['-approved_date']


class MonthlyReport(models.Model):
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('more_info', 'More Info Requested'),
    ]

    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='monthly_reports')
    period = models.DateField(help_text="First day of the month")
    council_comments = models.TextField(blank=True)
    ricd_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='more_info')
    ricd_comments = models.TextField(blank=True)

    class Meta:
        unique_together = ('council', 'period')
        ordering = ['-period']

    def __str__(self):
        return f"{self.council} Monthly Report - {self.period.strftime('%B %Y')}"


class CouncilQuarterlyReport(models.Model):
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('more_info', 'More Info Requested'),
    ]

    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='council_quarterly_reports')
    period = models.DateField(help_text="First day of the quarter, e.g., Jan 1, Apr 1, Jul 1, Oct 1")
    council_comments = models.TextField(blank=True)
    ricd_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='more_info')
    ricd_comments = models.TextField(blank=True)

    class Meta:
        unique_together = ('council', 'period')
        ordering = ['-period']

    def __str__(self):
        # Determine quarter
        month = self.period.month
        year = self.period.year
        if 1 <= month <= 3:
            quarter = "Q1"
        elif 4 <= month <= 6:
            quarter = "Q2"
        elif 7 <= month <= 9:
            quarter = "Q3"
        else:
            quarter = "Q4"
        return f"{self.council} Council Quarterly Report - {quarter} {year}"

# Signals for automation
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=StageReport)
def update_project_state(sender, instance, **kwargs):
    project = instance.funding_schedule.projects.first()  # Assuming one project per schedule
    if project:
        if instance.acceptance_date:
            if instance.stage == 1:
                project.state = "commenced"
            elif instance.stage == 2:
                project.state = "completed"
        else:
            if instance.stage == 2:
                project.state = "under_construction"
        project.save()

@receiver(post_save, sender=Instalment)
def update_project_funded(sender, instance, **kwargs):
    project = instance.funding_schedule.projects.first()
    if project and project.state == 'prospective' and (instance.paid or instance.release_date):
        project.state = "funded"
        project.save()

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
    
    
    # Dynamic User Extensions
    # Monkey patch the User model to add council property
    def user_council_property(self):
        """Dynamic property to get user's council from profile"""
        try:
            return self.profile.council
        except:
            return None
    
    User.council = property(user_council_property)
