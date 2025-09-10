import pytest
from decimal import Decimal
from django.utils import timezone
from ricd.models import MonthlyTracker, QuarterlyReport, Work


class TestMonthlyTracker:
    """Test MonthlyTracker model functionality"""

    @pytest.mark.django_db
    def test_monthly_tracker_creation(self, work):
        """Test basic monthly tracker creation with required fields"""
        tracker = MonthlyTracker.objects.create(
            work=work,
            month=timezone.now().date().replace(day=1),
            progress_notes="Work is progressing well"
        )

        assert tracker.work == work
        assert tracker.month == timezone.now().date().replace(day=1)
        assert tracker.progress_notes == "Work is progressing well"

    @pytest.mark.django_db
    def test_monthly_tracker_copy_from_previous(self, work):
        """Test copying data from previous month's tracker"""
        current_month = timezone.now().date().replace(day=1)
        previous_month = (current_month - timezone.timedelta(days=1)).replace(day=1)

        # Create previous month's tracker
        previous_tracker = MonthlyTracker.objects.create(
            work=work,
            month=previous_month,
            design_tender_date=previous_month + timezone.timedelta(days=5),
            earthworks_date=previous_month + timezone.timedelta(days=10)
        )

        # Create current month tracker
        current_tracker = MonthlyTracker.objects.create(
            work=work,
            month=current_month
        )

        # Copy from previous month
        result = current_tracker.copy_from_previous()

        assert result is True
        current_tracker.refresh_from_db()
        assert current_tracker.design_tender_date == previous_tracker.design_tender_date
        assert current_tracker.earthworks_date == previous_tracker.earthworks_date

    @pytest.mark.django_db
    def test_monthly_tracker_return_false_when_no_previous(self, work):
        """Test copy_from_previous returns False when no previous tracker exists"""
        current_month = timezone.now().date().replace(day=1)
        tracker = MonthlyTracker.objects.create(work=work, month=current_month)

        result = tracker.copy_from_previous()
        assert result is False

    @pytest.mark.django_db
    def test_monthly_tracker_string_representation(self, work):
        """Test monthly tracker __str__ method"""
        tracker = MonthlyTracker.objects.create(
            work=work,
            month=timezone.now().date().replace(day=1)
        )

        expected = f"{work} - {tracker.month.strftime('%B %Y')}"
        assert str(tracker) == expected


class TestQuarterlyReport:
    """Test QuarterlyReport model functionality"""

    @pytest.mark.django_db
    def test_quarterly_report_creation(self, work):
        """Test basic quarterly report creation"""
        report = QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=Decimal('75.5'),
            submission_date=timezone.now().date(),
            total_expenditure_council=Decimal('150000.00'),
            total_employed_people=10,
            adverse_matters="Minor delays due to weather"
        )

        assert report.work == work
        assert report.percentage_works_completed == Decimal('75.5')
        assert report.total_expenditure_council == Decimal('150000.00')
        assert report.total_employed_people == 10

    @pytest.mark.django_db
    def test_quarterly_report_quarter_auto_generation(self, work):
        """Test automatic quarter field generation"""
        # Test Q1: January-March
        jan_date = timezone.now().date().replace(month=1, day=15)
        report_jan = QuarterlyReport.objects.create(
            work=work,
            submission_date=jan_date
        )
        assert report_jan.quarter == f"Jan-Mar {jan_date.year}"

        # Test Q2: April-June
        apr_date = timezone.now().date().replace(month=4, day=15)
        report_apr = QuarterlyReport.objects.create(
            work=work,
            submission_date=apr_date
        )
        assert report_apr.quarter == f"Apr-Jun {apr_date.year}"

        # Test Q3: July-September
        jul_date = timezone.now().date().replace(month=7, day=15)
        report_jul = QuarterlyReport.objects.create(
            work=work,
            submission_date=jul_date
        )
        assert report_jul.quarter == f"Jul-Sep {jul_date.year}"

        # Test Q4: October-December
        oct_date = timezone.now().date().replace(month=10, day=15)
        report_oct = QuarterlyReport.objects.create(
            work=work,
            submission_date=oct_date
        )
        assert report_oct.quarter == f"Oct-Dec {oct_date.year}"

    @pytest.mark.django_db
    def test_quarterly_report_manual_quarter_override(self, work):
        """Test that manual quarter setting overrides auto-generation"""
        report = QuarterlyReport.objects.create(
            work=work,
            submission_date=timezone.now().date(),
            quarter="Custom Quarter 2024"
        )

        assert report.quarter == "Custom Quarter 2024"

    @pytest.mark.django_db
    def test_quarterly_report_string_representation(self, work):
        """Test quarterly report __str__ method"""
        report = QuarterlyReport.objects.create(
            work=work,
            submission_date=timezone.now().date()
        )

        year = timezone.now().year
        expected = f"{work} - {report.quarter}"
        assert str(report) == expected

    @pytest.mark.django_db
    def test_quarterly_report_total_contributions(self, work):
        """Test total contributions calculation"""
        report = QuarterlyReport.objects.create(
            work=work,
            submission_date=timezone.now().date(),
            council_contributions_amount=Decimal('50000'),
            other_contributions_amount=Decimal('25000')
        )

        assert report.total_contributions == Decimal('75000')

    @pytest.mark.django_db
    def test_quarterly_report_unspent_funding(self, work):
        """Test unspent funding calculation"""
        # Set estimated cost on work
        work.estimated_cost = Decimal('200000')
        work.save()

        report = QuarterlyReport.objects.create(
            work=work,
            submission_date=timezone.now().date(),
            total_expenditure_council=Decimal('150000')
        )

        assert report.unspent_funding == Decimal('50000')