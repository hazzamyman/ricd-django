from django.db import models

class Council(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    region = models.CharField(max_length=255, blank=True, db_index=True)
    # Free-text legacy fields (kept for display fallback during transition)
    state_electorate = models.CharField(max_length=100, blank=True, help_text="State Electorate (legacy free text)")
    federal_electorate = models.CharField(max_length=100, blank=True, help_text="Federal Electorate (legacy free text)")
    # FK to lookup tables — preferred for reporting / filtering
    state_electorate_link = models.ForeignKey(
        'StateElectorate', related_name='councils',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="State Electorate (linked)"
    )
    federal_electorate_link = models.ForeignKey(
        'FederalElectorate', related_name='councils',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Federal Electorate (linked)"
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    is_registered_housing_provider = models.BooleanField(default=False, db_index=True)

    # Default RICD staff assigned to projects for this council
    default_principal_officer = models.ForeignKey(
        'auth.User',
        related_name='default_principal_councils',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default Principal Officer applied to new projects for this council"
    )
    default_senior_officer = models.ForeignKey(
        'auth.User',
        related_name='default_senior_councils',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default Senior Officer applied to new projects for this council"
    )

    # RCPA Funding Agreement contact (Option 3)
    rcpa_contact_name = models.CharField(max_length=255, blank=True, help_text="RCPA contact name")
    rcpa_contact_phone = models.CharField(max_length=50, blank=True, help_text="RCPA contact phone")
    rcpa_contact_email = models.EmailField(blank=True, help_text="RCPA contact email")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CouncilContact(models.Model):
    council = models.ForeignKey(Council, related_name='contacts', on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.role} - {self.name}"