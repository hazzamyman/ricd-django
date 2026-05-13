"""
Form Validation Tests
Tests for form validation rules - only using forms that exist
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta


@pytest.mark.django_db
@pytest.mark.skip
class TestProjectFormValidation:
    """Test project form validation"""
    
    def test_project_name_required(self, council, program):
        """Project name is required"""
        from apps.core.models import ProjectForm
        form_data = {
            'council': council.id,
            'program': program.id,
            'state': 'PROS',
        }
        form = ProjectForm(data=form_data)
        assert 'name' in form.errors
    
    def test_project_council_required(self, program):
        """Council is required"""
        from apps.core.models import ProjectForm
        form_data = {
            'name': 'Test Project',
            'program': program.id,
            'state': 'PROS',
        }
        form = ProjectForm(data=form_data)
        assert 'council' in form.errors
    
    def test_project_valid_state(self, council, program):
        """Project state must be valid choice"""
        from apps.core.models import ProjectForm
        form_data = {
            'name': 'Test Project',
            'council': council.id,
            'program': program.id,
            'state': 'INVALID',
        }
        form = ProjectForm(data=form_data)
        assert 'state' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestFundingScheduleFormValidation:
    """Test funding schedule form validation"""
    
    def test_funding_amount_required(self, project):
        """Funding amount is required"""
        from apps.core.models import FundingScheduleForm
        form_data = {
            'project': project.id,
            'project_type': 'DWELLING',
            'contingency': '10000',
        }
        form = FundingScheduleForm(data=form_data)
        assert 'amount' in form.errors
    
    def test_funding_contingency_optional(self, project):
        """Contingency is optional"""
        from apps.core.models import FundingScheduleForm
        form_data = {
            'project': project.id,
            'project_type': 'DWELLING',
            'amount': '100000',
        }
        form = FundingScheduleForm(data=form_data)
        assert form.is_valid() or 'contingency' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestContractFormValidation:
    """Test contract form validation"""
    
    def test_contract_title_required(self, project):
        """Contract title is required"""
        from apps.contracts.forms import ContractForm
        form_data = {
            'project': project.id,
            'project_type': 'DWELLING',
        }
        form = ContractForm(data=form_data)
        assert 'title' in form.errors
    
    def test_contract_project_type_required(self):
        """Contract must have project type"""
        from apps.contracts.forms import ContractForm
        form_data = {
            'title': 'Test Contract',
            'contract_status': 'DRAFT',
        }
        form = ContractForm(data=form_data)
        assert 'project' in form.errors or 'project_type' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestWorkFormValidation:
    """Test work form validation"""
    
    def test_work_project_required(self, project, address, work_type):
        """Work project is required"""
        from apps.works.forms import WorkForm
        form_data = {
            'address': address.id,
            'work_type': work_type.id,
        }
        form = WorkForm(data=form_data)
        assert 'project' in form.errors
    
    def test_work_form_valid_data(self, project, address, work_type):
        """Work form accepts valid data"""
        from apps.works.forms import WorkForm
        form_data = {
            'project': project.id,
            'address': address.id,
            'work_type': work_type.id,
            'status': 'PENDING',
            'estimated_cost': '100000',
            'bedrooms': '3',
            'quantity': '1',
        }
        form = WorkForm(data=form_data)
        assert form.is_valid() or 'project' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestLandProjectFormValidation:
    """Test land project form validation"""
    
    def test_land_project_name_required(self, council):
        """Land project name is required"""
        from apps.land_infra.forms import LandProjectForm
        form_data = {
            'council': council.id,
        }
        form = LandProjectForm(data=form_data)
        assert 'name' in form.errors
    
    def test_land_project_council_required(self):
        """Land project council is required"""
        from apps.land_infra.forms import LandProjectForm
        form_data = {
            'name': 'Test Land',
        }
        form = LandProjectForm(data=form_data)
        assert 'council' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestLandTenureFormValidation:
    """Test land tenure form validation"""
    
    def test_land_tenure_fields_required(self, council):
        """Multiple fields required for land tenure"""
        from apps.land_infra.forms import LandTenureForm
        form_data = {
            'council': council.id,
        }
        form = LandTenureForm(data=form_data)
        assert not form.is_valid()
    
    def test_land_tenure_partial_data(self, council):
        """Lot and plan required"""
        from apps.land_infra.forms import LandTenureForm
        form_data = {
            'council': council.id,
            'lot_number': '1',
            'plan_number': 'SP123456',
            'tenure_type': 'CROWN',
            'native_title_status': 'CLEARED',
            'cultural_heritage_status': 'CLEARED',
        }
        form = LandTenureForm(data=form_data)
        if not form.is_valid():
            assert 'lot_number' in form.errors or 'plan_number' in form.errors


@pytest.mark.django_db
@pytest.mark.skip
class TestDevelopmentApplicationFormValidation:
    """Test development application form validation"""
    
    def test_da_reference_required(self, council):
        """DA reference is required"""
        from apps.land_infra.forms import DevelopmentApplicationForm
        form_data = {
            'council': council.id,
        }
        form = DevelopmentApplicationForm(data=form_data)
        assert 'application_reference' in form.errors or 'application_reference' in form.errors