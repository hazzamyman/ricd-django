import pytest
from ricd.models import Council
from tests.conftest import make_council_factory


class TestCouncilModel:
    """Test Council model functionality"""

    @pytest.mark.django_db
    def test_council_creation(self):
        """Test basic council creation with required fields"""
        council = Council.objects.create(
            name="Test Council",
            abn="12345678901",
            default_suburb="Test Suburb",
            default_postcode="4000",
            default_state="QLD"
        )
        assert council.name == "Test Council"
        assert council.abn == "12345678901"
        assert council.default_state == "QLD"

    @pytest.mark.django_db
    def test_council_string_representation(self):
        """Test council __str__ method"""
        council = Council.objects.create(name="Test Council")
        assert str(council) == "Test Council"

    @pytest.mark.django_db
    def test_council_optional_fields(self):
        """Test council creation with optional fields blank"""
        council = Council.objects.create(
            name="Test Council",
            default_state="QLD"
        )
        assert council.abn is None
        assert council.default_suburb is None
        assert council.default_postcode is None

    @pytest.mark.django_db
    def test_council_registered_housing_provider_flag(self):
        """Test is_registered_housing_provider boolean field"""
        # Default should be False
        council = Council.objects.create(name="Test Council")
        assert council.is_registered_housing_provider is False

        # Can be set to True
        council.is_registered_housing_provider = True
        council.save()
        council.refresh_from_db()
        assert council.is_registered_housing_provider is True

    @pytest.mark.django_db
    def test_council_geographic_fields(self):
        """Test council geographic fields"""
        council = Council.objects.create(
            name="Test Council",
            federal_electorate="Test Federal Electorate",
            state_electorate="Test State Electorate",
            qhigi_region="Test Region"
        )
        assert council.federal_electorate == "Test Federal Electorate"
        assert council.state_electorate == "Test State Electorate"
        assert council.qhigi_region == "Test Region"