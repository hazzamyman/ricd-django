from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Council


@login_required
def council_list(request):
    """List all councils"""
    councils = Council.objects.all()
    return render(request, 'councils/council_list.html', {'councils': councils})


@login_required
def council_create(request):
    """Create a new council"""
    if request.method == 'POST':
        name = request.POST.get('name')
        region = request.POST.get('region', '')
        is_registered = request.POST.get('is_registered') == 'on'
        if name:
            council = Council.objects.create(
                name=name,
                region=region,
                is_registered_housing_provider=is_registered
            )
            from django.contrib import messages
            messages.success(request, f'Council "{council.name}" created.')
            return redirect('councils:council_list')
    
    return render(request, 'councils/council_form.html')
