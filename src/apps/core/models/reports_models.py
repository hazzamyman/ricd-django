from django.db import models


class CouncilTrackerConfig(models.Model):
    """Per-council configuration for the monthly tracker (set in Maintenance)."""
    council = models.OneToOneField(
        'Council', related_name='tracker_config', on_delete=models.CASCADE
    )
    council_submission_enabled = models.BooleanField(
        default=False,
        help_text="Allow council users to submit their monthly tracker"
    )
    submission_due_day = models.PositiveSmallIntegerField(
        default=8,
        help_text="Day of the following month by which the council must submit (default 8)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TrackerConfig — {self.council.name}"


class MonthlyTracker(models.Model):
    """One living cumulative report per council per calendar month."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted by Council'
        REVIEWED = 'REVIEWED', 'Reviewed by RICD'

    council = models.ForeignKey(
        'Council', related_name='monthly_trackers', on_delete=models.CASCADE, db_index=True
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    month = models.PositiveSmallIntegerField(db_index=True, help_text="1–12")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    submitted_by = models.ForeignKey(
        'auth.User', null=True, blank=True,
        related_name='submitted_monthly_trackers', on_delete=models.SET_NULL
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'auth.User', null=True, blank=True,
        related_name='reviewed_monthly_trackers', on_delete=models.SET_NULL
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('council', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Monthly Tracker — {self.council.name} {self.year}-{self.month:02d}"

    @property
    def due_date(self):
        import datetime
        try:
            due_day = self.council.tracker_config.submission_due_day
        except Exception:
            due_day = 8
        if self.month == 12:
            return datetime.date(self.year + 1, 1, due_day)
        return datetime.date(self.year, self.month + 1, due_day)

    @property
    def is_overdue(self):
        import datetime
        return datetime.date.today() > self.due_date and self.status == self.Status.DRAFT


class MonthlyTrackerWorkEntry(models.Model):
    """
    One cell per (tracker, work_step).
    Syncs actual_completion_date and forecast_completion_date back to WorkStep.
    Only WorkSteps whose group_item.is_monthly_tracker_column=True appear here.
    """
    tracker = models.ForeignKey(MonthlyTracker, related_name='work_entries', on_delete=models.CASCADE)
    work_step = models.ForeignKey('WorkStep', related_name='tracker_entries', on_delete=models.CASCADE)
    actual_completion_date = models.DateField(
        null=True, blank=True,
        help_text="Set when council ticks the checkbox; cleared when unticked"
    )
    forecast_completion_date = models.DateField(
        null=True, blank=True,
        help_text="Council's forecast if the step is not yet complete"
    )
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tracker', 'work_step')

    def __str__(self):
        return f"{self.tracker} — {self.work_step.step_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Propagate completion dates back to the canonical WorkStep record
        ws = self.work_step
        changed = False
        if ws.actual_completion_date != self.actual_completion_date:
            ws.actual_completion_date = self.actual_completion_date
            ws.completed = self.actual_completion_date is not None
            changed = True
        if ws.forecast_completion_date != self.forecast_completion_date:
            ws.forecast_completion_date = self.forecast_completion_date
            changed = True
        if changed:
            ws.save(update_fields=['actual_completion_date', 'forecast_completion_date', 'completed', 'updated_at'])


class QuarterlyReportItemGroup(models.Model):
    """Configurable group of items for the quarterly report grid (columns)."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class QuarterlyReportItem(models.Model):
    """Configurable item (column) within a group."""

    class FieldType(models.TextChoices):
        DATE = 'DATE', 'Date'
        DATE_NA = 'DATE_NA', 'Date or N/A'
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
    is_active = models.BooleanField(default=True)
    help_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()})"


class QuarterlyReport(models.Model):
    """
    One living quarterly report per council per quarter (auto-derived from period).
    Covers ALL works on active projects (state in COMMENCED, UNDER_CONSTRUCTION)
    for the council during that quarter.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted by Council'
        APPROVED = 'APPROVED', 'Approved'

    council = models.ForeignKey(
        'Council', related_name='quarterly_reports', on_delete=models.CASCADE, db_index=True
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    quarter = models.PositiveSmallIntegerField(db_index=True, help_text="1-4")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    submitted_by = models.ForeignKey(
        'auth.User', null=True, blank=True,
        related_name='submitted_quarterly_reports', on_delete=models.SET_NULL
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'auth.User', null=True, blank=True,
        related_name='approved_quarterly_reports', on_delete=models.SET_NULL
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('council', 'year', 'quarter')
        ordering = ['-year', '-quarter']

    def __str__(self):
        return f"Q{self.quarter} {self.year} -- {self.council.name}"

    @staticmethod
    def quarter_for_month(month):
        """Return quarter (1-4) for a given calendar month (1-12)."""
        return ((month - 1) // 3) + 1

    @property
    def quarter_label(self):
        labels = {1: 'Jan-Mar', 2: 'Apr-Jun', 3: 'Jul-Sep', 4: 'Oct-Dec'}
        return f"{labels.get(self.quarter, '?')} {self.year}"

    @property
    def due_date(self):
        """14 days after quarter end."""
        import datetime
        end_month = self.quarter * 3
        end_year = self.year
        if end_month == 12:
            next_month_start = datetime.date(end_year + 1, 1, 1)
        else:
            next_month_start = datetime.date(end_year, end_month + 1, 1)
        return next_month_start + datetime.timedelta(days=13)  # 14 days inclusive

    @property
    def is_overdue(self):
        import datetime
        return datetime.date.today() > self.due_date and self.status != self.Status.APPROVED


class QuarterlyReportEntry(models.Model):
    """
    Single cell in the QR grid: (report, work, item) -> value.
    Rows = active Works, Columns = QuarterlyReportItems.
    """
    report = models.ForeignKey(QuarterlyReport, related_name='entries', on_delete=models.CASCADE)
    work = models.ForeignKey('Work', related_name='quarterly_entries', on_delete=models.CASCADE)
    item = models.ForeignKey(QuarterlyReportItem, on_delete=models.CASCADE)

    date_value = models.DateField(null=True, blank=True)
    number_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    text_value = models.TextField(blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    is_na = models.BooleanField(default=False, help_text="Mark cell as N/A when item supports it")
    updated_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('report', 'work', 'item')

    def __str__(self):
        return f"{self.report} -- {self.work} -- {self.item.name}"


class QuarterlyReportAttachment(models.Model):
    """Up to ~3 documents per Work per report (linked to OpenDocs/Drive)."""
    report = models.ForeignKey(QuarterlyReport, related_name='attachments', on_delete=models.CASCADE)
    work = models.ForeignKey('Work', null=True, blank=True, related_name='quarterly_attachments', on_delete=models.CASCADE)
    document_uri = models.URLField(blank=True, help_text='Link to attachment in OpenDocs/Google Drive')
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.report}"


class StageReport(models.Model):
    """
    Per-project Stage 1 or Stage 2 report.

    Linked to exactly ONE of: FundingSchedule, InterimFRPAgreement, or ForwardRPFAgreement
    (XOR enforced via CHECK constraint). Items populated from the project's pre-assigned
    StageItemGroup (project.stage1_item_group or project.stage2_item_group).
    """

    class StageType(models.TextChoices):
        STAGE1 = 'STAGE1', 'Stage 1'
        STAGE2 = 'STAGE2', 'Stage 2'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ENDORSED = 'ENDORSED', 'Endorsed by Council'
        ASSESSED = 'ASSESSED', 'Assessed by RICD'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    project = models.ForeignKey('Project', related_name='stage_reports', on_delete=models.CASCADE, db_index=True)
    stage_type = models.CharField(max_length=10, choices=StageType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    # XOR linkage: exactly one of these three must be set (enforced via CheckConstraint).
    funding_schedule = models.ForeignKey(
        'FundingSchedule', related_name='stage_reports',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Funding Schedule this report is linked to (use this XOR interim_frp XOR forward_rpf)"
    )
    interim_frp = models.ForeignKey(
        'InterimFRPAgreement', related_name='stage_reports',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Interim Forward Remote Capital Program agreement this report is linked to"
    )
    forward_rpf = models.ForeignKey(
        'ForwardRPFAgreement', related_name='stage_reports',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Forward Remote Capital Program agreement this report is linked to"
    )

    # The item group used to populate this report (snapshot from project.stage1_item_group at open time).
    item_group = models.ForeignKey(
        'StageItemGroup', related_name='instances',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Template group used when this report was opened"
    )

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
        constraints = [
            models.CheckConstraint(
                condition=(
                    # All-nulls allowed (early DRAFT before linkage); otherwise exactly one
                    (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=True)) |
                    (models.Q(funding_schedule__isnull=False) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=True)) |
                    (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=False) & models.Q(forward_rpf__isnull=True)) |
                    (models.Q(funding_schedule__isnull=True) & models.Q(interim_frp__isnull=True) & models.Q(forward_rpf__isnull=False))
                ),
                name='stage_report_agreement_xor'
            ),
        ]

    def __str__(self):
        return f"{self.get_stage_type_display()} Report ({self.project.name})"

    @property
    def agreement(self):
        """Return whichever agreement is linked (FS, Interim, or Forward), or None."""
        return self.funding_schedule or self.interim_frp or self.forward_rpf

    @property
    def agreement_type(self):
        """One of 'FUNDING_SCHEDULE', 'INTERIM_FRP', 'FORWARD_RPF', or None."""
        if self.funding_schedule_id:
            return 'FUNDING_SCHEDULE'
        if self.interim_frp_id:
            return 'INTERIM_FRP'
        if self.forward_rpf_id:
            return 'FORWARD_RPF'
        return None

    def create_draft_payment(self, funding_schedule):
        """Create a draft payment when stage report is submitted (FS path only)."""
        from apps.core.models import Payment

        if self.stage_type == self.StageType.STAGE1:
            payment_type = Payment.PaymentType.SECOND
        elif self.stage_type == self.StageType.STAGE2:
            payment_type = Payment.PaymentType.THIRD
        else:
            return None

        total = funding_schedule.total_funding
        rule = funding_schedule.payment_rule
        milestones = rule.config_json.get('milestones', []) if rule else []
        if milestones:
            idx = 1 if self.stage_type == self.StageType.STAGE1 else 2
            pct = milestones[idx]['percentage'] if idx < len(milestones) else 0
            from decimal import Decimal
            amount = total * Decimal(str(pct)) / Decimal('100')
            payment_split_value = Payment.PaymentSplit.CUSTOM
        else:
            amounts = Payment.calculate_standard_split(total)
            amount = amounts['second' if self.stage_type == self.StageType.STAGE1 else 'third']
            payment_split_value = Payment.PaymentSplit.STANDARD

        payment = Payment.objects.create(
            project=self.project,
            funding_schedule=funding_schedule,
            payment_type=payment_type,
            payment_split=payment_split_value,
            amount=amount,
            status=Payment.Status.PENDING,
            notes=f"Draft payment created from {self.get_stage_type_display()} Report"
        )
        return payment

    def submit(self, user):
        """Council submits the stage report; FS-linked reports also create a draft payment."""
        from django.utils import timezone
        self.status = self.Status.SUBMITTED
        self.submitted_by = user
        self.submitted_at = timezone.now()
        self.save()
        if self.funding_schedule_id:
            self.create_draft_payment(self.funding_schedule)

    def endorse(self, user):
        from django.utils import timezone
        self.status = self.Status.ENDORSED
        self.endorsed_by = user
        self.endorsed_at = timezone.now()
        self.save()

    def assess(self, user):
        from django.utils import timezone
        self.status = self.Status.ASSESSED
        self.assessed_by = user
        self.assessed_at = timezone.now()
        self.save()

    def approve(self, user):
        from django.utils import timezone
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()


class StageReportItem(models.Model):
    """Single cell in a stage report: (report, group_item) -> value(s).

    Field type / requires_attachment come from the group_item (template).
    """
    report = models.ForeignKey(StageReport, related_name='items', on_delete=models.CASCADE)
    group_item = models.ForeignKey(
        'StageItemGroupItem', related_name='report_instances', on_delete=models.PROTECT,
        help_text="Template item this entry is populated from"
    )
    # Value fields (one of these is populated based on group_item.field_type)
    date_value = models.DateField(null=True, blank=True)
    number_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    text_value = models.TextField(blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    is_na = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False, help_text="Convenience flag: derived from value type but explicit for queries")
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['group_item__order']
        unique_together = ('report', 'group_item')

    def __str__(self):
        return f"{self.report} -- {self.group_item.item.name if self.group_item_id else '(unset)'}"


class StageReportAttachment(models.Model):
    """One or more evidence documents per StageReportItem."""
    item = models.ForeignKey(StageReportItem, related_name='attachments', on_delete=models.CASCADE)
    document_uri = models.URLField(blank=True, help_text='Link to attachment in OpenDocs/Google Drive')
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.item}"
