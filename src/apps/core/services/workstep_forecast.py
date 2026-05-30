"""Rolling forecast service for WorkStep instances.

Two scheduling modes:

  Forward (default): actual_start_date is known — cursor starts at that date
  and each step's forecast dates are computed left-to-right.  When a step has
  actual_completion_date set, the cursor jumps forward to that date so
  downstream forecasts roll automatically.

  Backward: no actual_start_date but forecast_handover_date is explicitly set
  — cursor starts at the target handover and each step's forecast dates are
  computed right-to-left, giving planners implied start dates.

Side-effect: recalculate_forecast writes the final calculated PC date back to
Work.forecast_practical_completion_date.  forecast_handover_date is preserved
when it was explicitly set to a date *different* from the current computed PC
(manual target override); otherwise it tracks PC.
"""
from datetime import timedelta

# Sentinel update_fields used to mark a Work save triggered by this service so
# the post_save signal can short-circuit and not re-enter recalculate_forecast.
RECALC_UPDATE_FIELDS = frozenset({
    'forecast_practical_completion_date',
    'forecast_handover_date',
})


def _final_step(active_steps):
    """Return the step that defines the work's Practical Completion date.

    Preference: the step whose source WorkStepGroupItem has stage_gate='STAGE2'.
    Fallback: the last active step.
    """
    for s in active_steps:
        gi = getattr(s, 'group_item', None)
        if gi and getattr(gi, 'stage_gate', '') == 'STAGE2':
            return s
    return active_steps[-1] if active_steps else None


def recalculate_forecast(work):
    """Recompute step forecast dates and mirror the result onto Work."""
    steps = list(work.steps.select_related('group_item').order_by('order'))
    if not steps:
        return

    active_steps = [s for s in steps if s.is_active]
    inactive_steps = [s for s in steps if not s.is_active]

    for step in inactive_steps:
        if step.forecast_start_date or step.forecast_completion_date:
            step.forecast_start_date = None
            step.forecast_completion_date = None

    start = work.actual_start_date or (work.project.start_date if work.project_id else None)
    target = work.forecast_handover_date

    if start and active_steps:
        # Forward scheduling from known start date.
        cursor = start
        for step in active_steps:
            step.forecast_start_date = cursor
            step.forecast_completion_date = cursor + timedelta(days=step.expected_duration_days)
            cursor = step.actual_completion_date or step.forecast_completion_date

    elif target and active_steps:
        # Backward scheduling: anchor last step at target, cascade left.
        cursor = target
        for step in reversed(active_steps):
            step.forecast_completion_date = cursor
            step.forecast_start_date = cursor - timedelta(days=step.expected_duration_days)
            cursor = step.forecast_start_date

    from apps.core.models import WorkStep
    WorkStep.objects.bulk_update(steps, ['forecast_start_date', 'forecast_completion_date'])

    pc_step = _final_step(active_steps)
    new_pc = pc_step.forecast_completion_date if pc_step else None

    # Preserve a manually-set handover target: if forecast_handover_date was
    # already different from the current computed PC the user has explicitly
    # targeted a different delivery date — keep it.  In backward mode this also
    # preserves naturally because new_pc == target.
    old_pc = work.forecast_practical_completion_date
    handover_is_manual = (
        work.forecast_handover_date is not None
        and old_pc is not None
        and work.forecast_handover_date != old_pc
    )
    new_handover = work.forecast_handover_date if handover_is_manual else new_pc

    if work.forecast_practical_completion_date != new_pc or work.forecast_handover_date != new_handover:
        work.forecast_practical_completion_date = new_pc
        work.forecast_handover_date = new_handover
        work.save(update_fields=list(RECALC_UPDATE_FIELDS))


def apply_group_to_work(work):
    """Materialise WorkStep rows from work.step_group, then forecast."""
    from apps.core.models import WorkStep
    group = work.step_group
    if not group:
        return 0, 0
    created = 0
    skipped = 0
    for item in group.items.select_related('step').order_by('order'):
        _, was_created = WorkStep.objects.get_or_create(
            work=work, order=item.order,
            defaults={
                'group_item': item,
                'step_name': item.step.name,
                'expected_duration_days': item.expected_duration_days,
                'expected_cost_percentage': item.cost_percentage,
                'is_active': True,
            }
        )
        if was_created:
            created += 1
        else:
            skipped += 1
    recalculate_forecast(work)
    return created, skipped
