from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import StrategicPlan


@login_required
def planning_list(request):
    """List all strategic plans"""
    plans = StrategicPlan.objects.select_related('council').all()
    return render(request, 'planning/planning_list.html', {'plans': plans})
