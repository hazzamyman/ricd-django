from django import forms
from ricd.models import Council, Program, Officer, SiteConfiguration, Defect


class CouncilForm(forms.ModelForm):
    """Form for creating and editing Councils"""

    default_principal_officer = forms.ModelChoiceField(
        queryset=None,  # Will be filtered
        required=False,
        label="Default Principal Officer",
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text="This officer will be automatically assigned as Principal Officer for new projects in this council."
    )

    default_senior_officer = forms.ModelChoiceField(
        queryset=None,  # Will be filtered
        required=False,
        label="Default Senior Officer",
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text="This officer will be automatically assigned as Senior Officer for new projects in this council."
    )

    class Meta:
        model = Council
        fields = [
            'name', 'abn', 'default_suburb', 'default_postcode', 'default_state',
            'federal_electorate', 'state_electorate', 'qhigi_region',
            'default_principal_officer', 'default_senior_officer'
        ]
    # Add __init__ method to filter officer querysets
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter officers based on council - show all officers with councils
        # or filter by instance council for editing
        all_council_officers = Officer.objects.filter(
            is_active=True
        ).select_related('user', 'user__profile')

        # Separate querysets for principal and senior officers
        self.fields['default_principal_officer'].queryset = all_council_officers.filter(is_principal=True)
        self.fields['default_senior_officer'].queryset = all_council_officers.filter(is_senior=True)

        # For existing councils, pre-select current defaults
        if self.instance and self.instance.pk:
            self.fields['default_principal_officer'].initial = self.instance.default_principal_officer
            self.fields['default_senior_officer'].initial = self.instance.default_senior_officer

    widgets = {
        'name': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter council name'
        }),
        'abn': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '11-digit ABN (optional)'
        }),
        'default_suburb': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Default suburb'
        }),
        'default_postcode': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Postcode (optional)'
        }),
        'default_state': forms.Select(attrs={
            'class': 'form-select'
        }, choices=[('QLD', 'Queensland')]),
        'federal_electorate': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Federal electorate'
        }),
        'state_electorate': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'State electorate'
        }),
        'qhigi_region': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'QHiGi region'
        }),
    }


# Program Management Forms
class ProgramForm(forms.ModelForm):
    """Form for creating and editing Programs"""

    class Meta:
        model = Program
        fields = [
            'name', 'description', 'budget', 'funding_source'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter program name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Program description (optional)'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Budget amount (optional)'
            }),
            'funding_source': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

# Site Configuration Form
class SiteConfigurationForm(forms.ModelForm):
    """Form for site-wide configuration settings"""

    class Meta:
        model = SiteConfiguration
        fields = '__all__'
        widgets = {
            'date_format': forms.Select(attrs={'class': 'form-select'}),
            'time_format': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'default_currency': forms.Select(attrs={'class': 'form-select'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_position': forms.Select(attrs={'class': 'form-select'}),
            'default_language': forms.Select(attrs={'class': 'form-select'}),
            'decimal_places': forms.NumberInput(attrs={'class': 'form-control'}),
            'thousands_separator': forms.TextInput(attrs={'class': 'form-control'}),
            'decimal_separator': forms.TextInput(attrs={'class': 'form-control'}),
            'enable_dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_animations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'maintenance_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'maintenance_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'site_title': forms.TextInput(attrs={'class': 'form-control'}),
            'site_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'support_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'support_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
# Defect Form
class DefectForm(forms.ModelForm):
    """Form for creating and editing defects"""

    class Meta:
        model = Defect
        fields = ['work', 'description', 'identified_date', 'rectified_date']
        widgets = {
            'work': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'identified_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rectified_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }