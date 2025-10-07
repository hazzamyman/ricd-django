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


# Enhanced Analytics and Forecasting Views
class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Advanced analytics dashboard with budget forecasting and anomaly detection"""
    template_name = "portal/analytics_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get program filter
        program_filter = self.request.GET.get('program')

        # Filter projects based on user permissions - capture all projects without date restrictions
        try:
            user_profile = self.request.user.profile
            user_council = user_profile.council
        except:
            user_council = None
        if user_council:
            projects = Project.objects.filter(council=user_council)
        else:
            projects = Project.objects.all()

        # Apply program filter if specified
        if program_filter:
            projects = projects.filter(program_id=program_filter)

        # Get works data for output analytics - capture all without date restrictions
        works_queryset = Work.objects.filter(address__project__in=projects)

        # 1. Enhanced Outputs Analysis
        outputs_by_type = works_queryset.values('output_type_id').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        # Enhanced groupings
        outputs_by_work_type = works_queryset.values('work_type_id').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_bedrooms = works_queryset.values('bedrooms').annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_council = works_queryset.values(
            'address__project__council__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        outputs_by_program = works_queryset.values(
            'address__project__program__name'
        ).annotate(
            total_quantity=Sum('output_quantity'),
            total_cost=Sum('estimated_cost')
        ).order_by('-total_quantity')

        # 2. Project Status Tracking - capture all without date restrictions
        commenced_projects = projects.filter(
            date_physically_commenced__isnull=False
        ).count()

        completed_projects = projects.filter(
            actual_completion__isnull=False
        ).count()

        # Addresses/Projects commenced - capture all without date restrictions
        addresses_commenced = Address.objects.filter(
            project__in=projects,
            project__date_physically_commenced__isnull=False
        ).count()

        # 3. Budget Forecasting and Anomaly Detection - use current date for analysis
        budget_analytics = self.analyze_budget_forecasting(projects, timezone.now().date())

        # 4. Report overdue alerts - check all projects without date restrictions
        report_alerts = self.analyze_report_alerts(projects, timezone.now().date())

        # Combine all alerts
        all_alerts = budget_analytics.get('alerts', []) + report_alerts

        context.update({
            'program_filter': program_filter,
            'programs': Program.objects.all(),
            'outputs_by_type': outputs_by_type,
            'outputs_by_work_type': outputs_by_work_type,
            'outputs_by_bedrooms': outputs_by_bedrooms,
            'outputs_by_council': outputs_by_council,
            'outputs_by_program': outputs_by_program,
            'commenced_projects': commenced_projects,
            'completed_projects': completed_projects,
            'addresses_commenced': addresses_commenced,
            'budget_analytics': budget_analytics,
            'alerts': all_alerts,
            'report_alerts': report_alerts,
            'forecast_summary': budget_analytics.get('forecast_summary', {})
        })

        return context

    def analyze_budget_forecasting(self, projects, analysis_date):
        """Analyze budget spending patterns and detect anomalies"""
        try:
            import numpy as np
        except ImportError:
            np = None

        analytics = {
            'alerts': [],
            'forecast_summary': {},
            'council_spending': [],
            'spending_groups': defaultdict(list)
        }

        # Minimum sample size for confident analysis
        MIN_SAMPLES = 3

        # Get quarterly spending data for the last 6 quarters
        quarters = []
        for i in range(6):
            # Calculate quarter start (first month of quarter)
            quarter_start_month = ((analysis_date.month-1)//3)*3+1
            quarter_start = analysis_date.replace(month=quarter_start_month, day=1)

            # Calculate quarter end (last day of third month in quarter)
            quarter_end_month = min(quarter_start_month + 2, 12)
            _, last_day = calendar.monthrange(analysis_date.year, quarter_end_month)
            quarter_end = quarter_start.replace(month=quarter_end_month, day=last_day)

            quarters.append((quarter_start, quarter_end))

            # Move to previous quarter
            if quarter_start_month == 1:
                analysis_date = analysis_date.replace(year=analysis_date.year-1, month=12)
            else:
                analysis_date = analysis_date.replace(month=quarter_start_month-1)

        quarters.reverse()

        # Analyze spending by council
        council_spending = defaultdict(list)

        # Enhanced like-for-like comparison
        for quarter_start, quarter_end in quarters:
            quarterly_spending = QuarterlyReport.objects.filter(
                submission_date__range=[quarter_start, quarter_end],
                work__address__project__in=projects
            ).values(
                'work__address__project__council__name',
                'work__output_type_id',
                'work__bedrooms'
            ).annotate(
                total_spent=Sum('total_expenditure_council'),
                project_count=Count('work__address__project', distinct=True)
            )

            for entry in quarterly_spending:
                council_name = entry['work__address__project__council__name'] or 'Unknown Council'
                # Group by similar project types for better comparison
                group_key = f"{council_name}_{entry.get('work__output_type_id', 'unknown')}_{entry.get('work__bedrooms', 'unknown')}"

                analytics['spending_groups'][group_key] = analytics['spending_groups'].get(group_key, [])
                analytics['spending_groups'][group_key].append(float(entry['total_spent'] or 0))

            # Also maintain council-level summary for backwards compatibility
            for entry in quarterly_spending:
                council_name = entry['work__address__project__council__name'] or 'Unknown Council'
                council_spending[council_name].append(float(entry['total_spent'] or 0))

        # Enhanced anomaly detection with like-for-like comparison and sample size validation
        if np:
            # Analyze grouped spending (like-for-like comparison)
            for group_key, group_spending in analytics['spending_groups'].items():
                if len(group_spending) >= MIN_SAMPLES:  # Require minimum sample size
                    spending_array = np.array(group_spending)

                    if spending_array.std() > 0:  # Check if there's variance
                        mean_spend = spending_array.mean()
                        std_spend = spending_array.std()

                        current_trend = spending_array[-1]  # Most recent value
                        deviation = abs(current_trend - mean_spend)

                        # Split group key to extract metadata
                        parts = group_key.split('_', 2)
                        council = parts[0]
                        output_type = parts[1] if len(parts) > 1 else 'unknown'
                        bedrooms = parts[2] if len(parts) > 2 else 'unknown'

                        if deviation > 2 * std_spend:  # 2 standard deviations
                            trend = "over-spending" if current_trend > mean_spend else "under-spending"
                            analytics['alerts'].append({
                                'council': council,
                                'group_key': group_key,
                                'output_type': output_type,
                                'bedrooms': bedrooms,
                                'type': trend,
                                'deviation': deviation,
                                'mean': mean_spend,
                                'std': std_spend,
                                'current': current_trend,
                                'severity': 'high',
                                'sample_size': len(group_spending)
                            })

                        elif deviation > std_spend:  # 1 standard deviation
                            trend = "elevated spending" if current_trend > mean_spend else "reduced spending"
                            analytics['alerts'].append({
                                'council': council,
                                'group_key': group_key,
                                'output_type': output_type,
                                'bedrooms': bedrooms,
                                'type': trend,
                                'deviation': deviation,
                                'mean': mean_spend,
                                'current': current_trend,
                                'severity': 'medium',
                                'sample_size': len(group_spending)
                            })

            # Fallback to council-level analysis if no grouped data
            for council, spending_history in council_spending.items():
                if len(spending_history) >= MIN_SAMPLES:
                    spending_array = np.array(spending_history)

                    if spending_array.std() > 0:
                        mean_spend = spending_array.mean()

                        # Forecast next quarter spending
                        if len(spending_history) >= 2:
                            trend_slope = np.polyfit(range(len(spending_history)), spending_history, 1)[0]
                            next_quarter_forecast = spending_history[-1] + trend_slope
                            analytics['forecast_summary'][council] = {
                                'current_avg': mean_spend,
                                'next_forecast': max(0, next_quarter_forecast),
                                'trend': 'increasing' if trend_slope > 0 else 'decreasing',
                                'sample_size': len(spending_history)
                            }

        # Sort alerts by severity
        analytics['alerts'].sort(key=lambda x: ['high', 'medium', 'low'].index(x['severity']))

        return analytics

    def analyze_report_alerts(self, projects, analysis_date):
        """Analyze overdue reports and missing stage reports - only for commenced/under construction projects"""
        alerts = []
        today = analysis_date

        for project in projects:
            # Only require reports for projects that are commenced or under construction
            if project.state not in ['commenced', 'under_construction']:
                continue

            # Check monthly reports - required during construction
            if project.state == 'under_construction':
                last_month = today.replace(day=1) - timezone.timedelta(days=1)
                latest_monthly = MonthlyTracker.objects.filter(
                    work__address__project=project,
                    month__year=last_month.year,
                    month__month=last_month.month
                ).first()

                if not latest_monthly:
                    # Check how many days past due
                    days_overdue = (today - last_month.replace(day=1)).days
                    severity = 'high' if days_overdue >= 14 else 'medium'

                    alerts.append({
                        'type': 'Overdue Monthly Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'days_overdue': days_overdue,
                        'due_month': last_month.strftime('%B %Y'),
                        'project_id': project.id
                    })

            # Check quarterly reports - required for commenced and under construction projects
            latest_quarterly = QuarterlyReport.objects.filter(work__address__project=project).order_by('-submission_date').first()

            if not latest_quarterly:
                # Check how many months have passed since project started
                if project.date_physically_commenced:
                    months_since_start = ((today.year - project.date_physically_commenced.year) * 12 +
                                        (today.month - project.date_physically_commenced.month))

                    if months_since_start >= 3:  # At least 3 months passed
                        # Check when last quarterly was due
                        # Assume quarterly reports are due at end of each quarter
                        current_quarter_start_month = ((today.month-1)//3)*3+1
                        if today.month > current_quarter_start_month:
                            # We're past quarter start, check if quarter ended
                            if today.month > current_quarter_start_month + 2:
                                days_overdue = (today - project.date_physically_commenced).days
                                severity = 'high'

                                alerts.append({
                                    'type': 'Missing Initial Quarterly Report',
                                    'council': project.council.name,
                                    'project': project.name,
                                    'severity': severity,
                                    'months_since_start': months_since_start,
                                    'project_id': project.id
                                })
                elif project.state in ['commenced', 'under_construction']:
                    # Project is active but has no quarterly report ever
                    if project.date_physically_commenced:
                        days_since_start = (today - project.date_physically_commenced).days
                        if days_since_start > 90:  # More than 3 months active
                            alerts.append({
                                'type': 'Missing Quarterly Report',
                                'council': project.council.name,
                                'project': project.name,
                                'severity': 'high',
                                'days_since_start': days_since_start,
                                'project_id': project.id
                            })
            else:
                # Check if quarterly report is overdue (more than 3 months old)
                months_since_last_report = ((today.year - latest_quarterly.submission_date.year) * 12 +
                                          (today.month - latest_quarterly.submission_date.month))
                if months_since_last_report > 3:
                    days_overdue = (today - latest_quarterly.submission_date).days - 90  # 3 months
                    severity = 'high' if months_since_last_report >= 4 else 'medium'

                    alerts.append({
                        'type': 'Overdue Quarterly Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'days_overdue': max(0, days_overdue),
                        'last_report_date': latest_quarterly.submission_date.strftime('%d/%m/%Y'),
                        'project_id': project.id
                    })

            # Check Stage 1 reports - required when past target date but no report submitted
            if project.stage1_target and today > project.stage1_target:
                stage1_reports = Stage1Report.objects.filter(project=project)
                if not stage1_reports.exists():
                    days_overdue = (today - project.stage1_target).days
                    severity = 'high' if days_overdue >= 14 else 'medium'

                    alerts.append({
                        'type': 'Missing Stage 1 Report',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'target_date': project.stage1_target.strftime('%d/%m/%Y'),
                        'days_past_target': days_overdue,
                        'project_id': project.id
                    })

            # Check Stage 2 reports - required when past target date but no report submitted
            if project.stage2_target and today > project.stage2_target:
                stage2_reports = Stage2Report.objects.filter(project=project)
                if not stage2_reports.exists() or not stage2_reports.first().is_complete:
                    days_overdue = (today - project.stage2_target).days
                    severity = 'high' if days_overdue >= 14 else 'medium'
                    report_status = 'Not Submitted' if not stage2_reports.exists() else 'Incomplete'

                    alerts.append({
                        'type': f'Stage 2 Report {report_status}',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'target_date': project.stage2_target.strftime('%d/%m/%Y'),
                        'days_past_target': days_overdue,
                        'project_id': project.id
                    })

            # Check Stage sunset dates
            if project.stage1_sunset and today > project.stage1_sunset:
                stage1_reports = Stage1Report.objects.filter(project=project)
                if not stage1_reports.exists() or not stage1_reports.first().state_accepted:
                    days_overdue = (today - project.stage1_sunset).days
                    severity = 'critical'

                    alerts.append({
                        'type': 'Stage 1 Sunset Date Passed',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'sunset_date': project.stage1_sunset.strftime('%d/%m/%Y'),
                        'days_past_sunset': days_overdue,
                        'project_id': project.id
                    })

            if project.stage2_sunset and today > project.stage2_sunset:
                stage2_reports = Stage2Report.objects.filter(project=project)
                if not stage2_reports.exists() or not stage2_reports.first().is_complete:
                    days_overdue = (today - project.stage2_sunset).days
                    severity = 'critical'

                    alerts.append({
                        'type': 'Stage 2 Sunset Date Passed',
                        'council': project.council.name,
                        'project': project.name,
                        'severity': severity,
                        'sunset_date': project.stage2_sunset.strftime('%d/%m/%Y'),
                        'days_past_sunset': days_overdue,
                        'project_id': project.id
                    })

        # Sort alerts by severity (critical > high > medium)
        def get_severity_order(severity):
            order = {'critical': 0, 'high': 1, 'medium': 2}
            return order.get(severity, 3)

        alerts.sort(key=lambda x: get_severity_order(x['severity']))

        return alerts