from django.db import models

from .councils_models import Council


class Contractor(models.Model):
    class TradeType(models.TextChoices):
        CARPENTER = 'CARPENTER', 'Carpenter'
        BUILDER = 'BUILDER', 'Builder'
        ELECTRICIAN = 'ELECTRICIAN', 'Electrician'
        PLUMBER = 'PLUMBER', 'Plumber'
        CONCRETER = 'CONCRETER', 'Concreter'
        LANDSCAPER = 'LANDSCAPER', 'Landscaper'
        CIVIL_ENGINEER = 'CIVIL_ENGINEER', 'Civil Engineer'
        EARTHWORKS = 'EARTHWORKS', 'Earthworks'
        PAINTER = 'PAINTER', 'Painter'
        ROOFER = 'ROOFER', 'Roofing'
        TILER = 'TILER', 'Tiler'
        BRICKLAYER = 'BRICKLAYER', 'Bricklayer'
        PLANNER = 'PLANNER', 'Town Planner/Urban Planner'
        ARCHITECT = 'ARCHITECT', 'Architect'
        SURVEYOR = 'SURVEYOR', 'Surveyor'
        ENGINEER = 'ENGINEER', 'Engineer'
        OTHER = 'OTHER', 'Other'

    council = models.ForeignKey(Council, related_name='contractors', on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    trade_type = models.CharField(max_length=30, choices=TradeType.choices)
    contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    licence_number = models.CharField(max_length=100, blank=True)
    licence_expiry = models.DateField(null=True, blank=True)
    abn = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['council', 'company_name']
        unique_together = ['council', 'company_name', 'trade_type']

    def __str__(self):
        return f"{self.company_name} ({self.get_trade_type_display()}) - {self.council.name}"
