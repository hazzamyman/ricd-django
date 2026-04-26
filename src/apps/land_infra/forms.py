from django import forms
from django.core.exceptions import ValidationError
from apps.land_infra.models import LandProject, LandTenure, DevelopmentApplication


class LandProjectForm(forms.ModelForm):
    class Meta:
        model = LandProject
        fields = [
            'name', 'council', 'description', 'financial_year', 'status',
            'start_date', 'completion_date', 'development_application',
            'infra_water_assessment', 'infra_electricity_assessment',
            'infra_sewerage_assessment', 'infra_comments', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Land project name'}),
            'council': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'financial_year': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'development_application': forms.Select(attrs={'class': 'form-select'}),
            'infra_water_assessment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Is there sufficient water infrastructure to support the project? What is the connection capacity?'}),
            'infra_electricity_assessment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Is there sufficient electricity infrastructure to support the project? What is the transformer capacity?'}),
            'infra_sewerage_assessment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Is there sufficient sewerage infrastructure to support the project? What is the treatment capacity?'}),
            'infra_comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        completion_date = cleaned_data.get('completion_date')

        if start_date and completion_date and completion_date < start_date:
            raise ValidationError('Completion date cannot be before start date.')

        return cleaned_data


class LandTenureForm(forms.ModelForm):
    class Meta:
        model = LandTenure
        fields = [
            'council', 'parent_lot', 'lot_number', 'plan_number',
            'title_reference', 'tenure_type',
            'native_title_status', 'native_title_reference',
            'cultural_heritage_status', 'cultural_heritage_reference',
            'is_developed', 'developed_date', 'notes',
        ]
        widgets = {
            'council': forms.Select(attrs={'class': 'form-select'}),
            'parent_lot': forms.Select(attrs={'class': 'form-select'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2'}),
            'plan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SP34343'}),
            'title_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 12345678'}),
            'tenure_type': forms.Select(attrs={'class': 'form-select'}),
            'native_title_status': forms.Select(attrs={'class': 'form-select'}),
            'native_title_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'cultural_heritage_status': forms.Select(attrs={'class': 'form-select'}),
            'cultural_heritage_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'is_developed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'developed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DevelopmentApplicationForm(forms.ModelForm):
    class Meta:
        model = DevelopmentApplication
        fields = [
            'council', 'projects', 'application_type', 'application_reference',
            'status', 'lodged_date', 'decision_date', 'lapsing_date',
            'decision_notice_link', 'conditions', 'notes',
        ]
        widgets = {
            'council': forms.Select(attrs={'class': 'form-select'}),
            'projects': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'application_type': forms.Select(attrs={'class': 'form-select'}),
            'application_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DA Reference'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'lodged_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'decision_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lapsing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'decision_notice_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        lodged_date = cleaned_data.get('lodged_date')
        decision_date = cleaned_data.get('decision_date')

        if lodged_date and decision_date and decision_date < lodged_date:
            raise ValidationError('Decision date cannot be before lodged date.')

        return cleaned_data