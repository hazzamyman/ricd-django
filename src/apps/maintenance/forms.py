from django import forms
from django.core.exceptions import ValidationError
from apps.councils.models import Council, CouncilContact
from apps.programs.models import Program, ProgramBudget
from apps.works.models import WorkType, WorkStepTemplate, Work, NotionalCost
from apps.addresses.models import Address, Suburb
from apps.projects.models import Project
from apps.funding.models import FundingApproval, FundingSchedule, Delegation
from apps.contractors.models import Contractor
from apps.documents.models import DocumentType


class CouncilForm(forms.ModelForm):
    class Meta:
        model = Council
        fields = ['name', 'region', 'state_electorate', 'federal_electorate', 'contact_email', 'contact_phone', 'is_registered_housing_provider', 'rcpa_contact_name', 'rcpa_contact_phone', 'rcpa_contact_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'region': forms.TextInput(attrs={'class': 'form-control'}),
            'state_electorate': forms.TextInput(attrs={'class': 'form-control'}),
            'federal_electorate': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_registered_housing_provider': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rcpa_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'rcpa_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'rcpa_contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name', 'funding_source', 'funding_source_other', 'budget', 'gl_code', 'business_case_reference', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'funding_source': forms.Select(attrs={'class': 'form-select'}),
            'funding_source_other': forms.TextInput(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gl_code': forms.TextInput(attrs={'class': 'form-control'}),
            'business_case_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CouncilContactForm(forms.ModelForm):
    class Meta:
        model = CouncilContact
        fields = ['council', 'role', 'name', 'email', 'phone']
        widgets = {
            'council': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'role': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'council' in self.fields:
            from apps.councils.models import Council
            self.fields['council'].queryset = Council.objects.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        funding_source = cleaned_data.get('funding_source')
        funding_source_other = cleaned_data.get('funding_source_other')
        
        if funding_source == Program.FundingSource.OTHER and not funding_source_other:
            raise ValidationError("Please specify the funding source when 'Other' is selected.")
        
        return cleaned_data


class ProgramBudgetForm(forms.ModelForm):
    class Meta:
        model = ProgramBudget
        fields = ['program', 'financial_year', 'allocated', 'notes']
        widgets = {
            'program': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'financial_year': forms.Select(attrs={'class': 'form-select'}),
            'allocated': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = WorkType
        fields = ['name', 'category', 'has_bedrooms', 'default_bedrooms', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'has_bedrooms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WorkStepTemplateForm(forms.ModelForm):
    class Meta:
        model = WorkStepTemplate
        fields = ['work_type', 'name', 'description', 'order']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['project', 'street', 'suburb', 'lot', 'plan', 'residence_plc_ref']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'suburb': forms.Select(attrs={'class': 'form-select'}),
            'lot': forms.TextInput(attrs={'class': 'form-control'}),
            'plan': forms.TextInput(attrs={'class': 'form-control'}),
            'residence_plc_ref': forms.TextInput(attrs={'class': 'form-control'}),
        }


class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ['project', 'address', 'work_type', 'quantity', 'estimated_cost', 'status']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'address': forms.Select(attrs={'class': 'form-select'}),
            'work_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class FundingApprovalForm(forms.ModelForm):
    class Meta:
        model = FundingApproval
        fields = ['projects', 'total_amount', 'contingency_amount', 'mincor_reference', 'mincor_link', 'peer_review_required', 'notes']
        widgets = {
            'projects': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
            'contingency_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mincor_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'mincor_link': forms.URLInput(attrs={'class': 'form-control'}),
            'peer_review_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        if amount is not None and amount < 0:
            raise ValidationError("Total amount cannot be negative.")
        return amount


class FundingScheduleForm(forms.ModelForm):
    class Meta:
        model = FundingSchedule
        fields = ['project', 'amount', 'contingency', 'payment_split']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
            'contingency': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_split': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        contingency = cleaned_data.get('contingency') or 0
        
        if amount is not None and amount < 0:
            raise ValidationError("Amount cannot be negative.")
        if contingency < 0:
            raise ValidationError("Contingency cannot be negative.")
        
        return cleaned_data


class DelegationForm(forms.ModelForm):
    class Meta:
        model = Delegation
        fields = ['position', 'threshold_amount', 'is_active']
        widgets = {
            'position': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'threshold_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['company_name', 'trade_type', 'contact_name', 'email', 'phone', 'council', 'is_active']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'trade_type': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'council': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DocumentType
        fields = ['name', 'description', 'is_attachment', 'project_types', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_attachment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'project_types': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NotionalCostForm(forms.ModelForm):
    class Meta:
        model = NotionalCost
        fields = ['work_type', 'financial_year', 'cost_per_unit', 'bedrooms', 'is_default']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'financial_year': forms.Select(attrs={'class': 'form-select'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        cost_per_unit = cleaned_data.get('cost_per_unit')
        
        if cost_per_unit is not None and cost_per_unit < 0:
            raise ValidationError('Cost per unit cannot be negative.')
        
        return cleaned_data
