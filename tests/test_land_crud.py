"""
Tests for Land infrastructure CRUD views: LandTenure, DevelopmentApplication (issue #31).

LandProject is not a separate model — land projects are Project(project_type='LAND').
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from apps.core.models import DevelopmentApplication, LandTenure, Profile


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='land_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.OFFICER)
    client.force_login(user)
    return client, user


@pytest.fixture
def land_tenure(council):
    return LandTenure.objects.create(
        council=council,
        lot_number='123',
        plan_number='SP123456',
        tenure_type='CROWN',
    )


@pytest.fixture
def development_application(council):
    return DevelopmentApplication.objects.create(
        council=council,
        application_type='DA',
        application_reference='DA-2024-001',
        status='PREP',
    )


# ---------------------------------------------------------------------------
# LandTenure
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLandTenureList:
    def test_list_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/land-tenures/')
        assert response.status_code == 200

    def test_list_shows_tenure(self, auth_client, land_tenure):
        client, _ = auth_client
        response = client.get('/land-tenures/')
        assert response.status_code == 200
        assert b'123' in response.content

    def test_list_requires_login(self):
        response = Client().get('/land-tenures/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestLandTenureCreate:
    def test_create_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/land-tenures/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, council):
        client, _ = auth_client
        response = client.post('/land-tenures/create/', {
            'council': council.pk,
            'lot_number': '456',
            'plan_number': 'SP456789',
            'tenure_type': 'FREEHOLD',
            'native_title_status': 'PENDING',
            'cultural_heritage_status': 'PENDING',
        }, follow=True)
        assert response.status_code == 200
        assert LandTenure.objects.filter(lot_number='456', council=council).exists()

    def test_create_requires_login(self):
        response = Client().get('/land-tenures/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestLandTenureDetail:
    def test_detail_get(self, auth_client, land_tenure):
        client, _ = auth_client
        response = client.get(f'/land-tenures/{land_tenure.pk}/')
        assert response.status_code == 200

    def test_detail_shows_lot(self, auth_client, land_tenure):
        client, _ = auth_client
        response = client.get(f'/land-tenures/{land_tenure.pk}/')
        assert b'123' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        response = client.get('/land-tenures/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestLandTenureEdit:
    def test_edit_get(self, auth_client, land_tenure):
        client, _ = auth_client
        response = client.get(f'/land-tenures/{land_tenure.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, land_tenure, council):
        client, _ = auth_client
        client.post(f'/land-tenures/{land_tenure.pk}/edit/', {
            'council': council.pk,
            'lot_number': '789',
            'plan_number': 'SP789000',
            'tenure_type': 'LEASEHOLD',
            'native_title_status': 'CLEARED',
            'cultural_heritage_status': 'CLEARED',
        })
        land_tenure.refresh_from_db()
        assert land_tenure.lot_number == '789'
        assert land_tenure.tenure_type == 'LEASEHOLD'


@pytest.mark.django_db
class TestLandTenureDelete:
    def test_delete_get(self, auth_client, land_tenure):
        client, _ = auth_client
        response = client.get(f'/land-tenures/{land_tenure.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, land_tenure):
        client, _ = auth_client
        lt_id = land_tenure.pk
        client.post(f'/land-tenures/{lt_id}/delete/')
        assert not LandTenure.objects.filter(pk=lt_id).exists()


# ---------------------------------------------------------------------------
# DevelopmentApplication
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDevelopmentApplicationList:
    def test_list_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/development-applications/')
        assert response.status_code == 200

    def test_list_shows_da(self, auth_client, development_application):
        client, _ = auth_client
        response = client.get('/development-applications/')
        assert response.status_code == 200
        assert b'DA-2024-001' in response.content

    def test_list_requires_login(self):
        response = Client().get('/development-applications/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestDevelopmentApplicationCreate:
    def test_create_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/development-applications/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, council):
        client, _ = auth_client
        response = client.post('/development-applications/create/', {
            'council': council.pk,
            'application_type': 'MCU',
            'application_reference': 'MCU-2024-001',
            'status': 'SUB',
        }, follow=True)
        assert response.status_code == 200
        assert DevelopmentApplication.objects.filter(application_reference='MCU-2024-001').exists()

    def test_create_requires_login(self):
        response = Client().get('/development-applications/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestDevelopmentApplicationDetail:
    def test_detail_get(self, auth_client, development_application):
        client, _ = auth_client
        response = client.get(f'/development-applications/{development_application.pk}/')
        assert response.status_code == 200

    def test_detail_shows_reference(self, auth_client, development_application):
        client, _ = auth_client
        response = client.get(f'/development-applications/{development_application.pk}/')
        assert b'DA-2024-001' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        response = client.get('/development-applications/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestDevelopmentApplicationEdit:
    def test_edit_get(self, auth_client, development_application):
        client, _ = auth_client
        response = client.get(f'/development-applications/{development_application.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, development_application, council):
        client, _ = auth_client
        client.post(f'/development-applications/{development_application.pk}/edit/', {
            'council': council.pk,
            'application_type': 'DA',
            'application_reference': 'DA-2024-001',
            'status': 'APPR',
        })
        development_application.refresh_from_db()
        assert development_application.status == 'APPR'


@pytest.mark.django_db
class TestDevelopmentApplicationDelete:
    def test_delete_get(self, auth_client, development_application):
        client, _ = auth_client
        response = client.get(f'/development-applications/{development_application.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, development_application):
        client, _ = auth_client
        da_id = development_application.pk
        client.post(f'/development-applications/{da_id}/delete/')
        assert not DevelopmentApplication.objects.filter(pk=da_id).exists()
