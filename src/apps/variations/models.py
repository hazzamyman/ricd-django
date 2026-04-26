from django.db import models
from django.contrib.auth.models import User


class VariationType(models.Model):
    """Predefined variation type templates"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    option_number = models.CharField(max_length=10, blank=True, help_text="e.g., Option 1, Option 2")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Variation Types'
        ordering = ['option_number', 'name']

    def __str__(self):
        return f"{self.option_number} - {self.name}" if self.option_number else self.name


class Variation(models.Model):
    """Main variation document for a funding schedule"""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        COUNCIL_SIGNED = 'COUNCIL_SIGNED', 'Council Signed'
        EXECUTED = 'EXECUTED', 'Executed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class VariationOption(models.TextChoices):
        OPTION_1_ADD_FS = 'OPTION_1', 'Add Funding Schedule'
        OPTION_2_REMOVE_FS = 'OPTION_2', 'Remove Funding Schedule'
        OPTION_3_CONTACT_DETAILS = 'OPTION_3', 'Change Contact Details'
        OPTION_4_REPLACE_FS = 'OPTION_4', 'Replace Funding Schedule'
        OPTION_5_DATES = 'OPTION_5', 'Vary Funding Schedule Dates'
        OPTION_6_SCOPE = 'OPTION_6', 'Vary Scope of Works'
        OPTION_7_LAND = 'OPTION_7', 'Vary Land'
        OPTION_8_FUNDING = 'OPTION_8', 'Vary Funding'
        OPTION_9_REPORTING = 'OPTION_9', 'Vary Reporting Requirements'
        OPTION_OTHER = 'OPTION_OTHER', 'Other'

    funding_schedule = models.ForeignKey('funding.FundingSchedule', related_name='variations', on_delete=models.CASCADE, verbose_name="Primary Funding Schedule", null=True, blank=True)
    funding_schedules = models.ManyToManyField('funding.FundingSchedule', related_name='variation_changes', blank=True, help_text="Multiple FS can be affected by one variation")
    projects = models.ManyToManyField('projects.Project', related_name='variations', blank=True)
    land_projects = models.ManyToManyField('land_infra.LandProject', related_name='variations', blank=True)
    variation_type = models.ForeignKey(VariationType, on_delete=models.SET_NULL, null=True, blank=True)
    variation_option = models.CharField(max_length=20, choices=VariationOption.choices, blank=True, help_text="The specific variation option type")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    council_signed_date = models.DateField(null=True, blank=True)
    department_executed_date = models.DateField(null=True, blank=True)
    document_link = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    # Reporting requirements (Option 9)
    reporting_requirements = models.JSONField(blank=True, default=dict, help_text="Required report items: monthly, quarterly, stage1, stage2")
    
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        fs = self.funding_schedule
        project_name = fs.project.name if fs and fs.project else (fs.land_project.name if fs and fs.land_project else 'No Project')
        return f"Variation {self.id} - {project_name} ({self.get_status_display()})"

    @property
    def linked_projects(self):
        """Returns all linked projects (both dwelling and land)"""
        return list(self.projects.all()) + list(self.land_projects.all())


class VariationFundingSchedule(models.Model):
    """Additional funding schedules involved in a variation"""
    class LinkType(models.TextChoices):
        ORIGINAL = 'ORIGINAL', 'Original'
        REPLACEMENT = 'REPLACEMENT', 'Replacement'
        ADDED = 'ADDED', 'Added'
        REMOVED = 'REMOVED', 'Removed'

    variation = models.ForeignKey(Variation, related_name='additional_funding_schedules', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('funding.FundingSchedule', on_delete=models.CASCADE)
    link_type = models.CharField(max_length=20, choices=LinkType.choices, help_text="Relationship to this variation")
    scope_of_works = models.TextField(blank=True, help_text="Description of works for this funding schedule")

    def __str__(self):
        return f"{self.get_link_type_display()}: {self.funding_schedule}"


class VariationContactDetails(models.Model):
    """Contact details variation (Option 3)"""
    variation = models.ForeignKey(Variation, related_name='contact_details', on_delete=models.CASCADE)
    
    attention = models.CharField(max_length=255, blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    is_state_contact = models.BooleanField(default=True, help_text="If True, this is State contact. If False, Council contact.")
    is_new = models.BooleanField(default=True, help_text="If True, this is new contact. If False, this is original.")

    def __str__(self):
        return f"{'State' if self.is_state_contact else 'Council'} Contact ({'New' if self.is_new else 'Original'})"


class VariationDateChange(models.Model):
    """Date changes for Funding Schedule (Option 5)"""
    class DateType(models.TextChoices):
        STAGE1_TARGET = 'STAGE1_TARGET', 'Stage 1 Target Date'
        STAGE2_TARGET = 'STAGE2_TARGET', 'Stage 2 Target Date'
        STAGE1_SUNSET = 'STAGE1_SUNSET', 'Stage 1 Sunset Date'
        STAGE2_SUNSET = 'STAGE2_SUNSET', 'Stage 2 Sunset Date'
        COMPLETION = 'COMPLETION', 'Completion Date'
        OTHER = 'OTHER', 'Other Date'

    variation = models.ForeignKey(Variation, related_name='date_changes', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('funding.FundingSchedule', on_delete=models.CASCADE)
    date_type = models.CharField(max_length=20, choices=DateType.choices)
    original_date = models.DateField(null=True, blank=True)
    new_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_date_type_display()}: {self.original_date} → {self.new_date}"


class VariationScopeChange(models.Model):
    """Scope of works changes (Option 6)"""
    variation = models.ForeignKey(Variation, related_name='scope_changes', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('funding.FundingSchedule', on_delete=models.CASCADE)
    
    original_scope = models.TextField(blank=True, help_text="Original scope of works")
    new_scope = models.TextField(blank=True, help_text="New scope of works")
    annexure_reference = models.CharField(max_length=255, blank=True, help_text="Reference to attached annexure if applicable")

    def __str__(self):
        return f"Scope Change for FS {self.funding_schedule.id}"


class VariationLandChange(models.Model):
    """Land changes (Option 7)"""
    variation = models.ForeignKey(Variation, related_name='land_changes', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('funding.FundingSchedule', on_delete=models.CASCADE)
    
    original_lot = models.CharField(max_length=100, blank=True)
    original_plan = models.CharField(max_length=100, blank=True)
    original_title_reference = models.CharField(max_length=100, blank=True)
    original_street_address = models.TextField(blank=True)
    
    new_lot = models.CharField(max_length=100, blank=True)
    new_plan = models.CharField(max_length=100, blank=True)
    new_title_reference = models.CharField(max_length=100, blank=True)
    new_street_address = models.TextField(blank=True)
    
    annexure_reference = models.CharField(max_length=255, blank=True, help_text="Reference to attached annexure")

    def __str__(self):
        return f"Land Change: {self.original_street_address or 'N/A'} → {self.new_street_address or 'N/A'}"


class VariationFundingChange(models.Model):
    """Funding amount and payment changes (Option 8)"""
    variation = models.ForeignKey(Variation, related_name='funding_changes', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('funding.FundingSchedule', on_delete=models.CASCADE)
    
    original_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    
    payment_number = models.PositiveIntegerField(null=True, blank=True, help_text="Which payment is being changed")
    original_payment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_payment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    @property
    def funding_difference(self):
        if self.original_amount and self.new_amount:
            return self.new_amount - self.original_amount
        return None

    def __str__(self):
        return f"Funding Change: ${self.original_amount} → ${self.new_amount}"


class VariationReportingChange(models.Model):
    """Reporting requirement changes (Option 9)"""
    class ReportType(models.TextChoices):
        MONTHLY_TRACKER = 'MONTHLY_TRACKER', 'Monthly Tracker Report'
        QUARTERLY_REPORT = 'QUARTERLY_REPORT', 'Quarterly Report'
        STAGE1_REPORT = 'STAGE1_REPORT', 'Stage 1 Report'
        STAGE2_REPORT = 'STAGE2_REPORT', 'Stage 2 Report'
        OTHER = 'OTHER', 'Other Report'

    variation = models.ForeignKey(Variation, related_name='reporting_changes', on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    
    original_clause = models.TextField(blank=True, help_text="Original clause text")
    new_clause = models.TextField(blank=True, help_text="New clause text")
    attachment_reference = models.CharField(max_length=255, blank=True, help_text="Reference to attachment describing the variation")

    def __str__(self):
        return f"{self.get_report_type_display()} Reporting Change"


class VariationItem(models.Model):
    """Change items for a variation - each item represents a specific option change"""
    class OptionType(models.TextChoices):
        OPTION_1 = 'OPTION_1', 'Add Funding Schedule'
        OPTION_2 = 'OPTION_2', 'Remove Funding Schedule'
        OPTION_3 = 'OPTION_3', 'Change Contact Details'
        OPTION_4 = 'OPTION_4', 'Replace Funding Schedule'
        OPTION_5 = 'OPTION_5', 'Vary Dates'
        OPTION_6 = 'OPTION_6', 'Vary Scope of Works'
        OPTION_7 = 'OPTION_7', 'Vary Land'
        OPTION_8 = 'OPTION_8', 'Vary Funding'
        OPTION_9 = 'OPTION_9', 'Vary Reporting Requirements'
        OTHER = 'OTHER', 'Other'

    variation = models.ForeignKey(Variation, related_name='items', on_delete=models.CASCADE)
    option = models.CharField(max_length=20, choices=OptionType.choices, help_text="Which document option this implements")
    description = models.TextField(blank=True)
    
    # Entity references
    funding_schedule = models.ForeignKey('funding.FundingSchedule', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    funding_schedules = models.ManyToManyField('funding.FundingSchedule', related_name='+', blank=True, help_text="For multi-FS options")
    projects = models.ManyToManyField('projects.Project', related_name='+', blank=True)
    address = models.ForeignKey('addresses.Address', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    work = models.ForeignKey('works.Work', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    council = models.ForeignKey('councils.Council', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Option-specific fields (JSON for flexibility)
    details = models.JSONField(blank=True, default=dict, help_text="Option-specific details stored as JSON")
    
    # For Option 3 - Contact details
    state_contact_details = models.JSONField(blank=True, default=dict, help_text="State contact: attention, phone, email, address")
    council_contact_name = models.CharField(max_length=255, blank=True)
    council_contact_phone = models.CharField(max_length=50, blank=True)
    council_contact_email = models.EmailField(blank=True)
    update_council_contact = models.BooleanField(default=False, help_text="Also update council contact")
    
    # For Option 5 - Dates
    stage1_target_date = models.DateField(null=True, blank=True)
    stage2_target_date = models.DateField(null=True, blank=True)
    stage1_sunset_date = models.DateField(null=True, blank=True)
    stage2_sunset_date = models.DateField(null=True, blank=True)
    
    # For Option 6 - Scope
    original_scope = models.TextField(blank=True)
    new_scope = models.TextField(blank=True)
    
    # For Option 7 - Land
    land_lot = models.CharField(max_length=100, blank=True)
    land_plan = models.CharField(max_length=100, blank=True)
    land_title_reference = models.CharField(max_length=100, blank=True)
    land_street_address = models.TextField(blank=True)
    land_annexure_ref = models.CharField(max_length=255, blank=True)
    
    # For Option 8 - Funding
    original_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    original_contingency = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_contingency = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    original_payment_split = models.CharField(max_length=20, blank=True)
    new_payment_split = models.CharField(max_length=20, blank=True)
    
    # For Option 9 - Reporting
    monthly_required = models.BooleanField(default=False)
    quarterly_required = models.BooleanField(default=False)
    stage1_required = models.BooleanField(default=False)
    stage2_required = models.BooleanField(default=False)
    reporting_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.get_option_display()} - {self.id}"


class ProjectChangeLog(models.Model):
    """Auto-captured changes from projects that need variation approval"""
    class ChangeSource(models.TextChoices):
        PROJECT = 'PROJECT', 'Project'
        ADDRESS = 'ADDRESS', 'Address'
        WORK = 'WORK', 'Work'
        FUNDING_SCHEDULE = 'FUNDING_SCHEDULE', 'Funding Schedule'
        PAYMENT = 'PAYMENT', 'Payment'

    project = models.ForeignKey('projects.Project', related_name='change_logs', on_delete=models.CASCADE)
    variation = models.ForeignKey(Variation, null=True, blank=True, related_name='captured_changes', on_delete=models.SET_NULL)
    
    change_source = models.CharField(max_length=20, choices=ChangeSource.choices)
    source_id = models.PositiveIntegerField(help_text="ID of the source object (address, work, etc)")
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    is_captured = models.BooleanField(default=False, help_text="Whether this change has been added to a variation")
    captured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_change_source_display()}: {self.field_name} changed for Project {self.project.id}"


class VariationExecutionLog(models.Model):
    """Audit log of all changes applied when a variation is executed"""
    variation = models.ForeignKey(Variation, related_name='execution_logs', on_delete=models.CASCADE)
    entity = models.CharField(max_length=50, help_text="Entity type (Project, FundingSchedule, Address, Work, Payment)")
    entity_id = models.PositiveIntegerField(help_text="ID of the entity that was changed")
    field_name = models.CharField(max_length=100)
    field_display = models.CharField(max_length=150, blank=True, help_text="Display name for the field")
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name_plural = 'Variation Execution Logs'

    def __str__(self):
        return f"{self.field_display or self.field_name}: {self.old_value} → {self.new_value} (Variation #{self.variation_id})"
