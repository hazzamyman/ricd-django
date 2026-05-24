from django.db import models

from .projects_models import Project


class Contract(models.Model):
    class ContractStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT_TO_COUNCIL = 'SENT', 'Sent to Council'
        EXECUTED = 'EXECUTED', 'Executed'
        VARIED = 'VARIED', 'Varied'
        EXPIRED = 'EXPIRED', 'Expired'
        TERMINATED = 'TERMINATED', 'Terminated'

    project = models.ForeignKey(Project, related_name='contracts', on_delete=models.CASCADE)
    contract_status = models.CharField(max_length=10, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    title = models.CharField(max_length=255)
    document_uri = models.URLField(blank=True, help_text='Windows Share Drive, Sharepoint or OpenDocs link')
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
        return f"Contract: {self.title} ({self.project.name})"


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
