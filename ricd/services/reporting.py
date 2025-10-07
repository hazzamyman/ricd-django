from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date
from loguru import logger
from ..models import Council, Project, Work, Address, MonthlyReport, CouncilQuarterlyReport, QuarterlyReport


class ReportService:
    """Service class for reporting business logic"""

    @staticmethod
    def get_active_projects(council):
        """Get active projects for a council (commenced and under_construction)"""
        return council.projects.filter(state__in=[
            'commenced', 'under_construction'
        ]).prefetch_related('addresses', 'works')

    @staticmethod
    def prepare_report_data(council):
        """Prepare report data for monthly/quarterly reports"""
        active_projects = ReportService.get_active_projects(council)
        logger.info(f"Preparing report data for council {council.id}: {len(active_projects)} active projects")
        report_data = []

        for project in active_projects:
            for address in project.addresses.all():
                # For each address, list the works on that address
                works = project.works.filter(address_line__icontains=address.street if address.street else '')
                for work in works:
                    report_data.append({
                        'project': project,
                        'address': address,
                        'work_type': work.work_type_id.name if work.work_type_id else 'Unknown',
                        'output': work.output_type_id.name if work.output_type_id else 'Unknown',
                        'progress': None,  # Will be input in form
                        'notes': None,  # Will be in form
                    })

        logger.info(f"Report data prepared: {len(report_data)} items")
        return report_data

    @staticmethod
    def get_or_create_monthly_report(council, period_date):
        """Get or create MonthlyReport for council and period"""
        monthly_report, created = MonthlyReport.objects.get_or_create(
            council=council,
            period=period_date
        )
        if created:
            logger.info(f"Created new monthly report for council {council.id}, period {period_date}")
        else:
            logger.debug(f"Retrieved existing monthly report for council {council.id}, period {period_date}")
        return monthly_report, created

    @staticmethod
    def get_or_create_council_quarterly_report(council, period_date):
        """Get or create CouncilQuarterlyReport for council and period"""
        quarterly_report, created = CouncilQuarterlyReport.objects.get_or_create(
            council=council,
            period=period_date
        )
        return quarterly_report, created

    @staticmethod
    def parse_period_to_date(period, is_quarterly=False):
        """Parse period string to date object"""
        if is_quarterly:
            # Assume period is like '2025-Q1'
            year, quarter = period.split('-')
            quarter_num = int(quarter[1])
            month = (quarter_num - 1) * 3 + 1
            period_date = date(int(year), month, 1)
        else:
            # Monthly: YYYY-MM
            period_date = datetime.strptime(period, '%Y-%m').date().replace(day=1)
        return period_date

    @staticmethod
    def get_project_quarterly_summary(project, quarter_str):
        """Get aggregated summary for all works in a project for a specific quarter"""
        reports = QuarterlyReport.objects.filter(work__address__project=project, quarter=quarter_str)

        if not reports:
            return {}

        summary = {
            'works_completed_avg': reports.aggregate(avg=models.Avg('percentage_works_completed'))['avg'] or 0,
            'total_budget': sum(report.work.estimated_cost or 0 for report in reports),
            'total_expenditure': reports.aggregate(total=models.Sum('total_expenditure_council'))['total'] or 0,
            'total_unspent': sum((report.unspent_funding or 0) for report in reports),
            'total_employed': reports.aggregate(total=models.Sum('total_employed_people'))['total'] or 0,
            'total_indigenous': reports.aggregate(total=models.Sum('total_indigenous_employed'))['total'] or 0,
            'work_reports': reports
        }

        return summary

    @staticmethod
    def calculate_report_totals(reports):
        """Calculate totals for a set of reports"""
        total_contributions = Decimal('0.00')
        total_expenditure = Decimal('0.00')
        total_unspent = Decimal('0.00')

        for report in reports:
            if report.total_contributions:
                total_contributions += report.total_contributions
            if report.total_expenditure_council:
                total_expenditure += report.total_expenditure_council
            if report.unspent_funding:
                total_unspent += report.unspent_funding

        return {
            'total_contributions': total_contributions,
            'total_expenditure': total_expenditure,
            'total_unspent': total_unspent,
        }

    @staticmethod
    def check_payment_due(report):
        """Check if payments are due based on report approval"""
        if isinstance(report, QuarterlyReport):
            return {
                'stage1_payment_due': report.stage1_payment_due,
                'stage2_payment_due': report.stage2_payment_due,
            }
        return {}

    @staticmethod
    def copy_previous_monthly_tracker(current_tracker):
        """Copy data from previous month's tracker"""
        return current_tracker.copy_from_previous()