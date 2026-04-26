from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from apps.dashboard.decorators import ricd_required, manager_required
from apps.dashboard.pagination import paginate_queryset, get_pagination_context
from apps.councils.models import Council
from apps.programs.models import Program
from apps.works.models import WorkType, WorkStepTemplate, Work
from apps.addresses.models import Address, Suburb
from apps.projects.models import Project
from apps.funding.models import FundingApproval, FundingSchedule, Delegation
from apps.contractors.models import Contractor
from apps.documents.models import DocumentType
from .forms import (
    CouncilForm, ProgramForm, WorkTypeForm, WorkStepTemplateForm,
    AddressForm, WorkForm, FundingApprovalForm, FundingScheduleForm,
    DelegationForm, ContractorForm, DocumentTypeForm,
    NotionalCostForm, ProgramBudgetForm
)


@login_required
def maintenance_dashboard(request):
    """Main maintenance dashboard"""
    return render(request, 'maintenance/dashboard.html')


# ============== COUNCILS ==============
@login_required
@ricd_required
def council_list(request):
    councils = Council.objects.order_by('name')
    paginator, page_obj = paginate_queryset(request, councils)
    context = {
        'councils': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/council_list.html', context)


@login_required
@manager_required
def council_create(request):
    if request.method == 'POST':
        form = CouncilForm(request.POST)
        if form.is_valid():
            council = form.save()
            messages.success(request, f'Council "{council.name}" created.')
            return redirect('maintenance:council_list')
    else:
        form = CouncilForm()
    return render(request, 'maintenance/council_form.html', {'form': form, 'council': None})


@login_required
@manager_required
def council_edit(request, pk):
    council = get_object_or_404(Council, pk=pk)
    if request.method == 'POST':
        form = CouncilForm(request.POST, instance=council)
        if form.is_valid():
            council = form.save()
            messages.success(request, f'Council "{council.name}" updated.')
            return redirect('maintenance:council_list')
    else:
        form = CouncilForm(instance=council)
    return render(request, 'maintenance/council_form.html', {'form': form, 'council': council})


@login_required
@manager_required
def council_delete(request, pk):
    council = get_object_or_404(Council, pk=pk)
    if request.method == 'POST':
        council.delete()
        messages.success(request, 'Council deleted.')
    return redirect('maintenance:council_list')


@ricd_required
def councilcontact_list(request):
    from apps.councils.models import CouncilContact
    contacts = CouncilContact.objects.select_related('council').order_by('council__name', 'role')
    return render(request, 'maintenance/councilcontact_list.html', {'contacts': contacts})


@login_required
@manager_required
def councilcontact_create(request):
    from apps.councils.models import CouncilContact
    if request.method == 'POST':
        form = CouncilContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact "{contact.name}" created.')
            return redirect('maintenance:councilcontact_list')
    else:
        form = CouncilContactForm()
    return render(request, 'maintenance/councilcontact_form.html', {'form': form, 'contact': None})


@login_required
@manager_required
def councilcontact_edit(request, pk):
    from apps.councils.models import CouncilContact
    contact = get_object_or_404(CouncilContact, pk=pk)
    if request.method == 'POST':
        form = CouncilContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact "{contact.name}" updated.')
            return redirect('maintenance:councilcontact_list')
    else:
        form = CouncilContactForm(instance=contact)
    return render(request, 'maintenance/councilcontact_form.html', {'form': form, 'contact': contact})


# ============== PROGRAMS ==============
@login_required
@ricd_required
def program_list(request):
    from apps.programs.models import Program
    programs = Program.objects.order_by('name')
    paginator, page_obj = paginate_queryset(request, programs)
    context = {
        'programs': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/program_list.html', context)


@login_required
@manager_required
def program_create(request):
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f'Program "{program.name}" created.')
            return redirect('maintenance:program_list')
    else:
        form = ProgramForm()
    return render(request, 'maintenance/program_form.html', {'form': form, 'program': None})


@login_required
@manager_required
def program_edit(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            program = form.save()
            messages.success(request, f'Program "{program.name}" updated.')
            return redirect('maintenance:program_list')
    else:
        form = ProgramForm(instance=program)
    return render(request, 'maintenance/program_form.html', {'form': form, 'program': program})


@login_required
@manager_required
def program_delete(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        program.delete()
        messages.success(request, 'Program deleted.')
    return redirect('maintenance:program_list')


# ============== PROGRAM BUDGETS ==============
@ricd_required
def programbudget_list(request):
    from apps.programs.models import ProgramBudget
    budgets = ProgramBudget.objects.select_related('program').order_by('-financial_year', 'program__name')
    paginator, page_obj = paginate_queryset(request, budgets)
    context = {
        'budgets': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/programbudget_list.html', context)


@login_required
@manager_required
def programbudget_create(request):
    from apps.programs.models import Program
    from apps.core.utils import FINANCIAL_YEAR_CHOICES
    if request.method == 'POST':
        form = ProgramBudgetForm(request.POST)
        if form.is_valid():
            budget = form.save()
            messages.success(request, f'Budget for {budget.financial_year} created.')
            return redirect('maintenance:programbudget_list')
    else:
        form = ProgramBudgetForm()
        preselected_program = request.GET.get('program')
        if preselected_program:
            form.initial['program'] = preselected_program
    programs = Program.objects.filter(is_active=True).order_by('name')
    return render(request, 'maintenance/programbudget_form.html', {
        'form': form, 
        'budget': None,
        'programs': programs,
        'year_choices': FINANCIAL_YEAR_CHOICES
    })


@login_required
@manager_required
def programbudget_edit(request, pk):
    from apps.programs.models import Program
    from apps.core.utils import FINANCIAL_YEAR_CHOICES
    budget = get_object_or_404(ProgramBudget, pk=pk)
    if request.method == 'POST':
        form = ProgramBudgetForm(request.POST, instance=budget)
        if form.is_valid():
            budget = form.save()
            messages.success(request, f'Budget updated.')
            return redirect('maintenance:programbudget_list')
    else:
        form = ProgramBudgetForm(instance=budget)
    programs = Program.objects.filter(is_active=True).order_by('name')
    return render(request, 'maintenance/programbudget_form.html', {
        'form': form, 
        'budget': budget,
        'programs': programs,
        'year_choices': FINANCIAL_YEAR_CHOICES
    })


@login_required
@manager_required
def programbudget_delete(request, pk):
    budget = get_object_or_404(ProgramBudget, pk=pk)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted.')
    return redirect('maintenance:programbudget_list')


# ============== WORK TYPES ==============
@login_required
@ricd_required
def worktype_list(request):
    from apps.works.models import WorkType
    worktypes = WorkType.objects.order_by('category', 'name')
    paginator, page_obj = paginate_queryset(request, worktypes)
    context = {
        'worktypes': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/worktype_list.html', context)


@login_required
@manager_required
def worktype_create(request):
    from apps.works.models import WorkType
    if request.method == 'POST':
        form = WorkTypeForm(request.POST)
        if form.is_valid():
            worktype = form.save()
            messages.success(request, f'Work Type "{worktype.name}" created.')
            return redirect('maintenance:worktype_list')
    else:
        form = WorkTypeForm()
    return render(request, 'maintenance/worktype_form.html', {'form': form, 'worktype': None})


@login_required
@manager_required
def worktype_edit(request, pk):
    from apps.works.models import WorkType
    worktype = get_object_or_404(WorkType, pk=pk)
    if request.method == 'POST':
        form = WorkTypeForm(request.POST, instance=worktype)
        if form.is_valid():
            worktype = form.save()
            messages.success(request, f'Work Type "{worktype.name}" updated.')
            return redirect('maintenance:worktype_list')
    else:
        form = WorkTypeForm(instance=worktype)
    return render(request, 'maintenance/worktype_form.html', {'form': form, 'worktype': worktype})


@login_required
@manager_required
def worktype_delete(request, pk):
    from apps.works.models import WorkType
    worktype = get_object_or_404(WorkType, pk=pk)
    if request.method == 'POST':
        worktype.delete()
        messages.success(request, 'Work Type deleted.')
    return redirect('maintenance:worktype_list')


# ============== WORK STEP TEMPLATES ==============
@login_required
@ricd_required
def worksteptemplate_list(request):
    from apps.works.models import WorkStepTemplate
    templates = WorkStepTemplate.objects.select_related('work_type').all()
    paginator, page_obj = paginate_queryset(request, templates)
    context = {
        'templates': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/worksteptemplate_list.html', context)


@login_required
@manager_required
def worksteptemplate_create(request):
    from apps.works.models import WorkType
    if request.method == 'POST':
        form = WorkStepTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Work Step Template "{template.name}" created.')
            return redirect('maintenance:worksteptemplate_list')
    else:
        form = WorkStepTemplateForm()
    worktypes = WorkType.objects.order_by('name')
    return render(request, 'maintenance/worksteptemplate_form.html', {'form': form, 'template': None, 'worktypes': worktypes})


@login_required
@manager_required
def worksteptemplate_edit(request, pk):
    from apps.works.models import WorkStepTemplate, WorkType
    template = get_object_or_404(WorkStepTemplate, pk=pk)
    if request.method == 'POST':
        form = WorkStepTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Work Step Template "{template.name}" updated.')
            return redirect('maintenance:worksteptemplate_list')
    else:
        form = WorkStepTemplateForm(instance=template)
    worktypes = WorkType.objects.order_by('name')
    return render(request, 'maintenance/worksteptemplate_form.html', {'form': form, 'template': template, 'worktypes': worktypes})


@login_required
@manager_required
def worksteptemplate_delete(request, pk):
    from apps.works.models import WorkStepTemplate
    template = get_object_or_404(WorkStepTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Work Step Template deleted.')
    return redirect('maintenance:worksteptemplate_list')


# ============== ADDRESSES ==============
@login_required
@ricd_required
def address_list(request):
    from apps.addresses.models import Address
    addresses = Address.objects.select_related('project').order_by('street')
    paginator, page_obj = paginate_queryset(request, addresses)
    context = {
        'addresses': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/address_list.html', context)


@login_required
@manager_required
def address_create(request):
    from apps.addresses.models import Address, Suburb
    from apps.projects.models import Project
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save()
            messages.success(request, f'Address created.')
            return redirect('maintenance:address_list')
    else:
        form = AddressForm()
    projects = Project.objects.order_by('name')
    suburbs = Suburb.objects.order_by('name')
    return render(request, 'maintenance/address_form.html', {'form': form, 'address': None, 'projects': projects, 'suburbs': suburbs})


@login_required
@manager_required
def address_edit(request, pk):
    from apps.addresses.models import Address
    from apps.projects.models import Project
    address = get_object_or_404(Address, pk=pk)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save()
            messages.success(request, 'Address updated.')
            return redirect('maintenance:address_list')
    else:
        form = AddressForm(instance=address)
    projects = Project.objects.order_by('name')
    suburbs = Suburb.objects.order_by('name')
    return render(request, 'maintenance/address_form.html', {'form': form, 'address': address, 'projects': projects, 'suburbs': suburbs})


@login_required
@manager_required
def address_delete(request, pk):
    from apps.addresses.models import Address
    address = get_object_or_404(Address, pk=pk)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted.')
    return redirect('maintenance:address_list')


# ============== WORKS ==============
@login_required
@ricd_required
def work_list(request):
    from apps.works.models import Work
    works = Work.objects.select_related('project', 'address', 'work_type').order_by('-created_at')
    paginator, page_obj = paginate_queryset(request, works)
    context = {
        'works': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/work_list.html', context)


@login_required
@manager_required
def work_create(request):
    from apps.works.models import Work
    from apps.projects.models import Project
    from apps.addresses.models import Address
    from apps.works.models import WorkType
    if request.method == 'POST':
        form = WorkForm(request.POST)
        if form.is_valid():
            work = form.save()
            messages.success(request, f'Work created.')
            return redirect('maintenance:work_list')
    else:
        form = WorkForm()
    projects = Project.objects.order_by('name')
    addresses = Address.objects.order_by('street')
    worktypes = WorkType.objects.order_by('name')
    return render(request, 'maintenance/work_form.html', {
        'form': form, 'work': None, 'projects': projects, 'addresses': addresses, 'worktypes': worktypes
    })


@login_required
@manager_required
def work_edit(request, pk):
    from apps.works.models import Work
    from apps.projects.models import Project
    from apps.addresses.models import Address
    from apps.works.models import WorkType
    work = get_object_or_404(Work, pk=pk)
    if request.method == 'POST':
        form = WorkForm(request.POST, instance=work)
        if form.is_valid():
            work = form.save()
            messages.success(request, 'Work updated.')
            return redirect('maintenance:work_list')
    else:
        form = WorkForm(instance=work)
    projects = Project.objects.order_by('name')
    addresses = Address.objects.order_by('street')
    worktypes = WorkType.objects.order_by('name')
    return render(request, 'maintenance/work_form.html', {
        'form': form, 'work': work, 'projects': projects, 'addresses': addresses, 'worktypes': worktypes
    })


@login_required
@manager_required
def work_delete(request, pk):
    from apps.works.models import Work
    work = get_object_or_404(Work, pk=pk)
    if request.method == 'POST':
        work.delete()
        messages.success(request, 'Work deleted.')
    return redirect('maintenance:work_list')


# ============== FUNDING APPROVALS ==============
@login_required
@ricd_required
def fundingapproval_list(request):
    from apps.funding.models import FundingApproval
    approvals = FundingApproval.objects.order_by('-created_at')
    paginator, page_obj = paginate_queryset(request, approvals)
    context = {
        'approvals': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/fundingapproval_list.html', context)


@login_required
@manager_required
def fundingapproval_create(request):
    from apps.funding.models import FundingApproval
    from apps.projects.models import Project
    if request.method == 'POST':
        form = FundingApprovalForm(request.POST)
        if form.is_valid():
            fa = form.save(commit=False)
            fa.created_by = request.user
            fa.save()
            form.save_m2m()
            messages.success(request, f'Funding Approval created.')
            return redirect('maintenance:fundingapproval_list')
    else:
        form = FundingApprovalForm()
    projects = Project.objects.order_by('name')
    return render(request, 'maintenance/fundingapproval_form.html', {'form': form, 'approval': None, 'projects': projects})


@login_required
@manager_required
def fundingapproval_edit(request, pk):
    from apps.funding.models import FundingApproval
    from apps.projects.models import Project
    approval = get_object_or_404(FundingApproval, pk=pk)
    if request.method == 'POST':
        form = FundingApprovalForm(request.POST, instance=approval)
        if form.is_valid():
            approval = form.save()
            messages.success(request, 'Funding Approval updated.')
            return redirect('maintenance:fundingapproval_list')
    else:
        form = FundingApprovalForm(instance=approval)
    projects = Project.objects.order_by('name')
    return render(request, 'maintenance/fundingapproval_form.html', {'form': form, 'approval': approval, 'projects': projects})


@login_required
@manager_required
def fundingapproval_delete(request, pk):
    from apps.funding.models import FundingApproval
    approval = get_object_or_404(FundingApproval, pk=pk)
    if request.method == 'POST':
        approval.delete()
        messages.success(request, 'Funding Approval deleted.')
    return redirect('maintenance:fundingapproval_list')


# ============== DELEGATIONS ==============
@login_required
@ricd_required
def delegation_list(request):
    from apps.funding.models import Delegation
    delegations = Delegation.objects.order_by('position')
    paginator, page_obj = paginate_queryset(request, delegations)
    context = {
        'delegations': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/delegation_list.html', context)


@login_required
@manager_required
def delegation_create(request):
    from apps.funding.models import Delegation
    if request.method == 'POST':
        form = DelegationForm(request.POST)
        if form.is_valid():
            delegation = form.save()
            messages.success(request, f'Delegation created.')
            return redirect('maintenance:delegation_list')
    else:
        form = DelegationForm()
    return render(request, 'maintenance/delegation_form.html', {'form': form, 'delegation': None})


@login_required
@manager_required
def delegation_edit(request, pk):
    from apps.funding.models import Delegation
    delegation = get_object_or_404(Delegation, pk=pk)
    if request.method == 'POST':
        form = DelegationForm(request.POST, instance=delegation)
        if form.is_valid():
            delegation = form.save()
            messages.success(request, 'Delegation updated.')
            return redirect('maintenance:delegation_list')
    else:
        form = DelegationForm(instance=delegation)
    return render(request, 'maintenance/delegation_form.html', {'form': form, 'delegation': delegation})


@login_required
@manager_required
def delegation_delete(request, pk):
    from apps.funding.models import Delegation
    delegation = get_object_or_404(Delegation, pk=pk)
    if request.method == 'POST':
        delegation.delete()
        messages.success(request, 'Delegation deleted.')
    return redirect('maintenance:delegation_list')


# ============== FUNDING SCHEDULES ==============
@login_required
@ricd_required
def fundingschedule_list(request):
    from apps.funding.models import FundingSchedule
    schedules = FundingSchedule.objects.select_related('project').order_by('-created_at')
    paginator, page_obj = paginate_queryset(request, schedules)
    context = {
        'schedules': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/fundingschedule_list.html', context)


@login_required
@manager_required
def fundingschedule_create(request):
    from apps.funding.models import FundingSchedule
    from apps.projects.models import Project
    if request.method == 'POST':
        form = FundingScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Funding Schedule created.')
            return redirect('maintenance:fundingschedule_list')
    else:
        form = FundingScheduleForm()
    projects = Project.objects.order_by('name')
    return render(request, 'maintenance/fundingschedule_form.html', {'form': form, 'schedule': None, 'projects': projects})


@login_required
@manager_required
def fundingschedule_edit(request, pk):
    from apps.funding.models import FundingSchedule
    from apps.projects.models import Project
    schedule = get_object_or_404(FundingSchedule, pk=pk)
    if request.method == 'POST':
        form = FundingScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, 'Funding Schedule updated.')
            return redirect('maintenance:fundingschedule_list')
    else:
        form = FundingScheduleForm(instance=schedule)
    projects = Project.objects.order_by('name')
    return render(request, 'maintenance/fundingschedule_form.html', {'form': form, 'schedule': schedule, 'projects': projects})


@login_required
@manager_required
def fundingschedule_delete(request, pk):
    from apps.funding.models import FundingSchedule
    schedule = get_object_or_404(FundingSchedule, pk=pk)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'Funding Schedule deleted.')
    return redirect('maintenance:fundingschedule_list')


# ============== CONTRACTORS ==============
@login_required
@ricd_required
def contractor_list(request):
    from apps.contractors.models import Contractor
    contractors = Contractor.objects.select_related('council').all()
    paginator, page_obj = paginate_queryset(request, contractors)
    context = {
        'contractors': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/contractor_list.html', context)


@login_required
@manager_required
def contractor_create(request):
    from apps.contractors.models import Contractor
    from apps.councils.models import Council
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            contractor = form.save()
            messages.success(request, f'Contractor "{contractor.company_name}" created.')
            return redirect('maintenance:contractor_list')
    else:
        form = ContractorForm()
    councils = Council.objects.order_by('name')
    return render(request, 'maintenance/contractor_form.html', {'form': form, 'contractor': None, 'councils': councils})


@login_required
@manager_required
def contractor_edit(request, pk):
    from apps.contractors.models import Contractor
    from apps.councils.models import Council
    contractor = get_object_or_404(Contractor, pk=pk)
    if request.method == 'POST':
        form = ContractorForm(request.POST, instance=contractor)
        if form.is_valid():
            contractor = form.save()
            messages.success(request, f'Contractor "{contractor.company_name}" updated.')
            return redirect('maintenance:contractor_list')
    else:
        form = ContractorForm(instance=contractor)
    councils = Council.objects.order_by('name')
    return render(request, 'maintenance/contractor_form.html', {'form': form, 'contractor': contractor, 'councils': councils})


@login_required
@manager_required
def contractor_delete(request, pk):
    from apps.contractors.models import Contractor
    contractor = get_object_or_404(Contractor, pk=pk)
    if request.method == 'POST':
        contractor.delete()
        messages.success(request, 'Contractor deleted.')
    return redirect('maintenance:contractor_list')


# ============== DOCUMENT TYPES ==============
@login_required
@ricd_required
def documenttype_list(request):
    from apps.documents.models import DocumentType
    types = DocumentType.objects.order_by('name')
    paginator, page_obj = paginate_queryset(request, types)
    context = {
        'types': page_obj.object_list,
        **get_pagination_context(paginator, page_obj)
    }
    return render(request, 'maintenance/documenttype_list.html', context)


@login_required
@manager_required
def documenttype_create(request):
    from apps.documents.models import DocumentType
    if request.method == 'POST':
        form = DocumentTypeForm(request.POST)
        if form.is_valid():
            doctype = form.save()
            messages.success(request, f'Document Type "{doctype.name}" created.')
            return redirect('maintenance:documenttype_list')
    else:
        form = DocumentTypeForm()
    return render(request, 'maintenance/documenttype_form.html', {'form': form, 'type': None})


@login_required
@manager_required
def documenttype_edit(request, pk):
    from apps.documents.models import DocumentType
    doctype = get_object_or_404(DocumentType, pk=pk)
    if request.method == 'POST':
        form = DocumentTypeForm(request.POST, instance=doctype)
        if form.is_valid():
            doctype = form.save()
            messages.success(request, f'Document Type "{doctype.name}" updated.')
            return redirect('maintenance:documenttype_list')
    else:
        form = DocumentTypeForm(instance=doctype)
    return render(request, 'maintenance/documenttype_form.html', {'form': form, 'type': doctype})


@login_required
@manager_required
def documenttype_delete(request, pk):
    from apps.documents.models import DocumentType
    doctype = get_object_or_404(DocumentType, pk=pk)
    if request.method == 'POST':
        doctype.delete()
        messages.success(request, 'Document Type deleted.')
    return redirect('maintenance:documenttype_list')


# ============== NOTIONAL COSTS ==============
@login_required
@ricd_required
def notionalcost_list(request):
    from apps.works.models import NotionalCost, NotionalCostSettings
    financial_year = request.GET.get('year')
    settings = NotionalCostSettings.get_settings()
    
    costs = NotionalCost.objects.select_related('work_type').order_by('financial_year', 'work_type__category', 'work_type__name')
    
    if financial_year:
        costs = costs.filter(financial_year=financial_year)
    
    years = NotionalCost.objects.values_list('financial_year', flat=True).distinct().order_by('-financial_year')
    
    context = {
        'costs': costs,
        'years': years,
        'selected_year': financial_year,
        'current_year': settings.current_financial_year,
    }
    return render(request, 'maintenance/notionalcost_list.html', context)


@login_required
@manager_required
def notionalcost_create(request):
    from apps.works.models import NotionalCost
    if request.method == 'POST':
        form = NotionalCostForm(request.POST)
        if form.is_valid():
            cost = form.save()
            messages.success(request, 'Notional cost created.')
            return redirect('maintenance:notionalcost_list')
    else:
        form = NotionalCostForm()
    return render(request, 'maintenance/notionalcost_form.html', {'form': form, 'cost': None})


@login_required
@manager_required
def notionalcost_edit(request, pk):
    from apps.works.models import NotionalCost
    cost = get_object_or_404(NotionalCost, pk=pk)
    if request.method == 'POST':
        form = NotionalCostForm(request.POST, instance=cost)
        if form.is_valid():
            cost = form.save()
            messages.success(request, f'Notional cost updated.')
            return redirect('maintenance:notionalcost_list')
    else:
        form = NotionalCostForm(instance=cost)
    return render(request, 'maintenance/notionalcost_form.html', {'form': form, 'cost': cost})


@login_required
@manager_required
def notionalcost_bulk_update(request):
    from apps.works.models import NotionalCost, NotionalCostSettings
    settings = NotionalCostSettings.get_settings()
    
    if request.method == 'POST':
        from_year = request.POST.get('from_year')
        to_year = request.POST.get('to_year')
        inflation_rate = float(request.POST.get('inflation_rate', 0))
        
        source_costs = NotionalCost.objects.filter(financial_year=from_year)
        
        created_count = 0
        for source in source_costs:
            new_cost = source.cost_per_unit * (1 + inflation_rate / 100)
            
            existing = NotionalCost.objects.filter(
                work_type=source.work_type,
                financial_year=to_year,
                bedrooms=source.bedrooms
            ).first()
            
            if existing:
                existing.cost_per_unit = new_cost
                existing.save()
            else:
                NotionalCost.objects.create(
                    work_type=source.work_type,
                    financial_year=to_year,
                    cost_per_unit=new_cost,
                    bedrooms=source.bedrooms,
                    is_default=True
                )
                created_count += 1
        
        messages.success(request, f'Created/updated {created_count} notional costs for {to_year} with {inflation_rate}% inflation.')
        return redirect('maintenance:notionalcost_list')
    
    years = NotionalCost.objects.values_list('financial_year', flat=True).distinct().order_by('-financial_year')
    
    context = {
        'years': years,
        'default_inflation': settings.default_inflation_rate,
        'current_year': settings.current_financial_year,
    }
    return render(request, 'maintenance/notionalcost_bulk_update.html', context)
