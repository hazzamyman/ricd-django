from django.db import models


class MonthlyTrackerItemGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class MonthlyTrackerItem(models.Model):
    class FieldType(models.TextChoices):
        DATE = 'DATE', 'Date'
        DATE_NA = 'DATE_NA', 'Date or N/A'
        CHECKBOX = 'CHECKBOX', 'Checkbox'
        TEXT = 'TEXT', 'Text'
        NUMBER = 'NUMBER', 'Number'
        CURRENCY = 'CURRENCY', 'Currency'

    group = models.ForeignKey(MonthlyTrackerItemGroup, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.DATE_NA)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    works = models.ManyToManyField('Work', blank=True, related_name='monthly_tracker_items')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()})"


class MonthlyTracker(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ENDORSED = 'ENDORSED', 'Endorsed by Council'
        ASSESSED = 'ASSESSED', 'Assessed by FNC'

    funding_schedule = models.ForeignKey('FundingSchedule', related_name='monthly_trackers', on_delete=models.CASCADE, db_index=True)
    year = models.PositiveIntegerField(db_index=True)
    month = models.PositiveIntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    submitted_at = models.DateTimeField(null=True, blank=True)
    endorsed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='endorsed_monthly_trackers', on_delete=models.SET_NULL)
    endorsed_at = models.DateTimeField(null=True, blank=True)
    assessed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='assessed_monthly_trackers', on_delete=models.SET_NULL)
    assessed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('funding_schedule', 'year', 'month')

    def __str__(self):
        return f"Monthly Tracker {self.year}-{self.month:02d} ({self.funding_schedule.project.name})"


class MonthlyTrackerEntry(models.Model):
    tracker = models.ForeignKey(MonthlyTracker, related_name='entries', on_delete=models.CASCADE)
    item = models.ForeignKey(MonthlyTrackerItem, on_delete=models.CASCADE)
    work = models.ForeignKey('Work', null=True, blank=True, on_delete=models.CASCADE)
    date_value = models.DateField(null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    text_value = models.TextField(blank=True)
    number_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.tracker} - {self.item.name}"


class QuarterlyReportItemGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class QuarterlyReportItem(models.Model):
    class FieldType(models.TextChoices):
        DATE = 'DATE', 'Date'
        NUMBER = 'NUMBER', 'Number'
        CURRENCY = 'CURRENCY', 'Currency'
        TEXT = 'TEXT', 'Text'
        CHECKBOX = 'CHECKBOX', 'Checkbox'
        YES_NO = 'YES_NO', 'Yes/No'
        YES_NO_NA = 'YES_NO_NA', 'Yes/No/N/A'

    group = models.ForeignKey(QuarterlyReportItemGroup, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    works = models.ManyToManyField('Work', blank=True, related_name='quarterly_report_items')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()})"


class QuarterlyReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ENDORSED = 'ENDORSED', 'Endorsed by Council'
        ASSESSED = 'ASSESSED', 'Assessed by FNC'
        APPROVED = 'APPROVED', 'Approved'

    project = models.ForeignKey('Project', related_name='quarterly_reports', on_delete=models.CASCADE, db_index=True)
    year = models.PositiveIntegerField(db_index=True)
    quarter = models.PositiveIntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    submitted_at = models.DateTimeField(null=True, blank=True)
    endorsed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='endorsed_quarterly_reports', on_delete=models.SET_NULL)
    endorsed_at = models.DateTimeField(null=True, blank=True)
    assessed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='assessed_quarterly_reports', on_delete=models.SET_NULL)
    assessed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='approved_quarterly_reports', on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'year', 'quarter')

    def __str__(self):
        return f"Q{self.quarter} {self.year} Report ({self.project.name})"


class QuarterlyReportEntry(models.Model):
    report = models.ForeignKey(QuarterlyReport, related_name='entries', on_delete=models.CASCADE)
    item = models.ForeignKey(QuarterlyReportItem, on_delete=models.CASCADE)
    work = models.ForeignKey('Work', null=True, blank=True, on_delete=models.CASCADE)
    date_value = models.DateField(null=True, blank=True)
    number_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    text_value = models.TextField(blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.report} - {self.item.name}"


class QuarterlyReportAttachment(models.Model):
    report = models.ForeignKey(QuarterlyReport, related_name='attachments', on_delete=models.CASCADE)
    work = models.ForeignKey('Work', on_delete=models.CASCADE)
    file = models.FileField(upload_to='quarterly_reports/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.work} in {self.report}"


class StageReport(models.Model):
    class StageType(models.TextChoices):
        STAGE1 = 'STAGE1', 'Stage 1'
        STAGE2 = 'STAGE2', 'Stage 2'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ENDORSED = 'ENDORSED', 'Endorsed by Council'
        ASSESSED = 'ASSESSED', 'Assessed by FNC'
        APPROVED = 'APPROVED', 'Approved'

    project = models.ForeignKey('Project', related_name='stage_reports', on_delete=models.CASCADE, db_index=True)
    funding_schedule = models.ForeignKey('FundingSchedule', related_name='stage_reports', on_delete=models.SET_NULL, null=True, blank=True, help_text="Funding schedule this report is linked to")
    stage_type = models.CharField(max_length=10, choices=StageType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    submitted_at = models.DateField(null=True, blank=True)
    endorsed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='endorsed_stage_reports', on_delete=models.SET_NULL)
    endorsed_at = models.DateField(null=True, blank=True)
    assessed_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='assessed_stage_reports', on_delete=models.SET_NULL)
    assessed_at = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey('auth.User', null=True, blank=True, related_name='approved_stage_reports', on_delete=models.SET_NULL)
    approved_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'stage_type')

    def __str__(self):
        return f"{self.get_stage_type_display()} Report ({self.project.name})"

    def create_draft_payment(self, funding_schedule):
        """
        Create a draft payment when stage report is submitted.
        Called when Council User submits the report.

        Args:
            funding_schedule: FundingSchedule instance to link payment to

        Returns:
            Payment instance (draft)
        """
        from apps.core.models import Payment

        if self.stage_type == self.StageType.STAGE1:
            payment_type = Payment.PaymentType.SECOND
        elif self.stage_type == self.StageType.STAGE2:
            payment_type = Payment.PaymentType.THIRD
        else:
            return None

        # Calculate amount based on payment split
        split = funding_schedule.total_funding
        if funding_schedule.payment_split == Payment.PaymentSplit.STANDARD:
            amounts = Payment.calculate_standard_split(split)
            amount = amounts['second' if self.stage_type == self.StageType.STAGE1 else 'third']
        else:
            amounts = Payment.calculate_alternative_split(split)
            amount = amounts['second' if self.stage_type == self.StageType.STAGE1 else 'second']

        payment = Payment.objects.create(
            project=self.project,
            funding_schedule=funding_schedule,
            payment_type=payment_type,
            payment_split=funding_schedule.payment_split,
            amount=amount,
            status=Payment.Status.PENDING,
            notes=f"Draft payment created from {self.get_stage_type_display()} Report"
        )
        return payment

    def submit(self, user):
        """Submit the stage report and create draft payment."""
        from django.utils import timezone

        self.status = self.Status.SUBMITTED
        self.submitted_by = user
        self.submitted_at = timezone.now()
        self.save()

        # Create draft payment using the linked funding schedule
        funding_schedule = self.funding_schedule or self.project.funding_schedules.first()
        if funding_schedule:
            self.create_draft_payment(funding_schedule)

    def endorse(self, user):
        """Council Manager endorses the report."""
        from django.utils import timezone

        self.status = self.Status.ENDORSED
        self.endorsed_by = user
        self.endorsed_at = timezone.now()
        self.save()

    def assess(self, user):
        """FNC User assesses the report."""
        from django.utils import timezone

        self.status = self.Status.ASSESSED
        self.assessed_by = user
        self.assessed_at = timezone.now()
        self.save()

    def approve(self, user):
        """FNC Manager approves the report."""
        from django.utils import timezone

        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()


class StageReportItem(models.Model):
    report = models.ForeignKey(StageReport, related_name='items', on_delete=models.CASCADE)
    step_name = models.CharField(max_length=255)
    step_order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    requires_attachment = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"{self.report} - {self.step_name}"


class StageReportAttachment(models.Model):
    item = models.ForeignKey(StageReportItem, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='stage_reports/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.item.step_name}"
