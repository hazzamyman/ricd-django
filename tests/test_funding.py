"""
Tests for Funding Models
Test app: funding
Models: FundingSchedule, BriefFinancialApproval, WorkFunding
"""
import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestFundingScheduleModel:
    """Test cases for FundingSchedule model"""
    
    def test_funding_schedule_creation(self, funding_schedule):
        """Test creating a funding schedule"""
        assert funding_schedule.id is not None
        # total_funding now comes from WorkFunding allocations (fixture seeds 500k)
        assert funding_schedule.total_funding == Decimal('500000.00')
        assert funding_schedule.project.project_type == 'DWELLING'

    def test_funding_schedule_str(self, funding_schedule):
        """Test string representation"""
        assert "Test Housing Project" in str(funding_schedule)

    def test_funding_schedule_total(self, funding_schedule):
        """Total funding = SUM of WorkFunding allocations on this schedule."""
        # Fixture seeds a single 500k project-level allocation
        assert funding_schedule.total_funding == Decimal('500000.00')

    def test_funding_schedule_project_relationship(self, funding_schedule, project):
        """Test funding schedule -> project relationship"""
        assert funding_schedule.project == project
        assert project.funding_schedules.count() == 1

    def test_funding_schedule_payment_rule_optional_by_default(self, funding_schedule):
        """A DRAFT schedule does not yet require a payment_rule."""
        assert funding_schedule.payment_rule is None


@pytest.mark.django_db
class TestFundingScheduleLandProjects:
    """Test funding schedules for land projects"""

    def test_funding_schedule_land_creation(self, funding_schedule_land):
        """Test creating a funding schedule for land project"""
        assert funding_schedule_land.id is not None
        assert funding_schedule_land.project is not None

    def test_funding_schedule_land_total(self, funding_schedule_land):
        """Land fixture seeds a single 1M allocation."""
        assert funding_schedule_land.total_funding == Decimal('1000000.00')


@pytest.mark.django_db
class TestWorkFundingModel:
    """Test cases for WorkFunding model"""
    
    def test_work_funding_creation(self, work_funding):
        """Test creating work funding"""
        assert work_funding.id is not None
        assert work_funding.cost_centre == "316333"
        assert work_funding.gl_code == "ABC123"
        assert work_funding.tax_code == "GST"
        assert work_funding.amount == Decimal('200000.00')
    
    def test_work_funding_str(self, work_funding):
        """Test string representation"""
        assert "316333" in str(work_funding)
    
    def test_work_funding_work_relationship(self, work_funding, work):
        """Test work funding → work relationship"""
        assert work_funding.work == work
        assert work.funding_details.count() == 1
    
    def test_work_funding_schedule_relationship(self, work_funding, funding_schedule):
        """Test work funding → funding schedule relationship"""
        assert work_funding.funding_schedule == funding_schedule
    
    def test_work_funding_cost_centre(self, work_funding):
        """Test cost centre field"""
        assert work_funding.cost_centre == "316333"


from apps.core.models import FundingSchedule
from apps.core.models import Payment