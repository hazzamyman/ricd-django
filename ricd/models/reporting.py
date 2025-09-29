from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal

# Import models for proper resolution of forward references
from .core import Council
from .work import Work
from .project import Project
from .funding import FundingSchedule


class MonthlyReport(models.Model):
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('more_info', 'More Info Requested'),
    ]

    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name='monthly_reports')
    period = models.DateField(help_text="First day of the month")
    council_comments = models.TextField(blank=True)
    # Council Manager Approval
    COUNCIL_MANAGER_DECISIONS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    council_manager_decision = models.CharField(
        max_length=10,
        choices=COUNCIL_MANAGER_DECISIONS,
        default='pending',
        help_text="Council Manager approval decision"
    )
    council_manager_comments = models.TextField(blank=True, null=True, help_text="Council Manager comments")
    council_manager_decision_date = models.DateField(blank=True, null=True, help_text="Date of Council Manager decision")

    ricd_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='more_info')
    ricd_comments = models.TextField(blank=True)

    class Meta:
        unique_together = ('council', 'period')
        ordering = ['-period']

    def clean(self):
        """Validate MonthlyReport fields"""
        if self.council_manager_decision and self.council_manager_decision not in ['pending', 'approved', 'rejected']:
            raise ValidationError({'council_manager_decision': 'Invalid council manager decision'})

        if self.ricd_status not in ['accepted', 'rejected', 'more_info']:
            raise ValidationError({'ricd_status': 'Invalid RICD status'})

        # Date validation
        if self.period.day != 1:
            raise ValidationError({'period': 'Period must be the first day of the month'})

        # Decision date validation
        if self.council_manager_decision_date and self.council_manager_decision_date > timezone.now().date():
            raise ValidationError({'council_manager_decision_date': 'Decision date cannot be in the future'})

    def __str__(self):
        return f"{self.council} Monthly Report - {self.period.strftime('%B %Y')}"


class CouncilQuarterlyReport(models.Model):
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('more_info', 'More Info Requested'),
    ]

    council = models.ForeignKey(Council, on_delete=models.CASCADE, related_name='council_quarterly_reports')
    period = models.DateField(help_text="First day of the quarter, e.g., Jan 1, Apr 1, Jul 1, Oct 1")
    council_comments = models.TextField(blank=True)
    ricd_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='more_info')
    ricd_comments = models.TextField(blank=True)

    class Meta:
        unique_together = ('council', 'period')
        ordering = ['-period']

    def clean(self):
        """Validate CouncilQuarterlyReport fields"""
        if self.ricd_status not in ['accepted', 'rejected', 'more_info']:
            raise ValidationError({'ricd_status': 'Invalid RICD status'})

        # Period validation - should be first day of quarter
        month = self.period.month
        if month not in [1, 4, 7, 10] or self.period.day != 1:
            raise ValidationError({'period': 'Period must be the first day of a quarter (Jan 1, Apr 1, Jul 1, or Oct 1)'})

    def __str__(self):
        # Determine quarter
        month = self.period.month
        year = self.period.year
        if 1 <= month <= 3:
            quarter = "Q1"
        elif 4 <= month <= 6:
            quarter = "Q2"
        elif 7 <= month <= 9:
            quarter = "Q3"
        else:
            quarter = "Q4"
        return f"{self.council} Council Quarterly Report - {quarter} {year}"


class QuarterlyReport(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="quarterly_reports", null=True, blank=True)
    quarter = models.CharField(max_length=20, default="")  # Auto-generated like "Jan-Mar 2024"
    submission_date = models.DateField(default=timezone.now)

    # Progress Tracking
    percentage_works_completed = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    total_expenditure_council = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    unspent_funding_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    comments_indigenous_employment = models.TextField(blank=True, null=True)

    # Project Status
    practical_completion_forecast_date = models.DateField(blank=True, null=True)
    practical_completion_actual_date = models.DateField(blank=True, null=True)

    # Issues and Contributions
    adverse_matters = models.TextField(blank=True, null=True)
    council_contributions_details = models.TextField(blank=True, null=True)
    other_contributions_details = models.TextField(blank=True, null=True)
    council_contributions_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    other_contributions_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])

    # Additional summary/notes
    summary_notes = models.TextField(blank=True, null=True)

    # RICD Staff Assessment
    staff_assessment_notes = models.TextField(blank=True, null=True, help_text="RICD Staff assessment notes")
    staff_assessed_date = models.DateField(blank=True, null=True, help_text="Date when RICD Staff assessed")

    # Council Manager Approval
    COUNCIL_MANAGER_DECISIONS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    council_manager_decision = models.CharField(
        max_length=10,
        choices=COUNCIL_MANAGER_DECISIONS,
        default='pending',
        help_text="Council Manager approval decision"
    )
    council_manager_comments = models.TextField(blank=True, null=True, help_text="Council Manager comments")
    council_manager_decision_date = models.DateField(blank=True, null=True, help_text="Date of Council Manager decision")

    # RICD Manager Decision
    MANAGER_DECISIONS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    manager_decision = models.CharField(
        max_length=10,
        choices=MANAGER_DECISIONS,
        default='pending',
        help_text="RICD Manager approval decision"
    )
    manager_comments = models.TextField(blank=True, null=True, help_text="RICD Manager comments")
    manager_decision_date = models.DateField(blank=True, null=True, help_text="Date of RICD Manager decision")

    # Supporting documents
    supporting_document_1 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 1")
    supporting_document_2 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 2")
    supporting_document_3 = models.FileField(upload_to="reports/supporting/%Y/%m/", blank=True, null=True, help_text="Supporting document 3")
    supporting_document_description = models.TextField(blank=True, null=True, help_text="Description of supporting documents")

    def save(self, *args, **kwargs):
        """Auto-generate quarter field"""

        if not self.quarter:
            date_obj = self.submission_date or timezone.now()
            # Ensure we have a date object
            if isinstance(date_obj, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_obj).date()
            elif hasattr(date_obj, 'date'):
                # If it's a datetime, get the date part
                date_obj = date_obj.date()

            year = date_obj.year
            month = date_obj.month
            if 1 <= month <= 3:
                self.quarter = f"Jan-Mar {year}"
            elif 4 <= month <= 6:
                self.quarter = f"Apr-Jun {year}"
            elif 7 <= month <= 9:
                self.quarter = f"Jul-Sep {year}"
            elif 10 <= month <= 12:
                self.quarter = f"Oct-Dec {year}"
        super().save(*args, **kwargs)

    def clean(self):
        """Validate QuarterlyReport fields"""
        # Financial validations
        if self.percentage_works_completed is not None and (self.percentage_works_completed < 0 or self.percentage_works_completed > 100):
            raise ValidationError({'percentage_works_completed': 'Percentage works completed must be between 0 and 100'})

        if self.total_expenditure_council is not None and self.total_expenditure_council < 0:
            raise ValidationError({'total_expenditure_council': 'Total expenditure cannot be negative'})

        if self.unspent_funding_amount is not None and self.unspent_funding_amount < 0:
            raise ValidationError({'unspent_funding_amount': 'Unspent funding amount cannot be negative'})

        # Employment validations
        if self.total_employed_people is not None and self.total_employed_people < 0:
            raise ValidationError({'total_employed_people': 'Total employed people cannot be negative'})

        if self.total_indigenous_employed is not None and self.total_indigenous_employed < 0:
            raise ValidationError({'total_indigenous_employed': 'Total indigenous employed cannot be negative'})

        if self.total_indigenous_employed is not None and self.total_employed_people is not None:
            if self.total_indigenous_employed > self.total_employed_people:
                raise ValidationError({'total_indigenous_employed': 'Indigenous employed cannot exceed total employed'})

        # Contribution validations
        if self.council_contributions_amount is not None and self.council_contributions_amount < 0:
            raise ValidationError({'council_contributions_amount': 'Council contributions amount cannot be negative'})

        if self.other_contributions_amount is not None and self.other_contributions_amount < 0:
            raise ValidationError({'other_contributions_amount': 'Other contributions amount cannot be negative'})

        # Date validations
        if self.practical_completion_forecast_date and self.practical_completion_forecast_date < timezone.now().date():
            raise ValidationError({'practical_completion_forecast_date': 'Forecast date cannot be in the past'})

        if self.practical_completion_actual_date and self.practical_completion_actual_date > timezone.now().date():
            raise ValidationError({'practical_completion_actual_date': 'Actual completion date cannot be in the future'})

        # Decision validations
        if self.council_manager_decision and self.council_manager_decision not in ['pending', 'approved', 'rejected']:
            raise ValidationError({'council_manager_decision': 'Invalid council manager decision'})

        if self.manager_decision and self.manager_decision not in ['pending', 'approved', 'rejected']:
            raise ValidationError({'manager_decision': 'Invalid manager decision'})

        # Decision date validations
        if self.staff_assessed_date and self.staff_assessed_date > timezone.now().date():
            raise ValidationError({'staff_assessed_date': 'Staff assessed date cannot be in the future'})

        if self.council_manager_decision_date and self.council_manager_decision_date > timezone.now().date():
            raise ValidationError({'council_manager_decision_date': 'Council manager decision date cannot be in the future'})

        if self.manager_decision_date and self.manager_decision_date > timezone.now().date():
            raise ValidationError({'manager_decision_date': 'Manager decision date cannot be in the future'})

    def __str__(self):
        return f"{self.work} - {self.quarter}"

    @property
    def total_contributions(self):
        contributions = Decimal('0.00')
        if self.council_contributions_amount:
            contributions += self.council_contributions_amount
        if self.other_contributions_amount:
            contributions += self.other_contributions_amount
        return contributions

    @property
    def unspent_funding(self):
        """Calculate unspent funding for this work"""
        if self.work.estimated_cost and self.total_expenditure_council:
            return self.work.estimated_cost - self.total_expenditure_council
        return None

    @property
    def stage1_payment_due(self):
        """Check if Stage 1 report is approved and 60% payment should be released"""
        if (self.manager_decision == 'approved' and
            self.work.project.stage1_target and
            self.submission_date >= self.work.project.stage1_target):
            # Check if 60% payment has been released
            funding_schedule = self.work.project.funding_schedule
            if funding_schedule and not any(instalment.amount == funding_schedule.funding_amount * Decimal('0.6')
                                           and instalment.paid
                                           for instalment in funding_schedule.instalments.all()):
                return funding_schedule.funding_amount * Decimal('0.6')
        return None

    @property
    def stage2_payment_due(self):
        """Check if Stage 2 report is approved and 10% payment should be released"""
        # This would need to be called on Stage2Report, not QuarterlyReport
        # Or we need to adapt for Project-level payment tracking
        return None

    # Project-level aggregation properties for summary reporting
    @classmethod
    def get_project_quarterly_summary(cls, project, quarter_str):
        """Get aggregated summary for all works in a project for a specific quarter"""
        reports = cls.objects.filter(work__address__project=project, quarter=quarter_str)

        if not reports:
            return {}

        summary = {
            'works_completed_avg': reports.aggregate(avg=models.Avg('percentage_works_completed'))['avg'] or 0,
            'total_budget': sum(report.work.estimated_cost or 0 for report in reports),
            'total_expenditure': reports.aggregate(total=models.Sum('total_expenditure_council'))['total'] or 0,
            'total_unspent': sum((report.unspent_funding or 0) for report in reports),
            'total_employed': reports.aggregate(total=models.Sum('total_employed_people'))['total'] or 0,
            'total_indigenous': reports.aggregate(total=models.Sum('total_indigenous_employed'))['total'] or 0,
            'work_reports': reports
        }

        return summary

    @property
    def project(self):
        """Convenience property to get the project"""
        return self.work.project


class MonthlyTracker(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="monthly_trackers", null=True, blank=True)
    month = models.DateField(default=timezone.now)
    progress_notes = models.TextField(blank=True, null=True)

    # Design Phase
    design_tender_date = models.DateField(blank=True, null=True)
    design_award_date = models.DateField(blank=True, null=True)

    # Tender and Award Phase
    construction_tender_date = models.DateField(blank=True, null=True)
    construction_award_date = models.DateField(blank=True, null=True)

    # Utilities and Services
    ergon_connection_application_date = models.DateField(blank=True, null=True)
    ergon_connection_date = models.DateField(blank=True, null=True)

    # Site Preparation
    site_establishment_date = models.DateField(blank=True, null=True)
    earthworks_date = models.DateField(blank=True, null=True)
    slab_date = models.DateField(blank=True, null=True)
    underground_services_date = models.DateField(blank=True, null=True)

    # Foundation and Structure
    termite_prevention_date = models.DateField(blank=True, null=True)
    sub_floor_framing_concrete_date = models.DateField(blank=True, null=True)
    end_of_year_shutdown = models.DateField(blank=True, null=True)
    wall_frames_masonry_date = models.DateField(blank=True, null=True)

    # Roof Structure
    roof_framing_battens_date = models.DateField(blank=True, null=True)
    roof_sheeting_date = models.DateField(blank=True, null=True)
    fascia_gutter_date = models.DateField(blank=True, null=True)
    soffit_linings_gables_date = models.DateField(blank=True, null=True)

    # Services Rough-in
    plumbing_electrical_rough_in_date = models.DateField(blank=True, null=True)

    # Internal Finishes
    internal_wall_ceiling_linings_date = models.DateField(blank=True, null=True)
    internal_floor_coverings_date = models.DateField(blank=True, null=True)
    carpentry_2nd_fix_date = models.DateField(blank=True, null=True)
    wet_area_wall_linings_date = models.DateField(blank=True, null=True)
    joinery_install_date = models.DateField(blank=True, null=True)
    internal_painting_date = models.DateField(blank=True, null=True)

    # Exterior Elements
    external_doors_windows_date = models.DateField(blank=True, null=True)
    external_decks_stairs_balustrade_date = models.DateField(blank=True, null=True)

    # Waterproofing
    waterproofing_date = models.DateField(blank=True, null=True)

    # Final Touches
    external_painting_date = models.DateField(blank=True, null=True)
    electrical_fit_off_date = models.DateField(blank=True, null=True)
    plumbing_fit_off_date = models.DateField(blank=True, null=True)
    carpentry_3rd_fix_date = models.DateField(blank=True, null=True)

    # Site Completion
    fencing_gates_date = models.DateField(blank=True, null=True)
    clothesline_date = models.DateField(blank=True, null=True)
    driveway_paths_date = models.DateField(blank=True, null=True)
    shed_date = models.DateField(blank=True, null=True)
    site_clean_date = models.DateField(blank=True, null=True)
    final_internal_clean_handover_date = models.DateField(blank=True, null=True)

    def clean(self):
        """Validate MonthlyTracker fields"""
        # Month should be first day of month
        if self.month.day != 1:
            raise ValidationError({'month': 'Month must be the first day of the month'})

        # Date validations for construction milestones
        today = timezone.now().date()

        date_fields = [
            'design_tender_date', 'design_award_date', 'construction_tender_date',
            'construction_award_date', 'ergon_connection_application_date',
            'ergon_connection_date', 'site_establishment_date', 'earthworks_date',
            'slab_date', 'underground_services_date', 'termite_prevention_date',
            'sub_floor_framing_concrete_date', 'end_of_year_shutdown',
            'wall_frames_masonry_date', 'roof_framing_battens_date',
            'roof_sheeting_date', 'fascia_gutter_date', 'soffit_linings_gables_date',
            'plumbing_electrical_rough_in_date', 'internal_wall_ceiling_linings_date',
            'internal_floor_coverings_date', 'carpentry_2nd_fix_date',
            'wet_area_wall_linings_date', 'joinery_install_date', 'internal_painting_date',
            'external_doors_windows_date', 'external_decks_stairs_balustrade_date',
            'waterproofing_date', 'external_painting_date', 'electrical_fit_off_date',
            'plumbing_fit_off_date', 'carpentry_3rd_fix_date', 'fencing_gates_date',
            'clothesline_date', 'driveway_paths_date', 'shed_date', 'site_clean_date',
            'final_internal_clean_handover_date'
        ]

        for field_name in date_fields:
            field_value = getattr(self, field_name)
            if field_value:
                if field_value > today:
                    raise ValidationError({field_name: f'{field_name.replace("_", " ").title()} cannot be in the future'})

                # Check logical sequence - some dates should be before others
                if field_name == 'design_tender_date':
                    if hasattr(self, 'design_award_date') and self.design_award_date and self.design_tender_date > self.design_award_date:
                        raise ValidationError({'design_tender_date': 'Design tender date must be before design award date'})

                elif field_name == 'construction_tender_date':
                    if hasattr(self, 'construction_award_date') and self.construction_award_date and self.construction_tender_date > self.construction_award_date:
                        raise ValidationError({'construction_tender_date': 'Construction tender date must be before construction award date'})

    def __str__(self):
        return f"{self.work} - {self.month.strftime('%B %Y')}"

    @property
    def month_display(self):
        """Auto-generate month display like 'August 2024'"""
        return self.month.strftime('%B %Y')

    def copy_from_previous(self):
        """Copy data from the previous month's report for this work"""
        previous_month = self.month - timezone.timedelta(days=30)
        try:
            previous_report = MonthlyTracker.objects.get(
                work=self.work,
                month__year=previous_month.year,
                month__month=previous_month.month
            )
            # Copy all the date fields from previous report
            date_fields = [
                'design_tender_date', 'design_award_date', 'construction_tender_date',
                'construction_award_date', 'ergon_connection_application_date',
                'ergon_connection_date', 'site_establishment_date', 'earthworks_date',
                'slab_date', 'underground_services_date', 'termite_prevention_date',
                'sub_floor_framing_concrete_date', 'end_of_year_shutdown',
                'wall_frames_masonry_date', 'roof_framing_battens_date',
                'roof_sheeting_date', 'fascia_gutter_date', 'soffit_linings_gables_date',
                'plumbing_electrical_rough_in_date', 'internal_wall_ceiling_linings_date',
                'internal_floor_coverings_date', 'carpentry_2nd_fix_date',
                'wet_area_wall_linings_date', 'joinery_install_date', 'internal_painting_date',
                'external_doors_windows_date', 'external_decks_stairs_balustrade_date',
                'waterproofing_date', 'external_painting_date', 'electrical_fit_off_date',
                'plumbing_fit_off_date', 'carpentry_3rd_fix_date', 'fencing_gates_date',
                'clothesline_date', 'driveway_paths_date', 'shed_date', 'site_clean_date',
                'final_internal_clean_handover_date'
            ]
            for field_name in date_fields:
                if hasattr(previous_report, field_name):
                    setattr(self, field_name, getattr(previous_report, field_name))
            return True
        except MonthlyTracker.DoesNotExist:
            return False


class Stage1Report(models.Model):
    """Model for Stage 1 reports - land acquisition and planning phase"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stage1_reports")
    submission_date = models.DateField(default=timezone.now)

    # Reporting compliance
    expenditure_records_maintained = models.BooleanField(default=False)
    quarterly_reports_provided = models.BooleanField(default=False)

    # Reporting type
    REPORT_TYPES = [
        ('construction', 'Construction'),
        ('land', 'Land'),
    ]
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='construction')

    # Land and Works Documentation
    land_description_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    works_description_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    land_title_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Native Title and Heritage
    native_title_addressed = models.BooleanField(default=False)
    native_title_documentation = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    heritage_matters_addressed = models.BooleanField(default=False)
    heritage_documentation = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Approvals and Documentation
    development_approval_obtained = models.BooleanField(default=False)
    development_approval_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    tenure_obtained = models.BooleanField(default=False)
    tenure_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    land_surveyed = models.BooleanField(default=False)
    survey_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Subdivision
    subdivision_required = models.BooleanField(default=False)
    subdivision_plan_prepared = models.BooleanField(default=False)
    subdivision_plan_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Design
    design_approved = models.BooleanField(default=False)
    design_document_proposed = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    design_document_approved = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    structural_certification_obtained = models.BooleanField(default=False)
    structural_certification_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Contractors
    council_contractors_used = models.BooleanField(default=False)

    # Infrastructure Approvals
    infrastructure_approvals_obtained = models.BooleanField(default=False)
    infrastructure_documentation = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)
    building_approval_document = models.FileField(upload_to="reports/stage1/%Y/%m/", blank=True, null=True)

    # Tenders and Contractors
    tenders_called = models.BooleanField(default=False)
    contractor_appointed = models.BooleanField(default=False)
    contractor_details = models.TextField(blank=True, null=True)

    # Building and Infrastructure Approvals
    building_approval_obtained = models.BooleanField(default=False)

    # Additional notes
    completion_notes = models.TextField(blank=True, null=True)

    # RICD Assessment Fields
    RICD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('needs_more_info', 'Needs More Information'),
    ]
    ricd_status = models.CharField(max_length=20, choices=RICD_STATUS_CHOICES, default='pending')
    ricd_comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submission_date']

    def clean(self):
        """Validate Stage1Report fields"""
        if self.submission_date > timezone.now().date():
            raise ValidationError({'submission_date': 'Submission date cannot be in the future'})

        if self.ricd_status not in ['pending', 'accepted', 'rejected', 'needs_more_info']:
            raise ValidationError({'ricd_status': 'Invalid RICD status'})

    def __str__(self):
        return f"Stage 1 Report for {self.project} - {self.submission_date}"


class Stage2Report(models.Model):
    """Model for Stage 2 reports - construction completion phase"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stage2_reports")
    submission_date = models.DateField(default=timezone.now)

    # Reporting type
    REPORT_TYPES = [
        ('construction', 'Construction'),
        ('land', 'Land'),
    ]
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='construction')

    # Schedule of Works
    schedule_provided = models.BooleanField(default=False)
    schedule_provided_date = models.DateField(blank=True, null=True)

    # Reporting compliance
    quarterly_reports_provided = models.BooleanField(default=False)
    monthly_trackers_provided = models.BooleanField(default=False)

    # Practical Completion
    practical_completion_achieved = models.BooleanField(default=False)
    practical_completion_date = models.DateField(blank=True, null=True)
    practical_completion_notification_sent = models.BooleanField(default=False)
    notification_date = models.DateField(blank=True, null=True)

    # Land works completion
    land_works_completed = models.BooleanField(default=False)

    # Handover requirements
    handover_requirements_met = models.BooleanField(default=False)
    handover_checklist_completed = models.BooleanField(default=False)
    handover_checklist_document = models.FileField(upload_to="reports/stage2/%Y/%m/", blank=True, null=True)

    # Warranties and documentation
    warranties_provided = models.BooleanField(default=False)
    warranties_document = models.FileField(upload_to="reports/stage2/%Y/%m/", blank=True, null=True)
    final_plans_provided = models.BooleanField(default=False)
    final_plans_document = models.FileField(upload_to="reports/stage2/%Y/%m/", blank=True, null=True)

    # Inspections
    joint_inspection_completed = models.BooleanField(default=False)
    joint_inspection_date = models.DateField(blank=True, null=True)

    # Additional notes
    completion_notes = models.TextField(blank=True, null=True)

    # Council Manager Approval Fields
    COUNCIL_MANAGER_DECISIONS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    council_manager_decision = models.CharField(max_length=10, choices=COUNCIL_MANAGER_DECISIONS, default='pending')
    council_manager_comments = models.TextField(blank=True, null=True)

    # RICD Assessment Fields
    RICD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('needs_more_info', 'Needs More Information'),
    ]
    ricd_status = models.CharField(max_length=20, choices=RICD_STATUS_CHOICES, default='pending')
    ricd_comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submission_date']

    def clean(self):
        """Validate Stage2Report fields"""
        if self.submission_date > timezone.now().date():
            raise ValidationError({'submission_date': 'Submission date cannot be in the future'})

        if self.practical_completion_date and self.practical_completion_date > timezone.now().date():
            raise ValidationError({'practical_completion_date': 'Practical completion date cannot be in the future'})

        if self.notification_date and self.notification_date > timezone.now().date():
            raise ValidationError({'notification_date': 'Notification date cannot be in the future'})

        if self.joint_inspection_date and self.joint_inspection_date > timezone.now().date():
            raise ValidationError({'joint_inspection_date': 'Joint inspection date cannot be in the future'})

        if self.schedule_provided_date and self.schedule_provided_date > timezone.now().date():
            raise ValidationError({'schedule_provided_date': 'Schedule provided date cannot be in the future'})

        if self.council_manager_decision not in ['pending', 'approved', 'rejected']:
            raise ValidationError({'council_manager_decision': 'Invalid council manager decision'})

        if self.ricd_status not in ['pending', 'accepted', 'rejected', 'needs_more_info']:
            raise ValidationError({'ricd_status': 'Invalid RICD status'})

    def __str__(self):
        return f"Stage 2 Report for {self.project} - {self.submission_date}"


class StageReport(models.Model):
    funding_schedule = models.ForeignKey(FundingSchedule, on_delete=models.CASCADE, related_name="stage_reports")
    stage = models.IntegerField(choices=[(1, "Stage 1"), (2, "Stage 2")])
    submission_date = models.DateField()
    acceptance_date = models.DateField(blank=True, null=True)
    report_file = models.FileField(upload_to="reports/", blank=True, null=True)
    checklist = models.JSONField(default=dict)

    def clean(self):
        """Validate StageReport fields"""
        if self.stage not in [1, 2]:
            raise ValidationError({'stage': 'Stage must be 1 or 2'})

        if self.acceptance_date and self.acceptance_date > timezone.now().date():
            raise ValidationError({'acceptance_date': 'Acceptance date cannot be in the future'})

        if self.submission_date > timezone.now().date():
            raise ValidationError({'submission_date': 'Submission date cannot be in the future'})

        if self.acceptance_date and self.submission_date and self.acceptance_date < self.submission_date:
            raise ValidationError({'acceptance_date': 'Acceptance date cannot be before submission date'})

    def __str__(self):
        return f"Stage {self.stage} Report for {self.funding_schedule}"


class ReportAttachment(models.Model):
    # Generic attachment model that can be linked to various reports and tasks
    quarterly_report = models.ForeignKey(QuarterlyReport, on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    monthly_tracker = models.ForeignKey(MonthlyTracker, on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    step_completion = models.ForeignKey('Stage1StepCompletion', on_delete=models.CASCADE, related_name="attachments", blank=True, null=True)
    # Can add more report type foreign keys as needed

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="reports/attachments/%Y/%m/")
    description = models.TextField(blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Validate ReportAttachment fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Attachment name is required'})

        if not self.description.strip():
            raise ValidationError({'description': 'Attachment description is required'})

        # Check that at least one report type is linked
        linked_reports = [self.quarterly_report, self.monthly_tracker, self.step_completion]
        if not any(linked_reports):
            raise ValidationError('Attachment must be linked to at least one report')

        # Check that only one report type is linked
        linked_count = sum(1 for report in linked_reports if report is not None)
        if linked_count > 1:
            raise ValidationError('Attachment can only be linked to one report type')

    def __str__(self):
        return f"{self.name} - {self.file.name}"


class MonthlyTrackerItem(models.Model):
    """Configuration for individual tracker items in monthly reports"""
    DATA_TYPE_CHOICES = [
        ('date', 'Date'),
        ('checkbox', 'Checkbox'),
        ('text', 'Text Input'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('dropdown', 'Dropdown'),
    ]

    name = models.CharField(max_length=255, help_text='Display name for the tracker item')
    description = models.TextField(blank=True, null=True, help_text='Description of what this tracker item measures')
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='date', help_text='Type of data this tracker item collects')
    dropdown_options = models.TextField(blank=True, null=True, help_text="Comma-separated list of options for dropdown type (e.g., 'Yes,No,N/A')")
    required = models.BooleanField(default=False, help_text='Whether this field is required')
    na_acceptable = models.BooleanField(default=True, help_text='Whether N/A is an acceptable value')
    order = models.PositiveIntegerField(default=1, help_text='Display order in reports')
    is_active = models.BooleanField(default=True, help_text='Whether this tracker item is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Monthly Tracker Item'
        verbose_name_plural = 'Monthly Tracker Items'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class MonthlyTrackerItemGroup(models.Model):
    """Groups of tracker items for monthly reports"""
    name = models.CharField(max_length=255, help_text='Name of the tracker item group')
    description = models.TextField(blank=True, null=True, help_text='Description of this group')
    tracker_items = models.ManyToManyField(MonthlyTrackerItem, related_name='groups', help_text='Tracker items included in this group')
    is_active = models.BooleanField(default=True, help_text='Whether this group is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Monthly Tracker Item Group'
        verbose_name_plural = 'Monthly Tracker Item Groups'
        ordering = ['name']

    def __str__(self):
        return self.name


class QuarterlyReportItem(models.Model):
    """Configuration for individual report items in quarterly reports"""
    DATA_TYPE_CHOICES = [
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('text', 'Text Input'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date'),
        ('dropdown', 'Dropdown'),
        ('yes_no', 'Yes/No'),
    ]

    name = models.CharField(max_length=255, help_text='Display name for the report item')
    description = models.TextField(blank=True, null=True, help_text='Description of what this report item measures')
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='number', help_text='Type of data this report item collects')
    dropdown_options = models.TextField(blank=True, null=True, help_text='Comma-separated list of options for dropdown type')
    required = models.BooleanField(default=False, help_text='Whether this field is required')
    na_acceptable = models.BooleanField(default=True, help_text='Whether N/A is an acceptable value')
    order = models.PositiveIntegerField(default=1, help_text='Display order in reports')
    is_active = models.BooleanField(default=True, help_text='Whether this report item is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quarterly Report Item'
        verbose_name_plural = 'Quarterly Report Items'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Stage1Step(models.Model):
    """Configuration for individual steps in Stage 1 reports"""
    name = models.CharField(max_length=255, help_text='Name of the Stage 1 step')
    description = models.TextField(blank=True, null=True, help_text='Detailed description of this step')
    required_evidence = models.TextField(blank=True, null=True, help_text='Description of evidence required for this step')
    document_required = models.BooleanField(default=False, help_text='Whether a document upload is required for this step')
    document_description = models.TextField(blank=True, null=True, help_text='Description of what document should be uploaded')
    order = models.PositiveIntegerField(default=1, help_text='Display order in reports')
    is_active = models.BooleanField(default=True, help_text='Whether this step is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 1 Step'
        verbose_name_plural = 'Stage 1 Steps'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Stage2Step(models.Model):
    """Configuration for individual steps in Stage 2 reports"""
    name = models.CharField(max_length=255, help_text='Name of the Stage 2 step')
    description = models.TextField(blank=True, null=True, help_text='Detailed description of this step')
    required_evidence = models.TextField(blank=True, null=True, help_text='Description of evidence required for this step')
    document_required = models.BooleanField(default=False, help_text='Whether a document upload is required for this step')
    document_description = models.TextField(blank=True, null=True, help_text='Description of what document should be uploaded')
    order = models.PositiveIntegerField(default=1, help_text='Display order in reports')
    is_active = models.BooleanField(default=True, help_text='Whether this step is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 2 Step'
        verbose_name_plural = 'Stage 2 Steps'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Stage1StepGroup(models.Model):
    """Groups of Stage 1 steps"""
    name = models.CharField(max_length=255, help_text='Name of the step group')
    description = models.TextField(blank=True, null=True, help_text='Description of this group')
    steps = models.ManyToManyField(Stage1Step, related_name='groups', help_text='Steps included in this group')
    is_active = models.BooleanField(default=True, help_text='Whether this group is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 1 Step Group'
        verbose_name_plural = 'Stage 1 Step Groups'
        ordering = ['name']

    def __str__(self):
        return self.name


class Stage2StepGroup(models.Model):
    """Groups of Stage 2 steps"""
    name = models.CharField(max_length=255, help_text='Name of the step group')
    description = models.TextField(blank=True, null=True, help_text='Description of this group')
    steps = models.ManyToManyField(Stage2Step, related_name='groups', help_text='Steps included in this group')
    is_active = models.BooleanField(default=True, help_text='Whether this group is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 2 Step Group'
        verbose_name_plural = 'Stage 2 Step Groups'
        ordering = ['name']

    def __str__(self):
        return self.name


class QuarterlyReportItemGroup(models.Model):
    """Groups of quarterly report items"""
    name = models.CharField(max_length=255, help_text='Name of the report item group')
    description = models.TextField(blank=True, null=True, help_text='Description of this group')
    report_items = models.ManyToManyField(QuarterlyReportItem, related_name='groups', help_text='Report items included in this group')
    is_active = models.BooleanField(default=True, help_text='Whether this group is active')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quarterly Report Item Group'
        verbose_name_plural = 'Quarterly Report Item Groups'
        ordering = ['name']

    def __str__(self):
        return self.name



class Stage1StepCompletion(models.Model):
    """Completion status for individual Stage 1 steps in reports"""
    stage1_report = models.ForeignKey(Stage1Report, on_delete=models.CASCADE, related_name='step_completions')
    step = models.ForeignKey(Stage1Step, on_delete=models.CASCADE, related_name='completions')
    completed = models.BooleanField(default=False, help_text='Whether this step is completed')
    completed_date = models.DateField(blank=True, null=True, help_text='Date when step was completed')
    evidence_notes = models.TextField(blank=True, null=True, help_text='Notes about evidence provided for this step')
    supporting_document = models.FileField(blank=True, null=True, upload_to='reports/stage1/%Y/%m/', help_text='Supporting document for this step')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 1 Step Completion'
        verbose_name_plural = 'Stage 1 Step Completions'
        unique_together = [('stage1_report', 'step')]

    def clean(self):
        """Validate Stage1StepCompletion fields"""
        if self.completed and not self.completed_date:
            raise ValidationError({'completed_date': 'Completion date is required when step is marked as completed'})

        if self.completed_date and not self.completed:
            raise ValidationError({'completed': 'Step must be marked as completed when completion date is provided'})

    def __str__(self):
        return f"{self.step} - {self.stage1_report}"


class Stage2StepCompletion(models.Model):
    """Completion status for individual Stage 2 steps in reports"""
    stage2_report = models.ForeignKey(Stage2Report, on_delete=models.CASCADE, related_name='step_completions')
    step = models.ForeignKey(Stage2Step, on_delete=models.CASCADE, related_name='completions')
    completed = models.BooleanField(default=False, help_text='Whether this step is completed')
    completed_date = models.DateField(blank=True, null=True, help_text='Date when step was completed')
    evidence_notes = models.TextField(blank=True, null=True, help_text='Notes about evidence provided for this step')
    supporting_document = models.FileField(blank=True, null=True, upload_to='reports/stage2/%Y/%m/', help_text='Supporting document for this step')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stage 2 Step Completion'
        verbose_name_plural = 'Stage 2 Step Completions'
        unique_together = [('stage2_report', 'step')]

    def clean(self):
        """Validate Stage2StepCompletion fields"""
        if self.completed and not self.completed_date:
            raise ValidationError({'completed_date': 'Completion date is required when step is marked as completed'})

        if self.completed_date and not self.completed:
            raise ValidationError({'completed': 'Step must be marked as completed when completion date is provided'})

    def __str__(self):
        return f"{self.step} - {self.stage2_report}"


class QuarterlyReportItemEntry(models.Model):
    """Entry values for quarterly report items"""
    quarterly_report = models.ForeignKey(QuarterlyReport, on_delete=models.CASCADE, related_name='item_entries')
    report_item = models.ForeignKey(QuarterlyReportItem, on_delete=models.CASCADE, related_name='entries')
    value = models.JSONField(blank=True, null=True, help_text='Value for this report item entry')
    supporting_document = models.FileField(blank=True, null=True, upload_to='reports/quarterly/%Y/%m/', help_text='Supporting document for this entry')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quarterly Report Item Entry'
        verbose_name_plural = 'Quarterly Report Item Entries'
        unique_together = [('quarterly_report', 'report_item')]

    def __str__(self):
        return f"{self.report_item} - {self.quarterly_report}"


class MonthlyTrackerEntry(models.Model):
    """Entry values for monthly tracker items"""
    monthly_tracker = models.ForeignKey(MonthlyTracker, on_delete=models.CASCADE, related_name='entries')
    tracker_item = models.ForeignKey(MonthlyTrackerItem, on_delete=models.CASCADE, related_name='entries')
    value = models.JSONField(blank=True, null=True, help_text='Value for this tracker item entry')
    supporting_document = models.FileField(blank=True, null=True, upload_to='reports/monthly_tracker/%Y/%m/', help_text='Supporting document for this entry')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Monthly Tracker Entry'
        verbose_name_plural = 'Monthly Tracker Entries'
        unique_together = [('monthly_tracker', 'tracker_item')]

    def __str__(self):
        return f"{self.tracker_item} - {self.monthly_tracker}"



# Signals for automation
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=StageReport)
def update_project_state(sender, instance, **kwargs):
    project = instance.funding_schedule.projects.first()  # Assuming one project per schedule
    if project:
        if instance.acceptance_date:
            if instance.stage == 1:
                project.state = "commenced"
            elif instance.stage == 2:
                project.state = "completed"
        else:
            if instance.stage == 2:
                project.state = "under_construction"
        project.save()