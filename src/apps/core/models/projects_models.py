from django.db import models
from django.utils import timezone
from django.urls import reverse

from apps.core.utils import CURRENT_FINANCIAL_YEAR, FINANCIAL_YEAR_CHOICES


class Project(models.Model):
    class Type(models.TextChoices):
        DWELLING = 'DWELLING', 'Dwelling'
        LAND = 'LAND', 'Land'

    class State(models.TextChoices):
        PROSPECTIVE = 'PROS', 'Prospective'
        PROGRAMMED = 'PROG', 'Programmed'
        FUNDED = 'FUND', 'Funded'
        COMMENCED = 'COMM', 'Commenced'
        UNDER_CONSTRUCTION = 'UC', 'Under Construction'
        COMPLETED = 'COMP', 'Completed'

    class DwellingStatus(models.TextChoices):
        PROSPECTIVE = 'PROS', 'Prospective'
        PROGRAMMED = 'PROG', 'Programmed'
        FUNDED = 'FUND', 'Funded'
        COMMENCED = 'COMM', 'Commenced'
        WORKS_UNDERWAY = 'WU', 'Works Underway'
        COMPLETED = 'COMP', 'Completed'

    class StatusFlag(models.TextChoices):
        ON_TRACK = 'ON', 'On track'
        LATE = 'LA', 'Late'
        OVERDUE = 'OV', 'Overdue'

    council = models.ForeignKey('Council', related_name='projects', on_delete=models.CASCADE, db_index=True)
    program = models.ForeignKey('Program', related_name='projects', on_delete=models.CASCADE, db_index=True)
    lead_officer = models.ForeignKey(
        'auth.User', related_name='led_projects',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="FNC officer for this project. Overrides Council.lead_officer "
                  "(use effective_lead_officer for resolved value).",
    )
    project_type = models.CharField(max_length=10, choices=Type.choices, default=Type.DWELLING, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    funding_schedule = models.ForeignKey(
        'FundingSchedule',
        related_name='projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Funding schedule linked to this project"
    )
    financial_year = models.CharField(
        max_length=9,
        choices=FINANCIAL_YEAR_CHOICES,
        default='',
        blank=True,
        help_text="Expected financial year for funding (add later when funding confirmed)"
    )
    start_date = models.DateField(null=True, blank=True)
    funding_approval_date = models.DateField(null=True, blank=True, help_text="Date funding was approved")
    stage1_target_date = models.DateField(null=True, blank=True)
    stage2_target_date = models.DateField(null=True, blank=True)
    stage1_sunset_date = models.DateField(null=True, blank=True)
    stage2_sunset_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=4, choices=State.choices, default=State.PROSPECTIVE, db_index=True)
    dwelling_status = models.CharField(
        max_length=4,
        choices=DwellingStatus.choices,
        default=None,
        null=True,
        blank=True,
        db_index=True
    )
    status_flag = models.CharField(max_length=2, choices=StatusFlag.choices, default=StatusFlag.ON_TRACK, db_index=True)

    land_parcels = models.ManyToManyField('LandTenure', related_name='projects', blank=True)
    
    # Land-specific fields (from LandProject migration)
    parent_land_project = models.ForeignKey(
        'self',
        related_name='child_dwellings',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to parent LAND project this dwelling is built on (DWELLING only)"
    )
    development_application = models.ForeignKey(
        'DevelopmentApplication',
        related_name='primary_project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Development application for land projects"
    )
    infra_water_assessment = models.TextField(
        blank=True,
        help_text="Is there sufficient water infrastructure? What is the connection capacity?"
    )
    infra_electricity_assessment = models.TextField(
        blank=True,
        help_text="Is there sufficient electricity infrastructure? What is the transformer capacity?"
    )
    infra_sewerage_assessment = models.TextField(
        blank=True,
        help_text="Is there sufficient sewerage infrastructure? What is the treatment capacity?"
    )
    infra_comments = models.TextField(blank=True)
    
    # Stage item group assignments (pre-pick which template applies)
    stage1_item_group = models.ForeignKey(
        'StageItemGroup',
        related_name='stage1_projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Template group of Stage 1 items for this project's stage report",
    )
    stage2_item_group = models.ForeignKey(
        'StageItemGroup',
        related_name='stage2_projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Template group of Stage 2 items for this project's stage report",
    )
    quarterly_report_item_group = models.ForeignKey(
        'QuarterlyReportItemGroup',
        related_name='projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Template group of Quarterly Report items for this project's quarterly reports",
    )

    # Lease fields
    lease_signed_date = models.DateField(null=True, blank=True, help_text="Date lease was signed (only for non-registered housing providers)")
    
    # Staff assignment
    principal_officer = models.ForeignKey(
        'auth.User',
        related_name='principal_projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="RICD Principal Officer responsible for this project"
    )
    senior_officer = models.ForeignKey(
        'auth.User',
        related_name='senior_projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="RICD Senior Officer with carriage of this project"
    )

    # Post-completion fields
    completion_date = models.DateField(null=True, blank=True)
    handover_checklist_link = models.URLField(blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)

    # Financial year tracking (commenced captured via financial_year above)
    financial_year_completed = models.CharField(
        max_length=9, choices=FINANCIAL_YEAR_CHOICES, blank=True, default='',
        help_text="Financial year in which the project was completed",
    )

    # External system references
    sap_ion = models.CharField(
        max_length=50, blank=True,
        help_text="SAP Internal Order Number",
    )

    # Optionally-visible reference fields (kept for import/reporting; hidden in UI by default)
    cli_no = models.CharField(
        max_length=50, blank=True,
        help_text="Client reference number (hidden in UI by default — toggle via Advanced section)",
    )
    initial_caa_date = models.DateField(
        null=True, blank=True,
        help_text="Initial date of CAA (hidden in UI by default — toggle via Advanced section)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ui:project_detail', args=[self.id])

    def transition_state(self, new_state, changed_by=None, reason=''):
        """State transition method with validation and logging."""
        if new_state not in self.State.values:
            raise ValueError(f"Invalid state: {new_state}")
        
        # Define valid transitions
        valid_transitions = {
            self.State.PROSPECTIVE: [self.State.PROGRAMMED, self.State.FUNDED],
            self.State.PROGRAMMED: [self.State.FUNDED, self.State.COMMENCED, self.State.PROSPECTIVE],
            self.State.FUNDED: [self.State.COMMENCED, self.State.UNDER_CONSTRUCTION],
            self.State.COMMENCED: [self.State.UNDER_CONSTRUCTION, self.State.COMPLETED],
            self.State.UNDER_CONSTRUCTION: [self.State.COMPLETED],
            self.State.COMPLETED: [],  # No transitions from completed
        }
        
        # Check if transition is valid
        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")
        
        # Create log entry
        from apps.core.models import ProjectStateLog
        ProjectStateLog.objects.create(
            project=self,
            previous_state=self.state,
            new_state=new_state,
            changed_by=changed_by,
            reason=reason
        )
        
        # Update state
        self.state = new_state
        self.save()
    
    @property
    def lease_required(self):
        """Returns True if lease is required (council is NOT a registered housing provider)"""
        return not self.council.is_registered_housing_provider
    
    @property
    def effective_start_date(self):
        """Returns the effective start date for duration calculations"""
        if self.funding_approval_date:
            return self.funding_approval_date
        return self.start_date

    @property
    def financial_approvals(self):
        """BFAs that include this project (compat shim — actual link is via BFAItem)."""
        from apps.core.models import BriefFinancialApproval
        return BriefFinancialApproval.objects.filter(items__project=self).distinct()

    def bfa_program_ratios(self, *, approved_only=True):
        """Return a dict {program_id: Decimal ratio (0..1)} for this project.

        Ratios are derived from BriefFinancialApprovalItem rows
        (item.total = funding + contingency) grouped by program. Used for
        Payment co-funding splits at RELEASED time (see PaymentAllocation).

        If `approved_only` is True (default), only items on APPROVED BFAs count.
        Returns `{}` if no qualifying items — callers fall back to single-program
        behaviour (`{self.program_id: 1}`).
        """
        from decimal import Decimal
        from apps.core.models import BriefFinancialApprovalItem
        qs = BriefFinancialApprovalItem.objects.filter(project=self)
        if approved_only:
            qs = qs.filter(bfa__status='APPROVED')
        totals = {}
        grand = Decimal('0')
        for item in qs:
            t = (item.funding_amount or Decimal('0')) + (item.contingency_amount or Decimal('0'))
            if t <= 0:
                continue
            prog_id = item.program_id or self.program_id
            if prog_id is None:
                continue
            totals[prog_id] = totals.get(prog_id, Decimal('0')) + t
            grand += t
        if grand == 0:
            return {}
        return {pid: (amt / grand).quantize(Decimal('0.000001')) for pid, amt in totals.items()}

    # ----- Practical Completion + Handover aggregates (derived from child Works)
    #
    # Convention (Option C): Project doesn't store these dates directly. They
    # live on each Work; Project shows the LATEST work's date (the "all works
    # complete" date), unless any work hasn't reached that milestone yet, in
    # which case the actual aggregate is None — i.e. the project isn't there
    # yet. Forecast aggregates ignore nulls (best-effort projection).

    def _work_date_aggregate(self, field_name):
        """max(work.<field_name>) only if EVERY work has it set; else None."""
        works = list(self.works.all())
        if not works:
            return None
        vals = [getattr(w, field_name) for w in works]
        if any(v is None for v in vals):
            return None
        return max(vals)

    def _work_date_forecast(self, field_name):
        """max(work.<field_name>) ignoring nulls; None if every value is null."""
        works = list(self.works.all())
        if not works:
            return None
        vals = [v for v in (getattr(w, field_name) for w in works) if v is not None]
        return max(vals) if vals else None

    @property
    def practical_completion_date(self):
        """Latest actual PC across all works, or None if any work hasn't PC'd yet."""
        return self._work_date_aggregate('practical_completion_date')

    @property
    def forecast_practical_completion_date(self):
        """Latest forecast PC across all works (whichever finishes last)."""
        return self._work_date_forecast('forecast_practical_completion_date')

    @property
    def handover_date(self):
        """Latest actual Handover across all works, or None if any work hasn't handed over yet."""
        return self._work_date_aggregate('handover_date')

    @property
    def forecast_handover_date(self):
        """Latest forecast Handover across all works."""
        return self._work_date_forecast('forecast_handover_date')

    @property
    def is_practically_completed(self):
        """True when every Work has a recorded practical_completion_date."""
        return self.practical_completion_date is not None

    @property
    def effective_lead_officer(self):
        """FNC officer responsible for this project — own override, else council default."""
        return self.lead_officer or (self.council.lead_officer if self.council_id else None)

    @property
    def pc_breaches_sunset(self):
        """True when forecast PC is >30 days past Stage 2 sunset (warning, not blocker)."""
        from datetime import timedelta
        forecast = self.forecast_practical_completion_date
        if forecast is None or self.stage2_sunset_date is None:
            return False
        return forecast > self.stage2_sunset_date + timedelta(days=30)

    @property
    def dates_in_sync(self):
        """True when no FundingSchedule is linked, or all date fields match the FS.

        Project edits never propagate back to the FS, so editing Project dates
        after the FS was saved will turn this False (and surface a warning).
        """
        fs = self.funding_schedule
        if fs is None:
            return True
        for f in ('start_date', 'stage1_target_date', 'stage1_sunset_date',
                  'stage2_target_date', 'stage2_sunset_date'):
            if getattr(self, f) != getattr(fs, f):
                return False
        return True
    
    def active_funding_schedule(self):
        """Returns the ACTIVE funding schedule for this project (from reverse relation)"""
        fs_list = self.funding_schedules.filter(status='ACTIVE')
        return fs_list.first() if fs_list else None
    
    @property
    def active_funding_schedule_obj(self):
        """Returns the active FundingSchedule for this project (from reverse relation)."""
        return self.active_funding_schedule()
    
    def get_inherited_dates(self):
        """Returns dates from FundingSchedule if project has no dates set"""
        fs = self.active_funding_schedule()
        if fs:
            return {
                'stage1_target': fs.stage1_target_date,
                'stage2_target': fs.stage2_target_date,
                'stage1_sunset': fs.stage1_sunset_date,
                'stage2_sunset': fs.stage2_sunset_date,
            }
        return None
    
    def get_works_description(self):
        """Returns concatenated works description from Project.works"""
        works = self.works.all()
        if works:
            desc_parts = []
            for w in works:
                if w.description:
                    desc_parts.append(w.description)
                elif w.work_type_other:
                    desc_parts.append(w.work_type_other)
                elif w.work_type:
                    desc_parts.append(str(w.work_type))
            return "; ".join(desc_parts)
        return ""
    
    @property
    def had_approved_funding_approval(self):
        """Check if project had an approved Funding Approval Brief"""
        from apps.core.models import ProjectStateLog
        return ProjectStateLog.objects.filter(
            project=self,
            new_state=self.State.FUNDED,
            reason__icontains='funding approval'
        ).exists()
