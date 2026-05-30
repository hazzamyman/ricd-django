from django.db import models

from .projects_models import Project


# ============================================================================
# Geographic / electoral lookup tables
#
# These replace the free-text electorate / region columns on Suburb and Council.
# Reports often group by electorate (state or federal) or by QHIGI region, so
# having proper FK lookup tables enables filtering, dropdowns, and dedupe.
# ============================================================================

class StateElectorate(models.Model):
    """Queensland state electorate (one of ~93)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'State Electorate'
        verbose_name_plural = 'State Electorates'

    def __str__(self):
        return self.name


class FederalElectorate(models.Model):
    """Federal (Commonwealth) electorate."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Federal Electorate'
        verbose_name_plural = 'Federal Electorates'

    def __str__(self):
        return self.name


class QhigiRegion(models.Model):
    """QHIGI (Queensland Housing & Indigenous Growth Initiative) region."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'QHIGI Region'
        verbose_name_plural = 'QHIGI Regions'

    def __str__(self):
        return self.name


class Suburb(models.Model):
    """Lookup table for suburbs linked to postcodes and electorates"""

    name = models.CharField(max_length=100)
    postcode = models.CharField(max_length=4)
    state = models.CharField(max_length=3, default='QLD')
    # Free-text legacy fields (kept for display fallback; new code reads FK fields)
    state_electorate = models.CharField(max_length=100, blank=True)
    federal_electorate = models.CharField(max_length=100, blank=True)
    qhigi_region = models.CharField(max_length=100, blank=True)
    # FK to lookup tables — preferred when reporting / filtering by electorate
    state_electorate_link = models.ForeignKey(
        StateElectorate, related_name='suburbs',
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    federal_electorate_link = models.ForeignKey(
        FederalElectorate, related_name='suburbs',
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    qhigi_region_link = models.ForeignKey(
        QhigiRegion, related_name='suburbs',
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'postcode', 'state']

    def __str__(self):
        return f"{self.name} {self.postcode} ({self.state})"


class Address(models.Model):

    class LivableHousingLevel(models.TextChoices):
        SILVER = 'SILVER', 'Silver'
        GOLD = 'GOLD', 'Gold'
        PLATINUM = 'PLATINUM', 'Platinum'

    class LeaseStatus(models.TextChoices):
        NOT_REQUIRED = 'NR', 'Not Required'
        PENDING = 'PEND', 'Pending'
        EXECUTED = 'EXEC', 'Executed'

    class LandStatus(models.TextChoices):
        AVAILABLE = 'AVAIL', 'Available'
        ACQUIRED = 'ACQ', 'Acquired'
        CROWN = 'CROWN', 'Crown Land'
        TRANSFER_PENDING = 'TPEND', 'Transfer Pending'

    class UsageType(models.TextChoices):
        PUBLIC_HOUSING = 'PH', 'Public Housing'
        AFFORDABLE = 'AH', 'Affordable Housing'
        COMMUNITY = 'CH', 'Community Housing'
        MIXED = 'MX', 'Mixed Use'

    project = models.ForeignKey(Project, related_name='addresses', on_delete=models.CASCADE)
    street = models.CharField(max_length=255)
    suburb = models.ForeignKey(Suburb, related_name='addresses', on_delete=models.PROTECT, null=True, blank=True)
    lot = models.CharField(max_length=100, blank=True)
    plan = models.CharField(max_length=100, blank=True)
    residence_plc_ref = models.CharField(max_length=100, blank=True, help_text="Reside PLC system reference")

    # Dwelling characteristics
    floor_number = models.CharField(max_length=10, blank=True, help_text="Floor number for apartments (e.g. '3', 'G')")
    livable_housing_level = models.CharField(
        max_length=8, choices=LivableHousingLevel.choices, blank=True, default='',
        help_text="Livable Housing Design guideline level (Silver / Gold / Platinum)",
    )
    land_status = models.CharField(max_length=5, choices=LandStatus.choices, blank=True, default='')
    usage_type = models.CharField(max_length=2, choices=UsageType.choices, blank=True, default='')

    # Lease tracking
    lease_status = models.CharField(max_length=4, choices=LeaseStatus.choices, blank=True, default='')
    lease_executed_date = models.DateField(null=True, blank=True)

    # Construction materials (free text — recorded as-built)
    floor_material = models.CharField(max_length=100, blank=True)
    frame_material = models.CharField(max_length=100, blank=True)
    wall_material = models.CharField(max_length=100, blank=True)
    roof_material = models.CharField(max_length=100, blank=True)
    car_accommodation = models.CharField(max_length=100, blank=True)

    # Room counts
    bathrooms_count = models.PositiveIntegerField(null=True, blank=True)
    kitchens_count = models.PositiveIntegerField(null=True, blank=True)
    living_rooms_count = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # PC + Handover aggregates — derived from Works at this address (Option C)
    def _work_date_aggregate(self, field_name):
        works = list(self.works.all())
        if not works:
            return None
        vals = [getattr(w, field_name) for w in works]
        if any(v is None for v in vals):
            return None
        return max(vals)

    def _work_date_forecast(self, field_name):
        works = list(self.works.all())
        if not works:
            return None
        vals = [v for v in (getattr(w, field_name) for w in works) if v is not None]
        return max(vals) if vals else None

    @property
    def practical_completion_date(self):
        return self._work_date_aggregate('practical_completion_date')

    @property
    def forecast_practical_completion_date(self):
        return self._work_date_forecast('forecast_practical_completion_date')

    @property
    def handover_date(self):
        return self._work_date_aggregate('handover_date')

    @property
    def forecast_handover_date(self):
        return self._work_date_forecast('forecast_handover_date')

    def __str__(self):
        parts = [self.street]
        if self.suburb:
            parts.append(self.suburb.name)
            parts.append(self.suburb.postcode)
        return ", ".join(parts)
