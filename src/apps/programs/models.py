from django.db import models

from apps.core.utils import CURRENT_FINANCIAL_YEAR, FINANCIAL_YEAR_CHOICES


class Program(models.Model):
    class FundingSource(models.TextChoices):
        COMMONWEALTH = 'COMMONWEALTH', 'Commonwealth Government'
        STATE = 'STATE', 'State Budget'
        COMMONWEALTH_STATE = 'COMMONWEALTH_STATE', 'Commonwealth & State Joint'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=255, db_index=True)
    funding_source = models.CharField(max_length=20, choices=FundingSource.choices, blank=True, db_index=True)
    funding_source_other = models.CharField(max_length=255, blank=True, help_text="If 'Other' is selected")
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Total budget (use budgets below for year-specific)")
    gl_code = models.CharField(max_length=100, blank=True, db_index=True)
    business_case_reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def funding_source_display_name(self):
        if self.funding_source == self.FundingSource.OTHER:
            return self.funding_source_other
        return self.get_funding_source_display()
    
    @property
    def budgets_by_year(self):
        """Get all budgets ordered by year"""
        return self.budgets.all().order_by('financial_year')
    
    @property
    def total_allocated(self):
        """Total budget allocated across all years"""
        return self.budgets.aggregate(total=models.Sum('allocated'))['total'] or 0
    
    @property
    def total_spent(self):
        """Total spent across all years (calculated from payments)"""
        from decimal import Decimal
        from apps.payments.models import Payment
        total = Payment.objects.filter(
            project__program=self,
            status='PAID'
        ).aggregate(total=models.Sum('actual_amount'))['total']
        return total or Decimal('0')


class ProgramBudget(models.Model):
    """Year-specific budget allocation for a program"""
    program = models.ForeignKey(Program, related_name='budgets', on_delete=models.CASCADE)
    financial_year = models.CharField(max_length=9, choices=FINANCIAL_YEAR_CHOICES)
    allocated = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Budget allocated for this year")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Program Budget'
        verbose_name_plural = 'Program Budgets'
        unique_together = ['program', 'financial_year']
        ordering = ['financial_year']

    def __str__(self):
        return f"{self.program.name} - {self.financial_year}: ${self.allocated:,}"

    @property
    def committed(self):
        """Calculate committed amount from projects with funding approval"""
        from decimal import Decimal
        from apps.funding.models import FundingApproval
        approvals = FundingApproval.objects.filter(
            project__program=self.program,
            project__financial_year=self.financial_year,
            project__state__in=['FUNDED', 'COMMENCED', 'UNDER_CONSTRUCTION', 'COMPLETED']
        )
        return sum((a.amount or 0) + (a.contingency or 0) for a in approvals)

    @property
    def spent(self):
        """Calculate spent amount from projects at/completed payment stages"""
        from decimal import Decimal
        from apps.payments.models import Payment
        payments = Payment.objects.filter(
            project__program=self.program,
            project__financial_year=self.financial_year,
            status='PAID'
        )
        return sum(p.actual_amount or 0 for p in payments)

    @property
    def remaining(self):
        return self.allocated - self.committed

    @property
    def percent_used(self):
        if self.allocated == 0:
            return 0
        return (self.committed / self.allocated * 100)

    @property
    def percent_spent(self):
        if self.allocated == 0:
            return 0
        return (self.spent / self.allocated * 100)