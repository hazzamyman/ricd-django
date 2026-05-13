"""
Test Fixtures - Data factories for all RICD models
Used by pytest for creating test data
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from django.contrib.auth.models import User


# ============================================================================
# COUNCIL FIXTURES
# ============================================================================

@pytest.fixture
def council():
    """Create a test council"""
    from apps.core.models import Council
    return Council.objects.create(
        name="Test Aboriginal Shire Council",
        region="Test Region",
        state_electorate="Test State Electorate",
        federal_electorate="Test Federal Electorate",
        is_registered_housing_provider=False
    )


@pytest.fixture
def council_contact(council):
    """Create a test council contact"""
    from apps.core.models import CouncilContact
    return CouncilContact.objects.create(
        council=council,
        name="Test Contact",
        role="CEO",
        email="ceo@testcouncil.gov.au",
        phone="07 1234 5678"
    )


# ============================================================================
# PROGRAM FIXTURES
# ============================================================================

@pytest.fixture
def program():
    """Create a test program"""
    from apps.core.models import Program
    return Program.objects.create(
        name="Remote Indigenous Housing Program",
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('10000000.00'),
        gl_code="123456",
        business_case_reference="BC-2025-001"
    )


# ============================================================================
# PROJECT FIXTURES
# ============================================================================

@pytest.fixture
def project(council, program):
    """Create a test dwelling project"""
    from apps.core.models import Project
    return Project.objects.create(
        name="Test Housing Project",
        council=council,
        program=program,
        state=Project.State.PROSPECTIVE,
        dwelling_status=Project.DwellingStatus.PROSPECTIVE,
        financial_year="2025-26"
    )


@pytest.fixture
def project_completed(council, program):
    """Create a completed dwelling project"""
    from apps.core.models import Project
    return Project.objects.create(
        name="Test Completed Project",
        council=council,
        program=program,
        state=Project.State.COMPLETED,
        dwelling_status=Project.DwellingStatus.COMPLETED,
        financial_year="2024-25",
        completion_date=date(2025, 3, 15)
    )


# ============================================================================
# LAND/INFRA FIXTURES
# ============================================================================

@pytest.fixture
def land_project(council):
    """Create a test land/infra project"""
    from apps.core.models import LandProject
    return LandProject.objects.create(
        name="Test Land Development",
        council=council,
        status=LandProject.Status.PROSPECTIVE,
        financial_year="2025-26"
    )


@pytest.fixture
def land_project_completed(council):
    """Create a completed land/infra project"""
    from apps.core.models import LandProject
    return LandProject.objects.create(
        name="Test Completed Land Development",
        council=council,
        status=LandProject.Status.COMPLETED,
        financial_year="2024-25",
        completion_date=date(2025, 3, 15)
    )


@pytest.fixture
def land_tenure(council):
    """Create a test land tenure (lot/plan)"""
    from apps.core.models import LandTenure
    return LandTenure.objects.create(
        council=council,
        lot_number="2",
        plan_number="SP34343",
        tenure_type=LandTenure.TenureType.CROWN,
        native_title_status=LandTenure.NativeTitleStatus.CLEARED,
        cultural_heritage_status=LandTenure.NativeTitleStatus.CLEARED
    )


@pytest.fixture
def development_application(council):
    """Create a test development application"""
    from apps.core.models import DevelopmentApplication
    return DevelopmentApplication.objects.create(
        council=council,
        application_reference="DA-2025-001",
        application_type=DevelopmentApplication.ApplicationType.DA,
        status=DevelopmentApplication.Status.PREPARING
    )


# ============================================================================
# ADDRESS FIXTURES
# ============================================================================

@pytest.fixture
def address(project):
    """Create a test address"""
    from apps.core.models import Address
    return Address.objects.create(
        project=project,
        street="123 Test Street",
        lot="1",
        plan="CP123456"
    )


# ============================================================================
# FUNDING FIXTURES
# ============================================================================

@pytest.fixture
def funding_schedule(project):
    """Create a test funding schedule"""
    from apps.core.models import FundingSchedule
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('500000.00'),
        contingency=Decimal('50000.00'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD
    )


@pytest.fixture
def funding_schedule_land(project):
    """Create a test funding schedule for land project"""
    from apps.core.models import FundingSchedule
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('1000000.00'),
        contingency=Decimal('100000.00'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD
    )


@pytest.fixture
def work_funding(funding_schedule, work):
    """Create a test work funding (per-work cost centre)"""
    from apps.core.models import WorkFunding
    return WorkFunding.objects.create(
        work=work,
        funding_schedule=funding_schedule,
        cost_centre="316333",
        gl_code="ABC123",
        tax_code="GST",
        amount=Decimal('200000.00')
    )


@pytest.fixture
def funding_approval(project):
    """Create a test funding approval"""
    from apps.core.models import FundingApproval
    fa = FundingApproval.objects.create(
        total_amount=Decimal('550000.00'),
        contingency_amount=Decimal('55000.00'),
        status=FundingApproval.Status.APPROVED
    )
    fa.projects.add(project)
    return fa


# ============================================================================
# WORK FIXTURES
# ============================================================================

@pytest.fixture
def work_type():
    """Create a test work type"""
    from apps.core.models import WorkType
    return WorkType.objects.create(
        name="Detached House",
        category=WorkType.Category.RESIDENTIAL,
        description="Standard detached house",
        is_active=True
    )


@pytest.fixture
def work(address, project, work_type):
    """Create a test work"""
    from apps.core.models import Work
    return Work.objects.create(
        project=project,
        address=address,
        work_type=work_type,
        quantity=2,
        estimated_cost=Decimal('250000.00'),
        bedrooms=3,
        status=Work.Status.PENDING
    )


@pytest.fixture
def work_land(project, work_type):
    """Create a test work for land project"""
    from apps.core.models import Work
    return Work.objects.create(
        project=project,
        work_type=work_type,
        quantity=1,
        estimated_cost=Decimal('500000.00'),
        status=Work.Status.PENDING
    )


# ============================================================================
# PAYMENT FIXTURES
# ============================================================================

@pytest.fixture
def payment(project, funding_schedule):
    """Create a test payment"""
    from apps.core.models import Payment
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        percentage=Decimal('30.00'),
        payment_type=Payment.PaymentType.FIRST,
        payment_split=Payment.PaymentSplit.STANDARD,
        status=Payment.Status.PENDING
    )


# ============================================================================
# CONTRACT FIXTURES
# ============================================================================

@pytest.fixture
def contract(project):
    """Create a test contract"""
    from apps.core.models import Contract
    return Contract.objects.create(
        project=project,
        contract_status=Contract.ContractStatus.DRAFT,
        title="Test Funding Agreement",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 12, 31)
    )


# ============================================================================
# DEFECT FIXTURES
# ============================================================================

@pytest.fixture
def defect(project):
    """Create a test defect"""
    from apps.core.models import Defect
    return Defect.objects.create(
        project=project,
        description="Missing tap washer",
        identified_date=date(2025, 3, 1),
        defects_liability_expiry=date(2026, 3, 1)
    )


@pytest.fixture
def work_land(project, work_type):
    """Create a test work for land project"""
    from apps.core.models import Work
    return Work.objects.create(
        project=project,
        work_type=work_type,
        quantity=1,
        estimated_cost=Decimal('500000.00'),
        status=Work.Status.PENDING
    )


# ============================================================================
# PAYMENT FIXTURES
# ============================================================================

@pytest.fixture
def payment(project, funding_schedule):
    """Create a test payment"""
    from apps.core.models import Payment
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        percentage=Decimal('30.00'),
        payment_type=Payment.PaymentType.FIRST,
        payment_split=Payment.PaymentSplit.STANDARD,
        status=Payment.Status.PENDING
    )


# ============================================================================
# CONTRACT FIXTURES
# ============================================================================

@pytest.fixture
def contract(project):
    """Create a test contract"""
    from apps.core.models import Contract
    return Contract.objects.create(
        project=project,
        contract_status=Contract.ContractStatus.DRAFT,
        title="Test Funding Agreement",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 12, 31)
    )


# ============================================================================
# DEFECT FIXTURES
# ============================================================================

@pytest.fixture
def defect(project):
    """Create a test defect"""
    from apps.core.models import Defect
    return Defect.objects.create(
        project=project,
        description="Missing tap washer",
        identified_date=date(2025, 3, 1),
        defects_liability_expiry=date(2026, 3, 1)
    )


# ============================================================================
# PAYMENT FIXTURES
# ============================================================================

@pytest.fixture
def payment(project, funding_schedule):
    """Create a test payment"""
    from apps.core.models import Payment
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        percentage=Decimal('30.00'),
        payment_type=Payment.PaymentType.FIRST,
        payment_split=Payment.PaymentSplit.STANDARD,
        status=Payment.Status.PENDING
    )


# ============================================================================
# CONTRACT FIXTURES
# ============================================================================

@pytest.fixture
def contract(project):
    """Create a test contract"""
    from apps.core.models import Contract
    return Contract.objects.create(
        project=project,
        contract_status=Contract.ContractStatus.DRAFT,
        title="Test Funding Agreement",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 12, 31)
    )


@pytest.fixture
def contract_meeting(contract):
    """Create a test contract meeting"""
    from apps.core.models import ContractMeeting
    return ContractMeeting.objects.create(
        contract=contract,
        meeting_type=ContractMeeting.MeetingType.KICKOFF,
        meeting_date=datetime(2025, 2, 1, 10, 0),
        location="Council Chambers",
        attendees="Mayor, CEO, RICD Officer"
    )


# ============================================================================
# VARIATION FIXTURES
# ============================================================================

@pytest.fixture
def variation(funding_schedule, project):
    """Create a test variation"""
    from apps.core.models import Variation
    return Variation.objects.create(
        funding_schedule=funding_schedule,
        variation_option=Variation.VariationOption.OPTION_1_ADD_FS,
        status=Variation.Status.DRAFT,
        description="Add additional funding schedule"
    )


# ============================================================================
# NOTIONAL COST FIXTURES
# ============================================================================

@pytest.fixture
def notional_cost_type():
    """Create a test notional cost type"""
    from apps.core.models import NotionalCostType
    return NotionalCostType.objects.create(
        name="Standard House",
        category=NotionalCostType.Category.RESIDENTIAL,
        cost_basis=NotionalCostType.CostBasis.PER_BEDROOM,
        description="Standard house construction",
        is_active=True
    )


# ============================================================================
# STRATEGIC PLAN FIXTURES
# ============================================================================

@pytest.fixture
def strategic_plan(council):
    """Create a test strategic plan"""
    from apps.planning.models import StrategicPlan
    return StrategicPlan.objects.create(
        council=council,
        year=2025,
        housing_application_count=50,
        bedrooms_needed_2=10,
        bedrooms_needed_3=20,
        bedrooms_needed_4plus=15
    )


# ============================================================================
# COMBINED FLOW FIXTURES
# ============================================================================

@pytest.fixture
def full_project_flow(council, program, project, address, work_type, work, funding_schedule, payment):
    """Complete project flow for testing"""
    return {
        'council': council,
        'program': program,
        'project': project,
        'address': address,
        'work_type': work_type,
        'work': work,
        'funding_schedule': funding_schedule,
        'payment': payment
    }


@pytest.fixture
def full_land_flow(council, project, land_tenure, development_application, work_type, work_land):
    """Complete land project flow for testing"""
    return {
        'council': council,
        'project': project,
        'land_tenure': land_tenure,
        'development_application': development_application,
        'work_type': work_type,
        'work': work_land
    }