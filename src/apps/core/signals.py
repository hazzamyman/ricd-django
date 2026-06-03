"""
Django Signals for RICD business rules.

Handles:
- WorkflowAction auto-generation on state changes
- AuditLog auto-generation on financial table changes
- FundingSchedule lifecycle automation (EXECUTED, ACTIVE, SUPERSEDED)
- BriefFinancialApproval → FundingSchedule creation enforcement
"""
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
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
    if model_name not in ['stage', 'stagereport', 'report']:
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


# ---------------------------------------------------------------------------
# WorkStep forecast recalculation — fires when a Work's start date changes
# ---------------------------------------------------------------------------

@receiver(post_save, sender='core.Work')
def recalculate_work_forecast(sender, instance, **kwargs):
    """Re-run rolling forecast whenever the Work changes, except when the save
    was itself triggered by the forecast engine writing the computed PC date
    back onto the Work (those saves carry update_fields={pc, handover})."""
    update_fields = kwargs.get('update_fields')
    if update_fields:
        from apps.core.services.workstep_forecast import RECALC_UPDATE_FIELDS
        if set(update_fields).issubset(RECALC_UPDATE_FIELDS):
            return  # this save IS the forecast engine writing back — don't recurse
    if instance.cashflow_method != 'WORKSTEP':
        return
    if not instance.steps.exists():
        return
    try:
        from apps.core.services.workstep_forecast import recalculate_forecast
        recalculate_forecast(instance)
    except Exception:
        pass


@receiver(post_save, sender='core.WorkStep')
def recalculate_on_step_completion(sender, instance, **kwargs):
    """Re-run rolling forecast when a step's actual_completion_date is set."""
    try:
        from apps.core.services.workstep_forecast import recalculate_forecast
        recalculate_forecast(instance.work)
    except Exception:
        pass


def _resync_anchored_payments(project_id):
    """Re-save every milestone-anchored, not-yet-released payment on a project
    so its forecast_release_date follows the latest milestone dates. Staff only
    update the Monthly Tracker; payment cashflow dates follow automatically."""
    if not project_id:
        return
    try:
        from apps.core.models import Payment
        anchored = Payment.objects.filter(
            project_id=project_id,
            forecast_anchor=Payment.ForecastAnchor.SCHEDULED,
        ).exclude(status=Payment.Status.RELEASED)
        for p in anchored:
            p.save(update_fields=['forecast_release_date', 'updated_at'])
    except Exception:
        pass


@receiver(post_save, sender='core.Work')
def sync_anchored_payment_forecasts(sender, instance, **kwargs):
    """A Work's forecast PC (or start) shifted — roll its anchored payments."""
    _resync_anchored_payments(instance.project_id)


@receiver(post_save, sender='core.WorkStep')
def sync_anchored_payments_on_step(sender, instance, **kwargs):
    """A workstep slipped (e.g. Site establishment moved in the tracker) —
    roll the project's anchored payments even if the parent Work's PC is
    unchanged."""
    try:
        _resync_anchored_payments(instance.work.project_id)
    except Exception:
        pass


def _resync_payments_for_schedule(schedule_id):
    """Re-derive scheduled payments after a PaymentMilestoneSchedule/Rule edit,
    so config changes take effect immediately (not only on the next slip)."""
    try:
        from apps.core.models import PaymentMilestoneSchedule, Payment, Work
        sched = PaymentMilestoneSchedule.objects.filter(pk=schedule_id).first()
        if not sched:
            return
        project_ids = set()
        if sched.work_step_group_id:
            project_ids |= set(Work.objects.filter(
                step_group_id=sched.work_step_group_id
            ).values_list('project_id', flat=True))
        if sched.is_default:
            project_ids |= set(Payment.objects.filter(
                forecast_anchor=Payment.ForecastAnchor.SCHEDULED
            ).values_list('project_id', flat=True))
        for pid in project_ids:
            _resync_anchored_payments(pid)
    except Exception:
        pass


@receiver(post_save, sender='core.PaymentMilestoneRule')
@receiver(post_delete, sender='core.PaymentMilestoneRule')
def resync_payments_on_rule_change(sender, instance, **kwargs):
    _resync_payments_for_schedule(instance.schedule_id)


@receiver(post_save, sender='core.PaymentMilestoneSchedule')
def resync_payments_on_schedule_change(sender, instance, **kwargs):
    _resync_payments_for_schedule(instance.pk)

# ---------------------------------------------------------------------------
# FundingSchedule date cascade -> child Projects
# ---------------------------------------------------------------------------
# When a FundingSchedule is saved, copy its date fields down to each linked
# child project. Project edits NEVER propagate back (that drift is surfaced
# via Project.dates_in_sync and FundingSchedule.has_out_of_sync_projects).

@receiver(post_save, sender='core.FundingSchedule')
def cascade_fs_dates_to_projects(sender, instance, created, **kwargs):
    fields = ('start_date', 'stage1_target_date', 'stage1_sunset_date',
              'stage2_target_date', 'stage2_sunset_date')
    try:
        from apps.core.models import Project
        children = Project.objects.filter(funding_schedule=instance)
        for p in children:
            changed = []
            for f in fields:
                fs_val = getattr(instance, f)
                if fs_val is not None and getattr(p, f) != fs_val:
                    setattr(p, f, fs_val)
                    changed.append(f)
            if changed:
                # update_fields avoids running clean() and unwanted signal cascades
                p.save(update_fields=changed + ['updated_at'])
    except Exception:
        # Signal-safe: never crash a FundingSchedule save because of a stale state
        pass


# ---------------------------------------------------------------------------
# Payment -> PaymentAllocation snapshot (Option 2: lock at RELEASED, forever)
# ---------------------------------------------------------------------------
# When a Payment transitions to RELEASED, snapshot the program split using the
# project's current BFAItem ratios. Allocations are immutable thereafter —
# later BFA variations do NOT retro-adjust existing rows. Idempotent: re-saving
# a RELEASED payment does not create duplicate allocations.

@receiver(post_save, sender='core.Payment')
def snapshot_payment_allocations_on_release(sender, instance, **kwargs):
    try:
        from apps.core.models import PaymentAllocation
        if instance.status != instance.Status.RELEASED:
            return
        if instance.allocations.exists():
            return  # locked forever — never overwrite
        split = instance.compute_program_split()
        if not split:
            return
        for prog_id, (amount, ratio) in split.items():
            PaymentAllocation.objects.create(
                payment=instance,
                program_id=prog_id,
                amount=amount,
                ratio=ratio,
            )
    except Exception:
        pass
