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

    council = models.ForeignKey('councils.Council', related_name='projects', on_delete=models.CASCADE, db_index=True)
    program = models.ForeignKey('programs.Program', related_name='projects', on_delete=models.CASCADE, db_index=True)
    project_type = models.CharField(max_length=10, choices=Type.choices, default=Type.DWELLING, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    funding_schedule = models.ForeignKey(
        'funding.FundingSchedule',
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
    dwelling_status = models.CharField(max_length=4, choices=DwellingStatus.choices, default=DwellingStatus.PROSPECTIVE, db_index=True)
    status_flag = models.CharField(max_length=2, choices=StatusFlag.choices, default=StatusFlag.ON_TRACK, db_index=True)

    land_parcels = models.ManyToManyField('land_infra.LandTenure', related_name='projects', blank=True)
    
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
        'land_infra.DevelopmentApplication',
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
    
    # Lease fields
    lease_signed_date = models.DateField(null=True, blank=True, help_text="Date lease was signed (only for non-registered housing providers)")
    
    # Post-completion fields
    completion_date = models.DateField(null=True, blank=True)
    handover_checklist_link = models.URLField(blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:project_detail', args=[self.id])

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
        from apps.funding.models import ProjectStateLog
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
    
    def active_funding_schedule(self):
        """Returns the ACTIVE funding schedule for this project (from reverse relation)"""
        fs_list = self.funding_schedules.filter(status='ACTIVE')
        return fs_list.first() if fs_list else None
    
    @property
    def funding_schedule(self):
        """Returns the funding schedule this project is linked to (from reverse relation)"""
        return self.active_funding_schedule
    
    def get_inherited_dates(self):
        """Returns dates from FundingSchedule if project has no dates set"""
        fs = self.funding_schedule
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
        from apps.funding.models import ProjectStateLog
        return ProjectStateLog.objects.filter(
            project=self,
            new_state=self.State.FUNDED,
            reason__icontains='funding approval'
        ).exists()


class Comment(models.Model):
    """Project comments with visibility control"""
    
    class Visibility(models.TextChoices):
        ALL = 'ALL', 'All Users'
        FNC_ONLY = 'FNC_ONLY', 'FNC Users Only'
        COUNCIL_ONLY = 'COUNCIL_ONLY', 'Council Users Only'
        PROJECT_TEAM = 'PROJECT_TEAM', 'Project Team Only'
    
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.ALL)
    is_internal = models.BooleanField(default=False, help_text="Internal notes not visible to council")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.project.name}"
    
    def can_view(self, user):
        """Check if user can view this comment"""
        if self.visibility == self.Visibility.ALL:
            return True
        if user.is_superuser:
            return True
        # Check user's groups
        user_groups = set(user.groups.values_list('name', flat=True))
        if self.visibility == self.Visibility.FNC_ONLY:
            return any('FNC' in g for g in user_groups)
        if self.visibility == self.Visibility.COUNCIL_ONLY:
            return any('Council' in g for g in user_groups)
        if self.visibility == self.Visibility.PROJECT_TEAM:
            # Project team = same council
            return user.profile.council == self.project.council if hasattr(user, 'profile') else False
        return False
