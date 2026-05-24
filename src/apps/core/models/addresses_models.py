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
    project = models.ForeignKey(Project, related_name='addresses', on_delete=models.CASCADE)
    street = models.CharField(max_length=255)
    suburb = models.ForeignKey(Suburb, related_name='addresses', on_delete=models.PROTECT, null=True, blank=True)
    lot = models.CharField(max_length=100, blank=True)
    plan = models.CharField(max_length=100, blank=True)
    residence_plc_ref = models.CharField(max_length=100, blank=True, help_text="Reside PLC system reference")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        parts = [self.street]
        if self.suburb:
            parts.append(self.suburb.name)
            parts.append(self.suburb.postcode)
        return ", ".join(parts)
