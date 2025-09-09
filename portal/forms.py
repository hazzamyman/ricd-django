from django import forms
from django.contrib.auth.models import User
from ricd.models import (
    Project, FundingSchedule, QuarterlyReport, MonthlyTracker,
    Stage1Report, Stage2Report, Work, ReportAttachment, Council, Program, Address,
    WorkType, OutputType
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
            'summary_notes'
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

    class Meta:
        model = Council
        fields = [
            'name', 'abn', 'default_suburb', 'default_postcode', 'default_state',
            'federal_electorate', 'state_electorate', 'qhigi_region'
        ]
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
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label="Project",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = Work
        fields = [
            'project', 'address_line', 'work_type_id', 'output_type_id', 'output_quantity',
            'bedrooms', 'estimated_cost', 'actual_cost', 'start_date', 'end_date'
        ]
        # Removed construction details: floor_method, frame_method, external_wall_method,
        # roof_method, car_accommodation, additional_facilities, bathrooms, kitchens, dwellings_count
        widgets = {
            'address_line': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full address'
            }),
            'work_type_id': forms.Select(attrs={
                'class': 'form-select'
            }),
            'output_type_id': forms.Select(attrs={
                'class': 'form-select'
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

    class Meta:
        model = Address
        fields = [
            'street', 'suburb', 'postcode', 'state', 'lot_number', 'plan_number', 'title_reference',
            'work_type_id', 'output_type_id', 'bedrooms', 'output_quantity', 'budget'
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
            'work_type_id': forms.Select(attrs={
                'class': 'form-select'
            }),
            'output_type_id': forms.Select(attrs={
                'class': 'form-select'
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
        }


# Project Management Forms
class ProjectForm(forms.ModelForm):
    """Form for creating and editing Projects"""

    class Meta:
        model = Project
        fields = [
            'council', 'program', 'funding_schedule', 'name', 'description',
            'funding_schedule_amount', 'contingency_amount', 'contingency_percentage',
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
            'principal_officer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Principal officer name'
            }),
            'senior_officer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Senior officer name'
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

        # Filter queryset based on user council if not RICD user
        if user:
            user_council = getattr(user, 'council', None)
            if user_council:
                self.fields['council'].queryset = Council.objects.filter(id=user_council.id)
                self.fields['council'].initial = user_council
                # Only show funding schedules for user's council
                self.fields['funding_schedule'].queryset = FundingSchedule.objects.filter(council=user_council)
                # Filter projects to user's council
                self.fields['council'].widget.attrs['disabled'] = 'disabled'
            else:
                self.fields['council'].queryset = Council.objects.all()
                self.fields['funding_schedule'].queryset = FundingSchedule.objects.all()

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