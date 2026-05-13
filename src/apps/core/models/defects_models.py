from django.db import models

from .projects_models import Project


class Defect(models.Model):
    project = models.ForeignKey(Project, related_name='defects', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    identified_date = models.DateField()
    rectified_date = models.DateField(null=True, blank=True)
    
    defects_liability_expiry = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'defects'

    def __str__(self):
        return f"Defect on {self.project.name}"
