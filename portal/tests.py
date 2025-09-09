from django.test import TestCase
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from ricd.models import (
    Project, Council, Program, FundingApproval, QuarterlyReport, Work, WorkType, OutputType, Address,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement
)


class ProjectStageDatesTestCase(TestCase):
    """Test Project auto-calculate stage dates"""

    def setUp(self):
        self.council = Council.objects.create(name="Test Council")
        self.program = Program.objects.create(name="Test Program")

    def test_stage_dates_calculation(self):
        """Test that stage dates are calculated correctly"""
        start_date = timezone.now().date()
        project = Project.objects.create(
            council=self.council,
            program=self.program,
            name="Test Project",
            start_date=start_date
        )

        # Check calculated dates
        expected_stage1_target = start_date + relativedelta(months=12)
        expected_stage1_sunset = start_date + relativedelta(months=18)
        expected_stage2_target = expected_stage1_target + relativedelta(months=12)
        expected_stage2_sunset = expected_stage1_sunset + relativedelta(months=12)

        self.assertEqual(project.stage1_target, expected_stage1_target)
        self.assertEqual(project.stage1_sunset, expected_stage1_sunset)
        self.assertEqual(project.stage2_target, expected_stage2_target)
        self.assertEqual(project.stage2_sunset, expected_stage2_sunset)


class FundingApprovalTestCase(TestCase):
    """Test Funding Approval linking and display"""

    def setUp(self):
        self.council = Council.objects.create(name="Test Council")
        self.program = Program.objects.create(name="Test Program")
        self.project = Project.objects.create(
            council=self.council,
            program=self.program,
            name="Test Project"
        )

    def test_funding_approval_creation(self):
        """Test that funding approval can be created and linked to projects"""
        approval = FundingApproval.objects.create(
            mincor_reference="TEST-001",
            amount=Decimal("100000.00"),
            approved_by_position="Finance Manager",
            approved_date=timezone.now().date()
        )
        approval.projects.add(self.project)

        # Verify relationship
        self.assertIn(approval, self.project.funding_approvals.all())
        self.assertIn(self.project, approval.projects.all())

    def test_funding_approval_str(self):
        """Test string representation of funding approval"""
        approval = FundingApproval.objects.create(
            mincor_reference="TEST-002",
            amount=Decimal("150000.00"),
            approved_by_position="CEO",
            approved_date=timezone.now().date()
        )
        expected_str = "Approval TEST-002 - $150000.00"
        self.assertEqual(str(approval), expected_str)


class ReportWorkflowTestCase(TestCase):
    """Test Report workflow with staff assessment and manager approval"""

    def setUp(self):
        from ricd.models import Work, WorkType, OutputType

        # Create minimal required objects
        self.council = Council.objects.create(name="Test Council")
        self.program = Program.objects.create(name="Test Program")
        self.project = Project.objects.create(
            council=self.council,
            program=self.program,
            name="Test Project"
        )

        # Create work type and output type
        self.work_type = WorkType.objects.create(code="TEST", name="Test Work", is_active=True)
        self.output_type = OutputType.objects.create(code="TEST", name="Test Output", is_active=True)

    def test_report_workflow_fields(self):
        """Test that report has workflow fields"""
        # Create address and work
        from ricd.models import Address
        address = Address.objects.create(
            project=self.project,
            street="123 Test St",
            suburb="Test Suburb",
            postcode="4000",
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
            submission_date=timezone.now().date()
        )

        # Test default values
        self.assertEqual(report.manager_decision, 'pending')
        self.assertIsNone(report.staff_assessment_notes)

        # Test setting workflow values
        report.staff_assessment_notes = "Staff assessment notes"
        report.staff_assessed_date = timezone.now().date()
        report.manager_decision = 'approved'
        report.manager_comments = "Manager approval comments"
        report.manager_decision_date = timezone.now().date()
        report.save()

        # Verify values
        self.assertEqual(report.staff_assessment_notes, "Staff assessment notes")
        self.assertEqual(report.manager_decision, 'approved')
        self.assertEqual(report.manager_comments, "Manager approval comments")


class AgreementExecutedDateTestCase(TestCase):
    """Test calculated executed-date for older agreements"""

    def test_forward_rpf_agreement_executed_date(self):
        """Test executed date calculation for Forward Remote Program Funding Agreement"""
        council_date = timezone.now().date()
        delegate_date = council_date + timezone.timedelta(days=30)

        agreement = ForwardRemoteProgramFundingAgreement.objects.create(
            date_council_signed=council_date,
            date_delegate_signed=delegate_date
        )

        # Executed date should be the latest signature date
        self.assertEqual(agreement.date_executed, delegate_date)

    def test_interim_fp_agreement_executed_date(self):
        """Test executed date calculation for Interim Forward Program Funding Agreement"""
        council_date = timezone.now().date()
        delegate_date = None  # Only council signed

        agreement = InterimForwardProgramFundingAgreement.objects.create(
            date_council_signed=council_date,
            date_delegate_signed=delegate_date
        )

        # Executed date should be council signature date
        self.assertEqual(agreement.date_executed, council_date)

    def test_agreement_no_signatures(self):
        """Test agreement with no signatures has no executed date"""
        agreement = ForwardRemoteProgramFundingAgreement.objects.create()

        self.assertIsNone(agreement.date_executed)
