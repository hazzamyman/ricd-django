"""
Django Signals for RICD business rules.

Handles:
- WorkflowAction auto-generation on state changes
- AuditLog auto-generation on financial table changes
- FundingSchedule lifecycle automation (EXECUTED, ACTIVE, SUPERSEDED)
- BriefFinancialApproval → FundingSchedule creation enforcement
"""
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone


FINANCIAL_MODELS = {
    'fundingagreement', 'fundingschedule', 'variation', 'variationitem',
    'workfunding', 'payment', 'fundingnotice', 'expenseclaim',
    'brieffinancialapproval', 'approval', 'report', 'stage',
}


@receiver(pre_save)
def audit_log_pre_save(sender, instance, **kwargs):
    """Capture pre-save state for AuditLog."""
    if sender._meta.model_name.lower() not in FINANCIAL_MODELS:
        return
    if not instance.pk:
        return
    from decimal import Decimal
    try:
        old = sender._meta.model.objects.get(pk=instance.pk)
        instance._pre_save_state = {}
        for field in instance._meta.fields:
            fname = field.name
            if hasattr(old, fname):
                val = getattr(old, fname)
                if hasattr(val, 'pk'):
                    val = val.pk
                elif isinstance(val, Decimal):
                    val = str(val)
                elif isinstance(val, (set, frozenset)):
                    val = list(val)
                instance._pre_save_state[fname] = val
    except sender.DoesNotExist:
        instance._pre_save_state = {}


@receiver(post_save)
def audit_log_post_save(sender, instance, created, **kwargs):
    """Create AuditLog records after save."""
    model_name = sender._meta.model_name.lower()
    if model_name not in FINANCIAL_MODELS:
        return
    
    action = 'CREATE' if created else 'UPDATE'
    old_values = getattr(instance, '_pre_save_state', {})
    
    try:
        from apps.core.business_rules import log_audit
        log_audit(
            user=getattr(instance, '_current_user', None),
            action=action,
            instance=instance,
            old_values=old_values if not created else {}
        )
    except Exception:
        pass


@receiver(pre_delete)
def audit_log_pre_delete(sender, instance, **kwargs):
    """Create AuditLog records before delete."""
    model_name = sender._meta.model_name.lower()
    if model_name not in FINANCIAL_MODELS:
        return
    from decimal import Decimal
    old_values = {}
    for f in instance._meta.fields:
        val = getattr(instance, f.name, None)
        if hasattr(val, 'pk'):
            val = val.pk
        elif isinstance(val, Decimal):
            val = str(val)
        elif isinstance(val, (set, frozenset)):
            val = list(val)
        old_values[f.name] = val
    
    try:
        from apps.core.business_rules import log_audit
        log_audit(
            user=getattr(instance, '_current_user', None),
            action='DELETE',
            instance=instance,
            old_values=old_values
        )
    except Exception:
        pass


# ============================================================================
# WorkflowAction: State change tracking
# ============================================================================

STATE_CHANGE_MODELS = {
    'fundingschedule': {
        'field': 'status',
        'app': 'funding',
        'label': 'FundingSchedule',
    },
    'variation': {
        'field': 'status',
        'app': 'variations',
        'label': 'VariationDeed',
    },
    'payment': {
        'field': 'status',
        'app': 'payments',
        'label': 'Payment',
    },
    'expenseclaim': {
        'field': 'status',
        'app': 'funding',
        'label': 'ExpenseClaim',
    },
    'stage': {
        'field': 'status',
        'app': 'stages',
        'label': 'ProjectStage',
    },
    'fundingnotice': {
        'field': 'status',
        'app': 'funding',
        'label': 'FundingNotice',
    },
    'brieffinancialapproval': {
        'field': 'status',
        'app': 'funding',
        'label': 'BriefFinancialApproval',
    },
    'approval': {
        'field': 'status',
        'app': 'funding',
        'label': 'Approval',
    },
}


@receiver(pre_save)
def track_state_changes(sender, instance, **kwargs):
    """Track state changes and fire lifecycle triggers."""
    model_name = sender._meta.model_name.lower()
    
    if model_name not in STATE_CHANGE_MODELS:
        return
    
    config = STATE_CHANGE_MODELS[model_name]
    state_field = config['field']
    
    if not instance.pk:
        # New record - log creation
        instance._state_action_type = 'CREATE'
        return
    
    try:
        old = sender._meta.model.objects.get(pk=instance.pk)
        old_value = getattr(old, state_field)
        new_value = getattr(instance, state_field)
        
        if old_value != new_value:
            instance._state_action_type = f'{old_value}_TO_{new_value}'
            instance._state_old_value = old_value
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def emit_workflow_action(sender, instance, created, **kwargs):
    """Create WorkflowAction on state changes."""
    model_name = sender._meta.model_name.lower()
    
    if model_name not in STATE_CHANGE_MODELS:
        return
    
    config = STATE_CHANGE_MODELS[model_name]
    
    try:
        from apps.core.business_rules import log_workflow_action
        from apps.funding.models import WorkflowAction
        
        user = getattr(instance, '_current_user', None)
        
        if created:
            action_type = 'CREATE'
        elif hasattr(instance, '_state_action_type') and instance._state_action_type:
            action_type = 'UPDATE'
        else:
            return
        
        if action_type == 'UPDATE':
            old_state = getattr(instance, '_state_old_value', None)
            new_state = getattr(instance, config['field'], None)
            
            if model_name == 'payment' and new_state == 'RELEASED':
                action = WorkflowAction.ActionType.RELEASE_PAYMENT
            elif model_name == 'variation' and new_state == 'EXECUTED':
                action = WorkflowAction.ActionType.EXECUTE_VARIATION
            elif old_state == 'PENDING' and new_state == 'APPROVED':
                action = 'APPROVE'
            elif old_state == 'PENDING' and new_state == 'REJECTED':
                action = 'REJECT'
            else:
                action = 'UPDATE'
        else:
            action = 'CREATE'
        
        log_workflow_action(
            entity_type=config['label'],
            entity_id=instance.pk,
            action_type=action,
            user=user,
            metadata={'state_field': config['field']}
        )
        
        _fire_lifecycle_triggers(sender, instance, model_name)
    except Exception:
        pass


def _fire_lifecycle_triggers(sender, instance, model_name):
    """Fire domain-specific lifecycle triggers after state changes."""
    from apps.core.business_rules import (
        trigger_funding_schedule_executed,
        trigger_funding_schedule_active,
    )
    
    if model_name == 'variation':
        if instance.status == 'EXECUTED':
            for fs in instance.funding_schedules.all():
                trigger_funding_schedule_executed(fs)
    
    if model_name == 'payment':
        if instance.status == 'APPROVED':
            trigger_funding_schedule_active(instance.funding_schedule)
    
    if model_name == 'fundingschedule':
        if instance.status == 'READY_FOR_EXECUTION':
            trigger_funding_schedule_executed(instance)
        if instance.status == 'EXECUTED':
            trigger_funding_schedule_active(instance)


# ============================================================================
# Project state changes → WorkflowAction
# ============================================================================

@receiver(pre_save)
def track_project_state(sender, instance, **kwargs):
    if sender._meta.model_name != 'Project':
        return
    if not instance.pk:
        return
    try:
        old = Project.objects.get(pk=instance.pk)
        instance._old_project_state = old.state
        instance._old_project_type = old.project_type
    except Exception:
        pass


@receiver(post_save)
def emit_project_workflow_action(sender, instance, created, **kwargs):
    if sender._meta.model_name != 'Project':
        return
    try:
        from apps.core.business_rules import log_workflow_action
    except Exception:
        return
    try:
        if created:
            log_workflow_action('Project', instance.pk, 'CREATE', user=None)
        elif hasattr(instance, '_old_project_state'):
            old_state = instance._old_project_state
            new_state = instance.state
            old_type = getattr(instance, '_old_project_type', None)
            new_type = instance.project_type
            
            log_workflow_action(
                'Project', instance.pk, 'UPDATE',
                user=None,
                metadata={'previous_state': old_state, 'new_state': new_state, 'old_type': old_type, 'new_type': new_type}
            )
    except Exception:
        pass