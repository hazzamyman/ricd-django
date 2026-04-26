from django import forms
from django.core.exceptions import ValidationError
from apps.funding.models import FundingSchedule, FundingApproval, WorkFunding


class FundingScheduleForm(forms.ModelForm):
    class Meta:
        model = FundingSchedule
        fields = [
            'project_type', 'project', 'land_project', 'councils', 'works',
            'amount', 'contingency', 'payment_split',
            'notional_total', 'actual_total',
        ]
        widgets = {
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'land_project': forms.Select(attrs={'class': 'form-select'}),
            'councils': forms.CheckboxSelectMultiple(attrs={'class': 'form-check'}),
            'works': forms.CheckboxSelectMultiple(attrs={'class': 'form-check'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'contingency': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'payment_split': forms.Select(attrs={'class': 'form-select'}),
            'notional_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'actual_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        contingency = cleaned_data.get('contingency')
        project_type = cleaned_data.get('project_type')
        project = cleaned_data.get('project')
        land_project = cleaned_data.get('land_project')
        
        if amount is not None and amount < 0:
            raise ValidationError('Amount cannot be negative.')
        
        if contingency is not None and contingency < 0:
            raise ValidationError('Contingency cannot be negative.')
        
        if amount is not None and contingency is not None:
            if amount > 0 and contingency > (amount * 0.5):
                raise ValidationError('Contingency exceeds 50% of the amount. Please verify.')
        
        if project_type == FundingSchedule.ProjectType.DWELLING and not project:
            raise ValidationError('Please select a Dwelling Project.')
        
        if project_type == FundingSchedule.ProjectType.LAND and not land_project:
            raise ValidationError('Please select a Land/Infrastructure Project.')
        
        return cleaned_data


class FundingApprovalForm(forms.ModelForm):
    class Meta:
        model = FundingApproval
        fields = [
            'projects', 'status', 'total_amount', 'contingency_amount',
            'mincor_reference', 'mincor_link',
            'peer_review_required', 'peer_reviewer',
        ]
        widgets = {
            'projects': forms.CheckboxSelectMultiple(attrs={'class': 'form-check'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'contingency_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'mincor_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MN12345-2025'}),
            'mincor_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'peer_review_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'peer_reviewer': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        total_amount = cleaned_data.get('total_amount')
        contingency_amount = cleaned_data.get('contingency_amount')
        
        if total_amount is not None and total_amount < 0:
            raise ValidationError('Total amount cannot be negative.')
        
        if contingency_amount is not None and contingency_amount < 0:
            raise ValidationError('Contingency amount cannot be negative.')
        
        return cleaned_data


class WorkFundingForm(forms.ModelForm):
    class Meta:
        model = WorkFunding
        fields = [
            'work', 'funding_schedule',
            'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes',
        ]
        widgets = {
            'work': forms.Select(attrs={'class': 'form-select'}),
            'funding_schedule': forms.Select(attrs={'class': 'form-select'}),
            'cost_centre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 316333'}),
            'gl_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ABC123'}),
            'tax_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., GST'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
