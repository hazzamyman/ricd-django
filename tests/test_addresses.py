"""
Tests for Address Model
Test app: addresses
Model: Address, Suburb
"""
import pytest


@pytest.mark.django_db
class TestAddressModel:
    """Test cases for Address model"""
    
    def test_address_creation(self, address):
        """Test creating an address"""
        assert address.id is not None
        assert address.street == "123 Test Street"
        assert address.lot == "1"
        assert address.plan == "CP123456"
    
    def test_address_str(self, address):
        """Test string representation"""
        assert "123 Test Street" in str(address)
    
    def test_address_lot_plan(self, address):
        """Test lot/plan fields"""
        assert address.lot == "1"
        assert address.plan == "CP123456"
    
    def test_address_project_relationship(self, address, project):
        """Test address → project relationship"""
        assert address.project == project
        assert project.addresses.count() == 1