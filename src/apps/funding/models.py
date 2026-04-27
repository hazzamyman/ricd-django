from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ============================================================================
# PaymentRule - Versioned, immutable once linked to FundingSchedule
# ============================================================================

class PaymentRule(models.Model):
    """Payment calculation rules - versioned and immutable once used"""
    class RuleType(models.TextChoices):
        SPLIT = 'SPLIT', 'Milestone Percentage'
        INVOICE_BASED = 'INVOICE', 'Invoice/Expense Claim'

    name = models.CharField(max_length=255, unique=True)
    rule_type = models.CharField(max_length=10, choices=RuleType.choices)
    config_json = models.JSONField(default=dict, help_text="Milestones for SPLIT, requires_approval for INVOICE")
    version = models.PositiveIntegerField(default=1, help_text="Version number - increment for new versions")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', '-version']

    def __str__(self):
        return f"{self.name} (v{self.version}, {self.rule_type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.rule_type == self.RuleType.SPLIT:
            milestones = self.config_json.get('milestones', [])
            if not milestones:
                raise ValidationError("SPLIT requires 'milestones' in config_json")
            total_pct = sum(m.get('percentage', 0) for m in milestones)
            if total_pct != 100:
                raise ValidationError(f"SPLIT milestones must total 100%, got {total_pct}%")


# ============================================================================
# FundingAgreement - Legal umbrella
# ============================================================================

class FundingAgreement(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        CEASED = 'CEASED', 'Ceased'

    council = models.ForeignKey('councils.Council', related_name='funding_agreements', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, help_text="Agreement name/reference")
    execution_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    document_uri = models.URLField(blank=True, help_text="Google Drive or OpenDocs link")
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

    project = models.ForeignKey('projects.Project', related_name='financial_approvals', on_delete=models.CASCADE)
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

    project = models.ForeignKey('projects.Project', related_name='funding_notices', on_delete=models.CASCADE)
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
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_submitted']

    def __str__(self):
        return f"ExpenseClaim ${self.amount} for {self.funding_notice.project.name} ({self.status})"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Check cap not exceeded
        if self.funding_notice and self.status != self.Status.DRAFT:
            new_total = self.funding_notice.approved_claims_total + self.amount
            if new_total > self.funding_notice.capped_amount:
                raise ValidationError(
                    f"Claim ${self.amount} would exceed notice cap. "
                    f"Approved: ${self.funding_notice.approved_claims_total:,.2f}, "
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


class FundingApproval(models.Model):
    """Funding approval workflow - completed before Funding Schedule"""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_PEER_REVIEW = 'PENDING_PEER', 'Pending Peer Review'
        PENDING_MANAGER = 'PENDING_MGR', 'Pending Manager Approval'
        PENDING_DIRECTOR = 'PENDING_DIR', 'Pending Director Approval'
        PENDING_ED = 'PENDING_ED', 'Pending Executive Director Approval'
        PENDING_GM = 'PENDING_GM', 'Pending General Manager Approval'
        PENDING_DDG = 'PENDING_DDG', 'Pending Deputy Director-General Approval'
        PENDING_DG = 'PENDING_DG', 'Pending Director-General Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    projects = models.ManyToManyField('projects.Project', related_name='funding_approvals', blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Amount
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    contingency_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # MINCOR reference
    mincor_reference = models.CharField(max_length=50, blank=True, help_text="e.g., MN12345-YYYY")
    mincor_link = models.URLField(blank=True, help_text="Link to MINCOR system")
    
    # Peer review
    peer_review_required = models.BooleanField(default=False)
    peer_reviewer = models.ForeignKey(User, related_name='peer_reviews', null=True, blank=True, on_delete=models.SET_NULL)
    peer_review_completed = models.DateField(null=True, blank=True)
    
    # Approval chain dates and approvers
    sent_to_manager = models.DateField(null=True, blank=True)
    manager_approver = models.ForeignKey(User, related_name='mgr_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    manager_approved = models.DateField(null=True, blank=True)
    
    sent_to_director = models.DateField(null=True, blank=True)
    director_approver = models.ForeignKey(User, related_name='dir_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    director_approved = models.DateField(null=True, blank=True)
    
    sent_to_ed = models.DateField(null=True, blank=True)
    ed_approver = models.ForeignKey(User, related_name='ed_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    ed_approved = models.DateField(null=True, blank=True)
    
    sent_to_gm = models.DateField(null=True, blank=True)
    gm_approver = models.ForeignKey(User, related_name='gm_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    gm_approved = models.DateField(null=True, blank=True)
    
    sent_to_ddg = models.DateField(null=True, blank=True)
    ddg_approver = models.ForeignKey(User, related_name='ddg_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    ddg_approved = models.DateField(null=True, blank=True)
    
    sent_to_dg = models.DateField(null=True, blank=True)
    dg_approver = models.ForeignKey(User, related_name='dg_approvals', null=True, blank=True, on_delete=models.SET_NULL)
    dg_approved = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Funding Approval {self.id} - ${self.total_amount:,.2f}"

    @property
    def total_with_contingency(self):
        return self.total_amount + self.contingency_amount

    def get_required_approvers(self):
        """Calculate required approvers based on amount"""
        total = self.total_with_contingency
        return Delegation.get_approval_chain(total)

    def approve(self, position, approved_by):
        """Process approval at a specific level"""
        if position == Delegation.Position.MANAGER:
            self.manager_approver = approved_by
            self.manager_approved = timezone.now().date()
        elif position == Delegation.Position.DIRECTOR:
            self.director_approver = approved_by
            self.director_approved = timezone.now().date()
        elif position == Delegation.Position.EXECUTIVE_DIRECTOR:
            self.ed_approver = approved_by
            self.ed_approved = timezone.now().date()
        elif position == Delegation.Position.GENERAL_MANAGER:
            self.gm_approver = approved_by
            self.gm_approved = timezone.now().date()
        elif position == Delegation.Position.DEPUTY_DIRECTOR_GENERAL:
            self.ddg_approver = approved_by
            self.ddg_approved = timezone.now().date()
        elif position == Delegation.Position.DIRECTOR_GENERAL:
            self.dg_approver = approved_by
            self.dg_approved = timezone.now().date()
        
        self.save()
        self.check_and_update_project_statuses()

    def check_and_update_project_statuses(self):
        """If fully approved, update all linked projects to FUNDED"""
        from apps.projects.models import Project
        if self.status == self.Status.APPROVED:
            for project in self.projects.all():
                project.state = Project.State.FUNDED
                project.save()

    def send_to_next_approver(self):
        """Send to next approver in chain"""
        chain = self.get_required_approvers()
        
        if self.status == self.Status.DRAFT:
            if self.peer_review_required:
                self.status = self.Status.PENDING_PEER_REVIEW
            elif Delegation.Position.MANAGER in chain:
                self.status = self.Status.PENDING_MANAGER
                self.sent_to_manager = timezone.now().date()
        elif self.status == self.Status.PENDING_PEER_REVIEW and self.peer_review_completed:
            if Delegation.Position.MANAGER in chain:
                self.status = self.Status.PENDING_MANAGER
                self.sent_to_manager = timezone.now().date()
        
        self.save()


# Keep old FundingSchedule model
class FundingSchedule(models.Model):
    class PaymentSplit(models.TextChoices):
        STANDARD = '30/60/10', 'Standard (30/60/10)'
        ALTERNATIVE = '90/10', 'Alternative (90/10)'
        CUSTOM = 'CUSTOM', 'Custom'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        READY_FOR_EXECUTION = 'READY', 'Ready for Execution'
        EXECUTED = 'EXECUTED', 'Executed'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'
        CANCELLED = 'CANCELLED', 'Cancelled'

    # New fields per domain model
    funding_agreement = models.ForeignKey(FundingAgreement, related_name='schedules', on_delete=models.CASCADE, null=True, blank=True)
    payment_rule = models.ForeignKey(PaymentRule, related_name='schedules', on_delete=models.PROTECT, null=True, blank=True, help_text="Payment calculation rule")
    schedule_number = models.PositiveIntegerField(default=1)
    replaces_schedule = models.ForeignKey('self', related_name='replacements', on_delete=models.SET_NULL, null=True, blank=True, help_text="Replaced by this schedule")

    # Existing fields (kept for compatibility)
    project = models.ForeignKey('projects.Project', related_name='funding_schedules', on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    councils = models.ManyToManyField('councils.Council', related_name='funding_schedules', blank=True, help_text="Council participants in this funding agreement")
    works = models.ManyToManyField('works.Work', related_name='funding_schedules', blank=True, help_text="Works funded by this schedule (for per-work funding)")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    contingency = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_funding = models.DecimalField(max_digits=12, decimal_places=2, editable=False, db_index=True)
    payment_split = models.CharField(max_length=10, choices=PaymentSplit.choices, default=PaymentSplit.STANDARD)
    
    # Status for variation management
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True)
    
    # Date fields (Option 5 - Vary Dates)
    stage1_target_date = models.DateField(null=True, blank=True, help_text="Stage 1 Target Date")
    stage2_target_date = models.DateField(null=True, blank=True, help_text="Stage 2 Target Date")
    stage1_sunset_date = models.DateField(null=True, blank=True, help_text="Stage 1 Sunset Date")
    stage2_sunset_date = models.DateField(null=True, blank=True, help_text="Stage 2 Sunset Date")
    
    # Contact details (Option 3 - State contact for RCPA)
    contact_details = models.JSONField(blank=True, default=dict, help_text="State contact details: attention, phone, email, address")
    
    # Scope of works (Option 6 - Vary Scope)
    scope_of_works = models.TextField(blank=True, help_text="Concatenated scope of works description")
    
    # Land details (Option 7 - Vary Land)
    land_details = models.JSONField(blank=True, default=dict, help_text="Land details: lot, plan, title_reference, street_address")
    
    # Notional vs Actual cost tracking
    notional_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total calculated from notional costs")
    actual_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total from actual costs entered")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_funding = self.amount + self.contingency
        super().save(*args, **kwargs)
        self._calculate_totals()

    def _calculate_totals(self):
        """Calculate notional and actual totals from works"""
        from apps.works.models import Work
        works = self.works.all()
        
        notional_sum = 0
        actual_sum = 0
        
        for work in works:
            if work.is_notional_cost:
                notional_sum += work.total_estimated_cost
            else:
                actual_sum += work.total_effective_cost
        
        self.notional_total = notional_sum
        self.actual_total = actual_sum

    @property
    def effective_total(self):
        """Returns the effective total (actual if available, otherwise notional)"""
        if self.actual_total > 0:
            return self.actual_total
        return self.notional_total

    @property
    def linked_project(self):
        """Returns the linked project"""
        return self.project

    def clean(self):
        from django.core.exceptions import ValidationError
        # payment_rule required when moving beyond DRAFT
        if self.status != self.Status.DRAFT and not self.payment_rule:
            raise ValidationError("payment_rule is required when schedule is not DRAFT")

    def __str__(self):
        return f"FS#{self.schedule_number} - {self.project.name if self.project else 'No Project'} ({self.get_status_display()})"


class ProjectStateLog(models.Model):
    project = models.ForeignKey('projects.Project', related_name='state_logs', on_delete=models.CASCADE)
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
    project = models.ForeignKey('projects.Project', related_name='funding_allocations', null=True, blank=True, on_delete=models.CASCADE, help_text="Project allocation (use OR work, not both)")
    work = models.ForeignKey('works.Work', related_name='funding_details', null=True, blank=True, on_delete=models.CASCADE, help_text="Work allocation (use OR project, not both)")
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

    entity_type = models.CharField(max_length=50, help_text="Model name (e.g., 'projects.Project')")
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
