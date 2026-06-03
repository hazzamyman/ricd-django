from datetime import timedelta
from django.db import models
from decimal import Decimal


class Payment(models.Model):
    class CalculationType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage of Funding'
        FIXED = 'FIXED', 'Fixed Amount'
        REIMBURSEMENT = 'REIMBURSEMENT', 'Reimbursement (Actual Expenses)'

    class PaymentType(models.TextChoices):
        FIRST = 'FIRST', 'First Payment'
        SECOND = 'SECOND', 'Second Payment'
        THIRD = 'THIRD', 'Third Payment'
        INTERIM = 'INTERIM', 'Interim Payment'
        FINAL = 'FINAL', 'Final Payment'

    class PaymentSplit(models.TextChoices):
        STANDARD = '30/60/10', 'Standard (30/60/10)'
        ALTERNATIVE = '90/10', 'Alternative (90/10)'
        CUSTOM = 'CUSTOM', 'Custom'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RECOMMENDED = 'RECOMMENDED', 'Recommended'
        APPROVED = 'APPROVED', 'Approved'
        RELEASED = 'RELEASED', 'Released'
        REJECTED = 'REJECTED', 'Rejected'

    class ForecastAnchor(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual (I set the forecast date)'
        SCHEDULED = 'SCHEDULED', 'Scheduled (follows the work group milestone)'

    class DocumentSource(models.TextChoices):
        OPENDOCS = 'OPENDOCS', 'OpenDocs Content Manager'
        SHARED_DRIVE = 'SHARED_DRIVE', 'Shared Network Drive'
        LOCAL = 'LOCAL', 'Local Upload'

    project = models.ForeignKey('Project', related_name='payments', on_delete=models.CASCADE)
    funding_schedule = models.ForeignKey('FundingSchedule', related_name='payments', on_delete=models.CASCADE)
    
    # Payment calculation type
    calculation_type = models.CharField(max_length=20, choices=CalculationType.choices, default=CalculationType.PERCENTAGE)
    
    # For percentage calculations
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="e.g., 30 for 30%")
    
    # For fixed or reimbursement amounts
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    
    # Payment timing
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices)
    payment_split = models.CharField(max_length=10, choices=PaymentSplit.choices, default=PaymentSplit.STANDARD)

    # Status
    forecast_release_date = models.DateField(
        null=True, blank=True,
        help_text="Forecast release date for Capital Grants cashflow planning"
    )
    # When SCHEDULED, forecast_release_date is DERIVED from the work group's
    # PaymentMilestoneSchedule rule for this payment_type (so a Monthly Tracker
    # slip rolls the payment automatically). MANUAL keeps hand-set behaviour.
    forecast_anchor = models.CharField(
        max_length=20, choices=ForecastAnchor.choices, default=ForecastAnchor.MANUAL,
        blank=True,
        help_text="MANUAL = you set the forecast date. SCHEDULED = it follows the "
                  "work group's payment milestone schedule automatically."
    )
    reference = models.CharField(max_length=100, blank=True)
    gl_code = models.CharField(max_length=50, blank=True, help_text="GL code from program")
    business_case_ref = models.CharField(max_length=100, blank=True, help_text="Business case reference from program")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Tax Invoice & SAP References (NEW)
    tax_invoice_reference = models.CharField(max_length=100, blank=True, help_text="Tax Invoice or RCTI reference number")
    sap_payment_reference = models.CharField(max_length=100, blank=True, help_text="SAP Payment Document Number")
    sap_cost_centre = models.CharField(max_length=50, blank=True, help_text="SAP Cost Centre")
    
    # Document Management (supports OpenDocs or SharePoint/Shared Drive)
    class DocumentSource(models.TextChoices):
        OPENDOCS = 'OPENDOCS', 'OpenDocs Content Manager'
        SHARED_DRIVE = 'SHARED_DRIVE', 'Shared Network Drive'
        LOCAL = 'LOCAL', 'Local Upload'
    
    document_source = models.CharField(max_length=20, choices=DocumentSource.choices, blank=True, help_text="Where documents are stored")
    document_url = models.URLField(max_length=500, blank=True, help_text="Link to OpenDocs or SharePoint document")
    document_path = models.CharField(max_length=500, blank=True, help_text="Path to document on shared drive (e.g., \\\\server\\folder\\file.pdf)")
    document_added_date = models.DateField(null=True, blank=True, help_text="Date document was added/referenced")
    
    # Approval
    recommended_by = models.ForeignKey('auth.User', related_name='recommended_payments', null=True, blank=True, on_delete=models.SET_NULL)
    recommended_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey('auth.User', related_name='approved_payments', null=True, blank=True, on_delete=models.SET_NULL)
    approved_date = models.DateField(null=True, blank=True)
    
    # Release (when payment is sent to Finance for processing)
    release_date = models.DateField(null=True, blank=True, help_text="Date payment was released to Finance")
    release_sap_reference = models.CharField(max_length=100, blank=True, help_text="SAP Payment Document Number (from release)")
    release_receipt_number = models.CharField(max_length=100, blank=True, help_text="Receipt/Transaction Reference Number")
    release_document_source = models.CharField(max_length=20, choices=DocumentSource.choices, blank=True, help_text="Where release receipt is stored")
    release_document_url = models.URLField(max_length=500, blank=True, help_text="Link to receipt in OpenDocs/SharePoint")
    release_document_path = models.CharField(max_length=500, blank=True, help_text="Path to receipt on shared drive")
    release_notes = models.TextField(blank=True, help_text="Notes from release (e.g., finance team comments)")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.name} - {self.get_payment_type_display()} (${self.calculated_amount or self.amount or 0})"

    def applicable_milestone_schedule(self):
        """Resolve the PaymentMilestoneSchedule that governs this payment.

        Schedules are scoped to a WorkStepGroup. A payment is project-scoped, so
        we look at the groups used by the project's works: one group → its
        schedule; none/ambiguous → the global default schedule.
        """
        from apps.core.models import PaymentMilestoneSchedule
        if not self.project_id:
            return None
        group_ids = set(
            self.project.works.filter(step_group__isnull=False)
            .values_list('step_group_id', flat=True)
        )
        schedules = list(PaymentMilestoneSchedule.objects.filter(
            work_step_group_id__in=group_ids, is_active=True
        )) if group_ids else []
        if len(schedules) == 1:
            return schedules[0]
        return PaymentMilestoneSchedule.objects.filter(
            is_default=True, is_active=True
        ).first()

    def _milestone_rule(self):
        sched = self.applicable_milestone_schedule()
        if not sched:
            return None
        return sched.rules.filter(payment_type=self.payment_type).first()

    def resolve_forecast_date(self):
        """Derived forecast_release_date from the applicable schedule rule, or
        None when not SCHEDULED / no rule / milestone date not yet known."""
        if self.forecast_anchor != self.ForecastAnchor.SCHEDULED:
            return None
        rule = self._milestone_rule()
        return rule.resolve_for_project(self.project) if rule else None

    def save(self, *args, **kwargs):
        if not self.forecast_anchor:
            self.forecast_anchor = self.ForecastAnchor.MANUAL
        # New payments auto-opt into scheduling when a milestone rule applies, so
        # staff never hand-set dates for the standard flow. Explicit MANUAL picks
        # (or a hand-set date) are preserved.
        if self._state.adding and self.forecast_anchor == self.ForecastAnchor.MANUAL \
                and self.forecast_release_date is None and self._milestone_rule() is not None:
            self.forecast_anchor = self.ForecastAnchor.SCHEDULED
        if self.forecast_anchor == self.ForecastAnchor.SCHEDULED:
            new_date = self.resolve_forecast_date()
            if new_date is not None and new_date != self.forecast_release_date:
                self.forecast_release_date = new_date
                uf = kwargs.get('update_fields')
                if uf is not None:
                    kwargs['update_fields'] = set(uf) | {'forecast_release_date'}
        super().save(*args, **kwargs)

    @property
    def calculated_amount(self):
        """Calculate amount based on calculation type"""
        if self.calculation_type == self.CalculationType.PERCENTAGE and self.percentage and self.funding_schedule:
            funding_total = self.funding_schedule.total_funding
            percentage_value = Decimal(str(self.percentage))
            return (funding_total * percentage_value) / Decimal('100')
        return self.amount
    
    @property
    def calculated_amount_display(self):
        """Return the calculated or fixed amount"""
        amount = self.calculated_amount
        if amount is None:
            amount = self.amount or 0
        return f"${amount:,.2f}"
    
    @staticmethod
    def calculate_standard_split(total_funding):
        """Calculate standard 30/60/10 payment split"""
        return {
            'first': total_funding * Decimal('0.30'),
            'second': total_funding * Decimal('0.60'),
            'third': total_funding * Decimal('0.10'),
        }
    
    @staticmethod
    def calculate_alternative_split(total_funding):
        """Calculate alternative 90/10 payment split"""
        return {
            'first': total_funding * Decimal('0.90'),
            'second': total_funding * Decimal('0.10'),
        }
    
    @staticmethod
    def calculate_with_surplus(total_funding, surplus_amount):
        """Calculate payments with surplus reduction"""
        remaining = total_funding - surplus_amount
        return {
            'first': remaining * Decimal('0.30'),
            'second': remaining * Decimal('0.60'),
            'third': remaining * Decimal('0.10'),
            'surplus': surplus_amount,
        }

    # ------------------------------------------------------------------
    # Co-funding: per-program split helpers
    # ------------------------------------------------------------------

    def compute_program_split(self):
        """Return a dict {program_id: (Decimal_amount, Decimal_ratio)} for this
        payment based on the project's current BFAItem ratios.

        Falls back to `{project.program_id: (amount, 1.0)}` when the project has
        no APPROVED BFA items.
        """
        amount = self.calculated_amount or self.amount or Decimal('0')
        if amount <= 0 or not self.project_id:
            return {}
        ratios = self.project.bfa_program_ratios(approved_only=True)
        if not ratios:
            if self.project.program_id:
                return {self.project.program_id: (amount, Decimal('1.000000'))}
            return {}
        out = {}
        running = Decimal('0')
        ordered = sorted(ratios.items(), key=lambda kv: -kv[1])
        for i, (pid, ratio) in enumerate(ordered):
            if i == len(ordered) - 1:
                share = (amount - running).quantize(Decimal('0.01'))
            else:
                share = (amount * ratio).quantize(Decimal('0.01'))
                running += share
            out[pid] = (share, ratio)
        return out

    def released_to_program(self, program_id):
        """Total $ already locked against (this project, program_id) across all
        previously-released payments (sums PaymentAllocation rows), excluding self.
        """
        from apps.core.models import PaymentAllocation
        return PaymentAllocation.objects.filter(
            payment__project=self.project, program_id=program_id,
        ).exclude(payment_id=self.pk).aggregate(
            t=models.Sum('amount')
        )['t'] or Decimal('0')

    def clean(self):
        """Enforce per-program caps: for each program this payment would charge,
        approved capacity >= already released + this payment's share.
        """
        from django.core.exceptions import ValidationError
        if not self.project_id or not (self.amount or self.calculated_amount):
            return
        if self.status == self.Status.REJECTED:
            return
        split = self.compute_program_split()
        if not split:
            return
        from apps.core.models import BriefFinancialApprovalItem
        capacity = {}
        for item in BriefFinancialApprovalItem.objects.filter(
            project=self.project, bfa__status='APPROVED',
        ):
            pid = item.program_id or self.project.program_id
            if pid is None:
                continue
            capacity[pid] = capacity.get(pid, Decimal('0')) + (
                (item.funding_amount or 0) + (item.contingency_amount or 0)
            )
        errors = []
        for pid, (share, _ratio) in split.items():
            cap = capacity.get(pid, Decimal('0'))
            committed = self.released_to_program(pid)
            if committed + share > cap:
                from apps.core.models import Program
                name = Program.objects.filter(pk=pid).values_list('name', flat=True).first() or f"#{pid}"
                errors.append(
                    f"Program '{name}': allocating ${share:,.2f} would push committed "
                    f"(${committed:,.2f} + ${share:,.2f}) over the approved cap "
                    f"of ${cap:,.2f}."
                )
        if errors:
            raise ValidationError("Payment over-commits per-program BFA caps:\n - " + "\n - ".join(errors))


class PaymentMilestoneSchedule(models.Model):
    """Configurable payment-timing template, scoped to a WorkStepGroup.

    Replaces hard-coded milestone→payment wiring: each WorkStepGroup can own a
    schedule whose rules say which milestone each payment tracks. Outliers are
    handled by cloning a group (and its schedule) and applying it to the
    relevant works — no code change needed. The schedule marked is_default is
    the fallback for projects whose work group has no schedule of its own.
    """
    work_step_group = models.OneToOneField(
        'WorkStepGroup', related_name='payment_schedule', on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="The work step group this payment timing applies to. Leave blank "
                  "for the global default schedule.",
    )
    name = models.CharField(max_length=200, help_text="e.g. 'Standard 30/60/10'")
    is_default = models.BooleanField(
        default=False,
        help_text="Fallback schedule used when a project's work group has no schedule.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Payment Milestone Schedule'
        verbose_name_plural = 'Payment Milestone Schedules'

    def __str__(self):
        return self.name

    def clone_for_group(self, group, new_name=None):
        """Deep-copy this schedule (+ rules) onto another WorkStepGroup."""
        new = PaymentMilestoneSchedule.objects.create(
            work_step_group=group,
            name=new_name or f"{group.name} payments",
            is_default=False,
            is_active=self.is_active,
        )
        for r in self.rules.all():
            PaymentMilestoneRule.objects.create(
                schedule=new, payment_type=r.payment_type, anchor_type=r.anchor_type,
                work_step_definition=r.work_step_definition, offset_days=r.offset_days,
            )
        return new


class PaymentMilestoneRule(models.Model):
    """One payment's timing within a schedule: which milestone it tracks and the
    offset in days. WORK_STEP rules name the exact step to follow (e.g. Site
    establishment, or the final handover step), giving per-group control."""

    class AnchorType(models.TextChoices):
        PROJECT_START = 'PROJECT_START', 'Project start date'
        WORK_STEP = 'WORK_STEP', 'Work step completion (named)'
        PROJECT_PC = 'PROJECT_PC', 'Project forecast practical completion'
        MANUAL = 'MANUAL', 'Manual (no auto date)'

    schedule = models.ForeignKey(
        PaymentMilestoneSchedule, related_name='rules', on_delete=models.CASCADE
    )
    payment_type = models.CharField(max_length=10, choices=Payment.PaymentType.choices)
    anchor_type = models.CharField(
        max_length=20, choices=AnchorType.choices, default=AnchorType.WORK_STEP
    )
    work_step_definition = models.ForeignKey(
        'WorkStepDefinition', related_name='payment_rules',
        null=True, blank=True, on_delete=models.PROTECT,
        help_text="Which step to track when anchor is 'Work step completion'.",
    )
    offset_days = models.IntegerField(
        default=14, help_text="Days after the milestone (e.g. 14 = pay 14 days after).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['payment_type']
        unique_together = ['schedule', 'payment_type']
        verbose_name = 'Payment Milestone Rule'
        verbose_name_plural = 'Payment Milestone Rules'

    def __str__(self):
        return f"{self.schedule.name}: {self.get_payment_type_display()} → {self.get_anchor_type_display()}"

    def _base_date(self, project):
        if self.anchor_type == self.AnchorType.PROJECT_START:
            return project.start_date
        if self.anchor_type == self.AnchorType.PROJECT_PC:
            return project.forecast_practical_completion_date
        if self.anchor_type == self.AnchorType.WORK_STEP and self.work_step_definition_id:
            from apps.core.models import WorkStep
            dates = [
                s.actual_completion_date or s.forecast_completion_date
                for s in WorkStep.objects.filter(
                    work__project=project, step_name=self.work_step_definition.name
                )
            ]
            dates = [d for d in dates if d]
            return max(dates) if dates else None
        return None

    def resolve_for_project(self, project):
        """Milestone date + offset for this project, or None if not yet known."""
        if not project:
            return None
        base = self._base_date(project)
        if base is None:
            return None
        return base + timedelta(days=self.offset_days or 0)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.anchor_type == self.AnchorType.WORK_STEP and not self.work_step_definition_id:
            raise ValidationError(
                "Choose a work step definition when anchor is 'Work step completion'."
            )
