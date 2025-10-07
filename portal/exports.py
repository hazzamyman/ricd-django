from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Sum, Count
from django.utils import timezone
from django.utils.dateformat import format
from django import forms
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from collections import defaultdict
import calendar
import logging

from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View
import json
from ricd.models import (
    Project, Program, Council, QuarterlyReport, MonthlyTracker, Stage1Report, Stage2Report,
    FundingSchedule, Address, Work, WorkStep, FundingApproval, WorkType, OutputType, ConstructionMethod, Officer,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement,
    RemoteCapitalProgramFundingAgreement, Defect, UserProfile, FieldVisibilitySetting,
    MonthlyTrackerItem, MonthlyTrackerItemGroup, QuarterlyReportItem, QuarterlyReportItemGroup,
    Stage1Step, Stage1StepGroup, Stage2Step, Stage2StepGroup, ProjectReportConfiguration,
    MonthlyTrackerEntry, QuarterlyReportItemEntry, Stage1StepCompletion, Stage2StepCompletion,
    SiteConfiguration
)
from .forms import (
    MonthlyTrackerForm, QuarterlyReportForm, Stage1ReportForm, Stage2ReportForm,
    CouncilForm, ProgramForm, ProjectForm, ProjectStateForm, AddressForm, WorkForm,
    WorkTypeForm, OutputTypeForm, ConstructionMethodForm, ForwardRemoteProgramFundingAgreementForm,
    InterimForwardProgramFundingAgreementForm, RemoteCapitalProgramFundingAgreementForm,
    UserCreationForm, OfficerForm, OfficerAssignmentForm, FundingApprovalForm,
    CustomExcelExportForm, DefectForm, CouncilUserCreationForm, CouncilUserUpdateForm,
    MonthlyTrackerItemForm, MonthlyTrackerItemGroupForm, QuarterlyReportItemForm,
    Stage1StepForm, Stage2StepForm, ProjectReportConfigurationForm,
    MonthlyTrackerEntryForm, QuarterlyReportItemEntryForm, Stage1StepCompletionForm, Stage2StepCompletionForm,
    SiteConfigurationForm
)


# Export Views
class AddressWorkExportView(LoginRequiredMixin, View):
    """Export all addresses and works data to Excel format"""

    def get(self, request, *args, **kwargs):
        import pandas as pd
        from django.http import HttpResponse

        # Get all addresses with related data
        addresses = Address.objects.select_related(
            'project', 'project__council', 'project__program',
            'work_type_id', 'output_type_id'
        ).all()

        selected_fields = request.GET.getlist('fields')

        # Default fields if none selected
        if not selected_fields:
            selected_fields = [
                'State', 'Project', 'Council', 'Program', 'Street', 'Suburb',
                'Postcode', 'Work Type', 'Output Type', 'Bedrooms',
                'Output Quantity', 'Estimated Cost', 'Actual Cost',
                'Start Date', 'End Date'
            ]

        # Prepare data for export
        data = []
        for address in addresses:
            # Get associated works for this address
            works = Work.objects.filter(address=address).select_related('work_type_id', 'output_type_id')

            if works.exists():
                # Create a row for each work at this address
                for work in works:
                    full_row = {
                        'State': address.state or '',
                        'Project': address.project.name,
                        'Council': address.project.council.name if address.project.council else '',
                        'Program': address.project.program.name if address.project.program else '',
                        'Street': address.street,
                        'Suburb': address.suburb or '',
                        'Postcode': address.postcode or '',
                        'Work Type': work.work_type_id.name if work.work_type_id else '',
                        'Output Type': work.output_type_id.name if work.output_type_id else '',
                        'Bedrooms': work.bedrooms or '',
                        'Output Quantity': work.output_quantity or 1,
                        'Estimated Cost': work.estimated_cost or '',
                        'Actual Cost': work.actual_cost or '',
                        'Start Date': work.start_date.strftime('%Y-%m-%d') if work.start_date else '',
                        'End Date': work.end_date.strftime('%Y-%m-%d') if work.end_date else '',
                        'Land Status': work.land_status or '',
                        'Floor Method': work.floor_method or '',
                        'Frame Method': work.frame_method or '',
                        'External Wall Method': work.external_wall_method or '',
                        'Roof Method': work.roof_method or '',
                        'Car Accommodation': work.car_accommodation or '',
                        'Additional Facilities': work.additional_facilities or '',
                        'Extension High Low': work.extension_high_low or '',
                        'Bathrooms': work.bathrooms or '',
                        'Kitchens': work.kitchens or '',
                        'Dwellings Count': work.dwellings_count or '',
                        'Lot Number': address.lot_number or '',
                        'Plan Number': address.plan_number or '',
                        'Title Reference': address.title_reference or '',
                    }
                    # Filter to only selected fields
                    row = {field: full_row[field] for field in selected_fields if field in full_row}
                    data.append(row)
            else:
                # Address without work data
                full_row = {
                    'State': address.state or '',
                    'Project': address.project.name,
                    'Council': address.project.council.name if address.project.council else '',
                    'Program': address.project.program.name if address.project.program else '',
                    'Street': address.street,
                    'Suburb': address.suburb or '',
                    'Postcode': address.postcode or '',
                    'Work Type': '',
                    'Output Type': '',
                    'Bedrooms': '',
                    'Output Quantity': '',
                    'Estimated Cost': '',
                    'Actual Cost': '',
                    'Start Date': '',
                    'End Date': '',
                    'Land Status': '',
                    'Floor Method': '',
                    'Frame Method': '',
                    'External Wall Method': '',
                    'Roof Method': '',
                    'Car Accommodation': '',
                    'Additional Facilities': '',
                    'Extension High Low': '',
                    'Bathrooms': '',
                    'Kitchens': '',
                    'Dwellings Count': '',
                    'Lot Number': address.lot_number or '',
                    'Plan Number': address.plan_number or '',
                    'Title Reference': address.title_reference or '',
                }
                # Filter to only selected fields
                row = {field: full_row[field] for field in selected_fields if field in full_row}
                data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data)

        # Create Excel file
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="addresses_and_works_export.xlsx"'

        try:
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Addresses and Works', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Addresses and Works']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Max width of 50
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        except ImportError:
            # Fallback without pandas if not available
            response = HttpResponse("Excel export requires pandas and openpyxl libraries to be installed.", content_type='text/plain')

        return response


class CustomExportView(LoginRequiredMixin, TemplateView):
    """View for configuring custom Excel export with field selection"""
    template_name = 'portal/custom_export.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomExcelExportForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CustomExcelExportForm(request.POST)
        if form.is_valid():
            selected_fields = form.cleaned_data['fields']
            # Redirect to export view with selected fields as URL parameters
            from django.shortcuts import redirect
            from urllib.parse import urlencode

            query_string = urlencode({'fields': selected_fields}, doseq=True)
            return redirect(f'/analytics/export/addresses-works/?{query_string}')
        else:
            return self.render_to_response({'form': form})