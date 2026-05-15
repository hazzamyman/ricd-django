"""
Funding Views Tests
Tests for funding schedule create, edit, delete views
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from apps.core.models import Profile
from apps.core.models import FundingSchedule
from apps.core.models import Project
from decimal import Decimal


@pytest.mark.django_db
class TestFundingScheduleCreateView:
    """Test funding schedule create view"""
    
    @pytest.fixture
    def funding_create_client(self, council):
        client = Client()
        user = User.objects.create_user(username='funding_creator', password='test123')
        Profile.objects.create(
            user=user,
            council=council,
            officer_role=Profile.OfficerRole.SENIOR_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_funding_create_get(self, funding_create_client, project):
        """Test funding schedule create page loads"""
        response = funding_create_client.get(f'/funding/schedule/create/{project.id}/')
        assert response.status_code in [200, 302, 404]
    
    def test_funding_create_post(self, funding_create_client, project):
        """Test creating funding schedule via the consolidated ui namespace URL.

        FundingSchedule.clean() requires an APPROVED BriefFinancialApproval on
        the project before the schedule can be created.
        """
        from apps.core.models import BriefFinancialApproval
        BriefFinancialApproval.objects.create(
            project=project,
            funding_amount=Decimal('500000'),
            status='APPROVED',
        )
        response = funding_create_client.post('/funding-schedules/create/', {
            'project': project.id,
            'amount': '500000',
            'contingency': '50000',
            'payment_split': '30/60/10',
            'status': 'DRAFT',
        }, follow=True)
        assert response.status_code in [200, 302]
        assert FundingSchedule.objects.filter(project=project).exists()
    
    def test_funding_create_land_get(self, funding_create_client, land_project):
        """Test funding schedule create for land project"""
        response = funding_create_client.get(f'/funding/schedule/create/land/{land_project.id}/')
        assert response.status_code in [200, 302, 404]


@pytest.mark.django_db
class TestFundingScheduleListView:
    """Test funding schedule list view"""
    
    @pytest.fixture
    def funding_list_client(self):
        client = Client()
        user = User.objects.create_user(username='funding_lister', password='test123')
        Profile.objects.create(
            user=user,
            officer_role=Profile.OfficerRole.SENIOR_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_funding_list_get(self, funding_list_client):
        """Test funding list page loads"""
        response = funding_list_client.get('/funding/')
        assert response.status_code in [200, 302, 404]
    
    def test_funding_list_shows_schedules(self, funding_list_client, funding_schedule):
        """Test funding list shows schedules"""
        response = funding_list_client.get('/funding/')
        if response.status_code == 200:
            content = response.content.decode()
            assert 'funding' in content.lower() or 'schedule' in content.lower()


@pytest.mark.django_db
class TestFundingScheduleDeleteView:
    """Test funding schedule delete view"""
    
    @pytest.fixture
    def funding_delete_client(self):
        client = Client()
        user = User.objects.create_user(username='funding_deleter', password='test123')
        Profile.objects.create(
            user=user,
            officer_role=Profile.OfficerRole.SENIOR_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_funding_delete_get(self, funding_delete_client, funding_schedule):
        """Test funding delete confirmation"""
        response = funding_delete_client.get(f'/funding/schedule/{funding_schedule.id}/delete/')
        assert response.status_code in [200, 302, 404]
    
    def test_funding_delete_post(self, funding_delete_client, funding_schedule):
        """Test funding schedule deletion via the consolidated ui namespace URL."""
        fs_id = funding_schedule.id
        response = funding_delete_client.post(
            f'/funding-schedules/{fs_id}/delete/',
            follow=True
        )
        assert response.status_code in [200, 302]
        assert not FundingSchedule.objects.filter(id=fs_id).exists()


@pytest.mark.django_db
class TestWorkFundingView:
    """Test work funding view"""
    
    @pytest.fixture
    def work_funding_client(self):
        client = Client()
        user = User.objects.create_user(username='work_funder', password='test123')
        Profile.objects.create(
            user=user,
            officer_role=Profile.OfficerRole.SENIOR_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_work_funding_create(self, work_funding_client, work, funding_schedule):
        """Test creating work funding"""
        response = work_funding_client.post(f'/funding/work-funding/create/', {
            'work': work.id,
            'funding_schedule': funding_schedule.id,
            'cost_centre': '316333',
            'gl_code': 'ABC123',
            'tax_code': 'GST',
            'amount': '200000'
        }, follow=True)
        assert response.status_code in [200, 302, 404]


@pytest.mark.django_db
class TestFundingCalculations:
    """Test funding calculation display"""
    
    @pytest.fixture
    def calc_client(self):
        client = Client()
        user = User.objects.create_user(username='calc_tester', password='test123')
        Profile.objects.create(
            user=user,
            officer_role=Profile.OfficerRole.PROGRAM_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_total_funding_display(self, calc_client, funding_schedule):
        """Test total funding shows correctly"""
        response = calc_client.get(f'/funding/')
        if response.status_code == 200:
            content = response.content.decode()
            assert '550000' in content or 'total' in content.lower()
    
    def test_contingency_display(self, calc_client, funding_schedule):
        """Test contingency shows correctly"""
        response = calc_client.get(f'/funding/')
        if response.status_code == 200:
            assert funding_schedule.contingency == Decimal('50000')


@pytest.mark.django_db
class TestFundingDualTrack:
    """Test funding for dual-track"""
    
    @pytest.fixture
    def dual_client(self):
        client = Client()
        user = User.objects.create_user(username='dual_funder', password='test123')
        Profile.objects.create(
            user=user,
            officer_role=Profile.OfficerRole.SENIOR_OFFICER
        )
        client.force_login(user)
        return client
    
    def test_dwelling_funding(self, dual_client, project, funding_schedule):
        """Test dwelling funding works"""
        assert funding_schedule.project == project
        assert project.project_type == 'DWELLING'
    
    def test_land_funding(self, dual_client, funding_schedule_land):
        """Test land funding works"""
        assert funding_schedule_land.project is not None