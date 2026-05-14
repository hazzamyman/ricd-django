from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import Project


@login_required
def planning_list(request):
    """List all strategic plans"""
    plans = Project.objects.select_related('council', 'program').all()
    return render(request, 'planning/planning_list.html', {'projects': plans})
