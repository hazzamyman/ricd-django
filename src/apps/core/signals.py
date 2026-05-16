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
from apps.core.middleware import get_current_user


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
    user = getattr(instance, '_current_user', None) or get_current_user()

    try:
        from apps.core.business_rules import log_audit
        log_audit(
            user=user,
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
    
    user = getattr(instance, '_current_user', None) or get_current_user()
    try:
        from apps.core.business_rules import log_audit
        log_audit(
            user=user,
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
        from apps.core.models import WorkflowAction
        
        user = getattr(instance, '_current_user', None) or get_current_user()

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
            # Fetch fresh from DB — the in-memory FK may carry a stale status
            from apps.core.models import FundingSchedule
            try:
                fs = FundingSchedule.objects.get(pk=instance.funding_schedule_id)
                trigger_funding_schedule_active(fs)
            except FundingSchedule.DoesNotExist:
                pass

    if model_name == 'fundingschedule':
        if instance.status == 'READY_FOR_EXECUTION':
            trigger_funding_schedule_executed(instance)
        # EXECUTED → ACTIVE is triggered only by Payment APPROVED, not automatically


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


# ============================================================================
# GOVERNANCE: Payment Approval Workflow
# ============================================================================

@receiver(post_save)
def auto_create_payment_approval(sender, instance, created, **kwargs):
    """
    Governance Signal 1: Payment created → create Approval record.
    When a Payment is created, automatically create an Approval record with:
    - approval_type = PAYMENT, status = PENDING
    - required_role = determined by delegation level (amount-based)
    """
    if sender._meta.model_name != 'payment' or not created:
        return
    try:
        from apps.core.models import Approval, Delegation
        amount = instance.amount
        delegation_level = Delegation.get_delegation_level(amount)
        Approval.objects.create(
            entity_type='Payment',
            entity_id=instance.pk,
            approval_type=Approval.ApprovalType.PAYMENT,
            required_role=delegation_level,
            status=Approval.Status.PENDING
        )
    except Exception:
        pass


@receiver(post_save)
def sync_approval_to_payment_status(sender, instance, created, **kwargs):
    """
    Governance Signal 2: Approval approved → approve Payment.
    When an Approval record for a Payment transitions to APPROVED,
    automatically update the Payment status to APPROVED.
    This triggers the FundingSchedule ACTIVE signal.
    """
    if sender._meta.model_name != 'approval':
        return
    approval = instance
    if approval.entity_type != 'Payment' or approval.status != 'APPROVED':
        return
    try:
        from apps.core.models import Payment
        payment = Payment.objects.get(pk=approval.entity_id)
        if payment.status != Payment.Status.APPROVED:
            payment.status = Payment.Status.APPROVED
            payment.save(update_fields=['status', 'updated_at'])
    except Exception:
        pass


@receiver(post_save)
def unlock_next_payment_on_report_approval(sender, instance, created, **kwargs):
    """
    Governance Signal 3: Report/Stage approved → unlock next payment.
    When a Quarterly/Monthly Report or Project Stage transitions to APPROVED,
    unlock the next payment in the FundingSchedule by setting its status to READY.
    """
    model_name = sender._meta.model_name.lower()
    if model_name not in ['stage', 'report']:
        return
    if not hasattr(instance, 'status') or instance.status != 'APPROVED':
        return
    try:
        from apps.core.models import Payment, FundingSchedule
        project = None
        if model_name == 'stage':
            project = instance.project
        elif model_name == 'report':
            project = instance.project
        if not project:
            return
        fs = FundingSchedule.objects.filter(
            project=project,
            status=FundingSchedule.Status.ACTIVE
        ).first()
        if not fs:
            return
        next_payment = Payment.objects.filter(
            funding_schedule=fs,
            status=Payment.Status.PENDING
        ).order_by('payment_type').first()
        if next_payment:
            next_payment.status = Payment.Status.RECOMMENDED
            next_payment.save(update_fields=['status', 'updated_at'])
    except Exception:
        pass