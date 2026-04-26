from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Program


@login_required
def program_list(request):
    """List all programs"""
    programs = Program.objects.all()
    return render(request, 'programs/program_list.html', {'programs': programs})


@login_required
def program_create(request):
    """Create a new program"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            program = Program.objects.create(name=name, description=description)
            from django.contrib import messages
            messages.success(request, f'Program "{program.name}" created.')
            return redirect('programs:program_list')
    
    return render(request, 'programs/program_form.html')
