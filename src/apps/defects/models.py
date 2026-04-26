from django.db import models


class Defect(models.Model):
    class ProjectType(models.TextChoices):
        DWELLING = 'DWELLING', 'Dwelling/Construction'
        LAND = 'LAND', 'Land/Infrastructure'

    project = models.ForeignKey('projects.Project', related_name='defects', on_delete=models.CASCADE, null=True, blank=True)
    land_project = models.ForeignKey('land_infra.LandProject', related_name='defects', on_delete=models.CASCADE, null=True, blank=True)
    project_type = models.CharField(max_length=10, choices=ProjectType.choices, default=ProjectType.DWELLING)
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
        project_name = self.project.name if self.project else (self.land_project.name if self.land_project else 'No Project')
        return f"Defect on {project_name}"

    @property
    def linked_project(self):
        """Returns the linked project (either dwelling or land)"""
        if self.project_type == self.ProjectType.DWELLING:
            return self.project
        return self.land_project
