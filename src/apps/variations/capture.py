from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone

from apps.projects.models import Project
from apps.addresses.models import Address
from apps.works.models import Work
from apps.funding.models import FundingSchedule
from apps.payments.models import Payment
from .models import (
    Variation, ProjectChangeLog, VariationFundingSchedule,
    VariationContactDetails, VariationDateChange, VariationScopeChange,
    VariationLandChange, VariationFundingChange, VariationReportingChange
)


def create_draft_variation_for_project(project, variation_option=None):
    """
    Create a draft variation for a project that has an active funding schedule.
    This is typically called when a project becomes active or when changes are detected.
    """
    from apps.funding.models import FundingSchedule
    
    # Get active funding schedules for this project
    funding_schedules = FundingSchedule.objects.filter(project=project)
    
    if not funding_schedules.exists():
        return None
    
    # Use the first funding schedule or find the "active" one
    funding_schedule = funding_schedules.first()
    
    # Check if there's already a draft variation
    existing_draft = Variation.objects.filter(
        funding_schedule=funding_schedule,
        status=Variation.Status.DRAFT
    ).first()
    
    if existing_draft:
        return existing_draft
    
    # Create new draft variation
    variation = Variation.objects.create(
        funding_schedule=funding_schedule,
        variation_option=variation_option,
        status=Variation.Status.DRAFT,
        description=f"Auto-created draft variation for {project.name}"
    )
    variation.projects.add(project)
    
    return variation


def capture_project_change(project, change_source, source_id, field_name, old_value, new_value):
    """
    Capture a change from a project that may require a variation.
    Only captures changes for projects with active funding schedules.
    """
    # Only capture for projects that are not in PROSPECTIVE state
    if project.state == Project.State.PROSPECTIVE:
        return None
    
    # Check if project has active funding
    if not project.funding_schedules.exists():
        return None
    
    change_log = ProjectChangeLog.objects.create(
        project=project,
        change_source=change_source,
        source_id=source_id,
        field_name=field_name,
        old_value=str(old_value) if old_value else '',
        new_value=str(new_value) if new_value else ''
    )
    
    return change_log


def get_pending_changes_for_project(project):
    """Get all uncaptured changes for a project"""
    return ProjectChangeLog.objects.filter(
        project=project,
        is_captured=False
    ).order_by('-created_at')


def add_change_to_variation(change_log, variation):
    """Add a captured change to a variation and mark as captured"""
    change_log.variation = variation
    change_log.is_captured = True
    change_log.captured_at = timezone.now()
    change_log.save()
    
    # Also create a VariationItem for backward compatibility
    from .models import VariationItem
    VariationItem.objects.create(
        variation=variation,
        change_type=VariationItem.ChangeType.OTHER,
        field_name=change_log.field_name,
        old_value=change_log.old_value,
        new_value=change_log.new_value,
        description=f"Source: {change_log.get_change_source_display()}"
    )


def create_variation_from_changes(project, variation_option, created_by=None):
    """
    Create a complete variation from pending changes for a project.
    This is the main entry point for creating variations.
    """
    pending_changes = get_pending_changes_for_project(project)
    
    if not pending_changes.exists():
        return None
    
    # Create the variation
    variation = create_draft_variation_for_project(project, variation_option)
    
    if not variation:
        return None
    
    if created_by:
        variation.created_by = created_by
        variation.save()
    
    # Add all pending changes to the variation
    for change in pending_changes:
        add_change_to_variation(change, variation)
    
    return variation


# Signal handlers to automatically capture changes

@receiver(pre_save, sender=Project)
def capture_project_pre_save(sender, instance, **kwargs):
    """Capture changes to project fields"""
    if instance.pk:
        try:
            old_instance = Project.objects.get(pk=instance.pk)
            
            # Track specific important fields
            fields_to_track = [
                'name', 'funding_schedule_number', 'start_date', 
                'funding_approval_date', 'stage1_target_date', 'stage2_target_date',
                'stage1_sunset_date', 'stage2_sunset_date', 'state', 'status_flag',
                'completion_date', 'warranty_end_date', 'mincor_reference'
            ]
            
            for field_name in fields_to_track:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)
                
                if old_value != new_value:
                    capture_project_change(
                        instance, 
                        ProjectChangeLog.ChangeSource.PROJECT,
                        instance.pk,
                        field_name,
                        old_value,
                        new_value
                    )
        except Project.DoesNotExist:
            pass


@receiver(pre_save, sender=Address)
def capture_address_pre_save(sender, instance, **kwargs):
    """Capture changes to addresses"""
    if instance.pk:
        try:
            old_instance = Address.objects.get(pk=instance.pk)
            
            fields_to_track = ['street', 'suburb', 'lot', 'plan', 'residence_plc_ref']
            
            for field_name in fields_to_track:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)
                
                if str(old_value) != str(new_value):
                    capture_project_change(
                        instance.project,
                        ProjectChangeLog.ChangeSource.ADDRESS,
                        instance.pk,
                        field_name,
                        old_value,
                        new_value
                    )
        except Address.DoesNotExist:
            pass


@receiver(pre_save, sender=Work)
def capture_work_pre_save(sender, instance, **kwargs):
    """Capture changes to works"""
    if instance.pk:
        try:
            old_instance = Work.objects.get(pk=instance.pk)
            
            fields_to_track = ['work_type', 'quantity', 'estimated_cost', 'status']
            
            for field_name in fields_to_track:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)
                
                if str(old_value) != str(new_value):
                    capture_project_change(
                        instance.project,
                        ProjectChangeLog.ChangeSource.WORK,
                        instance.pk,
                        field_name,
                        old_value,
                        new_value
                    )
        except Work.DoesNotExist:
            pass


@receiver(pre_save, sender=FundingSchedule)
def capture_funding_schedule_pre_save(sender, instance, **kwargs):
    """Capture changes to funding schedules"""
    if instance.pk:
        try:
            old_instance = FundingSchedule.objects.get(pk=instance.pk)
            
            fields_to_track = ['amount', 'contingency', 'payment_split']
            
            for field_name in fields_to_track:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)
                
                if str(old_value) != str(new_value):
                    capture_project_change(
                        instance.project,
                        ProjectChangeLog.ChangeSource.FUNDING_SCHEDULE,
                        instance.pk,
                        field_name,
                        old_value,
                        new_value
                    )
        except FundingSchedule.DoesNotExist:
            pass


@receiver(pre_save, sender=Payment)
def capture_payment_pre_save(sender, instance, **kwargs):
    """Capture changes to payments"""
    if instance.pk:
        try:
            old_instance = Payment.objects.get(pk=instance.pk)
            
            fields_to_track = ['amount', 'percentage', 'payment_type', 'status', 'release_date']
            
            for field_name in fields_to_track:
                old_value = getattr(old_instance, field_name, None)
                new_value = getattr(instance, field_name, None)
                
                if str(old_value) != str(new_value):
                    capture_project_change(
                        instance.project,
                        ProjectChangeLog.ChangeSource.PAYMENT,
                        instance.pk,
                        field_name,
                        old_value,
                        new_value
                    )
        except Payment.DoesNotExist:
            pass
