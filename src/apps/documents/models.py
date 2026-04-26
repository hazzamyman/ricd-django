from django.db import models


class DocumentType(models.Model):
    class ProjectType(models.TextChoices):
        CONSTRUCTION = 'CONSTRUCTION', 'Construction'
        LAND_DEVELOPMENT = 'LAND_DEVELOPMENT', 'Land Development'
        DEMOLITION = 'DEMOLITION', 'Demolition'
        EXTENSION = 'EXTENSION', 'Extension'
        INFRASTRUCTURE = 'INFRASTRUCTURE', 'Infrastructure'

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_attachment = models.BooleanField(default=True, help_text="If True, upload file. If False, provide link.")
    project_types = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Document Types'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({'File' if self.is_attachment else 'Link'})"


class ProjectDocument(models.Model):
    project = models.ForeignKey('projects.Project', related_name='documents', on_delete=models.CASCADE)
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    file = models.FileField(upload_to='project_documents/', blank=True)
    link = models.URLField(blank=True)
    description = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document_type.name} - {self.project.name}"
