"""Rolling forecast service for WorkStep instances."""
from datetime import timedelta


def recalculate_forecast(work):
    steps = list(work.steps.order_by('order'))
    if not steps:
        return
    start = work.actual_start_date or (work.project.start_date if work.project_id else None)
    active_steps = [s for s in steps if s.is_active]
    inactive_steps = [s for s in steps if not s.is_active]
    for step in inactive_steps:
        if step.forecast_start_date or step.forecast_completion_date:
            step.forecast_start_date = None
            step.forecast_completion_date = None
    if start and active_steps:
        cursor = start
        for step in active_steps:
            step.forecast_start_date = cursor
            step.forecast_completion_date = cursor + timedelta(days=step.expected_duration_days)
            if step.actual_completion_date:
                cursor = step.actual_completion_date
            else:
                cursor = step.forecast_completion_date
    from apps.core.models import WorkStep
    WorkStep.objects.bulk_update(steps, ['forecast_start_date', 'forecast_completion_date'])


def apply_group_to_work(work):
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
