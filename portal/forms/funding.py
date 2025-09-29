from django import forms
from ricd.models import (
    FundingApproval, ForwardRemoteProgramFundingAgreement,
    InterimForwardProgramFundingAgreement, RemoteCapitalProgramFundingAgreement,
    Project, FundingSchedule, ForwardRemoteProgramFundingAgreement,
    InterimForwardProgramFundingAgreement, RemoteCapitalProgramFundingAgreement
)


class FundingApprovalForm(forms.ModelForm):
    """Form for creating and updating Funding Approvals with filtered project choices"""
    projects = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be filtered to active projects only
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        help_text="Only projects in 'prospective' or 'programmed' status are available for funding approval."
    )

    class Meta:
        model = FundingApproval
        fields = ['mincor_reference', 'amount', 'approved_by_position', 'approved_date', 'projects']
        widgets = {
            'mincor_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MINCOR reference number'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Approval amount'
            }),
            'approved_by_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Position that approved this funding'
            }),
            'approved_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        initial_project = kwargs.pop('initial_project', None)
        super().__init__(*args, **kwargs)
        # Filter projects to only show prospective or programmed projects
        self.fields['projects'].queryset = Project.objects.filter(
            state__in=['prospective', 'programmed']
        ).select_related('council').order_by('name')

        # If initial project provided, pre-select it
        if initial_project and initial_project.state in ['prospective', 'programmed']:
            self.fields['projects'].initial = [initial_project]


class ForwardRemoteProgramFundingAgreementForm(forms.Form):
    """Form for creating and editing Forward Remote Program Funding Agreements"""
    # TODO: Auto-converted from ModelForm due to model loading issues in commit autos/auto-fix-20250929-1
    # Original: ModelForm with model=ForwardRemoteProgramFundingAgreement, fields=['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed']

    council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'disabled': 'disabled'}))
    date_sent_to_council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_council_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_delegate_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))


class InterimForwardProgramFundingAgreementForm(forms.Form):
    """Form for creating and editing Interim Forward Remote Program Funding Agreements"""
    # TODO: Auto-converted from ModelForm due to model loading issues in commit autos/auto-fix-20250929-1
    # Original: ModelForm with model=InterimForwardProgramFundingAgreement, fields=['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed']

    council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'disabled': 'disabled'}))
    date_sent_to_council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_council_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_delegate_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))


class RemoteCapitalProgramFundingAgreementForm(forms.Form):
    """Form for creating and editing Remote Capital Program Funding Agreements"""
    # TODO: Auto-converted from ModelForm due to model loading issues in commit autos/auto-fix-20250929-1
    # Original: ModelForm with model=RemoteCapitalProgramFundingAgreement, fields=['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed', 'notes']

    council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'disabled': 'disabled'}))
    date_sent_to_council = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_council_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_delegate_signed = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Additional notes about the agreement (optional)'}))