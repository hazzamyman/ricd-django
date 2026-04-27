"""
E2E tests for RICD/FNC application
Uses Playwright + pytest-playwright
These tests require the Django dev server to be running
"""
import pytest
import urllib.request
import urllib.error


def is_server_running(url='http://127.0.0.1:8000/'):
    """Check if Django server is running"""
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except (urllib.error.URLError, TimeoutError):
        return False


@pytest.fixture
def check_server():
    """Skip e2e tests if server not running"""
    if not is_server_running():
        pytest.skip("Django dev server not running. Start with: python src/manage.py runserver")


@pytest.mark.e2e
def test_homepage_loads(page, base_url, check_server):
    """Test that the homepage loads without errors"""
    page.goto(base_url)
    assert page.title() is not None


@pytest.mark.e2e
def test_login_page_loads(page, base_url, check_server):
    """Test login page loads"""
    page.goto(f"{base_url}/accounts/login/")
    assert page.locator("input[name='username']").count() > 0


@pytest.mark.e2e
def test_project_list_redirects_to_login(page, base_url, check_server):
    """Test that project list redirects to login"""
    page.goto(f"{base_url}/projects/")
    # Should redirect to login
    assert "/accounts/login/" in page.url or page.locator("input[name='username']").count() > 0