from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .councils_models import Council
from .projects_models import Project


# ============================================================================
# PaymentRule - Versioned, immutable once linked to FundingSchedule
# ============================================================================

class PaymentRule(models.Model):
    """Payment calculation rules - versioned, with milestone child rows.

    Two rule types:
      * SPLIT  -- per-milestone percentage (e.g. 30/60/10). Milestones are stored
                  as PaymentRuleMilestone rows; config_json is no longer the
                  source of truth but is auto-synced for backward compatibility.
      * INVOICE -- expense-claim style, paid against actuals up to a cap.
    """
    class RuleType(models.TextChoices):
        SPLIT = 'SPLIT', 'Milestone Percentage'
        INVOICE_BASED = 'INVOICE', 'Invoice/Expense Claim'

    name = models.CharField(max_length=255, unique=True)
    rule_type = models.CharField(max_length=10, choices=RuleType.choices)
    config_json = models.JSONField(
        default=dict, blank=True,
        help_text="Auto-synced from milestone rows; do not edit directly."
    )
    version = models.PositiveIntegerField(default=1, help_text="Increment for new versions")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', '-version']

    def __str__(self):
        return f"{self.name} (v{self.version}, {self.rule_type})"

    @property
    def is_locked(self):
        """True if any FundingSchedule references this rule (per business_rules.check_payment_rule_immutable).

        While locked, the rule cannot be edited or deleted; users should create a new version instead.
        """
        try:
            return self.schedules.exclude(status__in=['CANCELLED', 'COMPLETED']).exists()
        except Exception:
            return False

    def sync_config_json(self):
        """Rebuild config_json from milestone rows (call after milestone changes)."""
        if self.rule_type == self.RuleType.SPLIT:
            self.config_json = {
                'milestones': [
                    {'name': m.name, 'percentage': float(m.percentage), 'order': m.order}
                    for m in self.milestones.all().order_by('order')
                ]
            }
        # INVOICE rules keep whatever metadata is already in config_json
        self.save(update_fields=['config_json', 'updated_at'])

    def clean(self):
        from django.core.exceptions import ValidationError
        # Allow saving a SPLIT rule with no milestones yet (caller will add rows next),
        # but if milestones exist, they must sum to 100%.
        if self.pk and self.rule_type == self.RuleType.SPLIT:
            rows = list(self.milestones.all())
            if rows:
                total = sum(float(m.percentage) for m in rows)
                if abs(total - 100.0) > 0.001:
                    raise ValidationError(f"SPLIT milestones must total 100%, got {total}%")
        # Immutability while in use
        if self.pk:
            from apps.core.business_rules import check_payment_rule_immutable
            existing = PaymentRule.objects.filter(pk=self.pk).first()
            if existing and check_payment_rule_immutable(existing):
                raise ValidationError(
                    f"PaymentRule '{self.name}' is in use by a FundingSchedule. "
                    "Create a new version instead of editing this one."
                )


class PaymentRuleMilestone(models.Model):
    """One row in a SPLIT rule (e.g. 'First payment 30%')."""
    rule = models.ForeignKey(PaymentRule, related_name='milestones', on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=100, help_text="e.g. 'First', 'Stage 1 completion'")
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="0.00 - 100.00"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('rule', 'order')

    def __str__(self):
        return f"{self.rule.name} [{self.order}] {self.name} ({self.percentage}%)"


# ============================================================================
# FundingAgreement - Legal umbrella
# ============================================================================

class FundingAgreement(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        CEASED = 'CEASED', 'Ceased'

    # 1:1 — each council has exactly one Remote Capital Program Funding Agreement.
    # That agreement then has many FundingSchedules under it.
    council = models.OneToOneField(
        Council, related_name='funding_agreement', on_delete=models.CASCADE,
        help_text="The single Remote Capital Program Funding Agreement for this council"
    )
    name = models.CharField(max_length=255, help_text="Agreement name/reference")
    execution_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    document_uri = models.URLField(blank=True, help_text="Windows Share Drive, Sharepoint or OpenDocs link")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.council.name} ({self.status})"


# ============================================================================
# BriefFinancialApproval - Pre-condition for funding creation
# ============================================================================

class BriefFinancialApproval(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class DelegateLevel(models.TextChoices):
        MANAGER = 'MGR', 'Manager'
        DIRECTOR = 'DIR', 'Director'
        GM = 'GM', 'General Manager'

    project = models.ForeignKey(Project, related_name='financial_approvals', on_delete=models.CASCADE)
    funding_amount = models.DecimalField(max_digits=14, decimal_places=2)
    contingency_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    delegate_level = models.CharField(max_length=3, choices=DelegateLevel.choices, default=DelegateLevel.MANAGER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(User, related_name='brief_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    mincor_reference = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"BriefFA ${self.funding_amount} for {self.project.name} ({self.status})"

    @property
    def total_amount(self):
        return self.funding_amount + self.contingency_amount


# ============================================================================
# FundingNotice - Capped payment pathway (alternative to FundingSchedule)
# ============================================================================

class FundingNotice(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    project = models.ForeignKey(Project, related_name='funding_notices', on_delete=models.CASCADE)
    capped_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Maximum funding available")
    issued_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_date']
        unique_together = ['project', 'issued_date']

    def __str__(self):
        return f"FundingNotice {self.project.name} - ${self.capped_amount:,.2f} ({self.status})"

    @property
    def approved_claims_total(self):
        from decimal import Decimal
        claims = self.claims.filter(status='APPROVED')
        return sum((c.amount for c in claims), Decimal('0'))

    @property
    def remaining(self):
        return self.capped_amount - self.approved_claims_total

    @property
    def is_exhausted(self):
        return self.approved_claims_total >= self.capped_amount


# ============================================================================
# ExpenseClaim - Against FundingNotice
# ============================================================================

class ExpenseClaim(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    funding_notice = models.ForeignKey(FundingNotice, related_name='claims', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date_submitted = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey(User, related_name='expense_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    approved_date = models.DateField(null=True, blank=True)
    sap_document_reference = models.CharField(
        max_length=100, blank=True,
        help_text="SAP Recipient Created Tax Invoice (RCTI) or SAP payment document number"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_submitted']

    def __str__(self):
        return f"ExpenseClaim ${self.amount} for {self.funding_notice.project.name} ({self.status})"


class ExpenseClaimAttachment(models.Model):
    """Linked documents for an expense claim (invoices, SAP RCTI, supporting evidence)."""
    claim = models.ForeignKey(ExpenseClaim, related_name='attachments', on_delete=models.CASCADE)
    document_uri = models.URLField(
        blank=True,
        help_text="Windows Share Drive, Sharepoint or OpenDocs link"
    )
    description = models.CharField(max_length=255, blank=True, help_text="e.g. 'Invoice 1234', 'SAP RCTI'")
    uploaded_by = models.ForeignKey(
        'auth.User', null=True, blank=True,
        related_name='expense_claim_attachments', on_delete=models.SET_NULL
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment for {self.claim}: {self.description or self.document_uri}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from apps.core.business_rules import get_approved_claims_total
        
        # Check cap not exceeded (exclude current row when updating)
        if self.funding_notice and self.status != self.Status.DRAFT:
            approved_total = get_approved_claims_total(self.funding_notice)
            # When updating an existing APPROVED claim, exclude it from the sum
            if self.pk:
                existing = ExpenseClaim.objects.filter(pk=self.pk, status=self.Status.APPROVED).first()
                if existing:
                    approved_total -= existing.amount
            new_total = approved_total + self.amount
            if new_total > self.funding_notice.capped_amount:
                raise ValidationError(
                    f"Claim ${self.amount} would exceed notice cap. "
                    f"Approved: ${approved_total:,.2f}, "
                    f"Cap: ${self.funding_notice.capped_amount:,.2f}"
                )


class Delegation(models.Model):
    """Financial delegation thresholds for positions"""
    class Position(models.TextChoices):
        SENIOR_PROJECT_OFFICER = 'SPO', 'Senior Project Officer'
        PRINCIPAL_PROJECT_OFFICER = 'PPO', 'Principal Project Officer'
        MANAGER = 'MGR', 'Manager'
        DIRECTOR = 'DIR', 'Director'
        EXECUTIVE_DIRECTOR = 'ED', 'Executive Director'
        GENERAL_MANAGER = 'GM', 'General Manager'
        DEPUTY_DIRECTOR_GENERAL = 'DDG', 'Deputy Director-General'
        DIRECTOR_GENERAL = 'DG', 'Director-General'

    position = models.CharField(max_length=3, choices=Position.choices, unique=True)
    threshold_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Leave blank for unlimited (e.g., Director-General)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.threshold_amount:
            return f"{self.get_position_display()} - Up to ${self.threshold_amount:,.2f}"
        return f"{self.get_position_display()} - Unlimited"

    @classmethod
    def get_approval_chain(cls, amount):
        """Return list of positions needed for approval based on amount"""
        chain = []
        # Order matters - check from lowest to highest
        for pos in [cls.Position.SENIOR_PROJECT_OFFICER, cls.Position.PRINCIPAL_PROJECT_OFFICER,
                    cls.Position.MANAGER, cls.Position.DIRECTOR, cls.Position.EXECUTIVE_DIRECTOR,
                    cls.Position.GENERAL_MANAGER, cls.Position.DEPUTY_DIRECTOR_GENERAL, 
                    cls.Position.DIRECTOR_GENERAL]:
            try:
                delegation = cls.objects.get(position=pos, is_active=True)
                if delegation.threshold_amount is None or amount <= delegation.threshold_amount:
                    chain.append(pos)
                    break
                else:
                    chain.append(pos)
            except cls.DoesNotExist:
                continue
        return chain

    @classmethod
    def get_delegation_level(cls, amount):
        """Return Approval.RequiredRole based on delegation amount threshold"""
        from apps.core.models import Approval
        # Get the first matching delegation level by amount
        chain = cls.get_approval_chain(amount)
        if not chain:
            return Approval.RequiredRole.DELEGATE
        # Map position codes to Approval.RequiredRole
        position_code = chain[0]
        if position_code == cls.Position.MANAGER:
            return Approval.RequiredRole.MANAGER
        elif position_code in [cls.Position.DIRECTOR, cls.Position.EXECUTIVE_DIRECTOR]:
            return Approval.RequiredRole.DIRECTOR
        elif position_code in [cls.Position.GENERAL_MANAGER, cls.Position.DEPUTY_DIRECTOR_GENERAL, cls.Position.DIRECTOR_GENERAL]:
            return Approval.RequiredRole.GM
        return Approval.RequiredRole.DELEGATE


class FundingSchedule(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        READY_FOR_EXECUTION = 'READY', 'Ready for Execution'
        EXECUTED = 'EXECUTED', 'Executed'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'
        CANCELLED = 'CANCELLED', 'Cancelled'

    funding_agreement = models.ForeignKey(FundingAgreement, related_name='schedules', on_delete=models.CASCADE, null=True, blank=True)
    payment_rule = models.ForeignKey(PaymentRule, related_name='schedules', on_delete=models.PROTECT, null=True, blank=True, help_text="Payment calculation rule")
    schedule_number = models.PositiveIntegerField(default=1)
    replaces_schedule = models.ForeignKey('self', related_name='replacements', on_delete=models.SET_NULL, null=True, blank=True, help_text="Replaced by this schedule")
    project = models.ForeignKey(Project, related_name='funding_schedules', on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    councils = models.ManyToManyField('Council', related_name='funding_schedules', blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True)

    # Date fields — the source of truth. A post_save signal cascades these
    # down to all child Projects (Project edits do NOT propagate back).
    start_date = models.DateField(
        null=True, blank=True,
        help_text="Project start (cascaded to child projects on save)"
    )
    stage1_target_date = models.DateField(null=True, blank=True)
    stage2_target_date = models.DateField(null=True, blank=True)
    stage1_sunset_date = models.DateField(null=True, blank=True)
    stage2_sunset_date = models.DateField(null=True, blank=True)

    # Stage report templates — picked by the FundingSchedule (per the per-FS
    # report design). When a Stage report is opened, items are populated from
    # the matching group here. Projects' equivalent fields are kept for
    # backward compatibility but FS takes precedence.
    stage1_item_group = models.ForeignKey(
        'StageItemGroup', related_name='stage1_funding_schedules',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Template group of Stage 1 items for the report covering this schedule's projects",
    )
    stage2_item_group = models.ForeignKey(
        'StageItemGroup', related_name='stage2_funding_schedules',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Template group of Stage 2 items for the report covering this schedule's projects",
    )

    # State contact details (Variation - State contact option)
    contact_details = models.JSONField(blank=True, default=dict, help_text="attention, phone, email, address")

    # Variation content fields
    scope_of_works = models.TextField(blank=True)
    land_details = models.JSONField(blank=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_funding(self):
        """Total funding = SUM of WorkFunding allocations (single source of truth)."""
        from django.db.models import Sum
        return self.work_fundings.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def effective_total(self):
        return self.total_funding

    @property
    def linked_project(self):
        return self.project

    DATE_FIELDS_FOR_SYNC = (
        'start_date', 'stage1_target_date', 'stage1_sunset_date',
        'stage2_target_date', 'stage2_sunset_date',
    )

    def child_projects(self):
        """All projects directly linked to this FundingSchedule (Project.funding_schedule FK)."""
        from apps.core.models import Project
        return Project.objects.filter(funding_schedule=self)

    def out_of_sync_projects(self):
        """Return child projects whose date fields differ from this schedule's."""
        out = []
        for p in self.child_projects():
            if any(getattr(self, f) != getattr(p, f) for f in self.DATE_FIELDS_FOR_SYNC):
                out.append(p)
        return out

    @property
    def has_out_of_sync_projects(self):
        return bool(self.out_of_sync_projects())

    def clean(self):
        from django.core.exceptions import ValidationError
        from apps.core.business_rules import check_brief_financial_approval

        if self.status != self.Status.DRAFT and not self.payment_rule:
            raise ValidationError("payment_rule is required when schedule is not DRAFT")

        if self.project and self._state.adding:
            if not check_brief_financial_approval(self.project):
                raise ValidationError(
                    f"Project '{self.project.name}' requires an APPROVED BriefFinancialApproval "
                    "before a FundingSchedule can be created."
                )

    def __str__(self):
        return f"FS#{self.schedule_number} - {self.project.name if self.project else 'No Project'} ({self.get_status_display()})"


class ProjectStateLog(models.Model):
    project = models.ForeignKey(Project, related_name='state_logs', on_delete=models.CASCADE)
    previous_state = models.CharField(max_length=4)
    new_state = models.CharField(max_length=4)
    changed_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True)
    change_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.project.name}: {self.previous_state} → {self.new_state} on {self.change_date}"


class WorkFunding(models.Model):
    """Per-work funding details for cost centre/GL/tax tracking.
    Allocation model: references exactly one of project OR work (DB CHECK).
    """
    funding_schedule = models.ForeignKey(FundingSchedule, related_name='work_fundings', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, related_name='funding_allocations', null=True, blank=True, on_delete=models.CASCADE, help_text="Project allocation (use OR work, not both)")
    work = models.ForeignKey('Work', related_name='funding_details', null=True, blank=True, on_delete=models.CASCADE, help_text="Work allocation (use OR project, not both)")
    cost_centre = models.CharField(max_length=50, blank=True, help_text="Cost centre code (e.g., 316333)")
    gl_code = models.CharField(max_length=50, blank=True, help_text="GL code from program")
    tax_code = models.CharField(max_length=20, blank=True, help_text="Tax code (e.g., GST, FBT)")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Allocated funding amount for this work")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['work', 'funding_schedule']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(project__isnull=False, work__isnull=True) |
                    models.Q(project__isnull=True, work__isnull=False)
                ),
                name="workfunding_project_xor_work"
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        both_set = self.project_id is not None and self.work_id is not None
        neither_set = self.project_id is None and self.work_id is None
        if both_set:
            raise ValidationError('An allocation must target either a project or a work item — not both.')
        if neither_set:
            raise ValidationError('An allocation must target either a project or a work item.')

    def __str__(self):
        if self.work:
            work_name = f"{self.work.work_type.name if self.work.work_type else self.work.work_type_other}"
            return f"WorkFunding: {work_name} → {self.cost_centre or 'No CC'}"
        return f"WorkFunding: Project {self.project_id} → {self.cost_centre or 'No CC'}"


# ============================================================================
# Generic Approval - Unified governance approval system
# ============================================================================

class Approval(models.Model):
    class ApprovalType(models.TextChoices):
        FINANCIAL = 'FINANCIAL', 'Financial'
        CONTRACT = 'CONTRACT', 'Contract'
        PAYMENT = 'PAYMENT', 'Payment'
        REPORT = 'REPORT', 'Report'
        VARIATION = 'VARIATION', 'Variation'

    class RequiredRole(models.TextChoices):
        MANAGER = 'MGR', 'Manager'
        DIRECTOR = 'DIR', 'Director'
        GM = 'GM', 'General Manager'
        DELEGATE = 'DELEGATE', 'Delegate'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    entity_type = models.CharField(max_length=50, help_text="Model name (e.g., 'Project')")
    entity_id = models.PositiveIntegerField(help_text="PK of the entity")
    approval_type = models.CharField(max_length=20, choices=ApprovalType.choices)
    required_role = models.CharField(max_length=10, choices=RequiredRole.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(User, related_name='approvals_given', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"Approval {self.approval_type} for {self.entity_type}:{self.entity_id} ({self.status})"


# ============================================================================
# WorkflowAction - Immutable event log (NOT decision authority)
# ============================================================================

class WorkflowAction(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', 'Created'
        UPDATE = 'UPDATE', 'Updated'
        APPROVE = 'APPROVE', 'Approved'
        REJECT = 'REJECT', 'Rejected'
        RELEASE_PAYMENT = 'RELEASE_PAYMENT', 'Payment Released'
        EXECUTE_VARIATION = 'EXECUTE_VARIATION', 'Variation Executed'

    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    performed_by = models.ForeignKey(User, related_name='workflow_actions', null=True, blank=True, on_delete=models.SET_NULL)
    performed_at = models.DateTimeField(default=timezone.now)
    metadata_json = models.JSONField(default=dict, blank=True, help_text="Free-form: rationale, external ticket IDs, etc.")

    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"{self.action_type} on {self.entity_type}:{self.entity_id} at {self.performed_at}"


# ============================================================================
# AuditLog - Low-level immutable change log
# ============================================================================

class AuditLog(models.Model):
    user = models.ForeignKey(User, related_name='audit_logs', null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)
    action = models.CharField(max_length=20, help_text="CREATE, UPDATE, DELETE")
    before_json = models.JSONField(default=dict, blank=True)
    after_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id} by {self.user}"


# ============================================================================
# Legacy Agreement Types (pre-Funding Schedule era)
# ============================================================================

class _LegacyAgreementBase(models.Model):
    """Abstract base for Forward RPF and Interim FRP agreements."""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        EXECUTED = 'EXECUTED', 'Executed'
        COMPLETED = 'COMPLETED', 'Completed'
        TERMINATED = 'TERMINATED', 'Terminated'

    council = models.OneToOneField(
        Council,
        on_delete=models.CASCADE,
        help_text="Council this agreement is with (one agreement per council)"
    )
    reference = models.CharField(max_length=100, blank=True, help_text="Internal reference / agreement number")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    date_sent_to_council = models.DateField(null=True, blank=True)
    date_council_signed = models.DateField(null=True, blank=True)
    date_delegate_signed = models.DateField(null=True, blank=True)
    document_uri = models.URLField(blank=True, help_text="Windows Share Drive, Sharepoint or OpenDocs link")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def executed_date(self):
        """Date agreement came into force — later of council and delegate signatures."""
        dates = [d for d in [self.date_council_signed, self.date_delegate_signed] if d]
        return max(dates) if len(dates) == 2 else None

    class Meta:
        abstract = True


class ForwardRPFAgreement(_LegacyAgreementBase):
    """Forward Remote Program Funding Agreement — 1:1 with Council, 1:many with Projects."""
    projects = models.ManyToManyField(
        'Project',
        related_name='forward_rpf_agreements',
        blank=True,
        help_text="Projects funded under this Forward RPF agreement"
    )

    class Meta:
        verbose_name = "Forward RPF Agreement"
        verbose_name_plural = "Forward RPF Agreements"
        ordering = ['council__name']

    def __str__(self):
        ref = f" ({self.reference})" if self.reference else ''
        return f"Forward RPF — {self.council.name}{ref}"


class InterimFRPAgreement(_LegacyAgreementBase):
    """Interim Forward Remote Program Funding Agreement — 1:1 with Council, 1:many with Projects."""
    projects = models.ManyToManyField(
        'Project',
        related_name='interim_frp_agreements',
        blank=True,
        help_text="Projects funded under this Interim FRP agreement"
    )

    class Meta:
        verbose_name = "Interim FRP Agreement"
        verbose_name_plural = "Interim FRP Agreements"
        ordering = ['council__name']

    def __str__(self):
        ref = f" ({self.reference})" if self.reference else ''
        return f"Interim FRP — {self.council.name}{ref}"
