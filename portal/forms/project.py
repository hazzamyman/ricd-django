from django import forms
from ricd.models import (
    Project, Work, Address, WorkType, OutputType, ConstructionMethod,
    FundingSchedule, ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement
)


class ProjectForm(forms.ModelForm):
    """Form for creating and editing Projects"""

    class Meta:
        model = Project
        fields = [
            'council', 'program', 'funding_schedule', 'forward_rpf_agreement', 'interim_fp_agreement',
            'name', 'description', 'funding_schedule_amount', 'contingency_amount', 'contingency_percentage',
            'principal_officer', 'senior_officer', 'state', 'start_date',
            'stage1_target', 'stage1_sunset', 'stage2_target', 'stage2_sunset',
            'sap_project', 'cli_no', 'sap_master_project',
            'project_manager', 'contractor', 'contractor_address',
            'commitments', 'forecast_final_cost', 'final_cost', 'costs_finalised',
            'handover_forecast', 'handover_actual', 'commencement_loa_forecast',
            'commencement_loa_actual', 'date_physically_commenced', 'estimated_completion',
            'actual_completion'
        ]
        widgets = {
            'council': forms.Select(attrs={'class': 'form-select'}),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'funding_schedule': forms.Select(attrs={'class': 'form-select'}),
            'forward_rpf_agreement': forms.Select(attrs={'class': 'form-select'}),
            'interim_fp_agreement': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Project description'
            }),
            'funding_schedule_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'contingency_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'contingency_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'principal_officer': forms.Select(attrs={
                'class': 'form-select'
            }),
            'senior_officer': forms.Select(attrs={
                'class': 'form-select'
            }),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'stage1_target': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'stage1_sunset': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'stage2_target': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'stage2_sunset': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'sap_project': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SAP project number'
            }),
            'cli_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CLI number'
            }),
            'sap_master_project': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SAP master project'
            }),
            'project_manager': forms.Select(attrs={'class': 'form-select'}),
            'contractor': forms.Select(attrs={'class': 'form-select'}),
            'contractor_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Contractor address'
            }),
            'commitments': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'forecast_final_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'final_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'costs_finalised': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'handover_forecast': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'handover_actual': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'commencement_loa_forecast': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'commencement_loa_actual': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_physically_commenced': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'estimated_completion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actual_completion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        import logging
        logger = logging.getLogger(__name__)

        # Filter queryset based on user council if not RICD user
        if user:
            user_council = getattr(user, 'council', None)
            logger.info(f"DEBUG: ProjectForm.__init__ - User: {user.username}, User Council: {user_council}, Is Staff: {user.is_staff}, Groups: {[g.name for g in user.groups.all()]}")

            if user_council:
                logger.info(f"DEBUG: ProjectForm.__init__ - Restricting to council: {user_council.name}")
                self.fields['council'].queryset = Council.objects.filter(id=user_council.id)
                self.fields['council'].initial = user_council
                # Only show funding schedules for user's council (includes remote capital programs)
                self.fields['funding_schedule'].queryset = FundingSchedule.objects.filter(council=user_council)
                # Filter agreements for user's council
                self.fields['forward_rpf_agreement'].queryset = ForwardRemoteProgramFundingAgreement.objects.filter(council=user_council)
                self.fields['interim_fp_agreement'].queryset = InterimForwardProgramFundingAgreement.objects.filter(council=user_council)
                # Filter officers to those assigned to user's council
                self.fields['principal_officer'].queryset = Officer.objects.filter(
                    user__profile__council=user_council,
                    is_principal=True,
                    is_active=True
                )
                self.fields['senior_officer'].queryset = Officer.objects.filter(
                    user__profile__council=user_council,
                    is_senior=True,
                    is_active=True
                )
                # Filter projects to user's council
                self.fields['council'].widget.attrs['disabled'] = 'disabled'

                # Restrict state choices for council users - they can only select basic states
                council_allowed_states = [
                    ('prospective', 'Prospective'),
                    ('programmed', 'Programmed'),
                    ('funded', 'Funded'),
                    ('commenced', 'Commenced'),
                    ('under_construction', 'Under Construction'),
                    ('completed', 'Completed'),
                ]
                self.fields['state'].choices = council_allowed_states
                logger.info("DEBUG: ProjectForm.__init__ - Restricted state choices for council user")

            else:
                logger.info("DEBUG: ProjectForm.__init__ - RICD user, no restrictions applied")
                self.fields['council'].queryset = Council.objects.all()
                self.fields['funding_schedule'].queryset = FundingSchedule.objects.all()
                # RICD users can see all agreements
                self.fields['forward_rpf_agreement'].queryset = ForwardRemoteProgramFundingAgreement.objects.all()
                self.fields['interim_fp_agreement'].queryset = InterimForwardProgramFundingAgreement.objects.all()
                # RICD user can see all officers
                self.fields['principal_officer'].queryset = Officer.objects.filter(
                    is_principal=True,
                    is_active=True
                ).select_related('user')
                self.fields['senior_officer'].queryset = Officer.objects.filter(
                    is_senior=True,
                    is_active=True
                ).select_related('user')

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
        return instance


class WorkForm(forms.ModelForm):
    """Form for work creation/updating"""
    address = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__ based on project
        required=True,
        label="Address",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    work_type_id = forms.ModelChoiceField(
        queryset=WorkType.objects.filter(is_active=True),
        required=True,
        label="Work Type",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    output_type_id = forms.ModelChoiceField(
        queryset=OutputType.objects.filter(is_active=True),
        required=True,
        label="Output Type",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields['address'].queryset = Address.objects.filter(project=project)
        else:
            self.fields['address'].queryset = Address.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        work_type_id = cleaned_data.get('work_type_id')
        output_type_id = cleaned_data.get('output_type_id')

        if work_type_id and output_type_id:
            # Check if the selected output type is allowed for the selected work type
            if not work_type_id.allowed_output_types.filter(id=output_type_id.id).exists():
                raise forms.ValidationError(
                    f"Output type '{output_type_id.name}' is not allowed for work type '{work_type_id.name}'."
                )

        return cleaned_data

    class Meta:
        model = Work
        fields = [
            'address', 'work_type_id', 'output_type_id', 'output_quantity',
            'bedrooms', 'estimated_cost', 'actual_cost', 'start_date', 'end_date',
            # Construction details
            'land_status', 'floor_method', 'frame_method', 'external_wall_method',
            'roof_method', 'car_accommodation', 'additional_facilities', 'extension_high_low',
            'bathrooms', 'kitchens', 'dwellings_count', 'construction_method'
        ]
        widgets = {
            'address_line': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full address'
            }),
            'output_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'kitchens': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'land_status': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Land status'
            }),
            'floor_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Concrete Slab/Timber Frame/Steel Frame'
            }),
            'frame_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Timber Frame/Steel Frame/Block/FC Panel'
            }),
            'external_wall_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Timber/Sheeting/Block/Brick'
            }),
            'roof_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Metal Sheeting/Tiles/Galv.Sheeting/Colourbond'
            }),
            'car_accommodation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Carport/Garage/Under House'
            }),
            'additional_facilities': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Additional WC/BATHROOM'
            }),
            'dwellings_count': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'actual_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'construction_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Optional - all works will start together'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class AddressForm(forms.ModelForm):
    """Form for address creation/updating with work details"""

    work_type_id = forms.ModelChoiceField(
        queryset=WorkType.objects.filter(is_active=True),
        required=True,
        label="Work Type",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    output_type_id = forms.ModelChoiceField(
        queryset=OutputType.objects.filter(is_active=True),
        required=True,
        label="Output Type",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def clean_budget(self):
        """Validate budget against project total funding"""
        budget = self.cleaned_data.get('budget')
        if not budget or not self.project:
            return budget

        # Calculate current total budget of all addresses in the project (excluding current instance if updating)
        current_addresses_budget = sum(
            addr.budget or 0
            for addr in self.project.addresses.all()
            if addr.pk != getattr(self.instance, 'pk', None)  # Exclude current instance if updating
        )

        total_budget_with_new = current_addresses_budget + budget

        # Get project total funding (funding_schedule_amount + contingency_amount)
        project_total_funding = (self.project.funding_schedule_amount or 0) + (self.project.contingency_amount or 0)

        # Get funding from funding agreement if available
        if self.project.funding_agreement:
            agreement_funding = self.project.funding_agreement.funding_amount + (self.project.funding_agreement.contingency_amount or 0)
            project_total_funding = max(project_total_funding, agreement_funding)

        if project_total_funding > 0 and total_budget_with_new > project_total_funding:
            raise forms.ValidationError(
                f'The total budget of all addresses (${total_budget_with_new:,.2f}) exceeds the project\'s total funding (${project_total_funding:,.2f}). '
                f'Please adjust the budget or contact your project manager.'
            )

        return budget

    class Meta:
        model = Address
        fields = [
            'street', 'suburb', 'postcode', 'state', 'lot_number', 'plan_number', 'title_reference',
            'work_type_id', 'output_type_id', 'bedrooms', 'output_quantity', 'budget', 'construction_method'
        ]
        widgets = {
            'street': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'suburb': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Suburb/Town'
            }),
            'postcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postcode'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'lot_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lot number'
            }),
            'plan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Plan number (e.g., RP3435)'
            }),
            'title_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Title reference (e.g., 123456)'
            }),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of bedrooms'
            }),
            'output_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of outputs',
                'min': 1
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Budget amount'
            }),
            'construction_method': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


# Management Forms
class WorkTypeForm(forms.ModelForm):
    """Form for creating and editing Work Types"""

    class Meta:
        model = WorkType
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter work type code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter work type name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class OutputTypeForm(forms.ModelForm):
    """Form for creating and editing Output Types"""

    class Meta:
        model = OutputType
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter output type code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter output type name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ConstructionMethodForm(forms.ModelForm):
    """Form for creating and editing Construction Methods"""

    class Meta:
        model = ConstructionMethod
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter construction method code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter construction method name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ProjectStateForm(forms.ModelForm):
    """Simple form for updating project state only"""

    class Meta:
        model = Project
        fields = ['state']
        widgets = {
            'state': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'this.form.submit()'
            })
        }