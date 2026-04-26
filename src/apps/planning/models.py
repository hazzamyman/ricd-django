from django.db import models


class StrategicPlan(models.Model):
    council = models.ForeignKey('councils.Council', related_name='strategic_plans', on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    
    housing_application_count = models.PositiveIntegerField(default=0)
    
    bedrooms_needed_1 = models.PositiveIntegerField(default=0)
    bedrooms_needed_2 = models.PositiveIntegerField(default=0)
    bedrooms_needed_3 = models.PositiveIntegerField(default=0)
    bedrooms_needed_4plus = models.PositiveIntegerField(default=0)
    
    overcrowded_households = models.PositiveIntegerField(default=0)
    additional_bedrooms_needed = models.PositiveIntegerField(default=0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['council', 'year']
        ordering = ['-year', 'council']
        verbose_name_plural = 'Strategic Plans'

    def __str__(self):
        return f"{self.council.name} - {self.year} Strategic Plan"

    @property
    def total_bedrooms_needed(self):
        return self.bedrooms_needed_1 + self.bedrooms_needed_2 + self.bedrooms_needed_3 + self.bedrooms_needed_4plus
