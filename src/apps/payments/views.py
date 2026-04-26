from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import date
from .models import Payment


@login_required
def payment_list(request):
    """List all payments with filters"""
    status_filter = request.GET.get('status')
    project_type = request.GET.get('project_type')
    council_id = request.GET.get('council')
    search = request.GET.get('search')
    
    payments = Payment.objects.select_related('project', 'land_project', 'funding_schedule').order_by('-created_at')
    
    if status_filter:
        payments = payments.filter(status=status_filter)
    if project_type:
        payments = payments.filter(project_type=project_type)
    if search:
        payments = payments.filter(
            Q(reference__icontains=search) |
            Q(tax_invoice_reference__icontains=search) |
            Q(sap_payment_reference__icontains=search) |
            Q(project__name__icontains=search)
        )
    
    context = {
        'payments': payments,
        'statuses': Payment.Status.choices,
        'project_types': Payment.ProjectType.choices,
    }
    return render(request, 'payments/payment_list.html', context)


@login_required
def payment_create(request):
    """Create a new payment"""
    from apps.projects.models import Project
    from apps.land_infra.models import LandProject
    from apps.funding.models import FundingSchedule
    from apps.councils.models import Council
    
    if request.method == 'POST':
        project_id = request.POST.get('project')
        land_project_id = request.POST.get('land_project')
        
        # Determine project type and get funding schedule
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            project_type = 'DWELLING'
            funding_schedule_id = request.POST.get('funding_schedule')
            funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_id) if funding_schedule_id else None
        elif land_project_id:
            project = None
            project_type = 'LAND'
            funding_schedule_id = request.POST.get('funding_schedule')
            funding_schedule = get_object_or_404(FundingSchedule, id=funding_schedule_id) if funding_schedule_id else None
        else:
            messages.error(request, 'Please select a project or land project.')
            return render(request, 'payments/payment_form.html', get_context())
        
        from decimal import Decimal
        calc_type = request.POST.get('calculation_type', 'PERCENTAGE')
        
        payment = Payment.objects.create(
            project=project,
            land_project_id=land_project_id if land_project_id else None,
            project_type=project_type,
            funding_schedule=funding_schedule,
            calculation_type=calc_type,
            percentage=Decimal(request.POST.get('percentage', '0')) if calc_type == 'PERCENTAGE' else None,
            amount=Decimal(request.POST.get('amount', '0')) if calc_type in ['FIXED', 'REIMBURSEMENT'] else None,
            payment_type=request.POST.get('payment_type'),
            payment_split=request.POST.get('payment_split', '30/60/10'),
            status='PENDING'
        )
        messages.success(request, f'Payment created for {payment}')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    context = get_context()
    return render(request, 'payments/payment_form.html', context)


def get_context():
    """Helper to get context for forms"""
    from apps.projects.models import Project
    from apps.land_infra.models import LandProject
    from apps.funding.models import FundingSchedule
    from apps.councils.models import Council
    
    return {
        'projects': Project.objects.filter(state__in=['PROG', 'FUND', 'COMM']).order_by('name'),
        'land_projects': LandProject.objects.filter(status__in=['PROG', 'FUND', 'COMM']).order_by('name'),
        'funding_schedules': FundingSchedule.objects.all().order_by('-created_at')[:50],
        'calculation_types': Payment.CalculationType.choices,
        'payment_types': Payment.PaymentType.choices,
        'payment_splits': Payment.PaymentSplit.choices,
    }


@login_required
def payment_detail(request, payment_id):
    """Show payment details"""
    payment = get_object_or_404(Payment.objects.select_related('project', 'land_project', 'funding_schedule'), id=payment_id)
    return render(request, 'payments/payment_detail.html', {'payment': payment})


@login_required
def payment_edit(request, payment_id):
    """Edit payment details"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        from decimal import Decimal
        
        payment.reference = request.POST.get('reference', '')
        payment.tax_invoice_reference = request.POST.get('tax_invoice_reference', '')
        payment.sap_payment_reference = request.POST.get('sap_payment_reference', '')
        payment.sap_cost_centre = request.POST.get('sap_cost_centre', '')
        payment.gl_code = request.POST.get('gl_code', '')
        payment.business_case_ref = request.POST.get('business_case_ref', '')
        
        # Document linking
        payment.document_source = request.POST.get('document_source', '')
        payment.document_url = request.POST.get('document_url', '')
        payment.document_path = request.POST.get('document_path', '')
        
        payment.notes = request.POST.get('notes', '')
        payment.save()
        
        messages.success(request, 'Payment updated.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    return render(request, 'payments/payment_form.html', {
        'payment': payment,
        **get_context()
    })


@login_required
def payment_delete(request, payment_id):
    """Delete payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    payment.delete()
    messages.success(request, 'Payment deleted.')
    return redirect('payments:payment_list')


@login_required
def payment_recommend(request, payment_id):
    """Recommend payment for approval"""
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'RECOMMENDED'
    payment.recommended_by = request.user
    payment.recommended_date = date.today()
    payment.save()
    messages.success(request, f'Payment recommended by {request.user}')
    return redirect('payments:payment_detail', payment_id=payment.id)


@login_required
def payment_approve(request, payment_id):
    """Approve payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'APPROVED'
    payment.approved_by = request.user
    payment.approved_date = date.today()
    payment.save()
    messages.success(request, f'Payment approved by {request.user}')
    return redirect('payments:payment_detail', payment_id=payment.id)


@login_required
def payment_release(request, payment_id):
    """Release payment to Finance with SAP reference and receipt details"""
    from datetime import datetime
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        payment.status = 'RELEASED'
        release_date = request.POST.get('release_date')
        payment.release_date = datetime.strptime(release_date, '%Y-%m-%d').date() if release_date else date.today()
        
        payment.release_sap_reference = request.POST.get('release_sap_reference', '')
        payment.release_receipt_number = request.POST.get('release_receipt_number', '')
        payment.release_document_source = request.POST.get('release_document_source', '')
        payment.release_document_url = request.POST.get('release_document_url', '')
        payment.release_document_path = request.POST.get('release_document_path', '')
        payment.release_notes = request.POST.get('release_notes', '')
        
        payment.save()
        messages.success(request, 'Payment released to Finance.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    return render(request, 'payments/payment_release.html', {
        'payment': payment,
        'today': date.today().isoformat()
    })


@login_required
def payment_reject(request, payment_id):
    """Reject payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'REJECTED'
    payment.save()
    messages.success(request, 'Payment rejected.')
    return redirect('payments:payment_detail', payment_id=payment.id)


@login_required
def payment_add_document(request, payment_id):
    """Add document link to payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        payment.document_source = request.POST.get('document_source')
        payment.document_url = request.POST.get('document_url', '')
        payment.document_path = request.POST.get('document_path', '')
        payment.document_added_date = date.today()
        payment.save()
        messages.success(request, 'Document reference added.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    return render(request, 'payments/payment_document_form.html', {
        'payment': payment,
        'document_sources': Payment.DocumentSource.choices
    })