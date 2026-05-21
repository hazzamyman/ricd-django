from django.db import models

class Stage(models.Model):
    project = models.ForeignKey('Project', related_name='stages', on_delete=models.CASCADE)
    stage_name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.name} - {self.stage_name}"

class WorkStep(models.Model):
    work = models.ForeignKey('Work', related_name='steps', on_delete=models.CASCADE)
    group_item = models.ForeignKey(
        'WorkStepGroupItem', related_name='instances', on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Source group item this step was created from"
    )
    step_name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0, help_text="Step sequence for cumulative calculation")
    expected_duration_days = models.PositiveIntegerField(default=0)
    expected_cost_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to mark step as n/a for this work item"
    )
    # Forecast dates (calculated by recalculate_forecast service)
    forecast_start_date = models.DateField(null=True, blank=True)
    forecast_completion_date = models.DateField(null=True, blank=True)
    # Actual dates (entered by Council / Qbuild)
    actual_completion_date = models.DateField(
        null=True, blank=True,
        help_text="Actual completion date — triggers cascade recalculation of subsequent forecasts"
    )
    # Legacy fields kept for backward compatibility
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['work', 'order']

    def __str__(self):
        return f"{self.work} — {self.step_name}"