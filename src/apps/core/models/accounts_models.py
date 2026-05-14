from django.db import models
from django.contrib.auth.models import Group, User

from .councils_models import Council


class Profile(models.Model):
    """
    User profile extending Django's User with council assignment.
    """
    class OfficerRole(models.TextChoices):
        PRINCIPAL_OFFICER = 'PRINCIPAL_OFFICER', 'Principal Officer'
        SENIOR_OFFICER = 'SENIOR_OFFICER', 'Senior Officer'
        PROGRAM_OFFICER = 'PROGRAM_OFFICER', 'Program Officer'
        MANAGER = 'MANAGER', 'Manager'
        DIRECTOR = 'DIRECTOR', 'Director'
        COUNCIL_USER = 'COUNCIL_USER', 'Council User'
        COUNCIL_MANAGER = 'COUNCIL_MANAGER', 'Council Manager'
        OTHER = 'OTHER', 'Other'

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
        FNC_USER = 'FNC_USER', 'FNC User'
        FNC_MANAGER = 'FNC_MANAGER', 'FNC Manager'
        COUNCIL_USER = 'COUNCIL_USER', 'Council User'
        COUNCIL_MANAGER = 'COUNCIL_MANAGER', 'Council Manager'
        OTHER_TEAM_USER = 'OTHER_TEAM_USER', 'HPW Other Team User'
        OTHER_TEAM_MANAGER = 'OTHER_TEAM_MANAGER', 'HPW Other Team Manager'

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
            if 'fnc manager' in name_lower:
                self.group_type = self.GroupType.FNC_MANAGER
                self.can_approve_reports = True
                self.can_approve_payments = True
            elif 'fnc user' in name_lower:
                self.group_type = self.GroupType.FNC_USER
            elif 'council manager' in name_lower:
                self.group_type = self.GroupType.COUNCIL_MANAGER
            elif 'council user' in name_lower:
                self.group_type = self.GroupType.COUNCIL_USER
            elif 'other team manager' in name_lower:
                self.group_type = self.GroupType.OTHER_TEAM_MANAGER
            elif 'other team user' in name_lower:
                self.group_type = self.GroupType.OTHER_TEAM_USER

        super().save(*args, **kwargs)
