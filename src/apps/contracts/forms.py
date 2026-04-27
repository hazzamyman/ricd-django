from django import forms
from django.core.exceptions import ValidationError
from apps.contracts.models import Contract, ContractMeeting


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'project', 'contract_status',
            'title', 'document', 'sent_to_council_date', 'council_executed_date',
            'execution_date', 'start_date', 'end_date', 'expiry_date', 'termination_date', 'notes',
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'contract_status': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contract title'}),
            'document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'sent_to_council_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'council_executed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'execution_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'termination_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        
        if not project:
            raise ValidationError('Please select a project.')
        
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data


class ContractMeetingForm(forms.ModelForm):
    class Meta:
        model = ContractMeeting
        fields = [
            'contract', 'meeting_type', 'meeting_date',
            'location', 'attendees', 'minutes', 'action_items', 'notes',
        ]
        widgets = {
            'contract': forms.Select(attrs={'class': 'form-select'}),
            'meeting_type': forms.Select(attrs={'class': 'form-select'}),
            'meeting_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'attendees': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Attendees (one per line)'}),
            'minutes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'action_items': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Action items (one per line)'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }