from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal


class BaseAgreement(models.Model):
    """Base class for funding agreements"""
    date_sent_to_council = models.DateField(blank=True, null=True, help_text="Date funding agreement sent to council")
    date_council_signed = models.DateField(blank=True, null=True, help_text="Date council signed the agreement")
    date_delegate_signed = models.DateField(blank=True, null=True, help_text="Date delegate signed the agreement")

    class Meta:
        abstract = True

    @property
    def date_executed(self):
        """Calculate executed date as the latest of council or delegate signed"""
        dates = [date for date in [self.date_council_signed, self.date_delegate_signed] if date is not None]
        return max(dates) if dates else None


class FundingSchedule(models.Model):
    council = models.ForeignKey('ricd.Council', on_delete=models.CASCADE, related_name="funding_schedules", null=True, blank=True)
    program = models.ForeignKey('ricd.Program', on_delete=models.CASCADE, related_name="funding_schedules", null=True, blank=True)
    funding_schedule_number = models.IntegerField(validators=[MinValueValidator(1)])
    # Simplified funding structure
    funding_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Total funding amount allocated")
    contingency_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0.01'))], help_text="Contingency amount (calculated or manual)")

    # Simplified payment tracking
    first_payment_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0.01'))])
    first_release_date = models.DateField(blank=True, null=True)
    first_reference_number = models.CharField(max_length=100, blank=True, null=True)

    # Additional agreement fields for different agreement types
    agreement_type = models.CharField(
        max_length=50,
        choices=[
            ('funding_schedule', 'Funding Schedule'),
            ('frpf_agreement', 'Forward Remote Program Funding Agreement'),
            ('ifrpf_agreement', 'Interim Forward Remote Program Funding Agreement'),
            ('rcpf_agreement', 'Remote Capital Program Funding Agreement'),
        ],
        default='funding_schedule',
        help_text="Type of funding agreement"
    )

    remote_capital_program = models.ForeignKey(
        'ricd.RemoteCapitalProgramFundingAgreement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_funding",
        help_text="Remote Capital Program Funding Agreement this schedule belongs to"
    )

    # Signature dates for agreements
    date_sent_to_council = models.DateField(blank=True, null=True, help_text="Date funding agreement sent to council")
    date_council_signed = models.DateField(blank=True, null=True, help_text="Date council signed the agreement")
    date_delegate_signed = models.DateField(blank=True, null=True, help_text="Date delegate signed the agreement")
    executed_date = models.DateField(blank=True, null=True, help_text="Date agreement was executed (calculated)")

    class Meta:
        unique_together = ('council', 'funding_schedule_number')

    def clean(self):
        """Validate FundingSchedule fields"""
        if self.funding_schedule_number <= 0:
            raise ValidationError({'funding_schedule_number': 'Funding schedule number must be positive'})

        if self.funding_amount <= 0:
            raise ValidationError({'funding_amount': 'Funding amount must be positive'})

        if self.contingency_amount is not None and self.contingency_amount <= 0:
            raise ValidationError({'contingency_amount': 'Contingency amount must be positive'})

        if self.first_payment_amount is not None and self.first_payment_amount <= 0:
            raise ValidationError({'first_payment_amount': 'First payment amount must be positive'})

        if self.first_release_date and self.first_release_date < timezone.now().date():
            raise ValidationError({'first_release_date': 'First release date cannot be in the past'})

        if self.agreement_type not in ['funding_schedule', 'frpf_agreement', 'ifrpf_agreement', 'rcpf_agreement']:
            raise ValidationError({'agreement_type': 'Invalid agreement type'})

        # Date validations for signatures
        if self.date_sent_to_council and self.date_sent_to_council > timezone.now().date():
            raise ValidationError({'date_sent_to_council': 'Date sent to council cannot be in the future'})

        if self.date_council_signed and self.date_council_signed > timezone.now().date():
            raise ValidationError({'date_council_signed': 'Date council signed cannot be in the future'})

        if self.date_delegate_signed and self.date_delegate_signed > timezone.now().date():
            raise ValidationError({'date_delegate_signed': 'Date delegate signed cannot be in the future'})

        # Date sequence validation
        if self.date_sent_to_council and self.date_council_signed and self.date_sent_to_council > self.date_council_signed:
            raise ValidationError({'date_council_signed': 'Council signed date cannot be before date sent to council'})

        if self.date_sent_to_council and self.date_delegate_signed and self.date_sent_to_council > self.date_delegate_signed:
            raise ValidationError({'date_delegate_signed': 'Delegate signed date cannot be before date sent to council'})

    @property
    def total_funding(self):
        return self.funding_amount + (self.contingency_amount or 0)

    def save(self, *args, **kwargs):
        # Auto-set first payment if funding is allocated but payment details blank
        if self.funding_amount and not self.first_payment_amount:
            # Calculate contingency portion from commitment percentage if project exists
            project = self.projects.first()
            if project and project.contingency_percentage:
                contingency_portion = self.funding_amount * project.contingency_percentage
                payment_amount = self.funding_amount - contingency_portion + (self.contingency_amount or 0)
                self.first_payment_amount = payment_amount.quantize(Decimal('0.01'))
            else:
                # Default: 90% of total as first payment
                self.first_payment_amount = (self.funding_amount * Decimal('0.9')).quantize(Decimal('0.01'))

            # Set release date and reference
            if not self.first_release_date:
                self.first_release_date = timezone.now().date() + timezone.timedelta(days=30)
            if not self.first_reference_number:
                self.first_reference_number = f"FS-{self.funding_schedule_number}-001"

        # Auto-calculate executed_date if council_signed and delegate_signed dates are available
        if self.date_council_signed and self.date_delegate_signed:
            # Executed date is the later of the two signature dates
            self.executed_date = max(self.date_council_signed, self.date_delegate_signed)
        elif self.date_council_signed:
            self.executed_date = self.date_council_signed
        elif self.date_delegate_signed:
            self.executed_date = self.date_delegate_signed

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.council} - {self.funding_schedule_number}"


class ForwardRemoteProgramFundingAgreement(BaseAgreement):
    """Forward Remote Program Funding Agreement"""
    council = models.OneToOneField(
        'ricd.Council',
        on_delete=models.CASCADE,
        null=True,
        related_name="forward_rpf_agreement",
        help_text="Council this agreement applies to"
    )

    def clean(self):
        """Validate ForwardRemoteProgramFundingAgreement fields"""
        # Date validations from BaseAgreement
        if self.date_council_signed and self.date_council_signed > timezone.now().date():
            raise ValidationError({'date_council_signed': 'Date council signed cannot be in the future'})

        if self.date_delegate_signed and self.date_delegate_signed > timezone.now().date():
            raise ValidationError({'date_delegate_signed': 'Date delegate signed cannot be in the future'})

        if self.date_sent_to_council and self.date_sent_to_council > timezone.now().date():
            raise ValidationError({'date_sent_to_council': 'Date sent to council cannot be in the future'})

    def __str__(self):
        return f"FRPF Agreement - {self.council.name} - Executed: {self.date_executed}"


class InterimForwardProgramFundingAgreement(BaseAgreement):
    """Interim Forward Remote Program Funding Agreement"""
    council = models.OneToOneField(
        'ricd.Council',
        on_delete=models.CASCADE,
        null=True,
        related_name="interim_fp_agreement",
        help_text="Council this agreement applies to"
    )

    def clean(self):
        """Validate InterimForwardProgramFundingAgreement fields"""
        # Date validations from BaseAgreement
        if self.date_council_signed and self.date_council_signed > timezone.now().date():
            raise ValidationError({'date_council_signed': 'Date council signed cannot be in the future'})

        if self.date_delegate_signed and self.date_delegate_signed > timezone.now().date():
            raise ValidationError({'date_delegate_signed': 'Date delegate signed cannot be in the future'})

        if self.date_sent_to_council and self.date_sent_to_council > timezone.now().date():
            raise ValidationError({'date_sent_to_council': 'Date sent to council cannot be in the future'})

    def __str__(self):
        return f"IFRPF Agreement - {self.council.name} - Executed: {self.date_executed}"


class RemoteCapitalProgramFundingAgreement(BaseAgreement):
    """Remote Capital Program Funding Agreement"""
    council = models.OneToOneField(
        'ricd.Council',
        on_delete=models.CASCADE,
        related_name="remote_capital_program_agreement",
        help_text="Council this agreement applies to"
    )

    # Can have many funding schedules
    funding_schedules = models.ManyToManyField(
        FundingSchedule,
        blank=True,
        related_name="remote_capital_program_agreements",
        help_text="Funding schedules under this program agreement"
    )

    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the agreement")

    def clean(self):
        """Validate RemoteCapitalProgramFundingAgreement fields"""
        # Date validations from BaseAgreement
        if self.date_council_signed and self.date_council_signed > timezone.now().date():
            raise ValidationError({'date_council_signed': 'Date council signed cannot be in the future'})

        if self.date_delegate_signed and self.date_delegate_signed > timezone.now().date():
            raise ValidationError({'date_delegate_signed': 'Date delegate signed cannot be in the future'})

        if self.date_sent_to_council and self.date_sent_to_council > timezone.now().date():
            raise ValidationError({'date_sent_to_council': 'Date sent to council cannot be in the future'})

    def __str__(self):
        return f"RCFP Agreement - {self.council.name} - Executed: {self.date_executed}"

    class Meta:
        verbose_name = "Remote Capital Program Funding Agreement"
        verbose_name_plural = "Remote Capital Program Funding Agreements"


class FundingApproval(models.Model):
    mincor_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    approved_by_position = models.CharField(max_length=255, help_text="Position/role that approved")
    approved_date = models.DateField()
    projects = models.ManyToManyField('Project', related_name='funding_approvals')

    def clean(self):
        """Validate FundingApproval fields"""
        if not self.mincor_reference.strip():
            raise ValidationError({'mincor_reference': 'Mincor reference is required'})

        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be positive'})

        if not self.approved_by_position.strip():
            raise ValidationError({'approved_by_position': 'Approved by position is required'})

        if self.approved_date > timezone.now().date():
            raise ValidationError({'approved_date': 'Approved date cannot be in the future'})

    def __str__(self):
        return f"Approval {self.mincor_reference} - ${self.amount}"

    class Meta:
        ordering = ['-approved_date']


class Instalment(models.Model):
    funding_schedule = models.ForeignKey(FundingSchedule, on_delete=models.CASCADE, related_name="instalments")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paid = models.BooleanField(default=False)
    release_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    def clean(self):
        """Validate Instalment fields"""
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be positive'})

        if self.due_date < timezone.now().date():
            raise ValidationError({'due_date': 'Due date cannot be in the past'})

        if self.release_date and self.release_date > timezone.now().date():
            raise ValidationError({'release_date': 'Release date cannot be in the future'})

        if self.release_date and self.release_date > self.due_date:
            raise ValidationError({'release_date': 'Release date cannot be after due date'})

        if self.paid and not self.release_date:
            raise ValidationError({'paid': 'Release date is required when payment is marked as paid'})

    def __str__(self):
        return f"Instalment {self.amount} due {self.due_date} - {self.payment_reference or 'No ref'}"


# Signals for automation
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Instalment)
def update_project_funded(sender, instance, **kwargs):
    project = instance.funding_schedule.projects.first()
    if project and project.state == 'prospective' and (instance.paid or instance.release_date):
        project.state = "funded"
        project.save()