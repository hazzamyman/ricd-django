from django.db import models

class Stage(models.Model):
    project = models.ForeignKey('projects.Project', related_name='stages', on_delete=models.CASCADE)
    stage_name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.name} - {self.stage_name}"

class WorkStep(models.Model):
    work = models.ForeignKey('works.Work', related_name='steps', on_delete=models.CASCADE)
    step_name = models.CharField(max_length=100)
    expected_duration_days = models.PositiveIntegerField()
    expected_cost_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.work.work_type} - {self.step_name}"