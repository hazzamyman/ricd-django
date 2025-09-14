import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from ricd.models import FundingSchedule, Council, Program, Project


class TestFundingScheduleModel:
    """Test FundingSchedule model functionality"""

    @pytest.mark.django_db
    def test_funding_schedule_creation(self):
        """Test basic funding schedule creation"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        schedule = FundingSchedule.objects.create(
            council=council,
            program=program,
            funding_schedule_number=1,
            funding_amount=Decimal('500000.00'),
            contingency_amount=Decimal('50000.00')
        )

        assert schedule.council == council
        assert schedule.program == program
        assert schedule.funding_schedule_number == 1
        assert schedule.funding_amount == Decimal('500000.00')
        assert schedule.contingency_amount == Decimal('50000.00')

    @pytest.mark.django_db
    def test_funding_schedule_string_representation(self):
        """Test funding schedule __str__ method"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        schedule = FundingSchedule.objects.create(
            council=council,
            program=program,
            funding_schedule_number=42
        )

        assert str(schedule) == "Test Council - 42"

    @pytest.mark.django_db
    def test_funding_schedule_unique_constraint(self):
        """Test unique together constraint on council and funding_schedule_number"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        # First schedule should be fine
        FundingSchedule.objects.create(
            council=council,
            program=program,
            funding_schedule_number=1
        )

        # Second schedule with same council and number should fail
        with pytest.raises(Exception):  # IntegrityError
            FundingSchedule.objects.create(
                council=council,
                program=program,
                funding_schedule_number=1
            )

    @pytest.mark.django_db
    def test_funding_schedule_total_funding_property(self):
        """Test total_funding property calculation"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        # With contingency
        schedule = FundingSchedule.objects.create(
            funding_amount=Decimal('400000.00'),
            contingency_amount=Decimal('40000.00')
        )
        assert schedule.total_funding == Decimal('440000.00')

        # Without contingency
        schedule_no_contingency = FundingSchedule.objects.create(
            funding_amount=Decimal('500000.00'),
            contingency_amount=None
        )
        assert schedule_no_contingency.total_funding == Decimal('500000.00')

    @pytest.mark.django_db
    def test_funding_schedule_auto_payment_calculation(self):
        """Test auto-calculation of first payment when funding is allocated"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        # Create project with contingency percentage
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            contingency_percentage=Decimal('0.10')  # 10%
        )

        # Create funding schedule linked to project
        schedule = FundingSchedule.objects.create(
            council=council,
            program=program,
            funding_schedule_number=1,
            funding_amount=Decimal('550000.00'),
            contingency_amount=Decimal('55000.00')  # 10% of total funding
        )

        # Add project relationship
        schedule.projects.add(project)
        schedule.save()

        # Check auto-calculation
        assert schedule.first_payment_amount == Decimal('495000.00')  # 90% of funding amount minus contingency portion
        assert schedule.first_reference_number == "FS-1-001"

    @pytest.mark.django_db
    def test_funding_schedule_release_date_calculation(self):
        """Test auto-setting of release date"""
        schedule = FundingSchedule.objects.create(
            funding_amount=Decimal('100000.00')
        )

        # Should set release date to 30 days from creation
        expected = timezone.now().date() + timedelta(days=30)
        assert schedule.first_release_date == expected

    @pytest.mark.django_db
    def test_funding_schedule_executed_date_calculation(self):
        """Test executed date calculation when both signatures are present"""
        schedule = FundingSchedule.objects.create(funding_amount=Decimal('100000'))

        # Test when both dates are None
        assert schedule.save()
        assert schedule.executed_date is None

        # Test with one signature date
        schedule.date_council_signed = timezone.now().date()
        schedule.save()
        assert schedule.executed_date == schedule.date_council_signed

        # Test with both signature dates
        schedule.date_delegate_signed = schedule.date_council_signed + timedelta(days=2)
        schedule.save()
        # Should pick the later date
        assert schedule.executed_date == schedule.date_delegate_signed

    @pytest.mark.django_db
    def test_funding_schedule_agreement_types(self):
        """Test different agreement types"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        agreement_types = [
            'funding_schedule',
            'frpf_agreement',
            'ifrpf_agreement',
            'rcpf_agreement'
        ]

        for agreement_type in agreement_types:
            schedule = FundingSchedule.objects.create(
                funding_amount=Decimal('100000'),
                agreement_type=agreement_type
            )
            assert schedule.agreement_type == agreement_type