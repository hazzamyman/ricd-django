"""
Tests for FundingAgreement CRUD views.
Covers: list, create, detail, edit, delete — GET and POST.
"""
import pytest
from django.contrib.auth.models import User
from apps.core.models import FundingAgreement


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='fa_superuser', email='fa@test.com', password='testpass123'
    )


@pytest.fixture
def auth_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture
def agreement(council):
    return FundingAgreement.objects.create(
        council=council,
        name='Test Agreement',
        status='DRAFT',
    )


@pytest.mark.django_db
class TestFundingAgreementList:

    def test_list_get(self, auth_client):
        response = auth_client.get('/funding-agreements/')
        assert response.status_code == 200

    def test_list_shows_agreement(self, auth_client, agreement):
        response = auth_client.get('/funding-agreements/')
        assert response.status_code == 200
        assert agreement.name.encode() in response.content

    def test_list_requires_login(self, client):
        response = client.get('/funding-agreements/')
        assert response.status_code == 302
        assert '/login/' in response['Location']


@pytest.mark.django_db
class TestFundingAgreementCreate:

    def test_create_get(self, auth_client):
        response = auth_client.get('/funding-agreements/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, council):
        before = FundingAgreement.objects.count()
        response = auth_client.post('/funding-agreements/create/', {
            'council': council.pk,
            'name': 'New Agreement',
            'status': 'DRAFT',
            'document_uri': '',
            'notes': '',
        })
        assert response.status_code in (200, 302)
        assert FundingAgreement.objects.count() == before + 1
        assert FundingAgreement.objects.filter(name='New Agreement').exists()

    def test_create_requires_login(self, client):
        response = client.get('/funding-agreements/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestFundingAgreementDetail:

    def test_detail_get(self, auth_client, agreement):
        response = auth_client.get(f'/funding-agreements/{agreement.pk}/')
        assert response.status_code == 200
        assert agreement.name.encode() in response.content

    def test_detail_shows_council(self, auth_client, agreement):
        response = auth_client.get(f'/funding-agreements/{agreement.pk}/')
        assert response.status_code == 200
        assert agreement.council.name.encode() in response.content

    def test_detail_404_on_missing(self, auth_client):
        response = auth_client.get('/funding-agreements/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestFundingAgreementEdit:

    def test_edit_get(self, auth_client, agreement):
        response = auth_client.get(f'/funding-agreements/{agreement.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, agreement, council):
        response = auth_client.post(f'/funding-agreements/{agreement.pk}/edit/', {
            'council': council.pk,
            'name': 'Updated Agreement Name',
            'status': 'ACTIVE',
            'document_uri': '',
            'notes': '',
        })
        assert response.status_code in (200, 302)
        agreement.refresh_from_db()
        assert agreement.name == 'Updated Agreement Name'
        assert agreement.status == 'ACTIVE'


@pytest.mark.django_db
class TestFundingAgreementDelete:

    def test_delete_get(self, auth_client, agreement):
        response = auth_client.get(f'/funding-agreements/{agreement.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, agreement):
        pk = agreement.pk
        response = auth_client.post(f'/funding-agreements/{pk}/delete/')
        assert response.status_code in (200, 302)
        assert not FundingAgreement.objects.filter(pk=pk).exists()
