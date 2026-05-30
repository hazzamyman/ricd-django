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
