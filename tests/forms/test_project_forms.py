import pytest
from django.test import TestCase
from django.test.client import Client
from ricd.models import Council, Program, Project, Work, Address, WorkType, OutputType
from portal.forms import ProjectForm, WorkForm
from django.contrib.auth.models import User


class TestProjectForm(TestCase):
    """Test ProjectForm validation and behavior"""

    def setUp(self):
        """Set up test data"""
        self.council = Council.objects.create(name="Test Council")
        self.program = Program.objects.create(name="Test Program")
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    @pytest.mark.django_db
    def test_project_form_valid_data(self):
        """Test ProjectForm accepts valid data"""
        form_data = {
            'name': 'Test Project Form',
            'description': 'Test description',
            'council': self.council.pk,
            'program': self.program.pk,
            'state': 'prospective',
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert form.is_valid(), f"Form errors: {form.errors}"

        project = form.save()
        assert project.name == 'Test Project Form'
        assert project.council == self.council
        assert project.program == self.program

    @pytest.mark.django_db
    def test_project_form_required_fields(self):
        """Test ProjectForm validates required fields"""
        # Missing name
        form_data = {
            'description': 'Test description',
            'council': self.council.pk,
            'program': self.program.pk,
            'state': 'prospective',
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert not form.is_valid()
        assert 'name' in form.errors

        # Missing council
        form_data = {
            'name': 'Test Project',
            'description': 'Test description',
            'program': self.program.pk,
            'state': 'prospective',
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert not form.is_valid()
        assert 'council' in form.errors

        # Missing program
        form_data = {
            'name': 'Test Project',
            'description': 'Test description',
            'council': self.council.pk,
            'state': 'prospective',
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert not form.is_valid()
        assert 'program' in form.errors

    @pytest.mark.django_db
    def test_project_form_invalid_state(self):
        """Test ProjectForm rejects invalid state values"""
        form_data = {
            'name': 'Test Project',
            'council': self.council.pk,
            'program': self.program.pk,
            'state': 'invalid_state',
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert not form.is_valid()
        assert 'state' in form.errors

    @pytest.mark.django_db
    def test_project_form_with_start_date(self):
        """Test ProjectForm handles start_date properly"""
        from django.utils import timezone
        start_date = timezone.now().date()

        form_data = {
            'name': 'Test Project with Date',
            'council': self.council.pk,
            'program': self.program.pk,
            'state': 'prospective',
            'start_date': start_date.strftime('%Y-%m-%d'),
        }
        form = ProjectForm(data=form_data, user=self.user)
        assert form.is_valid(), f"Form errors: {form.errors}"

        project = form.save()
        assert project.start_date == start_date


class TestWorkForm(TestCase):
    """Test WorkForm validation and behavior"""

    def setUp(self):
        """Set up test data"""
        self.council = Council.objects.create(name="Test Council")
        self.program = Program.objects.create(name="Test Program")
        self.project = Project.objects.create(
            name="Test Project",
            council=self.council,
            program=self.program
        )
        self.address = Address.objects.create(
            project=self.project,
            street="123 Test Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD"
        )
        self.work_type = WorkType.objects.create(
            name="New Dwelling",
            code="ND",
            is_active=True
        )
        self.output_type = OutputType.objects.create(
            name="House",
            code="HOUSE",
            is_active=True
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    @pytest.mark.django_db
    def test_work_form_valid_data(self):
        """Test WorkForm accepts valid data"""
        form_data = {
            'work_type_id': self.work_type.pk,
            'output_type_id': self.output_type.pk,
            'output_quantity': 1,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        work = form.save(commit=False)
        work.address = self.address
        work.save()

        assert work.work_type_id == self.work_type
        assert work.output_type_id == self.output_type
        assert work.output_quantity == 1
        assert work.bedrooms == 3

    @pytest.mark.django_db
    def test_work_form_required_fields(self):
        """Test WorkForm validates required fields"""
        # Missing work_type_id
        form_data = {
            'output_type_id': self.output_type.pk,
            'output_quantity': 1,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        assert not form.is_valid()
        assert 'work_type_id' in form.errors

        # Missing output_type_id
        form_data = {
            'work_type_id': self.work_type.pk,
            'output_quantity': 1,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        assert not form.is_valid()
        assert 'output_type_id' in form.errors

    @pytest.mark.django_db
    def test_work_form_output_quantity_validation(self):
        """Test WorkForm validation for output_quantity"""
        # Test zero
        form_data = {
            'work_type_id': self.work_type.pk,
            'output_type_id': self.output_type.pk,
            'output_quantity': 0,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        assert not form.is_valid()
        assert 'output_quantity' in form.errors

        # Test negative
        form_data = {
            'work_type_id': self.work_type.pk,
            'output_type_id': self.output_type.pk,
            'output_quantity': -1,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        assert not form.is_valid()
        assert 'output_quantity' in form.errors

    @pytest.mark.django_db
    def test_work_form_under_construction_project_validation(self):
        """Test WorkForm handles different project states correctly"""
        # Test with prospective project (should be fine)
        prospective_project = Project.objects.create(
            name="Prospective Project",
            council=self.council,
            program=self.program,
            state='prospective'
        )
        address = Address.objects.create(
            project=prospective_project,
            street="456 Test Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD"
        )

        form_data = {
            'work_type_id': self.work_type.pk,
            'output_type_id': self.output_type.pk,
            'output_quantity': 1,
            'bedrooms': 3,
        }
        form = WorkForm(data=form_data)
        # Form validation should not depend on project state
        assert form.is_valid(), f"Form errors: {form.errors}"