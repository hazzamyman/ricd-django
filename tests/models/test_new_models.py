from django.test import TestCase
from django.utils import timezone
from ricd.models import Variation, RemoteCapitalProgramFundingAgreement, QuarterlyReport, Stage1Report, Stage2Report, Council, FundingSchedule, Project

class NewModelsTestCase(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Test Council")

    def test_variation_date_calculation(self):
        """Test variation executed date calculation"""
        variation = Variation.objects.create(
            agreement_type='funding_schedule',
            agreement_id=1,
            variation_description="Test variation",
            variation_date=timezone.now().date(),
            date_council_signed=timezone.now().date(),
            date_delegate_signed=timezone.now().date() - timezone.timedelta(days=1)
        )
        variation.save()
        self.assertIsNotNone(variation.executed_date)

    def test_remote_capital_program_agreement(self):
        """Test Remote Capital Program agreement creation"""
        agreement = RemoteCapitalProgramFundingAgreement.objects.create(
            council=self.council,
            date_sent_to_council=timezone.now().date()
        )
        self.assertEqual(agreement.council.name, "Test Council")
        self.assertEqual(agreement.date_executed, agreement.date_sent_to_council)
class PaymentReminderTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Test Council")
        self.funding_schedule = FundingSchedule.objects.create(
            council=self.council,
            funding_schedule_number=1,
            funding_amount=600000.00,
            agreement_type='funding_schedule'
        )
        self.project = Project.objects.create(
            name="Test Project",
            council=self.council,
            funding_schedule=self.funding_schedule
        )

    def test_stage1_payment_due_calculation(self):
        """Test 60% payment calculation after Stage 1 approval"""
        stage1 = Stage1Report.objects.create(
            project=self.project,
            state_accepted=True,
            acceptance_date=timezone.now().date()
        )
        self.assertIsNotNone(stage1.stage1_payment_due)
        self.assertEqual(stage1.stage1_payment_due, self.funding_schedule.funding_amount * 0.6)

    def test_stage2_payment_due_calculation(self):
        """Test 10% payment calculation after Stage 2 approval"""
        stage2 = Stage2Report.objects.create(
            project=self.project,
            state_accepted=True,
            acceptance_date=timezone.now().date(),
            practical_completion_achieved=True,
            practical_completion_date=timezone.now().date()
        )
        self.assertIsNotNone(stage2.stage2_payment_due)
        self.assertEqual(stage2.stage2_payment_due, self.funding_schedule.funding_amount * 0.1)