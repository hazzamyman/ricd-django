"""
Pytest configuration for RICD tests
Re-exports fixtures from fixtures.py for pytest discovery
"""
import pytest
import os
import sys

pytest_plugins = ['pytest_django']

# Add src to path
project_root = os.path.dirname(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "django_db: mark test as using Django database"
    )
    config.addinivalue_line(
        "markers", "e2e: end-to-end test using Playwright"
    )
    config.addinivalue_line(
        "markers", "unit: unit test"
    )
    config.addinivalue_line(
        "markers", "integration: integration test"
    )


@pytest.fixture(scope='session')
def base_url():
    """Base URL for e2e tests"""
    return BASE_URL


@pytest.fixture(scope='session')
def django_db_blocker(django_db_blocker):
    """Allow e2e tests to use database"""
    return django_db_blocker


# Import all fixtures from fixtures.py so they're discovered
from tests.fixtures import *


@pytest.fixture
def client():
    """Provide a Django test client"""
    from django.test import Client
    return Client()


@pytest.fixture
def admin_client(client, admin_user):
    """Provide an authenticated admin client"""
    client.force_login(admin_user)
    return client