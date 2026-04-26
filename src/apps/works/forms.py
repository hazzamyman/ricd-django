from django import forms
from django.core.exceptions import ValidationError
from apps.works.models import Work, WorkType, NotionalCost


class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = [
            'project_type', 'address', 'project', 'land_project',
            'work_type', 'work_type_other', 'bedrooms', 'quantity', 'estimated_cost', 'status',
            'bathrooms', 'kitchens', 'living_rooms',
            'residence_plc_ref', 'is_notional_cost', 'actual_cost',
        ]
        widgets = {
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'land_project': forms.Select(attrs={'class': 'form-select'}),
            'work_type': forms.Select(attrs={'class': 'form-select'}),
            'work_type_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'If Other, specify type'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'kitchens': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'living_rooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'residence_plc_ref': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PLC reference'}),
            'is_notional_cost': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'actual_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'work_type' in self.fields:
            work_types = WorkType.objects.filter(is_active=True)
            choices = [(wt.id, f"{wt.name} ({wt.get_category_display()})") for wt in work_types]
            self.fields['work_type'].choices = [('', '-- Select Work Type --')] + choices

    def clean(self):
        cleaned_data = super().clean()
        project_type = cleaned_data.get('project_type')
        project = cleaned_data.get('project')
        land_project = cleaned_data.get('land_project')
        
        quantity = cleaned_data.get('quantity')
        estimated_cost = cleaned_data.get('estimated_cost')
        actual_cost = cleaned_data.get('actual_cost')
        
        if quantity is not None and quantity < 1:
            raise ValidationError('Quantity must be at least 1.')
        
        if estimated_cost is not None and estimated_cost < 0:
            raise ValidationError('Estimated cost cannot be negative.')
        
        if actual_cost is not None and actual_cost < 0:
            raise ValidationError('Actual cost cannot be negative.')
        
        work_type = cleaned_data.get('work_type')
        work_type_other = cleaned_data.get('work_type_other')
        if not work_type and not work_type_other:
            raise ValidationError('Please select a work type or specify "Other".')
        
        if project_type == Work.ProjectType.DWELLING and not project:
            raise ValidationError('Please select a Dwelling Project.')
        
        if project_type == Work.ProjectType.LAND and not land_project:
            raise ValidationError('Please select a Land/Infrastructure Project.')
        
        return cleaned_data


class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = WorkType
        fields = ['name', 'category', 'has_bedrooms', 'default_bedrooms', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'has_bedrooms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NotionalCostForm(forms.ModelForm):
    class Meta:
        model = NotionalCost
        fields = ['work_type', 'financial_year', 'cost_per_unit', 'bedrooms', 'is_default']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-select'}),
            'financial_year': forms.Select(attrs={'class': 'form-select'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'work_type' in self.fields:
            work_types = WorkType.objects.filter(is_active=True)
            choices = [(wt.id, f"{wt.name} ({wt.get_category_display()})") for wt in work_types]
            self.fields['work_type'].choices = [('', '-- Select Work Type --')] + choices

    def clean(self):
        cleaned_data = super().clean()
        cost_per_unit = cleaned_data.get('cost_per_unit')
        
        if cost_per_unit is not None and cost_per_unit < 0:
            raise ValidationError('Cost per unit cannot be negative.')
        
        return cleaned_data