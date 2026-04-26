from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Contractor


@login_required
def contractor_list(request):
    """List all contractors"""
    contractors = Contractor.objects.select_related('council').all()
    return render(request, 'contractors/contractor_list.html', {'contractors': contractors})


@login_required
def contractor_create(request):
    """Create a new contractor"""
    from apps.councils.models import Council
    
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        trade_type = request.POST.get('trade_type')
        contact_name = request.POST.get('contact_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        council_id = request.POST.get('council')
        
        if company_name and trade_type and council_id:
            council = Council.objects.get(id=council_id)
            contractor = Contractor.objects.create(
                company_name=company_name,
                trade_type=trade_type,
                contact_name=contact_name,
                email=email,
                phone=phone,
                council=council
            )
            from django.contrib import messages
            messages.success(request, f'Contractor "{contractor.company_name}" created.')
            return redirect('contractors:contractor_list')
    
    councils = Council.objects.all()
    return render(request, 'contractors/contractor_form.html', {'councils': councils})
