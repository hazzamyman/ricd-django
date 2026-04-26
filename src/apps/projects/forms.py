from django import forms
from django.core.exceptions import ValidationError
from apps.projects.models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'council', 'program', 'funding_schedule',
            'financial_year', 'start_date', 'funding_approval_date',
            'stage1_target_date', 'stage2_target_date',
            'stage1_sunset_date', 'stage2_sunset_date',
            'state', 'dwelling_status', 'status_flag',
            'land_project', 'land_parcels',
            'lease_signed_date', 'completion_date',
            'handover_checklist_link', 'warranty_end_date',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project name'}),
            'council': forms.Select(attrs={'class': 'form-select'}),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'funding_schedule': forms.Select(attrs={'class': 'form-select'}),
            'financial_year': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'funding_approval_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stage1_target_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stage2_target_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stage1_sunset_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stage2_sunset_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'dwelling_status': forms.Select(attrs={'class': 'form-select'}),
            'status_flag': forms.Select(attrs={'class': 'form-select'}),
            'land_project': forms.Select(attrs={'class': 'form-select'}),
            'land_parcels': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'lease_signed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'handover_checklist_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'warranty_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        completion_date = cleaned_data.get('completion_date')
        
        if start_date and completion_date and completion_date < start_date:
            raise ValidationError('Completion date cannot be before start date.')
        
        stage1_target = cleaned_data.get('stage1_target_date')
        stage1_sunset = cleaned_data.get('stage1_sunset_date')
        if stage1_target and stage1_sunset and stage1_sunset < stage1_target:
            raise ValidationError('Stage 1 sunset date cannot be before target date.')
        
        stage2_target = cleaned_data.get('stage2_target_date')
        stage2_sunset = cleaned_data.get('stage2_sunset_date')
        if stage2_target and stage2_sunset and stage2_sunset < stage2_target:
            raise ValidationError('Stage 2 sunset date cannot be before target date.')
        
        return cleaned_data