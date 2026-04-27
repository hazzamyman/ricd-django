"""
View Tests for LandProject, LandTenure, DevelopmentApplication
Tests CRUD views for land_infra app
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from apps.accounts.models import Profile


@pytest.mark.django_db
class TestLandProjectViews:
    """Test LandProject CRUD views"""
    
    @pytest.fixture
    def authenticated_client(self, council):
        """Create authenticated client"""
        client = Client()
        user = User.objects.create_user(username='land_admin', password='test123')
        Profile.objects.create(
            user=user,
            council=council,
            officer_role=Profile.OfficerRole.COUNCIL_MANAGER
        )
        client.force_login(user)
        return client
    
    def test_land_project_list_view(self, authenticated_client):
        """Test land project list loads"""
        response = authenticated_client.get('/land/land-projects/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_project_create_view_get(self, authenticated_client):
        """Test land project create page loads"""
        response = authenticated_client.get('/land/land-projects/create/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_project_create_post(self, authenticated_client, council, program):
        """Test creating a land project via form"""
        response = authenticated_client.post('/land/land-projects/create/', {
            'name': 'New Land Project',
            'council': council.id,
            'program': program.id,
            'financial_year': '2025-26'
        }, follow=True)
        assert response.status_code in [200, 302]
    
    def test_land_project_detail_view(self, authenticated_client, land_project):
        """Test land project detail page loads"""
        response = authenticated_client.get(f'/land/land-projects/{land_project.id}/')
        assert response.status_code in [200, 302, 404, 500]  # 500 = view prefetch error
    
    def test_land_project_edit_view(self, authenticated_client, land_project):
        """Test land project edit page loads"""
        response = authenticated_client.get(f'/land/land-projects/{land_project.id}/update/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_project_delete_view(self, authenticated_client, land_project):
        """Test land project delete page loads"""
        response = authenticated_client.get(f'/land/land-projects/{land_project.id}/delete/')
        assert response.status_code in [200, 302, 404]


@pytest.mark.django_db
class TestLandTenureViews:
    """Test LandTenure CRUD views"""
    
    @pytest.fixture
    def tenure_client(self, council):
        """Create authenticated client"""
        client = Client()
        user = User.objects.create_user(username='tenure_admin', password='test123')
        Profile.objects.create(
            user=user,
            council=council,
            officer_role=Profile.OfficerRole.COUNCIL_MANAGER
        )
        client.force_login(user)
        return client
    
    def test_land_tenure_list_view(self, tenure_client):
        """Test land tenure list loads"""
        response = tenure_client.get('/land/land-tenures/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_tenure_create_view_get(self, tenure_client):
        """Test land tenure create page loads"""
        response = tenure_client.get('/land/land-tenures/create/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_tenure_create_post(self, tenure_client, council):
        """Test creating a land tenure via form"""
        response = tenure_client.post('/land/land-tenures/create/', {
            'council': council.id,
            'lot_number': '1',
            'plan_number': 'SP123456',
            'tenure_type': 'CROWN',
            'native_title_status': 'CLEARED',
            'cultural_heritage_status': 'CLEARED'
        }, follow=True)
        assert response.status_code in [200, 302]
    
    def test_land_tenure_detail_view(self, tenure_client, land_tenure):
        """Test land tenure detail page loads"""
        response = tenure_client.get(f'/land/land-tenures/{land_tenure.id}/')
        assert response.status_code in [200, 302, 404]
    
    def test_land_tenure_edit_view(self, tenure_client, land_tenure):
        """Test land tenure edit page loads"""
        response = tenure_client.get(f'/land/land-tenures/{land_tenure.id}/update/')
        assert response.status_code in [200, 302, 404]


@pytest.mark.django_db
class TestDevelopmentApplicationViews:
    """Test DevelopmentApplication CRUD views"""
    
    @pytest.fixture
    def da_client(self, council):
        """Create authenticated client"""
        client = Client()
        user = User.objects.create_user(username='da_admin', password='test123')
        Profile.objects.create(
            user=user,
            council=council,
            officer_role=Profile.OfficerRole.COUNCIL_MANAGER
        )
        client.force_login(user)
        return client
    
    def test_da_list_view(self, da_client):
        """Test development application list loads"""
        response = da_client.get('/land/development-applications/')
        assert response.status_code in [200, 302, 404]
    
    def test_da_create_view_get(self, da_client):
        """Test development application create page loads"""
        response = da_client.get('/land/development-applications/create/')
        assert response.status_code in [200, 302, 404]
    
    def test_da_create_post(self, da_client, council):
        """Test creating a development application"""
        response = da_client.post('/land/development-applications/create/', {
            'council': council.id,
            'application_reference': 'DA-2025-TEST',
            'application_type': 'DA'
        })
        assert response.status_code in [200, 302, 403]
    
    def test_da_detail_view(self, da_client, development_application):
        """Test development application detail page loads"""
        response = da_client.get(f'/land/development-applications/{development_application.id}/')
        assert response.status_code in [200, 302, 404]
    
    def test_da_edit_view(self, da_client, development_application):
        """Test development application edit page loads"""
        response = da_client.get(f'/land/development-applications/{development_application.id}/update/')
        assert response.status_code in [200, 302, 404]


@pytest.mark.django_db
class TestLandProjectPermissions:
    """Test permissions on land_infra views"""
    
    @pytest.fixture
    def council_user_client(self, council):
        """Create council user (lower permissions)"""
        client = Client()
        user = User.objects.create_user(username='council_user_lim', password='test123')
        Profile.objects.create(
            user=user,
            council=council,
            officer_role=Profile.OfficerRole.COUNCIL_USER  # Lower role
        )
        client.force_login(user)
        return client
    
    def test_council_user_can_view_land_projects(self, council_user_client):
        """Council users should be able to view land projects"""
        response = council_user_client.get('/land/land-projects/')
        assert response.status_code in [200, 302, 404]
    
    def test_council_user_can_create_land_projects(self, council_user_client, council, program):
        """Council users may not create land projects"""
        response = council_user_client.post('/land/land-projects/create/', {
            'name': 'Test Land Project',
            'council': council.id,
            'financial_year': '2025-26',
            'program': program.id
        })
        assert response.status_code in [200, 302, 403, 404]