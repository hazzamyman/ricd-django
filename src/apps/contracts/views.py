from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Contract, ContractMeeting


@login_required
def contract_list(request):
    """List all contracts with filters"""
    project_type = request.GET.get('project_type')
    contract_status = request.GET.get('status')
    council_id = request.GET.get('council')
    
    contracts = Contract.objects.select_related('project', 'land_project').order_by('-created_at')
    
    if project_type:
        contracts = contracts.filter(project_type=project_type)
    if contract_status:
        contracts = contracts.filter(contract_status=contract_status)
    
    from apps.councils.models import Council
    
    context = {
        'contracts': contracts,
        'project_types': Contract.ProjectType.choices,
        'contract_statuses': Contract.ContractStatus.choices,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'contracts/contract_list.html', context)


@login_required
def contract_detail(request, contract_id):
    """Show contract details"""
    contract = get_object_or_404(
        Contract.objects.select_related('project', 'land_project').prefetch_related('meetings'),
        id=contract_id
    )
    
    context = {
        'contract': contract,
    }
    return render(request, 'contracts/contract_detail.html', context)


@login_required
def contract_create(request):
    """Create a new contract"""
    from apps.councils.models import Council
    
    if request.method == 'POST':
        from .forms import ContractForm
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save()
            messages.success(request, f'Contract "{contract.title}" created successfully.')
            return redirect('contracts:contract_detail', contract_id=contract.id)
    else:
        from .forms import ContractForm
        form = ContractForm()
    
    context = {
        'form': form,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'contracts/contract_form.html', context)


@login_required
def contract_edit(request, contract_id):
    """Edit an existing contract"""
    from apps.councils.models import Council
    
    contract = get_object_or_404(Contract, id=contract_id)
    
    if request.method == 'POST':
        from .forms import ContractForm
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save()
            messages.success(request, f'Contract "{contract.title}" updated successfully.')
            return redirect('contracts:contract_detail', contract_id=contract.id)
    else:
        from .forms import ContractForm
        form = ContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'councils': Council.objects.order_by('name'),
    }
    return render(request, 'contracts/contract_form.html', context)


@login_required
def contract_delete(request, contract_id):
    """Delete a contract"""
    contract = get_object_or_404(Contract, id=contract_id)
    
    if request.method == 'POST':
        title = contract.title
        contract.delete()
        messages.success(request, f'Contract "{title}" deleted successfully.')
        return redirect('contracts:contract_list')
    
    return render(request, 'contracts/contract_confirm_delete.html', {'contract': contract})


@login_required
def contract_meeting_create(request, contract_id):
    """Create a new contract meeting"""
    contract = get_object_or_404(Contract, id=contract_id)
    
    if request.method == 'POST':
        from .forms import ContractMeetingForm
        form = ContractMeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save()
            messages.success(request, f'Meeting scheduled for {meeting.meeting_date}.')
            return redirect('contracts:contract_detail', contract_id=contract.id)
    else:
        from .forms import ContractMeetingForm
        initial_data = {'contract': contract.id}
        form = ContractMeetingForm(initial=initial_data)
    
    context = {
        'form': form,
        'contract': contract,
    }
    return render(request, 'contracts/contract_meeting_form.html', context)