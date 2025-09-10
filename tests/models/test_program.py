import pytest
from ricd.models import Program
from tests.conftest import make_program_factory


class TestProgramModel:
    """Test Program model functionality"""

    @pytest.mark.django_db
    def test_program_creation(self):
        """Test basic program creation"""
        program = Program.objects.create(
            name="Test Program",
            description="Test program description",
            budget=1000000,
            funding_source="Commonwealth"
        )
        assert program.name == "Test Program"
        assert program.description == "Test program description"
        assert program.budget == 1000000
        assert program.funding_source == "Commonwealth"

    @pytest.mark.django_db
    def test_program_string_representation(self):
        """Test program __str__ method"""
        program = Program.objects.create(name="Test Program")
        assert str(program) == "Test Program"

    @pytest.mark.django_db
    def test_program_optional_fields(self):
        """Test program creation with optional fields blank"""
        program = Program.objects.create(name="Test Program")
        assert program.description is None
        assert program.budget is None
        assert program.funding_source is None

    @pytest.mark.django_db
    def test_program_funding_source_choices(self):
        """Test funding source choice field values"""
        choices = ["Commonwealth", "State"]
        for choice in choices:
            program = Program.objects.create(
                name=f"Program {choice}",
                funding_source=choice
            )
            assert program.funding_source == choice