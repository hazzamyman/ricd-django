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
