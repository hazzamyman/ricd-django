from django.db import models

from .projects_models import Project


class Suburb(models.Model):
    """Lookup table for suburbs linked to postcodes and electorates"""
    
    name = models.CharField(max_length=100)
    postcode = models.CharField(max_length=4)
    state = models.CharField(max_length=3, default='QLD')
    state_electorate = models.CharField(max_length=100, blank=True)
    federal_electorate = models.CharField(max_length=100, blank=True)
    qhigi_region = models.CharField(max_length=100, blank=True)
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
