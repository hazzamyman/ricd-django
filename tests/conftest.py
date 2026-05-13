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


# Lazy-load fixtures to avoid import issues before Django is fully initialized
def pytest_configure(config):
    """Configure pytest and set up Django"""
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricdapp.settings')
    django.setup()




@pytest.fixture(scope='session')
def base_url():
    """Base URL for e2e tests"""
    return BASE_URL


@pytest.fixture(scope='session')
def django_db_blocker(django_db_blocker):
    """Allow e2e tests to use database"""
    return django_db_blocker


# Fixtures from fixtures.py are auto-discovered by pytest
# Module-level import avoided to prevent Django initialization issues


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


# Import fixtures from fixtures.py after Django is set up
from fixtures import *  # noqa: F401, F403