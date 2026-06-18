from django.db import models


class CashflowMethodRule(models.Model):
    """How the ACCRUAL basis is forecast for each project cashflow method.

    The CASH basis is always milestone payments (not stored here). One row per
    Project.CashflowMethod: Capital Grant (MILESTONE) and Capital Works (WORKSTEP).
    Consumed by apps.core.services.cashflow and the Maintenance config page.
    """
    METHOD_CHOICES = [
        ('MILESTONE', 'Capital Grants (Payment Milestone)'),
        ('WORKSTEP', 'Capital Works (WorkStep Progressive)'),
    ]

    class AccrualSource(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment milestones'
        WORKSTEP = 'WORKSTEP', 'WorkStep progressive'

    class WorkstepDate(models.TextChoices):
        FORECAST_COMPLETION = 'FCOMP', 'Forecast completion date'
        FORECAST_START = 'FSTART', 'Forecast start date'

    class CostBasis(models.TextChoices):
        EFFECTIVE = 'EFFECTIVE', 'Effective (actual where entered, else estimated)'
        ESTIMATED = 'ESTIMATED', 'Estimated only'

    method = models.CharField(max_length=10, choices=METHOD_CHOICES, unique=True)
    accrual_source = models.CharField(max_length=10, choices=AccrualSource.choices)
    workstep_date = models.CharField(
        max_length=10, choices=WorkstepDate.choices,
        default=WorkstepDate.FORECAST_COMPLETION,
        help_text="Which workstep date forecasts the accrual (actuals always use the "
                  "actual completion date). Only used when accrual is via worksteps.",
    )
    cost_basis = models.CharField(
        max_length=10, choices=CostBasis.choices, default=CostBasis.EFFECTIVE,
        help_text="Value base for a workstep's share of the work cost. Only used when "
                  "accrual is via worksteps.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['method']
        verbose_name = 'Cashflow method rule'

    def __str__(self):
        return f"{self.get_method_display()} — accrual via {self.get_accrual_source_display()}"

    @classmethod
    def get(cls, method):
        """Return the rule for a method, seeding a sensible default if absent.

        Capital Grant -> accrual via payments; Capital Works -> accrual via worksteps.
        """
        defaults = ({'accrual_source': cls.AccrualSource.WORKSTEP}
                    if method == 'WORKSTEP'
                    else {'accrual_source': cls.AccrualSource.PAYMENT})
        obj, _ = cls.objects.get_or_create(method=method, defaults=defaults)
        return obj
