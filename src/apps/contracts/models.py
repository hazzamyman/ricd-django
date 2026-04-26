from django.db import models


class Contract(models.Model):
    class ProjectType(models.TextChoices):
        DWELLING = 'DWELLING', 'Dwelling/Construction'
        LAND = 'LAND', 'Land/Infrastructure'

    class ContractStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT_TO_COUNCIL = 'SENT', 'Sent to Council'
        EXECUTED = 'EXECUTED', 'Executed'
        VARIED = 'VARIED', 'Varied'
        EXPIRED = 'EXPIRED', 'Expired'
        TERMINATED = 'TERMINATED', 'Terminated'

    project = models.ForeignKey('projects.Project', related_name='contracts', on_delete=models.CASCADE, null=True, blank=True)
    land_project = models.ForeignKey('land_infra.LandProject', related_name='contracts', on_delete=models.CASCADE, null=True, blank=True)
    project_type = models.CharField(max_length=10, choices=ProjectType.choices, default=ProjectType.DWELLING)
    contract_status = models.CharField(max_length=10, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to='contracts/', blank=True)
    sent_to_council_date = models.DateField(null=True, blank=True)
    council_executed_date = models.DateField(null=True, blank=True)
    execution_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        project_name = self.project.name if self.project else (self.land_project.name if self.land_project else 'No Project')
        return f"Contract: {self.title} ({project_name})"

    @property
    def linked_project(self):
        """Returns the linked project (either dwelling or land)"""
        if self.project_type == self.ProjectType.DWELLING:
            return self.project
        return self.land_project


class ContractMeeting(models.Model):
    class MeetingType(models.TextChoices):
        KICKOFF = 'KICKOFF', 'Kick-off Meeting'
        INTERIM = 'INTERIM', 'Interim Meeting'
        CLOSEOUT = 'CLOSEOUT', 'Close-out Meeting'

    contract = models.ForeignKey(Contract, related_name='meetings', on_delete=models.CASCADE)
    meeting_type = models.CharField(max_length=20, choices=MeetingType.choices)
    meeting_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    attendees = models.TextField(blank=True)
    minutes = models.TextField(blank=True)
    action_items = models.TextField(blank=True, help_text="Action items from meeting")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        project_name = self.contract.project.name if self.contract.project else self.contract.land_project.name
        return f"{self.get_meeting_type_display()} - {project_name} ({self.meeting_date})"
