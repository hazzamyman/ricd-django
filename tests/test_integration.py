"""
Integration Tests - Unified Project Workflows
Tests the full workflows for unified Projects (both LAND and DWELLING project_types)
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.core.models import Profile
from apps.core.models import Project
from apps.core.models import FundingSchedule
from apps.core.models import Payment
from apps.core.models import Work, WorkType


@pytest.mark.django_db
class TestDwellingTrackWorkflow:
    """Test full dwelling project workflow"""
    
    @pytest.fixture
    def dwelling_setup(self, council, program):
        """Setup for dwelling track"""
        project = Project.objects.create(
            name="Test Dwelling Project",
            council=council,
            program=program,
            project_type=Project.Type.DWELLING,
            state=Project.State.PROSPECTIVE,
            dwelling_status=Project.DwellingStatus.PROSPECTIVE,
            financial_year="2025-26"
        )
        funding = FundingSchedule.objects.create(
            project=project,
            amount=Decimal('500000'),
            contingency=Decimal('50000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD
        )
        return project, funding
    
    def test_create_dwelling_project(self, dwelling_setup):
        """Test creating a dwelling project"""
        project, funding = dwelling_setup
        assert project.id is not None
        assert project.state == 'PROS'
        assert project.project_type == 'DWELLING'
    
    def test_dwelling_funding_creation(self, dwelling_setup):
        """Test funding for dwelling project"""
        project, funding = dwelling_setup
        assert funding.total_funding == Decimal('550000')
        assert funding.project == project
    
    def test_dwelling_payment_workflow(self, dwelling_setup):
        """Test payment for dwelling project"""
        project, funding = dwelling_setup
        payment = Payment.objects.create(
            project=project,
            funding_schedule=funding,
            calculation_type=Payment.CalculationType.PERCENTAGE,
            percentage=Decimal('30'),
            payment_type=Payment.PaymentType.FIRST,
            status=Payment.Status.PENDING
        )
        payment.status = Payment.Status.RECOMMENDED
        payment.save()
        assert payment.status == 'RECOMMENDED'
        
        payment.status = Payment.Status.APPROVED
        payment.save()
        assert payment.status == 'APPROVED'
        
        payment.status = Payment.Status.RELEASED
        payment.release_date = date.today()
        payment.save()
        assert payment.status == 'RELEASED'


@pytest.mark.django_db
class TestLandTrackWorkflow:
    """Test full land project workflow"""
    
    @pytest.fixture
    def land_setup(self, council, program):
        """Setup for land track using unified Project model"""
        project = Project.objects.create(
            name="Test Land Project",
            council=council,
            program=program,
            project_type=Project.Type.LAND,
            state=Project.State.PROSPECTIVE,
            dwelling_status=None,
            financial_year="2025-26"
        )
        funding = FundingSchedule.objects.create(
            project=project,
            amount=Decimal('1000000'),
            contingency=Decimal('100000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD
        )
        return project, funding
    
    def test_create_land_project(self, land_setup):
        """Test creating a land project"""
        project, funding = land_setup
        assert project.id is not None
        assert project.project_type == 'LAND'
    
    def test_land_funding_creation(self, land_setup):
        """Test funding for land project"""
        project, funding = land_setup
        assert funding.total_funding == Decimal('1100000')
        assert funding.project == project
    
    def test_land_payment_workflow(self, land_setup):
        """Test payment for land project"""
        project, funding = land_setup
        payment = Payment.objects.create(
            project=project,
            funding_schedule=funding,
            calculation_type=Payment.CalculationType.PERCENTAGE,
            percentage=Decimal('50'),
            payment_type=Payment.PaymentType.FIRST,
            status=Payment.Status.PENDING
        )
        assert payment.id is not None
        assert payment.project == project


@pytest.mark.django_db
class TestLinkedProjectsWorkflow:
    """Test linking dwellings to parent land projects"""
    
    @pytest.fixture
    def linked_setup(self, council, program, work_type):
        """Setup linked projects using parent_land_project"""
        land = Project.objects.create(
            name="Parent Land",
            council=council,
            program=program,
            project_type=Project.Type.LAND,
            state=Project.State.COMPLETED,
            dwelling_status=None,
            financial_year="2024-25"
        )
        dwelling = Project.objects.create(
            name="New Dwelling on Completed Land",
            council=council,
            program=program,
            parent_land_project=land,
            project_type=Project.Type.DWELLING,
            state=Project.State.PROSPECTIVE,
            dwelling_status=Project.DwellingStatus.PROSPECTIVE,
            financial_year="2025-26"
        )
        work = Work.objects.create(
            project=dwelling,
            work_type=work_type,
            quantity=1,
            estimated_cost=Decimal('250000'),
            status=Work.Status.PENDING
        )
        return land, dwelling, work
    
    def test_link_dwelling_to_land_project(self, linked_setup):
        """Test linking dwelling to land project"""
        land, dwelling, work = linked_setup
        assert dwelling.parent_land_project == land
        assert land.id is not None
    
    def test_dwelling_work_on_linked_project(self, linked_setup):
        """Test work creation on linked dwelling"""
        land, dwelling, work = linked_setup
        assert work.project == dwelling
        assert work.quantity == 1


@pytest.mark.django_db
class TestFullRICDWorkflow:
    """Test complete RICD workflow end-to-end"""
    
    @pytest.fixture
    def full_workflow_setup(self, council, program, work_type):
        """Full workflow from land to dwelling completion"""
        land = Project.objects.create(
            name="Full Test Land",
            council=council,
            program=program,
            project_type=Project.Type.LAND,
            state=Project.State.COMPLETED,
            dwelling_status=None,
            financial_year="2024-25"
        )
        
        dwelling = Project.objects.create(
            name="Full Test Dwelling",
            council=council,
            program=program,
            parent_land_project=land,
            project_type=Project.Type.DWELLING,
            state=Project.State.PROSPECTIVE,
            dwelling_status=Project.DwellingStatus.PROSPECTIVE,
            financial_year="2025-26"
        )
        
        work = Work.objects.create(
            project=dwelling,
            work_type=work_type,
            quantity=1,
            estimated_cost=Decimal('300000'),
            status=Work.Status.PENDING
        )
        
        funding = FundingSchedule.objects.create(
            project=dwelling,
            amount=Decimal('350000'),
            contingency=Decimal('35000'),
            payment_split=FundingSchedule.PaymentSplit.STANDARD
        )
        
        return land, dwelling, work, funding
    
    def test_complete_workflow(self, full_workflow_setup):
        """Test complete workflow"""
        land, dwelling, work, funding = full_workflow_setup
        assert dwelling.parent_land_project == land
        assert work.project == dwelling
        assert funding.project == dwelling
    
    def test_workflow_data_integrity(self, full_workflow_setup):
        """Test workflow maintains data integrity"""
        land, dwelling, work, funding = full_workflow_setup
        assert land.project_type == 'LAND'
        assert dwelling.project_type == 'DWELLING'
        assert dwelling.parent_land_project == land
        assert funding.total_funding == Decimal('385000')