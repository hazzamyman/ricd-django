from django.db import models
from django.contrib.auth.models import Group, User

from .councils_models import Council


class Profile(models.Model):
    """
    User profile extending Django's User with council assignment.
    """
    class OfficerRole(models.TextChoices):
        OFFICER = 'OFFICER', 'Officer'
        MANAGER = 'MANAGER', 'Manager'
        COUNCIL_USER = 'COUNCIL_USER', 'Council User'
        COUNCIL_MANAGER = 'COUNCIL_MANAGER', 'Council Manager'
        READ_ONLY = 'READ_ONLY', 'Read Only'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    council = models.ForeignKey(Council, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)
    officer_role = models.CharField(max_length=30, choices=OfficerRole.choices, blank=True, help_text="FNC role for the officer")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.council.name if self.council else 'No Council'}"


class GroupPermission(models.Model):
    """
    Extended permission group for FNC system.
    Provides additional metadata beyond Django's default Group.
    """
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='fnc_permissions')

    class GroupType(models.TextChoices):
        OFFICER = 'OFFICER', 'Officer'
        MANAGER = 'MANAGER', 'Manager'
        COUNCIL_USER = 'COUNCIL_USER', 'Council User'
        COUNCIL_MANAGER = 'COUNCIL_MANAGER', 'Council Manager'
        READ_ONLY = 'READ_ONLY', 'Read Only'

    group_type = models.CharField(max_length=30, choices=GroupType.choices)
    description = models.TextField(blank=True)
    can_approve_reports = models.BooleanField(default=False)
    can_approve_payments = models.BooleanField(default=False)
    can_manage_councils = models.BooleanField(default=False)
    can_manage_programs = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.group.name} ({self.get_group_type_display()})"

    def save(self, *args, **kwargs):
        if not self.group_type and self.group.name:
            name_lower = self.group.name.lower()
            if 'manager' in name_lower and 'council' not in name_lower:
                self.group_type = self.GroupType.MANAGER
                self.can_approve_reports = True
                self.can_approve_payments = True
            elif 'officer' in name_lower or 'fnc' in name_lower:
                self.group_type = self.GroupType.OFFICER
            elif 'council manager' in name_lower:
                self.group_type = self.GroupType.COUNCIL_MANAGER
            elif 'council' in name_lower:
                self.group_type = self.GroupType.COUNCIL_USER
            elif 'read' in name_lower or 'audit' in name_lower or 'finance' in name_lower:
                self.group_type = self.GroupType.READ_ONLY

        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """
    Singleton (pk=1) holding site-wide config that RICD managers can edit
    at runtime without a deployment.
    """
    reports_email = models.EmailField(
        default='reports@ricd.qld.gov.au',
        help_text='Email address that quarterly-report submission emails are addressed to.',
    )
    notifications_from_email = models.EmailField(
        default='noreply@ricd.qld.gov.au',
        help_text='"From" address used for automated notification emails sent by the system.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site settings'
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return 'Site settings'

    @classmethod
    def get(cls):
        """Return the singleton row, creating it with defaults if it doesn't exist yet."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
