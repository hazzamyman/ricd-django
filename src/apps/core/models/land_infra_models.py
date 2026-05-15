from django.db import models
from django.urls import reverse


class LandTenure(models.Model):
    class TenureType(models.TextChoices):
        CROWN = 'CROWN', 'Crown Land'
        FREEHOLD = 'FREEHOLD', 'Freehold'
        LEASEHOLD = 'LEASEHOLD', 'Leasehold'

    class NativeTitleStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CLEARED = 'CLEARED', 'Cleared'
        IULA = 'IULA', 'IULA'
        JJAA_24JAA = '24JAA', '24JAA'
        KKAA_24KAA = '24KAA', '24KAA'

    class CulturalHeritageStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CLEARED = 'CLEARED', 'Cleared'

    council = models.ForeignKey('Council', related_name='land_tenures', on_delete=models.CASCADE)
    parent_lot = models.ForeignKey(
        'self',
        related_name='subdivided_lots',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Parent lot if this is a subdivided child parcel"
    )
    lot_number = models.CharField(max_length=50)
    plan_number = models.CharField(max_length=50)
    title_reference = models.CharField(max_length=100, blank=True)
    tenure_type = models.CharField(max_length=10, choices=TenureType.choices, default=TenureType.CROWN)

    native_title_status = models.CharField(
        max_length=10,
        choices=NativeTitleStatus.choices,
        default=NativeTitleStatus.PENDING
    )
    native_title_reference = models.CharField(max_length=100, blank=True)

    cultural_heritage_status = models.CharField(
        max_length=10,
        choices=CulturalHeritageStatus.choices,
        default=CulturalHeritageStatus.PENDING
    )
    cultural_heritage_reference = models.CharField(max_length=100, blank=True)

    is_developed = models.BooleanField(default=False)
    developed_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['council', 'lot_number', 'plan_number']
        ordering = ['council', 'lot_number', 'plan_number']

    def __str__(self):
        return f"Lot {self.lot_number} on {self.plan_number}"


class DevelopmentApplication(models.Model):
    class ApplicationType(models.TextChoices):
        DA = 'DA', 'Development Application'
        MCU = 'MCU', 'Material Change of Use'
        RAL = 'RAL', 'Reconfiguring a Lot'
        PA = 'PA', 'Preliminary Approval'

    class Status(models.TextChoices):
        PREPARING = 'PREP', 'Preparing'
        SUBMITTED = 'SUB', 'Submitted'
        UNDER_ASSESSMENT = 'ASSESS', 'Under Assessment'
        APPROVED = 'APPR', 'Approved'
        REFUSED = 'REF', 'Refused'
        WITHDRAWN = 'WD', 'Withdrawn'

    council = models.ForeignKey('Council', related_name='development_applications', on_delete=models.CASCADE)
    projects = models.ManyToManyField('Project', related_name='development_applications', blank=True)
    application_type = models.CharField(max_length=5, choices=ApplicationType.choices, default=ApplicationType.DA)
    application_reference = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PREPARING)

    lodged_date = models.DateField(null=True, blank=True)
    decision_date = models.DateField(null=True, blank=True)
    lapsing_date = models.DateField(null=True, blank=True)

    decision_notice_link = models.URLField(blank=True)
    conditions = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application_type} - {self.application_reference}"

    def get_absolute_url(self):
        return reverse('land_infra:development_application_detail', args=[self.id])