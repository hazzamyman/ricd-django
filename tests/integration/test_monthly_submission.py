import pytest
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from ricd.models import Council, Program, Project, Address, Work, QuarterlyReport, MonthlyTracker
from ricd.models import WorkType, OutputType, UserProfile
from django.urls import reverse
from django.utils import timezone


class TestMonthlySubmission(TestCase):
    """Test monthly report submission workflow"""

    def setUp(self):
        """Set up test data"""

        # Create council user
        self.user = User.objects.create_user(
            username='counciluser',
            email='council@example.com',
            password='password123'
        )

        # Create UserProfile to link user to council
        self.council = Council.objects.create(name="Council Monthly Test")
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            council=self.council
        )

        # Create program and project
        self.program = Program.objects.create(name="Monthly Program")
        self.project = Project.objects.create(
            name="Monthly Test Project",
            council=self.council,
            program=self.program,
            state='under_construction',  # Required for monthly reports
            start_date=timezone.now().date() - timezone.timedelta(days=30)
        )

        # Create work and address
        self.work_type = WorkType.objects.create(name="Monthly Work", code="MW", is_active=True)
        self.output_type = OutputType.objects.create(name="Test Output", code="TO", is_active=True)

        self.address = Address.objects.create(
            project=self.project,
            street="123 Monthly Street",
            suburb="Monthly Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=self.work_type,
            output_type_id=self.output_type
        )

        self.work = Work.objects.create(
            address=self.address,
            work_type_id=self.work_type,
            output_type_id=self.output_type,
            output_quantity=1
        )

        self.client = Client()
        self.client.login(username='counciluser', password='password123')

    @pytest.mark.django_db
    def test_monthly_submission_form_renders(self):
        """Test that monthly report form renders correctly for council user"""
        url = reverse('portal:monthly_report')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Monthly Tracker Form')  # Template should contain form elements

    @pytest.mark.django_db
    def test_monthly_submission_success(self):
        """Test successful monthly report submission"""
        url = reverse('portal:monthly_report')

        # Submit monthly report form
        form_data = {
            'work': self.work.pk,
            'month': '2024-12-01',
            'progress_notes': 'Test monthly progress notes',
            'design_tender_date': '2024-12-15',
            'construction_tender_date': '2024-12-20',
        }

        response = self.client.post(url, form_data, follow=True)

        # Should redirect to council dashboard
        self.assertRedirects(response, reverse('portal:council_dashboard'))

        # Should create MonthlyTracker instance
        monthly = MonthlyTracker.objects.filter(
            work=self.work,
            month='2024-12-01'
        ).first()

        self.assertIsNotNone(monthly)
        self.assertEqual(monthly.progress_notes, 'Test monthly progress notes')

        # Should show success message
        messages = list(response.context['messages'])
        self.assertTrue(any('Monthly report submitted successfully!' in str(msg) for msg in messages))

    @pytest.mark.django_db
    def test_monthly_submission_without_work(self):
        """Test monthly report submission when user has no associated work"""
        # Remove user's council association temporarily
        self.user_profile.council = None
        self.user_profile.save()

        url = reverse('portal:monthly_report')
        response = self.client.get(url)

        # Should still render (form might be empty but should not crash)
        self.assertEqual(response.status_code, 200)

    @pytest.mark.django_db
    def test_monthly_submission_invalid_data(self):
        """Test monthly report submission with invalid data"""
        url = reverse('portal:monthly_report')

        # Submit with missing required fields
        form_data = {
            'work': '',
            'month': '',
        }

        response = self.client.post(url, form_data)

        # Should return to form with errors
        self.assertEqual(response.status_code, 200)

        # Should contain error messages in context
        self.assertIn('Please correct the errors below.', str(response.content))

    @pytest.mark.django_db
    def test_monthly_submission_duplicate_month(self):
        """Test duplicate monthly report for same work and month"""
        # Create existing monthly report
        MonthlyTracker.objects.create(
            work=self.work,
            month='2024-12-01',
            progress_notes='Existing report'
        )

        url = reverse('portal:monthly_report')

        # Try to submit another report for same month
        form_data = {
            'work': self.work.pk,
            'month': '2024-12-01',
            'progress_notes': 'Duplicate report',
        }

        response = self.client.post(url, form_data)

        # Should handle duplicate gracefully (either accept or show error)
        # For this implementation, Django will create a duplicate since no unique constraint
        self.assertEqual(response.status_code, 302)  # Redirect on success

    @pytest.mark.django_db
    def test_monthly_submission_form_fields(self):
        """Test that monthly submission form contains expected fields"""
        url = reverse('portal:monthly_report')
        response = self.client.get(url)

        # Form should contain expected fields
        self.assertContains(response, 'name="work"')
        self.assertContains(response, 'name="month"')
        self.assertContains(response, 'name="progress_notes"')

        # Should include available work options for user
        # This depends on template implementation

    @pytest.mark.django_db
    def test_copy_from_previous_month(self):
        """Test the copy_from_previous_month functionality"""
        # Create previous month data
        previous_month = timezone.now().date() - timezone.timedelta(days=30)
        MonthlyTracker.objects.create(
            work=self.work,
            month=previous_month.replace(day=1),
            progress_notes='Previous month notes',
            design_tender_date=timezone.now().date()
        )

        # Create current month tracker
        current_month = timezone.now().date()
        tracker = MonthlyTracker.objects.create(
            work=self.work,
            month=current_month.replace(day=1),
            progress_notes=''
        )

        # Test copy functionality
        copied = tracker.copy_from_previous()

        self.assertTrue(copied)
        tracker.refresh_from_db()
        self.assertEqual(tracker.progress_notes, 'Previous month notes')
        self.assertEqual(tracker.design_tender_date, timezone.now().date())


class TestQuarterlyReportIntegration(TestCase):
    """Test quarterly report workflow with monthly data"""

    def setUp(self):
        """Set up quarterly report test data"""

        # Create council with user
        self.user = User.objects.create_user(
            username='quarterly_council',
            email='quarterly@example.com',
            password='password123'
        )

        self.council = Council.objects.create(name="Quarterly Council")
        UserProfile.objects.create(
            user=self.user,
            council=self.council
        )

        self.program = Program.objects.create(name="Quarterly Program")
        self.work_type = WorkType.objects.create(name="Q Work", code="QW", is_active=True)
        self.output_type = OutputType.objects.create(name="Q Output", code="QO", is_active=True)

    @pytest.mark.django_db
    def test_council_can_submit_quarterly_report(self):
        """Test that council can submit quarterly reports for their projects"""
        # Create project and work
        project = Project.objects.create(
            name="Quarterly Project",
            council=self.council,
            program=self.program,
            state='commenced'
        )

        address = Address.objects.create(
            project=project,
            street="123 Q Street",
            suburb="Q Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=self.work_type,
            output_type_id=self.output_type
        )

        work = Work.objects.create(
            address=address,
            work_type_id=self.work_type,
            output_type_id=self.output_type
        )

        # Login as council user
        self.client = Client()
        self.client.login(username='quarterly_council', password='password123')

        # Submit quarterly report
        url = reverse('portal:quarterly_report')
        form_data = {
            'work': work.pk,
            'percentage_works_completed': 25.5,
            'total_expenditure_council': 15000,
            'total_employed_people': 5,
            'comments_indigenous_employment': 'Test indigenous employment',
            'adverse_matters': 'Test matters',
            'summary_notes': 'Quarterly summary',
        }

        response = self.client.post(url, form_data, follow=True)

        # Should redirect to dashboard
        self.assertRedirects(response, reverse('portal:council_dashboard'))

        # Should create quarterly report
        quarterly_report = QuarterlyReport.objects.filter(
            work=work,
            percentage_works_completed=25.5
        ).first()

        self.assertIsNotNone(quarterly_report)
        self.assertEqual(quarterly_report.total_employed_people, 5)

    @pytest.mark.django_db
    def test_ricd_staff_assessment_fields(self):
        """Test that RICD staff assessment fields are blank on creation"""

        # Create quarterly report
        project = Project.objects.create(
            name="Staff Assessment Project",
            council=self.council,
            program=self.program
        )

        address = Address.objects.create(
            project=project,
            street="456 Staff Street",
            suburb="Staff Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=self.work_type,
            output_type_id=self.output_type
        )

        work = Work.objects.create(
            address=address,
            work_type_id=self.work_type,
            output_type_id=self.output_type
        )

        report = QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=50.0
        )

        # RICD fields should be blank on council submission
        self.assertIsNone(report.staff_assessment_notes)
        self.assertIsNone(report.staff_assessed_date)
        self.assertEqual(report.manager_decision, 'pending')
        self.assertIsNone(report.manager_comments)
        self.assertIsNone(report.manager_decision_date)