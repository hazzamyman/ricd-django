import pytest
from ricd.models import WorkType, OutputType
from tests.conftest import make_work_type_factory, make_output_type_factory


class TestWorkTypeModel:
    """Test WorkType model functionality"""

    @pytest.mark.django_db
    def test_work_type_creation(self):
        """Test basic work type creation with required fields"""
        work_type = WorkType.objects.create(
            name="New Dwelling",
            code="ND",
            description="New dwelling construction"
        )
        assert work_type.name == "New Dwelling"
        assert work_type.code == "ND"
        assert work_type.description == "New dwelling construction"
        assert work_type.is_active is True  # Default value

    @pytest.mark.django_db
    def test_work_type_string_representation(self):
        """Test work type __str__ method"""
        work_type = WorkType.objects.create(name="Test Work Type", code="TWT")
        assert str(work_type) == "Test Work Type"

    @pytest.mark.django_db
    def test_work_type_inactive_creation(self):
        """Test creating inactive work type"""
        work_type = WorkType.objects.create(
            name="Inactive Work Type",
            code="IWT",
            is_active=False
        )
        assert work_type.is_active is False

    @pytest.mark.django_db
    def test_work_type_optional_fields(self):
        """Test work type with optional description blank"""
        work_type = WorkType.objects.create(
            name="Minimal Work Type",
            code="MWT"
        )
        assert work_type.description is None

    @pytest.mark.django_db
    def test_work_type_unique_code(self):
        """Test that work type codes must be unique"""
        WorkType.objects.create(name="First Work Type", code="UNIQUE")

        # Should raise IntegrityError for duplicate code
        with pytest.raises(Exception):  # IntegrityError in PostgreSQL
            WorkType.objects.create(name="Second Work Type", code="UNIQUE")


class TestOutputTypeModel:
    """Test OutputType model functionality"""

    @pytest.mark.django_db
    def test_output_type_creation(self):
        """Test basic output type creation with required fields"""
        output_type = OutputType.objects.create(
            name="House",
            code="HOUSE",
            description="Single family dwelling"
        )
        assert output_type.name == "House"
        assert output_type.code == "HOUSE"
        assert output_type.description == "Single family dwelling"
        assert output_type.is_active is True  # Default value

    @pytest.mark.django_db
    def test_output_type_string_representation(self):
        """Test output type __str__ method"""
        output_type = OutputType.objects.create(name="Test Output Type", code="TOT")
        assert str(output_type) == "Test Output Type"

    @pytest.mark.django_db
    def test_output_type_inactive_creation(self):
        """Test creating inactive output type"""
        output_type = OutputType.objects.create(
            name="Inactive Output Type",
            code="IOT",
            is_active=False
        )
        assert output_type.is_active is False

    @pytest.mark.django_db
    def test_output_type_optional_fields(self):
        """Test output type with optional description blank"""
        output_type = OutputType.objects.create(
            name="Minimal Output Type",
            code="MOT"
        )
        assert output_type.description is None

    @pytest.mark.django_db
    def test_output_type_unique_code(self):
        """Test that output type codes must be unique"""
        OutputType.objects.create(name="First Output Type", code="UNIQUE")

        # Should raise IntegrityError for duplicate code
        with pytest.raises(Exception):  # IntegrityError in PostgreSQL
            OutputType.objects.create(name="Second Output Type", code="UNIQUE")