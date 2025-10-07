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
class EnhancedMonthlyTrackerView(LoginRequiredMixin, TemplateView):
    """
    Enhanced monthly tracker table view with the specific layout requested.

    Key Features:
    - Direct inline editing of tracker cells without opening separate forms
    - Live updates: Council users can update data for any month at any time
    - Dynamic work handling: Automatically adapts to new/removed work addresses each month
    - Submission deadline awareness: Tracks 8th of month deadline but allows continuous updates
    - Batch saving: Save button submits all form data at once
    """

    template_name = "portal/enhanced_monthly_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Add submission deadline information
        context['submission_deadline'] = self.get_submission_deadline_info()

        # Add last submission information
        context['last_submission_info'] = self.get_last_submission_info()

        # Get all active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Group projects by their funding agreements
        funding_agreements_data = self.group_projects_by_funding_agreements(active_projects)

        # Create entry forms for workflow management
        entry_forms = self.create_entry_forms(funding_agreements_data)

        context.update({
            'funding_agreements_data': funding_agreements_data,
            'is_ricd': is_ricd,
            'user_council': user_council,
            'user': self.request.user,  # Add user for template workflow checks
            'entry_forms': entry_forms,  # Add forms for workflow management
        })

        return context

    def group_projects_by_funding_agreements(self, projects):
        """Group projects by their funding agreements and prepare table data"""
        from collections import defaultdict

        # Get all monthly tracker items that are active
        tracker_items = MonthlyTrackerItem.objects.filter(is_active=True).order_by('order')
        tracker_items_list = list(tracker_items)

        # Track active entries for cleanup
        self._active_entry_ids = set()

        funding_groups = defaultdict(list)

        for project in projects:
            # Determine which funding agreement this project belongs to
            funding_agreement_name = self.get_funding_agreement_name(project)

            # Get all addresses for this project
            addresses_with_work = Address.objects.filter(
                project=project
            ).select_related('work_type_id', 'output_type_id')

            # Prepare address work data with tracker items
            work_data = []
            for address in addresses_with_work:
                # Skip addresses without work type information
                if not address.work_type_id or not address.output_type_id:
                    continue

                # Get or create the Work object for this address
                work = Work.objects.filter(address=address).first()
                if not work:
                    # Create Work from address data
                    work = Work.objects.create(
                        address=address,
                        work_type_id=address.work_type_id,
                        output_type_id=address.output_type_id,
                        bedrooms=address.bedrooms,
                        output_quantity=address.output_quantity or 1,
                        estimated_cost=address.budget,
                        actual_cost=None,
                        start_date=project.date_physically_commenced,
                        end_date=None
                    )

                work_info = {
                    'work': work,  # Use the Work object
                    'address': address,
                    'tracker_values': {}
                }

                # For each tracker item, determine if it's applicable and get value
                for item in tracker_items_list:
                    tracker_value = self.get_tracker_value_for_address(address, item, project)
                    work_info['tracker_values'][item.id] = tracker_value

                    # Track active entries for cleanup of removed works
                    if tracker_value.get('entry_id'):
                        self._active_entry_ids.add(tracker_value['entry_id'])

                work_data.append(work_info)

            # Always include the project, even if it has no works (but only if it's active)
            if work_data:
                funding_groups[funding_agreement_name].extend(work_data)
            else:
                # Create a placeholder entry for projects without works
                funding_groups[funding_agreement_name].append({
                    'project': project,
                    'work': None,
                    'address': None,
                    'tracker_values': {}
                })

        # Convert to list format for template
        result = []
        for agreement_name, works_list in funding_groups.items():
            result.append({
                'funding_agreement': agreement_name,
                'works': works_list
            })

        # Clean up orphaned entries for removed works
        self.cleanup_orphaned_entries()

        return {
            'tracker_items': tracker_items_list,
            'funding_groups': result,
            'total_columns': len(tracker_items_list) + 1  # +1 for the work address column
        }

    def get_funding_agreement_name(self, project):
        """Get the funding agreement name for a project"""
        if project.funding_schedule:
            if project.funding_schedule.agreement_type == 'rcpf_agreement':
                return f"Remote Capital Program Funding Agreement - {project.funding_schedule.funding_schedule_number}"
            else:
                return f"Funding Schedule {project.funding_schedule.funding_schedule_number}"
        elif project.forward_rpf_agreement:
            return "Forward Remote Program Funding Agreement"
        elif project.interim_fp_agreement:
            return "Interim Forward Remote Program Funding Agreement"
        else:
            return "No Funding Agreement"

    def get_tracker_value_for_address(self, address, tracker_item, project):
        """Determine the value to display for a specific address and tracker item"""
        from datetime import date
        from django.utils import timezone

        # Check if this tracker item is configured for this project
        try:
            config = project.report_configuration
            # Check if this tracker item is in any of the project's configured groups
            applicable_groups = config.monthly_tracker_groups.all()
            item_in_groups = any(
                tracker_item in group.tracker_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is applicable by default
            # Fall through to check for actual data
            pass

        # Item is applicable, check if there's actual data
        try:
            # Get the Work for this address (should already exist from the main method)
            work = Work.objects.filter(address=address).first()

            if not work:
                # This shouldn't happen, but handle it gracefully
                return {
                    'value': '',
                    'display': '',
                    'applicable': False
                }

            # Get the most recent monthly tracker for this work
            latest_tracker = MonthlyTracker.objects.filter(work=work).order_by('-month').first()

            # If no tracker exists, create one for the current month
            if not latest_tracker:
                # Get current month and year
                current_date = timezone.now().date()
                current_month = date(current_date.year, current_date.month, 1)

                # Check if project has commenced
                if project.state in ['commenced', 'under_construction'] and project.date_physically_commenced:
                    # Create new monthly tracker for current month
                    latest_tracker = MonthlyTracker.objects.create(
                        work=work,
                        month=current_month,
                        # Set other default values as needed
                        total_construction_cost=work.estimated_cost or 0,
                        total_expenditure_council=0,
                        total_expenditure_ricd=0,
                        percentage_works_completed=0
                    )

            if latest_tracker:
                # Try to get the value from the tracker entry
                try:
                    entry = MonthlyTrackerEntry.objects.get(
                        monthly_tracker=latest_tracker,
                        tracker_item=tracker_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_tracker_value(entry.value, tracker_item),
                        'applicable': True,
                        'has_data': True,
                        'entry': entry,
                        'entry_id': entry.id
                    }
                except MonthlyTrackerEntry.DoesNotExist:
                    # Create the entry if it doesn't exist and item is applicable
                    if tracker_item.is_active:
                        entry = MonthlyTrackerEntry.objects.create(
                            monthly_tracker=latest_tracker,
                            tracker_item=tracker_item,
                            value=None,  # Start with no value
                            workflow_status='draft'
                        )
                        return {
                            'value': '',
                            'display': '',
                            'applicable': True,
                            'has_data': False,
                            'entry': entry,
                            'entry_id': entry.id
                        }
        except Exception:
            # Handle any exceptions gracefully
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if tracker_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }

    def create_entry_forms(self, funding_agreements_data):
        """Create MonthlyTrackerEntryForm instances for all tracker entries"""
        entry_forms = {}

        for funding_group in funding_agreements_data['funding_groups']:
            for work_info in funding_group['works']:
                for tracker_id, tracker_value in work_info['tracker_values'].items():
                    if tracker_value.get('entry'):
                        # Create form with existing entry
                        entry = tracker_value['entry']
                        form = MonthlyTrackerEntryForm(instance=entry)
                        entry_forms[entry.id] = form
                    elif tracker_value.get('entry_id'):
                        # Create form for entry with ID
                        try:
                            entry = MonthlyTrackerEntry.objects.get(id=tracker_value['entry_id'])
                            form = MonthlyTrackerEntryForm(instance=entry)
                            entry_forms[entry.id] = form
                        except MonthlyTrackerEntry.DoesNotExist:
                            pass  # Entry was deleted, skip form creation
                    elif tracker_value.get('applicable') and tracker_value.get('has_data') == False:
                        # Create a new entry for applicable items without data
                        try:
                            tracker_item = MonthlyTrackerItem.objects.get(id=tracker_id)
                            work = work_info.get('work')
                            if work and tracker_item.is_active:
                                # Find the monthly tracker for this work
                                latest_tracker = MonthlyTracker.objects.filter(work=work).order_by('-month').first()
                                if latest_tracker:
                                    entry = MonthlyTrackerEntry.objects.create(
                                        monthly_tracker=latest_tracker,
                                        tracker_item=tracker_item,
                                        value=None,
                                        workflow_status='draft'
                                    )
                                    form = MonthlyTrackerEntryForm(instance=entry)
                                    entry_forms[entry.id] = form
                        except (MonthlyTrackerItem.DoesNotExist, Exception):
                            pass  # Skip if there are any issues

        return entry_forms

    def format_tracker_value(self, value, tracker_item):
        """Format the tracker value for display based on data type"""
        if not value:
            return ''

        if tracker_item.data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif tracker_item.data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif tracker_item.data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)

    def post(self, request, *args, **kwargs):
        """Handle form submissions and workflow approvals for tracker entries"""
        action = request.POST.get('action')

        # Handle workflow approval actions
        if action in ['approve_council_manager', 'approve_ricd_officer']:
            return self.handle_workflow_approval(request, action)

        # Handle regular form submissions
        return self.handle_form_submission(request)

    def handle_form_submission(self, request):
        """Handle regular form submissions for tracker entries with submission status tracking"""
        from django.utils import timezone
        logger = logging.getLogger(__name__)

        success_count = 0
        error_count = 0
        entry_forms = {}
        current_time = timezone.now()

        # Process each form entry in the POST data
        for key in request.POST:
            if key.startswith('form-'):
                parts = key.split('-')
                if len(parts) < 3:
                    continue

                entry_id = parts[1]
                field_name = '-'.join(parts[2:])

                # Initialize form data dictionary for this entry
                if entry_id not in entry_forms:
                    entry_forms[entry_id] = {'id': entry_id}

                # Store the field value
                entry_forms[entry_id][field_name] = request.POST[key]

        # Process each entry form
        for entry_id, data in entry_forms.items():
            try:
                # Get existing entry or prepare for new entry
                if entry_id and entry_id != 'new':
                    try:
                        entry = MonthlyTrackerEntry.objects.get(id=entry_id)
                        form = MonthlyTrackerEntryForm(data, instance=entry)
                    except MonthlyTrackerEntry.DoesNotExist:
                        form = MonthlyTrackerEntryForm(data)
                else:
                    form = MonthlyTrackerEntryForm(data)

                if form.is_valid():
                    saved_entry = form.save()
                    # Set initial workflow status for new entries
                    if saved_entry.workflow_status == 'draft':
                        pass  # Keep as draft initially

                    # Update submission timestamp for tracking
                    if hasattr(saved_entry, 'monthly_tracker'):
                        saved_entry.monthly_tracker.submission_date = current_time
                        saved_entry.monthly_tracker.save()

                    success_count += 1
                else:
                    error_count += 1
                    # Log form errors for debugging
                    logger.error(f"Form errors for entry {entry_id}: {form.errors}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing entry {entry_id}: {str(e)}")

        # Check if this submission meets the deadline requirement (informational only)
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
            submission_deadline = self.get_submission_deadline_info()

            if user_council and success_count > 0:
                # Always allow updates to previous months' data (live updates)
                # Just provide informational feedback about deadlines
                current_time = timezone.now()
                if current_time.day <= 8:
                    messages.info(request, f'Data updated. Monthly tracker remains open for live updates until the 8th of each month.')
                else:
                    messages.info(request, f'Data updated. You can continue to make live updates to previous months\' data.')

                # Log the update for tracking purposes
                logger.info(f"Live update: User {request.user.username} updated {success_count} tracker entries on {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass  # Ignore errors in deadline checking

        # Set appropriate messages
        if success_count > 0:
            messages.success(request, f'Successfully updated {success_count} tracker entries.')
        if error_count > 0:
            messages.error(request, f'Failed to update {error_count} tracker entries. Please check the form for errors.')

        # Redirect to prevent form resubmission
        return redirect(request.path)

    def handle_workflow_approval(self, request, action):
        """Handle workflow approval actions"""
        entry_id = request.POST.get('entry_id')
        comments = request.POST.get('comments', '')

        if not entry_id:
            messages.error(request, 'No entry specified for approval.')
            return redirect(request.path)

        try:
            entry = MonthlyTrackerEntry.objects.get(id=entry_id)

            if action == 'approve_council_manager':
                entry.approve_council_manager(request.user, comments)
                messages.success(request, f'Tracker entry approved as Council Manager.')
            elif action == 'approve_ricd_officer':
                entry.approve_ricd_officer(request.user, comments)
                messages.success(request, f'Tracker entry approved as RICD Officer.')

        except MonthlyTrackerEntry.DoesNotExist:
            messages.error(request, 'Tracker entry not found.')
        except Exception as e:
            messages.error(request, f'Error processing approval: {str(e)}')

        return redirect(request.path)

    def get_submission_deadline_info(self):
        """Get information about the submission deadline for the current month"""
        from django.utils import timezone
        today = timezone.now().date()
class EnhancedQuarterlyTrackerView(LoginRequiredMixin, TemplateView):
    """
    Enhanced quarterly tracker table view with the specific layout requested.
    Similar to EnhancedMonthlyTrackerView but for quarterly tracking with editing capabilities.

    Key Features:
    - Direct inline editing of tracker cells without opening separate forms
    - Live updates: Council users can update data for any quarter at any time
    - Dynamic work handling: Automatically adapts to new/removed work addresses each quarter
    - Submission deadline awareness: Tracks quarterly deadlines but allows continuous updates
    - Batch saving: Save button submits all form data at once
    - Workflow management for approvals
    """

    template_name = "portal/enhanced_quarterly_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user and their council
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        is_ricd = self.request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()

        # Add submission deadline information
        context['submission_deadline'] = self.get_submission_deadline_info()

        # Add last submission information
        context['last_submission_info'] = self.get_last_submission_info()

        # Get all active projects (commenced or under construction)
        if user_council:
            active_projects = Project.objects.filter(
                council=user_council,
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')
        else:
            active_projects = Project.objects.filter(
                state__in=['commenced', 'under_construction']
            ).prefetch_related('addresses__works')

        # Group projects by their funding agreements
        funding_agreements_data = self.group_projects_by_funding_agreements(active_projects)

        # Create entry forms for workflow management
        entry_forms = self.create_entry_forms(funding_agreements_data)

        context.update({
            'funding_agreements_data': funding_agreements_data,
            'is_ricd': is_ricd,
            'user_council': user_council,
            'user': self.request.user,  # Add user for template workflow checks
            'entry_forms': entry_forms,  # Add forms for workflow management
        })

        return context

    def group_projects_by_funding_agreements(self, projects):
        """Group projects by their funding agreements and prepare table data"""
        from collections import defaultdict

        # Get all quarterly tracker items that are active
        tracker_items = QuarterlyReportItem.objects.filter(is_active=True).order_by('order')
        tracker_items_list = list(tracker_items)

        # Track active entries for cleanup
        self._active_entry_ids = set()

        funding_groups = defaultdict(list)

        for project in projects:
            # Determine which funding agreement this project belongs to
            funding_agreement_name = self.get_funding_agreement_name(project)

            # Get all addresses for this project
            addresses_with_work = Address.objects.filter(
                project=project
            ).select_related('work_type_id', 'output_type_id')

            # Prepare address work data with tracker items
            work_data = []
            for address in addresses_with_work:
                # Skip addresses without work type information
                if not address.work_type_id or not address.output_type_id:
                    continue

                # Get or create the Work object for this address
                work = Work.objects.filter(address=address).first()
                if not work:
                    # Create Work from address data
                    work = Work.objects.create(
                        address=address,
                        work_type_id=address.work_type_id,
                        output_type_id=address.output_type_id,
                        bedrooms=address.bedrooms,
                        output_quantity=address.output_quantity or 1,
                        estimated_cost=address.budget,
                        actual_cost=None,
                        start_date=project.date_physically_commenced,
                        end_date=None
                    )

                work_info = {
                    'work': work,  # Use the Work object
                    'address': address,
                    'tracker_values': {}
                }

                # For each tracker item, determine if it's applicable and get value
                for item in tracker_items_list:
                    tracker_value = self.get_tracker_value_for_address(address, item, project)
                    work_info['tracker_values'][item.id] = tracker_value

                    # Track active entries for cleanup of removed works
                    if tracker_value.get('entry_id'):
                        self._active_entry_ids.add(tracker_value['entry_id'])

                work_data.append(work_info)

            # Always include the project, even if it has no works (but only if it's active)
            if work_data:
                funding_groups[funding_agreement_name].extend(work_data)
            else:
                # Create a placeholder entry for projects without works
                funding_groups[funding_agreement_name].append({
                    'project': project,
                    'work': None,
                    'address': None,
                    'tracker_values': {}
                })

        # Convert to list format for template
        result = []
        for agreement_name, works_list in funding_groups.items():
            result.append({
                'funding_agreement': agreement_name,
                'works': works_list
            })

        # Clean up orphaned entries for removed works
        self.cleanup_orphaned_entries()

        return {
            'tracker_items': tracker_items_list,
            'funding_groups': result,
            'total_columns': len(tracker_items_list) + 1  # +1 for the work address column
        }

    def get_funding_agreement_name(self, project):
        """Get the funding agreement name for a project"""
        if project.funding_schedule:
            if project.funding_schedule.agreement_type == 'rcpf_agreement':
                return f"Remote Capital Program Funding Agreement - {project.funding_schedule.funding_schedule_number}"
            else:
                return f"Funding Schedule {project.funding_schedule.funding_schedule_number}"
        elif project.forward_rpf_agreement:
            return "Forward Remote Program Funding Agreement"
        elif project.interim_fp_agreement:
            return "Interim Forward Remote Program Funding Agreement"
        else:
            return "No Funding Agreement"

    def get_tracker_value_for_address(self, address, tracker_item, project):
        """Determine the value to display for a specific address and tracker item"""
        from datetime import date
        from django.utils import timezone

        # Check if this tracker item is configured for this project
        try:
            config = project.report_configuration
            # Check if this tracker item is in any of the project's configured groups
            applicable_groups = config.quarterly_report_groups.all()
            item_in_groups = any(
                tracker_item in group.report_items.all()
                for group in applicable_groups
            )

            if not item_in_groups:
                # Item is not configured for this project
                return {'value': '', 'display': '', 'applicable': False}

        except Project.report_configuration.RelatedObjectDoesNotExist:
            # No configuration exists, so item is applicable by default
            # Fall through to check for actual data
            pass

        # Item is applicable, check if there's actual data
        try:
            # Get the Work for this address (should already exist from the main method)
            work = Work.objects.filter(address=address).first()

            if not work:
                # This shouldn't happen, but handle it gracefully
                return {
                    'value': '',
                    'display': '',
                    'applicable': False
                }

            # Get the most recent quarterly tracker for this work
            latest_tracker = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()

            # If no tracker exists, create one for the current quarter
            if not latest_tracker:
                # Get current date and determine current quarter
                current_date = timezone.now().date()
                current_quarter_start = self.get_quarter_start(current_date)

                # Check if project has commenced
                if project.state in ['commenced', 'under_construction'] and project.date_physically_commenced:
                    # Create new quarterly tracker for current quarter
                    latest_tracker = QuarterlyReport.objects.create(
                        work=work,
                        submission_date=current_quarter_start,
                        # Set other default values as needed
                        total_expenditure_council=0,
                        total_expenditure_ricd=0,
                        percentage_works_completed=0
                    )

            if latest_tracker:
                # Try to get the value from the tracker entry
                try:
                    entry = QuarterlyReportItemEntry.objects.get(
                        quarterly_report=latest_tracker,
                        report_item=tracker_item
                    )
                    return {
                        'value': entry.value,
                        'display': self.format_tracker_value(entry.value, tracker_item),
                        'applicable': True,
                        'has_data': True,
                        'entry': entry,
                        'entry_id': entry.id
                    }
                except QuarterlyReportItemEntry.DoesNotExist:
                    # Create the entry if it doesn't exist and item is applicable
                    if tracker_item.is_active:
                        entry = QuarterlyReportItemEntry.objects.create(
                            quarterly_report=latest_tracker,
                            report_item=tracker_item,
                            value=None,  # Start with no value
                            workflow_status='draft'
                        )
                        return {
                            'value': '',
                            'display': '',
                            'applicable': True,
                            'has_data': False,
                            'entry': entry,
                            'entry_id': entry.id
                        }
        except Exception:
            # Handle any exceptions gracefully
            pass

        # No data exists, return N/A if acceptable, otherwise blank
        if hasattr(tracker_item, 'na_acceptable') and tracker_item.na_acceptable:
            return {
                'value': 'N/A',
                'display': 'N/A',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }
        else:
            return {
                'value': '',
                'display': '',
                'applicable': True,
                'has_data': False,
                'entry': None,
                'entry_id': None
            }

    def get_quarter_start(self, date):
        """Get the start date of the quarter for a given date"""
        quarter = (date.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        return date.replace(month=quarter_start_month, day=1)

    def create_entry_forms(self, funding_agreements_data):
        """Create QuarterlyReportItemEntryForm instances for all tracker entries"""
        entry_forms = {}

        for funding_group in funding_agreements_data['funding_groups']:
            for work_info in funding_group['works']:
                for tracker_id, tracker_value in work_info['tracker_values'].items():
                    if tracker_value.get('entry'):
                        # Create form with existing entry
                        entry = tracker_value['entry']
                        form = QuarterlyReportItemEntryForm(instance=entry)
                        entry_forms[entry.id] = form
                    elif tracker_value.get('entry_id'):
                        # Create form for entry with ID
                        try:
                            entry = QuarterlyReportItemEntry.objects.get(id=tracker_value['entry_id'])
                            form = QuarterlyReportItemEntryForm(instance=entry)
                            entry_forms[entry.id] = form
                        except QuarterlyReportItemEntry.DoesNotExist:
                            pass  # Entry was deleted, skip form creation
                    elif tracker_value.get('applicable') and tracker_value.get('has_data') == False:
                        # Create a new entry for applicable items without data
                        try:
                            tracker_item = QuarterlyReportItem.objects.get(id=tracker_id)
                            work = work_info.get('work')
                            if work and tracker_item.is_active:
                                # Find the quarterly report for this work
                                latest_report = QuarterlyReport.objects.filter(work=work).order_by('-submission_date').first()
                                if latest_report:
                                    entry = QuarterlyReportItemEntry.objects.create(
                                        quarterly_report=latest_report,
                                        report_item=tracker_item,
                                        value=None,
                                        workflow_status='draft'
                                    )
                                    form = QuarterlyReportItemEntryForm(instance=entry)
                                    entry_forms[entry.id] = form
                        except (QuarterlyReportItem.DoesNotExist, Exception):
                            pass  # Skip if there are any issues

        return entry_forms

    def format_tracker_value(self, value, tracker_item):
        """Format the tracker value for display based on data type"""
        if not value:
            return ''

        if hasattr(tracker_item, 'data_type'):
            data_type = tracker_item.data_type
        else:
            data_type = 'text'  # Default fallback

        if data_type == 'date' and value:
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.fromisoformat(value.split('T')[0])
                else:
                    date_obj = value
                return date_obj.strftime('%d/%m/%Y')
            except:
                return str(value)
        elif data_type == 'currency' and value:
            try:
                return f"${float(value):,.2f}"
            except:
                return str(value)
        elif data_type == 'checkbox':
            return '✓' if value else '✗'
        else:
            return str(value)

    def post(self, request, *args, **kwargs):
        """Handle form submissions and workflow approvals for tracker entries"""
        action = request.POST.get('action')

        # Handle workflow approval actions
        if action in ['approve_council_manager', 'approve_ricd_officer']:
            return self.handle_workflow_approval(request, action)

        # Handle regular form submissions
        return self.handle_form_submission(request)

    def handle_form_submission(self, request):
        """Handle regular form submissions for tracker entries with submission status tracking"""
        from django.utils import timezone

        success_count = 0
        error_count = 0
        entry_forms = {}
        current_time = timezone.now()

        # Process each form entry in the POST data
        for key in request.POST:
            if key.startswith('form-'):
                parts = key.split('-')
                if len(parts) < 3:
                    continue

                entry_id = parts[1]
                field_name = '-'.join(parts[2:])

                # Initialize form data dictionary for this entry
                if entry_id not in entry_forms:
                    entry_forms[entry_id] = {'id': entry_id}

                # Store the field value
                entry_forms[entry_id][field_name] = request.POST[key]

        # Process each entry form
        for entry_id, data in entry_forms.items():
            try:
                # Get existing entry or prepare for new entry
                if entry_id and entry_id != 'new':
                    try:
                        entry = QuarterlyReportItemEntry.objects.get(id=entry_id)
                        form = QuarterlyReportItemEntryForm(data, instance=entry)
                    except QuarterlyReportItemEntry.DoesNotExist:
                        form = QuarterlyReportItemEntryForm(data)
                else:
                    form = QuarterlyReportItemEntryForm(data)

                if form.is_valid():
                    saved_entry = form.save()
                    # Set initial workflow status for new entries
                    if saved_entry.workflow_status == 'draft':
                        pass  # Keep as draft initially

                    # Update submission timestamp for tracking
                    if hasattr(saved_entry, 'quarterly_report'):
                        saved_entry.quarterly_report.submission_date = current_time
                        saved_entry.quarterly_report.save()

                    success_count += 1
                else:
                    error_count += 1
                    # Log form errors for debugging
                    print(f"Form errors for entry {entry_id}: {form.errors}")

            except Exception as e:
                error_count += 1
                print(f"Error processing entry {entry_id}: {str(e)}")

        # Check if this submission meets the deadline requirement (informational only)
        try:
            user_profile = request.user.profile
            user_council = user_profile.council
            submission_deadline = self.get_submission_deadline_info()

            if user_council and success_count > 0:
                # Always allow updates to previous quarters' data (live updates)
                # Just provide informational feedback about deadlines
                current_time = timezone.now()
                messages.info(request, f'Data updated. Quarterly tracker remains open for live updates throughout each quarter.')

                # Log the update for tracking purposes
                print(f"Live update: User {request.user.username} updated {success_count} quarterly tracker entries on {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass  # Ignore errors in deadline checking

        # Set appropriate messages
        if success_count > 0:
            messages.success(request, f'Successfully updated {success_count} quarterly tracker entries.')
        if error_count > 0:
            messages.error(request, f'Failed to update {error_count} quarterly tracker entries. Please check the form for errors.')

        # Redirect to prevent form resubmission
        return redirect(request.path)

    def handle_workflow_approval(self, request, action):
        """Handle workflow approval actions"""
        entry_id = request.POST.get('entry_id')
        comments = request.POST.get('comments', '')

        if not entry_id:
            messages.error(request, 'No entry specified for approval.')
            return redirect(request.path)

        try:
            entry = QuarterlyReportItemEntry.objects.get(id=entry_id)

            if action == 'approve_council_manager':
                entry.approve_council_manager(request.user, comments)
                messages.success(request, f'Quarterly tracker entry approved as Council Manager.')
            elif action == 'approve_ricd_officer':
                entry.approve_ricd_officer(request.user, comments)
                messages.success(request, f'Quarterly tracker entry approved as RICD Officer.')

        except QuarterlyReportItemEntry.DoesNotExist:
            messages.error(request, 'Quarterly tracker entry not found.')
        except Exception as e:
            messages.error(request, f'Error processing approval: {str(e)}')

        return redirect(request.path)

    def get_submission_deadline_info(self):
        """Get information about the submission deadline for the current quarter"""
        from django.utils import timezone
        today = timezone.now().date()

        # Calculate the end of the current quarter for deadline
        current_quarter = (today.month - 1) // 3 + 1
        quarter_end_month = current_quarter * 3
        if quarter_end_month > 12:
            quarter_end_month = 12

        # Last day of the quarter
        from calendar import monthrange
        _, last_day = monthrange(today.year, quarter_end_month)
        quarter_end = today.replace(month=quarter_end_month, day=last_day)

        # Calculate days until end of quarter
        days_until_deadline = (quarter_end - today).days + 1  # +1 to include today

        return {
            'deadline_date': quarter_end,
            'days_until_deadline': days_until_deadline,
            'current_quarter': current_quarter,
            'quarter_end_month': quarter_end_month,
            'quarter_year': today.year
        }

    def get_last_submission_info(self):
        """Get information about the last submission for the user's council"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council:
                # Get the most recent quarterly report submission for this council
                last_submission = QuarterlyReport.objects.filter(
                    work__address__project__council=user_council
                ).order_by('-submission_date').first()

                if last_submission:
                    # Calculate which quarter this was
                    quarter = (last_submission.submission_date.month - 1) // 3 + 1
                    quarter_name = f"Q{quarter} {last_submission.submission_date.year}"

                    return {
                        'date': last_submission.submission_date,
                        'quarter': quarter_name,
                        'has_submission': True
                    }
        except:
            pass

        return {
            'date': None,
            'quarter': None,
            'has_submission': False
        }

    def cleanup_orphaned_entries(self):
        """Clean up QuarterlyReportItemEntry objects for removed works"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council and hasattr(self, '_active_entry_ids'):
                # Get all entries for this council's works
                all_entries = QuarterlyReportItemEntry.objects.filter(
                    quarterly_report__work__address__project__council=user_council
                ).values_list('id', flat=True)

                # Find orphaned entries (entries that exist but aren't in active entries)
                orphaned_entry_ids = set(all_entries) - self._active_entry_ids

                if orphaned_entry_ids:
                    # Mark orphaned entries as inactive rather than deleting them
                    # This preserves data integrity and allows for recovery if needed
                    QuarterlyReportItemEntry.objects.filter(id__in=orphaned_entry_ids).update(
                        workflow_status='archived'
                    )
                    print(f"Archived {len(orphaned_entry_ids)} orphaned quarterly tracker entries for council {user_council.name}")

        except Exception as e:
            # Log but don't fail the request if cleanup fails
            print(f"Error during orphaned entry cleanup: {str(e)}")
            pass
        current_day = today.day

        # Calculate the deadline for the previous month (should be submitted by 8th of current month)
        previous_month = today.replace(day=1) - timezone.timedelta(days=1)
        deadline_date = today.replace(day=8)

        # Check if we're past the 8th (deadline has passed for previous month)
        is_past_deadline = current_day > 8

        days_until_deadline = (deadline_date - today).days if not is_past_deadline else 0

        return {
            'deadline_date': deadline_date,
            'is_past_deadline': is_past_deadline,
            'days_until_deadline': days_until_deadline,
            'previous_month': previous_month,
            'current_day': current_day,
            'deadline_day': 8
        }

    def get_last_submission_info(self):
        """Get information about the last submission for the user's council"""
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council:
                # Get the most recent monthly tracker submission for this council
                last_submission = MonthlyTracker.objects.filter(
                    work__address__project__council=user_council
                ).order_by('-submission_date').first()

                if last_submission:
                    return {
                        'date': last_submission.submission_date,
                        'month': last_submission.month.strftime('%B %Y'),
                        'has_submission': True
                    }
        except:
            pass

        return {
            'date': None,
            'month': None,
            'has_submission': False
        }

    def cleanup_orphaned_entries(self):
        """Clean up MonthlyTrackerEntry objects for removed works"""
        logger = logging.getLogger(__name__)
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council

            if user_council and hasattr(self, '_active_entry_ids'):
                # Get all entries for this council's works
                all_entries = MonthlyTrackerEntry.objects.filter(
                    monthly_tracker__work__address__project__council=user_council
                ).values_list('id', flat=True)

                # Find orphaned entries (entries that exist but aren't in active entries)
                orphaned_entry_ids = set(all_entries) - self._active_entry_ids

                if orphaned_entry_ids:
                    # Mark orphaned entries as inactive rather than deleting them
                    # This preserves data integrity and allows for recovery if needed
                    MonthlyTrackerEntry.objects.filter(id__in=orphaned_entry_ids).update(
                        workflow_status='archived'
                    )
                    logger.info(f"Archived {len(orphaned_entry_ids)} orphaned tracker entries for council {user_council.name}")

        except Exception as e:
            # Log but don't fail the request if cleanup fails
            logger.error(f"Error during orphaned entry cleanup: {str(e)}")
            pass