from django import forms
from django.contrib.auth.models import User, Group
from ricd.models import (
    Project, FundingSchedule, QuarterlyReport, MonthlyTracker,
    Stage1Report, Stage2Report, Work, ReportAttachment, Council, Program, Address,
    WorkType, OutputType, ConstructionMethod, Officer, ForwardRemoteProgramFundingAgreement,
    InterimForwardProgramFundingAgreement, RemoteCapitalProgramFundingAgreement, FundingApproval, Defect, UserProfile,
    MonthlyTrackerItem, MonthlyTrackerItemGroup, QuarterlyReportItem, QuarterlyReportItemGroup,
    Stage1Step, Stage1StepGroup, Stage2Step, Stage2StepGroup, ProjectReportConfiguration,
    MonthlyTrackerEntry, QuarterlyReportItemEntry, Stage1StepCompletion, Stage2StepCompletion
)
from django.utils import timezone


class QuarterlyReportForm(forms.ModelForm):
    """Form for submitting quarterly reports"""

    work = forms.ModelChoiceField(
        queryset=None,  # Will be filtered based on user's council
        required=True,
        label="Work Item",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    submission_date = forms.DateField(
        initial=timezone.now().date(),
        label="Submission Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    percentage_works_completed = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        initial=0,
        label="Percentage of Works Completed (%)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    total_expenditure_council = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        label="Total Council Expenditure",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    unspent_funding_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        label="Unspent Funding Amount",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    total_employed_people = forms.IntegerField(
        min_value=0,
        required=False,
        label="Total People Employed",
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    total_indigenous_employed = forms.IntegerField(
        min_value=0,
        required=False,
        label="Total Indigenous People Employed",
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    comments_indigenous_employment = forms.CharField(
        required=False,
        label="Comments on Indigenous Employment",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )

    practical_completion_forecast_date = forms.DateField(
        required=False,
        label="Practical Completion Forecast Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    practical_completion_actual_date = forms.DateField(
        required=False,
        label="Practical Completion Actual Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    adverse_matters = forms.CharField(
        required=False,
        label="Adverse Matters",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4
        })
    )

    council_contributions_details = forms.CharField(
        required=False,
        label="Council Contributions Details",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )

    council_contributions_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        label="Council Contributions Amount",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    other_contributions_details = forms.CharField(
        required=False,
        label="Other Contributions Details",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )

    other_contributions_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        label="Other Contributions Amount",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    summary_notes = forms.CharField(
        required=False,
        label="Summary Notes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4
        })
    )

    # RICD Assessment Fields
    ricd_status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('needs_more_info', 'Needs More Information')],
        initial='pending',
        required=False,
        label="RICD Status",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    ricd_comments = forms.CharField(
        required=False,
        label="RICD Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'RICD assessment comments and reasons for decision'
        })
    )

    # Display-only fields for Funding Schedule and Address info
    funding_schedule_display = forms.CharField(
        required=False,
        label="Funding Schedule",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    works_address_display = forms.CharField(
        required=False,
        label="Works Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    class Meta:
        model = QuarterlyReport
        fields = [
            'work', 'submission_date', 'percentage_works_completed',
            'total_expenditure_council', 'unspent_funding_amount',
            'total_employed_people', 'total_indigenous_employed',
            'comments_indigenous_employment', 'practical_completion_forecast_date',
            'practical_completion_actual_date', 'adverse_matters',
            'council_contributions_details', 'council_contributions_amount',
            'other_contributions_details', 'other_contributions_amount',
            'summary_notes', 'council_manager_decision', 'council_manager_comments'
        ]

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                # Council user - filter works and make ricd fields readonly
                self.fields['work'].queryset = Work.objects.filter(project__council=user_council)
                self.fields['ricd_status'].widget.attrs['disabled'] = 'disabled'
                self.fields['ricd_comments'].widget.attrs['readonly'] = 'readonly'
            else:
                # RICD user - can edit ricd fields, no filtering
                self.fields['work'].queryset = Work.objects.all()

        # Populate display fields if instance exists
        if self.instance and self.instance.pk:
            # Funding schedule
            if self.instance.work and self.instance.work.project and self.instance.work.project.funding_schedule:
                funding = self.instance.work.project.funding_schedule
                total_funding = funding.funding_amount + (funding.contingency_amount or 0)
                self.fields['funding_schedule_display'].initial = f"{funding.funding_schedule_number} - ${total_funding:,}"

            # Works address
            if self.instance.work and self.instance.work.address_line:
                self.fields['works_address_display'].initial = self.instance.work.address_line
            elif self.instance.work and self.instance.work.project.addresses.first():
                addr = self.instance.work.project.addresses.first()
                self.fields['works_address_display'].initial = str(addr)


class MonthlyTrackerForm(forms.ModelForm):
    """Form for submitting monthly tracker reports"""

    work = forms.ModelChoiceField(
        queryset=None,  # Will be filtered based on user's council
        required=True,
        label="Work Item",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    month = forms.DateField(
        initial=timezone.now().date().replace(day=1),
        label="Month",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    progress_notes = forms.CharField(
        required=False,
        label="Progress Notes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4
        })
    )

    # Design Phase
    design_tender_date = forms.DateField(
        required=False,
        label="Design Tender Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    design_award_date = forms.DateField(
        required=False,
        label="Design Award Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # Tender and Award Phase
    construction_tender_date = forms.DateField(
        required=False,
        label="Construction Tender Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    construction_award_date = forms.DateField(
        required=False,
        label="Construction Award Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # Other relevant dates (subset for the form)
    site_establishment_date = forms.DateField(
        required=False,
        label="Site Establishment Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # RICD Assessment Fields
    ricd_status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('needs_more_info', 'Needs More Information')],
        initial='pending',
        required=False,
        label="RICD Status",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    ricd_comments = forms.CharField(
        required=False,
        label="RICD Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'RICD assessment comments and reasons for decision'
        })
    )

    # Display-only fields for Funding Schedule and Address info
    funding_schedule_display = forms.CharField(
        required=False,
        label="Funding Schedule",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    works_address_display = forms.CharField(
        required=False,
        label="Works Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    class Meta:
        model = MonthlyTracker
        fields = [
            'work', 'month', 'progress_notes',
            'design_tender_date', 'design_award_date',
            'construction_tender_date', 'construction_award_date',
            'site_establishment_date'
        ]

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                # Council user - filter works and make ricd fields readonly
                self.fields['work'].queryset = Work.objects.filter(project__council=user_council)
                self.fields['ricd_status'].widget.attrs['disabled'] = 'disabled'
                self.fields['ricd_comments'].widget.attrs['readonly'] = 'readonly'
            else:
                # RICD user - can edit ricd fields, no filtering
                self.fields['work'].queryset = Work.objects.all()

        # Populate display fields if instance exists
        if self.instance and self.instance.pk:
            # Funding schedule
            if self.instance.work and self.instance.work.project and self.instance.work.project.funding_schedule:
                funding = self.instance.work.project.funding_schedule
                total_funding = funding.funding_amount + (funding.contingency_amount or 0)
                self.fields['funding_schedule_display'].initial = f"{funding.funding_schedule_number} - ${total_funding:,}"

            # Works address
            if self.instance.work and self.instance.work.address_line:
                self.fields['works_address_display'].initial = self.instance.work.address_line
            elif self.instance.work and self.instance.work.project.addresses.first():
                addr = self.instance.work.project.addresses.first()
                self.fields['works_address_display'].initial = str(addr)


class Stage1ReportForm(forms.ModelForm):
    """Form for submitting Stage 1 reports"""

    project = forms.ModelChoiceField(
        queryset=None,  # Will be filtered based on user's council
        required=True,
        label="Project",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    submission_date = forms.DateField(
        initial=timezone.now().date(),
        label="Submission Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # Administrative fields
    expenditure_records_maintained = forms.BooleanField(
        required=False,
        label="Expenditure records maintained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    quarterly_reports_provided = forms.BooleanField(
        required=False,
        label="Quarterly reports provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Reporting type
    report_type = forms.ChoiceField(
        choices=[('construction', 'Construction'), ('land', 'Land')],
        initial='construction',
        required=True,
        label="Report Type"
    )

    # Land and Works Documentation
    land_description_document = forms.FileField(
        required=False,
        label="Land Description Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    works_description_document = forms.FileField(
        required=False,
        label="Works Description Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    land_title_document = forms.FileField(
        required=False,
        label="Land Title Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Native Title and Heritage
    native_title_addressed = forms.BooleanField(
        required=False,
        label="Native Title Addressed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    native_title_documentation = forms.FileField(
        required=False,
        label="Native Title Documentation",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    heritage_matters_addressed = forms.BooleanField(
        required=False,
        label="Heritage Matters Addressed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    heritage_documentation = forms.FileField(
        required=False,
        label="Heritage Documentation",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Approvals and Documentation
    development_approval_obtained = forms.BooleanField(
        required=False,
        label="Development Approval Obtained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    development_approval_document = forms.FileField(
        required=False,
        label="Development Approval Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    tenure_obtained = forms.BooleanField(
        required=False,
        label="Tenure Obtained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    tenure_document = forms.FileField(
        required=False,
        label="Tenure Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    land_surveyed = forms.BooleanField(
        required=False,
        label="Land Surveyed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    survey_document = forms.FileField(
        required=False,
        label="Survey Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Subdivision
    subdivision_required = forms.BooleanField(
        required=False,
        label="Subdivision Required",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    subdivision_plan_prepared = forms.BooleanField(
        required=False,
        label="Subdivision Plan Prepared",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    subdivision_plan_document = forms.FileField(
        required=False,
        label="Subdivision Plan Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Design
    design_approved = forms.BooleanField(
        required=False,
        label="Design Approved",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    design_document_proposed = forms.FileField(
        required=False,
        label="Design Document (Proposed)",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    design_document_approved = forms.FileField(
        required=False,
        label="Design Document (Approved)",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    structural_certification_obtained = forms.BooleanField(
        required=False,
        label="Structural Certification Obtained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    structural_certification_document = forms.FileField(
        required=False,
        label="Structural Certification Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Contractors
    council_contractors_used = forms.BooleanField(
        required=False,
        label="Council Contractors Used",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Infrastructure Approvals
    infrastructure_approvals_obtained = forms.BooleanField(
        required=False,
        label="Infrastructure Approvals Obtained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    infrastructure_documentation = forms.FileField(
        required=False,
        label="Infrastructure Documentation",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    building_approval_document = forms.FileField(
        required=False,
        label="Building Approval Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    # Tenders and Contractors
    tenders_called = forms.BooleanField(
        required=False,
        label="Tenders Called",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    contractor_appointed = forms.BooleanField(
        required=False,
        label="Contractor Appointed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    contractor_details = forms.CharField(
        required=False,
        label="Contractor Details",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )

    # Building and Infrastructure Approvals
    building_approval_obtained = forms.BooleanField(
        required=False,
        label="Building Approval Obtained",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Additional notes
    completion_notes = forms.CharField(
        required=False,
        label="Completion Notes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4
        })
    )

    # RICD Assessment Fields
    ricd_status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('needs_more_info', 'Needs More Information')],
        initial='pending',
        required=False,
        label="RICD Status",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    ricd_comments = forms.CharField(
        required=False,
        label="RICD Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'RICD assessment comments and reasons for decision'
        })
    )

    # Display-only fields for Funding Schedule and Address info
    funding_schedule_display = forms.CharField(
        required=False,
        label="Funding Schedule",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    project_address_display = forms.CharField(
        required=False,
        label="Project Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    class Meta:
        model = Stage1Report
        fields = [
            'project', 'report_type', 'submission_date',
            'expenditure_records_maintained', 'quarterly_reports_provided',
            'land_description_document', 'works_description_document',
            'land_title_document', 'native_title_addressed', 'native_title_documentation',
            'heritage_matters_addressed', 'heritage_documentation',
            'development_approval_obtained', 'development_approval_document',
            'tenure_obtained', 'tenure_document', 'land_surveyed', 'survey_document',
            'subdivision_required', 'subdivision_plan_prepared', 'subdivision_plan_document',
            'design_approved', 'design_document_proposed', 'design_document_approved',
            'structural_certification_obtained', 'structural_certification_document',
            'tenders_called', 'contractor_appointed', 'contractor_details',
            'council_contractors_used', 'building_approval_obtained', 'building_approval_document',
            'infrastructure_approvals_obtained', 'infrastructure_documentation', 'completion_notes'
        ]

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                # Council user - filter projects and make ricd fields readonly
                self.fields['project'].queryset = Project.objects.filter(council=user_council)
                self.fields['ricd_status'].widget.attrs['disabled'] = 'disabled'
                self.fields['ricd_comments'].widget.attrs['readonly'] = 'readonly'
            else:
                # RICD user - can edit ricd fields, no filtering
                self.fields['project'].queryset = Project.objects.all()

        # Populate display fields if instance exists
        if self.instance and self.instance.pk:
            # Funding schedule
            if self.instance.project and self.instance.project.funding_schedule:
                funding = self.instance.project.funding_schedule
                total_funding = funding.funding_amount + (funding.contingency_amount or 0)
                self.fields['funding_schedule_display'].initial = f"{funding.funding_schedule_number} - ${total_funding:,}"

            # Project address
            if self.instance.project.addresses.first():
                addr = self.instance.project.addresses.first()
                self.fields['project_address_display'].initial = str(addr)


class Stage2ReportForm(forms.ModelForm):
    """Form for submitting Stage 2 reports"""

    project = forms.ModelChoiceField(
        queryset=None,  # Will be filtered based on user's council
        required=True,
        label="Project",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    submission_date = forms.DateField(
        initial=timezone.now().date(),
        label="Submission Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # For Construction projects - Schedule of Works
    schedule_provided = forms.BooleanField(
        required=False,
        label="Schedule of Works Provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Reporting compliance
    quarterly_reports_provided = forms.BooleanField(
        required=False,
        label="Quarterly Reports Provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    monthly_trackers_provided = forms.BooleanField(
        required=False,
        label="Monthly Trackers Provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Practical Completion
    practical_completion_achieved = forms.BooleanField(
        required=False,
        label="Practical Completion Achieved",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    practical_completion_date = forms.DateField(
        required=False,
        label="Practical Completion Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # Land works completion
    land_works_completed = forms.BooleanField(
        required=False,
        label="Land Works Completed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Handover requirements
    handover_requirements_met = forms.BooleanField(
        required=False,
        label="Handover Requirements Met",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    handover_checklist_completed = forms.BooleanField(
        required=False,
        label="Handover Checklist Completed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    warranties_provided = forms.BooleanField(
        required=False,
        label="Warranties Provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    final_plans_provided = forms.BooleanField(
        required=False,
        label="Final Plans Provided",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Additional documentation
    completion_notes = forms.CharField(
        required=False,
        label="Completion Notes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4
        })
    )

    # Council Manager Approval Fields
    council_manager_decision = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        initial='pending',
        required=False,
        label="Council Manager Decision",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    council_manager_comments = forms.CharField(
        required=False,
        label="Council Manager Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Council Manager approval comments and reasons for decision'
        })
    )

    # Council Manager Approval Fields
    council_manager_decision = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        initial='pending',
        required=False,
        label="Council Manager Decision",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    council_manager_comments = forms.CharField(
        required=False,
        label="Council Manager Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Council Manager approval comments and reasons for decision'
        })
    )

    # RICD Assessment Fields
    ricd_status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('needs_more_info', 'Needs More Information')],
        initial='pending',
        required=False,
        label="RICD Status",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    ricd_comments = forms.CharField(
        required=False,
        label="RICD Comments",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'RICD assessment comments and reasons for decision'
        })
    )

    # Display-only fields for Funding Schedule and Address info
    funding_schedule_display = forms.CharField(
        required=False,
        label="Funding Schedule",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    project_address_display = forms.CharField(
        required=False,
        label="Project Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    # Additional fields from Stage2Report model
    schedule_provided_date = forms.DateField(
        required=False,
        label="Schedule Provided Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    practical_completion_notification_sent = forms.BooleanField(
        required=False,
        label="Practical Completion Notification Sent",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    notification_date = forms.DateField(
        required=False,
        label="Notification Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    joint_inspection_completed = forms.BooleanField(
        required=False,
        label="Joint Inspection Completed",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    joint_inspection_date = forms.DateField(
        required=False,
        label="Joint Inspection Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # File uploads
    handover_checklist_document = forms.FileField(
        required=False,
        label="Handover Checklist Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    warranties_document = forms.FileField(
        required=False,
        label="Warranties Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    final_plans_document = forms.FileField(
        required=False,
        label="Final Plans Document",
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Stage2Report
        fields = [
            'project', 'report_type', 'submission_date',
            'schedule_provided', 'schedule_provided_date', 'quarterly_reports_provided', 'monthly_trackers_provided',
            'practical_completion_achieved', 'practical_completion_date', 'practical_completion_notification_sent', 'notification_date',
            'land_works_completed', 'handover_requirements_met', 'handover_checklist_completed', 'handover_checklist_document',
            'warranties_provided', 'warranties_document', 'final_plans_provided', 'final_plans_document',
            'joint_inspection_completed', 'joint_inspection_date', 'completion_notes'
        ]

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                # Council user - filter projects and make ricd fields readonly
                self.fields['project'].queryset = Project.objects.filter(council=user_council)
                self.fields['ricd_status'].widget.attrs['disabled'] = 'disabled'
                self.fields['ricd_comments'].widget.attrs['readonly'] = 'readonly'
            else:
                # RICD user - can edit ricd fields, no filtering
                self.fields['project'].queryset = Project.objects.all()

        # Populate display fields if instance exists
        if self.instance and self.instance.pk:
            # Funding schedule
            if self.instance.project and self.instance.project.funding_schedule:
                funding = self.instance.project.funding_schedule
                total_funding = funding.funding_amount + (funding.contingency_amount or 0)
                self.fields['funding_schedule_display'].initial = f"{funding.funding_schedule_number} - ${total_funding:,}"

            # Project address
            if self.instance.project.addresses.first():
                addr = self.instance.project.addresses.first()
                self.fields['project_address_display'].initial = str(addr)


# Council Management Forms
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


# Address Formset for Project Creation
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


# Project Management Forms
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


# Work Type Management Forms
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


# Agreement Forms
class ForwardRemoteProgramFundingAgreementForm(forms.ModelForm):
    """Form for creating and editing Forward Remote Program Funding Agreements"""

    class Meta:
        model = ForwardRemoteProgramFundingAgreement
        fields = ['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed']
        widgets = {
            'council': forms.Select(attrs={
                'class': 'form-select',
                'disabled': 'disabled'  # Usually determined by existing council
            }),
            'date_sent_to_council': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_council_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_delegate_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class InterimForwardProgramFundingAgreementForm(forms.ModelForm):
    """Form for creating and editing Interim Forward Remote Program Funding Agreements"""

    class Meta:
        model = InterimForwardProgramFundingAgreement
        fields = ['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed']
        widgets = {
            'council': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_sent_to_council': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_council_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_delegate_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class RemoteCapitalProgramFundingAgreementForm(forms.ModelForm):
    """Form for creating and editing Remote Capital Program Funding Agreements"""

    class Meta:
        model = RemoteCapitalProgramFundingAgreement
        fields = ['council', 'date_sent_to_council', 'date_council_signed', 'date_delegate_signed', 'notes']
        widgets = {
            'council': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_sent_to_council': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_council_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_delegate_signed': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about the agreement (optional)'
            }),
        }


# User and Officer Management Forms
class UserCreationForm(forms.ModelForm):
    """Form for creating new users with group assignment"""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        })
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            if self.cleaned_data.get('groups'):
                user.groups.set(self.cleaned_data['groups'])
        return user


class OfficerForm(forms.ModelForm):
    """Form for creating and editing Officers"""

    create_user = forms.BooleanField(
        required=False,
        label="Create new user account",
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = Officer
        fields = ['user', 'position', 'is_principal', 'is_senior', 'is_active']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-select'
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Official position title'
            }),
            'is_principal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_senior': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class OfficerAssignmentForm(forms.ModelForm):
    """Form for assigning officers to projects"""

    class Meta:
        model = Project
        fields = ['principal_officer', 'senior_officer']
        widgets = {
            'principal_officer': forms.Select(attrs={
                'class': 'form-select'
            }),
            'senior_officer': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class CustomExcelExportForm(forms.Form):
    """Form for selecting fields to include in Excel export"""

    # Available fields with checkboxes
    fields = forms.MultipleChoiceField(
        choices=[
            ('State', 'State'),
            ('Project', 'Project Name'),
            ('Council', 'Council'),
            ('Program', 'Program'),
            ('Street', 'Street Address'),
            ('Suburb', 'Suburb'),
            ('Postcode', 'Postcode'),
            ('Work Type', 'Work Type'),
            ('Output Type', 'Output Type'),
            ('Bedrooms', 'Bedrooms'),
            ('Bathrooms', 'Bathrooms'),
            ('Kitchens', 'Kitchens'),
            ('Dwellings Count', 'Dwellings Count'),
            ('Output Quantity', 'Output Quantity'),
            ('Estimated Cost', 'Estimated Cost'),
            ('Actual Cost', 'Actual Cost'),
            ('Start Date', 'Start Date'),
            ('End Date', 'End Date'),
            ('Land Status', 'Land Status'),
            ('Floor Method', 'Floor Method'),
            ('Frame Method', 'Frame Method'),
            ('External Wall Method', 'External Wall Method'),
            ('Roof Method', 'Roof Method'),
            ('Car Accommodation', 'Car Accommodation'),
            ('Additional Facilities', 'Additional Facilities'),
            ('Extension High Low', 'Extension High/Low'),
            ('Lot Number', 'Lot Number'),
            ('Plan Number', 'Plan Number'),
            ('Title Reference', 'Title Reference'),
        ],
        initial=[
            'State', 'Project', 'Council', 'Program', 'Street',
            'Suburb', 'Postcode', 'Work Type', 'Output Type',
            'Bedrooms', 'Output Quantity', 'Estimated Cost', 'Actual Cost'
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Select Fields to Include",
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default checked items
        if not self.is_bound:
            self.fields['fields'].initial = [
                'State', 'Project', 'Council', 'Program', 'Street',
                'Suburb', 'Postcode', 'Work Type', 'Output Type',
                'Bedrooms', 'Output Quantity', 'Estimated Cost', 'Actual Cost'
            ]


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


# Council User Creation Form
class CouncilUserCreationForm(forms.ModelForm):
    """Form for creating new council users with role restrictions"""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        })
    )

    # Council selection for RICD users
    council = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__ based on user permissions
        required=False,
        label="Council",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the council this user belongs to"
    )

    # Role choices restricted based on current user
    ROLE_CHOICES = [
        ('council_user', 'Council User'),
        ('council_manager', 'Council Manager'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="User Role",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the role for this council user"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, council=None, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.council = council

        # Set council field behavior based on user permissions
        if user and user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            # RICD users can select council
            self.fields['council'].queryset = Council.objects.all().order_by('name')
            self.fields['council'].required = True
            if council:
                # If council was passed, pre-select it
                self.fields['council'].initial = council
        else:
            # Council managers can't select council - it's fixed to their own
            self.fields['council'].widget = forms.HiddenInput()
            self.fields['council'].queryset = Council.objects.none()
            if council:
                self.fields['council'].initial = council
            # For council managers, council is always provided, so make it not required for form validation
            self.fields['council'].required = False

        # Restrict role choices based on current user permissions
        if user:
            user_council = getattr(user, 'council', None)
            if user_council and not user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # Council Manager can only create Council User
                self.fields['role'].choices = [('council_user', 'Council User')]
                self.fields['role'].help_text = "As a Council Manager, you can only create Council User accounts."
                # For council managers, role is restricted to council_user only
                self.fields['role'].initial = 'council_user'
                self.fields['role'].required = True  # Make sure role is required
                print(f"DEBUG: Council Manager form setup - restricted choices: {self.fields['role'].choices}")
            elif user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # RICD users can create both roles
                self.fields['role'].choices = self.ROLE_CHOICES
                self.fields['role'].help_text = "Select the appropriate role for this council user."
                print(f"DEBUG: RICD user form setup - all choices: {self.fields['role'].choices}")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        council = cleaned_data.get('council') or self.council

        # Ensure council is provided
        if not council:
            raise forms.ValidationError("A council must be selected for the user.")

        # Ensure council is in the form data for hidden fields
        if not cleaned_data.get('council') and self.council:
            cleaned_data['council'] = self.council

        return cleaned_data

    def clean_role(self):
        """Ensure role selection is valid for current user's permissions"""
        role = self.cleaned_data.get('role')
        if role and self.fields['role'].choices:
            # Check if the selected role is in the allowed choices
            allowed_roles = [choice[0] for choice in self.fields['role'].choices]
            if role not in allowed_roles:
                raise forms.ValidationError("You don't have permission to create users with this role.")
        elif not self.fields['role'].choices:
            raise forms.ValidationError("You don't have permission to create users with roles.")
        return role

    def save(self, commit=True):
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER CREATION FORM SAVE STARTED ===")
        logger.info(f"Form data - Username: {self.cleaned_data.get('username')}, Email: {self.cleaned_data.get('email')}")
        logger.info(f"Form council: {self.cleaned_data.get('council')}, Instance council: {self.council}")
        logger.info(f"Role: {self.cleaned_data.get('role')}, Commit: {commit}")

        user = super().save(commit=False)
        logger.info(f"User object created (not yet saved) - Username: {user.username}")

        # Set password
        password1 = self.cleaned_data.get("password1")
        if password1:
            user.set_password(password1)
            logger.info("Password set successfully")
        else:
            logger.warning("No password provided in form data")

        # Set user profile council - use form data if available, otherwise fall back to passed parameter
        council = self.cleaned_data.get('council') or self.council
        logger.info(f"Final council determined: {council}")

        if commit:
            try:
                logger.info("Starting atomic transaction for user creation")

                # Use atomic transaction to ensure all operations succeed or fail together
                with transaction.atomic():
                    logger.info("Transaction started - Saving user object")
                    # Save the user first
                    user.save()
                    logger.info(f"✅ User saved successfully - ID: {user.pk}, Username: {user.username}")

                    logger.info("Creating/updating UserProfile")
                    # Ensure UserProfile exists and is linked to council
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'council': council}
                    )

                    if not created and profile.council != council:
                        logger.info(f"Profile exists but council differs - Old: {profile.council}, New: {council}")
                        # Update existing profile with new council
                        profile.council = council
                        profile.save()
                        logger.info(f"✅ UserProfile updated - Council: {council}")
                    elif created:
                        logger.info(f"✅ UserProfile created - Council: {council}")
                    else:
                        logger.info(f"UserProfile already exists with correct council: {council}")

                    logger.info("Clearing existing groups to prevent duplicates")
                    # Clear existing groups to prevent duplicates
                    user.groups.clear()

                    logger.info("Assigning groups based on role")
                    # Assign groups based on role
                    role = self.cleaned_data.get('role')
                    if role == 'council_user':
                        group, group_created = Group.objects.get_or_create(name='Council User')
                        user.groups.add(group)
                        logger.info(f"✅ Added Council User group (created: {group_created})")
                    elif role == 'council_manager':
                        group, group_created = Group.objects.get_or_create(name='Council Manager')
                        user.groups.add(group)
                        logger.info(f"✅ Added Council Manager group (created: {group_created})")
                    else:
                        logger.warning(f"Unknown role: {role}")

                    # Force refresh user groups from database
                    user.groups.through.objects.filter(user=user).exists()
                    final_groups = [g.name for g in user.groups.all()]
                    logger.info(f"✅ User creation completed successfully - Final groups: {final_groups}")
                    logger.info("=== COUNCIL USER CREATION FORM SAVE COMPLETED ===")

            except Exception as e:
                logger.error(f"❌ ERROR during user creation: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Re-raise the exception to ensure transaction rollback
                raise

        return user


class CouncilUserUpdateForm(forms.ModelForm):
    """Form for updating existing council users"""

    # Role choices restricted based on current user
    ROLE_CHOICES = [
        ('council_user', 'Council User'),
        ('council_manager', 'Council Manager'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="User Role",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the role for this council user"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, council=None, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.council = council
        self.current_user = user

        # Set current user's role for display
        if self.instance and self.instance.pk:
            # Determine current role from groups
            if self.instance.groups.filter(name='Council Manager').exists():
                self.fields['role'].initial = 'council_manager'
            elif self.instance.groups.filter(name='Council User').exists():
                self.fields['role'].initial = 'council_user'

        # Restrict role choices based on current user permissions
        if user:
            user_council = getattr(user, 'council', None)
            if user_council and not user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # Council Manager can only assign Council User role
                self.fields['role'].choices = [('council_user', 'Council User')]
                self.fields['role'].help_text = "As a Council Manager, you can only assign Council User role."
            elif user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # RICD users can assign both roles
                self.fields['role'].choices = self.ROLE_CHOICES
                self.fields['role'].help_text = "Select the appropriate role for this council user."

    def clean_role(self):
        """Ensure role selection is valid for current user's permissions"""
        role = self.cleaned_data.get('role')
        if role and self.current_user:
            user_council = getattr(self.current_user, 'council', None)
            if user_council and not self.current_user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                if role != 'council_user':
                    raise forms.ValidationError("You don't have permission to assign this role.")
        return role

    def save(self, commit=True):
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER UPDATE FORM SAVE STARTED ===")
        logger.info(f"Updating user: {self.instance.username}, Role: {self.cleaned_data.get('role')}")

        user = super().save(commit=False)

        if commit:
            try:
                with transaction.atomic():
                    logger.info("Saving user object")
                    user.save()

                    # Update groups based on role
                    logger.info("Updating user groups")
                    user.groups.clear()  # Clear existing groups

                    role = self.cleaned_data.get('role')
                    if role == 'council_user':
                        group, _ = Group.objects.get_or_create(name='Council User')
                        user.groups.add(group)
                        logger.info("✅ Added Council User group")
                    elif role == 'council_manager':
                        group, _ = Group.objects.get_or_create(name='Council Manager')
                        user.groups.add(group)
                        logger.info("✅ Added Council Manager group")

                    # Ensure UserProfile exists and is linked to council
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'council': self.council}
                    )

                    if not created and (profile.council != self.council or profile.council is None):
                        profile.council = self.council
                        profile.save()
                        logger.info(f"✅ Updated UserProfile council to: {self.council}")

                    logger.info("=== COUNCIL USER UPDATE FORM SAVE COMPLETED ===")

            except Exception as e:
                logger.error(f"❌ Error during user update: {str(e)}")
                raise

        return user


# Defect Management Forms
class DefectForm(forms.ModelForm):
    """Form for creating and editing Defects"""

    work = forms.ModelChoiceField(
        queryset=Work.objects.none(),  # Default empty queryset, will be filtered based on user permissions
        required=True,
        label="Work Item",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    identified_date = forms.DateField(
        initial=timezone.now().date(),
        label="Date Identified",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    description = forms.CharField(
        required=True,
        label="Defect Description",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the defect that was identified'
        })
    )

    rectified_date = forms.DateField(
        required=False,
        label="Date Rectified",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Leave blank if not yet rectified'
        })
    )

    class Meta:
        model = Defect
        fields = ['work', 'description', 'identified_date', 'rectified_date']
        widgets = {
            # Work queryset is handled in __init__
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter work queryset based on user permissions
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                # Council user - only show their works
                self.fields['work'].queryset = Work.objects.filter(
                    address__project__council=user_council
                ).select_related('address__project', 'work_type_id', 'output_type_id')
            else:
                # RICD user - can see all works
                self.fields['work'].queryset = Work.objects.select_related(
                    'address__project', 'work_type_id', 'output_type_id'
                )
        else:
            # No user provided - set empty queryset to prevent errors
            self.fields['work'].queryset = Work.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        work = cleaned_data.get('work')

        if work and not self.fields['work'].queryset.filter(pk=work.pk).exists():
            raise forms.ValidationError("You don't have permission to add defects to this work.")

        return cleaned_data


class ProjectFieldVisibilityForm(forms.Form):
    """Form for configuring field visibility settings for a specific project"""

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        if not self.project:
            return

        # Get current council settings for this project
        from ricd.models import get_field_visibility_settings, FieldVisibilitySetting
        council_settings = get_field_visibility_settings(self.project.council)

        # Create checkboxes for each field
        for field_code, field_name in FieldVisibilitySetting.FIELD_CHOICES:
            # Check if there's a project-specific override
            try:
                override = self.project.field_visibility_overrides.get(field_name=field_code)
                initial_value = override.visible_to_council_users
            except self.project.field_visibility_overrides.model.DoesNotExist:
                # Fall back to council default
                initial_value = council_settings.get(field_code, True)

            self.fields[field_code] = forms.BooleanField(
                required=False,
                initial=initial_value,
                label=field_name,
                widget=forms.CheckboxInput(attrs={
                    'class': 'form-check-input'
                })
            )

    def save(self):
        """Save the form data as project-specific overrides"""
        from ricd.models import ProjectFieldVisibilityOverride
        from django.db import transaction

        if not self.project:
            return

        with transaction.atomic():
            # Delete existing overrides for this project
            self.project.field_visibility_overrides.all().delete()

            # Create new overrides for fields that differ from council defaults
            from ricd.models import get_field_visibility_settings
            council_settings = get_field_visibility_settings(self.project.council)

            for field_code, field_name in ProjectFieldVisibilityOverride._meta.get_field('field_name').choices:
                form_value = self.cleaned_data.get(field_code, True)
                council_default = council_settings.get(field_code, True)

                # Only create an override if it differs from the council default
                if form_value != council_default:
                    ProjectFieldVisibilityOverride.objects.create(
                        project=self.project,
                        field_name=field_code,
                        visible_to_council_users=form_value
                    )

        return True


# Enhanced Reporting Forms

class MonthlyTrackerItemForm(forms.ModelForm):
    """Form for creating and editing monthly tracker items"""

    class Meta:
        model = MonthlyTrackerItem
        fields = [
            'name', 'description', 'data_type', 'dropdown_options',
            'required', 'na_acceptable', 'order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tracker item name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what this tracker item measures'
            }),
            'data_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'dropdown_options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Comma-separated options (e.g., Yes,No,N/A)'
            }),
            'required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'na_acceptable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MonthlyTrackerItemGroupForm(forms.ModelForm):
    """Form for creating and editing monthly tracker item groups"""

    tracker_items = forms.ModelMultipleChoiceField(
        queryset=MonthlyTrackerItem.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select the tracker items to include in this group"
    )

    class Meta:
        model = MonthlyTrackerItemGroup
        fields = ['name', 'description', 'tracker_items', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this group of tracker items'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class QuarterlyReportItemForm(forms.ModelForm):
    """Form for creating and editing quarterly report items"""

    class Meta:
        model = QuarterlyReportItem
        fields = [
            'name', 'description', 'data_type', 'dropdown_options',
            'required', 'na_acceptable', 'order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter report item name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what this report item measures'
            }),
            'data_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'dropdown_options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Comma-separated options (e.g., Yes,No,N/A)'
            }),
            'required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'na_acceptable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class QuarterlyReportItemGroupForm(forms.ModelForm):
    """Form for creating and editing quarterly report item groups"""

    report_items = forms.ModelMultipleChoiceField(
        queryset=QuarterlyReportItem.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select the report items to include in this group"
    )

    class Meta:
        model = QuarterlyReportItemGroup
        fields = ['name', 'description', 'report_items', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this group of report items'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class Stage1StepForm(forms.ModelForm):
    """Form for creating and editing Stage 1 steps"""

    class Meta:
        model = Stage1Step
        fields = [
            'name', 'description', 'required_evidence', 'document_required',
            'document_description', 'order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter step name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this stage 1 step'
            }),
            'required_evidence': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe evidence required for this step'
            }),
            'document_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'document_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Describe what document should be uploaded'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class Stage1StepGroupForm(forms.ModelForm):
    """Form for creating and editing Stage 1 step groups"""

    steps = forms.ModelMultipleChoiceField(
        queryset=Stage1Step.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select the steps to include in this group"
    )

    class Meta:
        model = Stage1StepGroup
        fields = ['name', 'description', 'steps', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this group of steps'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class Stage2StepForm(forms.ModelForm):
    """Form for creating and editing Stage 2 steps"""

    class Meta:
        model = Stage2Step
        fields = [
            'name', 'description', 'required_evidence', 'document_required',
            'document_description', 'order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter step name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this stage 2 step'
            }),
            'required_evidence': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe evidence required for this step'
            }),
            'document_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'document_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Describe what document should be uploaded'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class Stage2StepGroupForm(forms.ModelForm):
    """Form for creating and editing Stage 2 step groups"""

    steps = forms.ModelMultipleChoiceField(
        queryset=Stage2Step.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select the steps to include in this group"
    )

    class Meta:
        model = Stage2StepGroup
        fields = ['name', 'description', 'steps', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this group of steps'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ProjectReportConfigurationForm(forms.ModelForm):
    """Form for configuring report items and groups for a specific project"""

    monthly_tracker_groups = forms.ModelMultipleChoiceField(
        queryset=MonthlyTrackerItemGroup.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select monthly tracker item groups for this project"
    )

    quarterly_report_groups = forms.ModelMultipleChoiceField(
        queryset=QuarterlyReportItemGroup.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select quarterly report item groups for this project"
    )

    stage1_step_groups = forms.ModelMultipleChoiceField(
        queryset=Stage1StepGroup.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select Stage 1 step groups for this project"
    )

    stage2_step_groups = forms.ModelMultipleChoiceField(
        queryset=Stage2StepGroup.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'width: 100%;'
        }),
        required=False,
        help_text="Select Stage 2 step groups for this project"
    )

    class Meta:
        model = ProjectReportConfiguration
        fields = [
            'monthly_tracker_groups', 'quarterly_report_groups',
            'stage1_step_groups', 'stage2_step_groups'
        ]


class MonthlyTrackerEntryForm(forms.ModelForm):
    """Dynamic form for individual monthly tracker item entries with data type-specific fields"""

    class Meta:
        model = MonthlyTrackerEntry
        fields = ['supporting_document']
        widgets = {
            'supporting_document': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove the value field from Meta fields so we can dynamically create it
        if 'value' in self.fields:
            del self.fields['value']
            
        if self.instance and self.instance.tracker_item:
            tracker_item = self.instance.tracker_item
            data_type = tracker_item.data_type
            required = tracker_item.required and not tracker_item.na_acceptable
            
            # Create appropriate field based on data type
            if data_type == 'date':
                self.fields['value'] = forms.DateField(
                    required=required,
                    widget=forms.DateInput(attrs={
                        'type': 'date',
                        'class': 'form-control'
                    }),
                    label=tracker_item.name
                )
            elif data_type == 'checkbox':
                self.fields['value'] = forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input'
                    }),
                    label=tracker_item.name,
                    initial=False
                )
            elif data_type == 'text':
                self.fields['value'] = forms.CharField(
                    required=required,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': f'Enter {tracker_item.name.lower()}'
                    }),
                    label=tracker_item.name
                )
            elif data_type in ['number', 'currency']:
                self.fields['value'] = forms.DecimalField(
                    required=required,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'step': 'any'
                    }),
                    label=tracker_item.name
                )
            elif data_type == 'dropdown':
                choices = [(opt, opt) for opt in tracker_item.get_dropdown_options_list()]
                if tracker_item.na_acceptable:
                    choices.append(('N/A', 'N/A'))
                self.fields['value'] = forms.ChoiceField(
                    choices=choices,
                    required=required,
                    widget=forms.Select(attrs={
                        'class': 'form-select'
                    }),
                    label=tracker_item.name
                )
            
            # Add N/A checkbox if applicable
            if tracker_item.na_acceptable and data_type != 'dropdown':
                self.fields['na_value'] = forms.BooleanField(
                    required=False,
                    label='N/A',
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input na-checkbox',
                        'data-target': f'id_value_{self.instance.id}'
                    }),
                    initial=(self.instance.value == 'N/A')
                )

    def clean(self):
        cleaned_data = super().clean()
        tracker_item = self.instance.tracker_item if self.instance else None
        
        if tracker_item and tracker_item.na_acceptable:
            na_value = cleaned_data.get('na_value', False)
            if na_value:
                cleaned_data['value'] = 'N/A'
                
        return cleaned_data


class QuarterlyReportItemEntryForm(forms.ModelForm):
    """Form for individual quarterly report item entries"""

    class Meta:
        model = QuarterlyReportItemEntry
        fields = ['value', 'supporting_document']
        widgets = {
            'value': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter value'
            }),
            'supporting_document': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class Stage1StepCompletionForm(forms.ModelForm):
    """Form for Stage 1 step completion"""

    class Meta:
        model = Stage1StepCompletion
        fields = ['completed', 'completed_date', 'evidence_notes', 'supporting_document']
        widgets = {
            'completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'completed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'evidence_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes about evidence provided'
            }),
            'supporting_document': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class Stage2StepCompletionForm(forms.ModelForm):
    """Form for Stage 2 step completion"""

    class Meta:
        model = Stage2StepCompletion
        fields = ['completed', 'completed_date', 'evidence_notes', 'supporting_document']
        widgets = {
            'completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'completed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'evidence_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes about evidence provided'
            }),
            'supporting_document': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }