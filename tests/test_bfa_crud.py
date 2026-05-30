"""
Tests for BriefFinancialApproval CRUD views (un-nested + multi-project).
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User
from apps.core.models import (
    BriefFinancialApproval, BriefFinancialApprovalItem, Profile,
)


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='bfa_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.MANAGER)
    client.force_login(user)
    return client, user


@pytest.fixture
def bfa(project):
    """BFA header with one item row for `project`."""
    bfa = BriefFinancialApproval.objects.create(
        mincor_reference='MINCOR-TEST',
        delegate_level=BriefFinancialApproval.DelegateLevel.MANAGER,
        status=BriefFinancialApproval.Status.PENDING,
    )
    BriefFinancialApprovalItem.objects.create(
        bfa=bfa, project=project,
        funding_amount=Decimal('500000'),
        contingency_amount=Decimal('50000'),
    )
    return bfa


@pytest.mark.django_db
class TestBFAList:
    def test_global_list_get(self, auth_client):
        client, _ = auth_client
        assert client.get('/bfa/').status_code == 200

    def test_global_list_shows_bfa(self, auth_client, bfa):
        client, _ = auth_client
        response = client.get('/bfa/')
        assert response.status_code == 200
        assert b'MINCOR-TEST' in response.content

    def test_per_project_list_get(self, auth_client, project):
        client, _ = auth_client
        assert client.get(f'/projects/{project.pk}/bfa/').status_code == 200

    def test_per_project_list_shows_bfa(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/')
        assert response.status_code == 200
        assert b'MINCOR-TEST' in response.content

    def test_list_requires_login(self):
        response = Client().get('/bfa/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestBFACreate:
    def test_create_get(self, auth_client):
        client, _ = auth_client
        assert client.get('/bfa/create/').status_code == 200

    def test_create_post_with_one_item(self, auth_client, council, project):
        client, _ = auth_client
        before = BriefFinancialApproval.objects.count()
        response = client.post('/bfa/create/', {
            'mincor_reference': 'MINCOR-001',
            'document_uri': 'https://example.com/brief.pdf',
            'delegate_level': 'DIR',
            'comments': 'Test approval',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-project': project.pk,
            'items-0-cost_centre': '316333',
            'items-0-gl_code': 'GL-1234',
            'items-0-funding_amount': '750000',
            'items-0-contingency_amount': '75000',
        })
        assert response.status_code in (200, 302), response.content[:200]
        assert BriefFinancialApproval.objects.count() == before + 1
        bfa = BriefFinancialApproval.objects.filter(mincor_reference='MINCOR-001').first()
        assert bfa is not None
        assert bfa.project_count == 1
        assert bfa.funding_amount == Decimal('750000')


@pytest.mark.django_db
class TestBFADetail:
    def test_detail_get(self, auth_client, bfa):
        client, _ = auth_client
        assert client.get(f'/bfa/{bfa.pk}/').status_code == 200

    def test_detail_shows_amounts(self, auth_client, bfa):
        client, _ = auth_client
        response = client.get(f'/bfa/{bfa.pk}/')
        assert b'500,000' in response.content or b'500000' in response.content

    def test_detail_shows_approve_button_when_pending(self, auth_client, bfa):
        client, _ = auth_client
        response = client.get(f'/bfa/{bfa.pk}/')
        assert b'Approve' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        assert client.get('/bfa/99999/').status_code == 404


@pytest.mark.django_db
class TestBFAEdit:
    def test_edit_get(self, auth_client, bfa):
        client, _ = auth_client
        assert client.get(f'/bfa/{bfa.pk}/edit/').status_code == 200

    def test_edit_post_updates_object(self, auth_client, bfa, project):
        client, _ = auth_client
        item = bfa.items.first()
        client.post(f'/bfa/{bfa.pk}/edit/', {
            'mincor_reference': 'MINCOR-UPDATED',
            'document_uri': '',
            'delegate_level': 'DIR',
            'comments': '',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': str(item.pk),
            'items-0-bfa': str(bfa.pk),
            'items-0-project': str(project.pk),
            'items-0-cost_centre': '',
            'items-0-gl_code': '',
            'items-0-funding_amount': '600000',
            'items-0-contingency_amount': '60000',
        })
        bfa.refresh_from_db()
        assert bfa.mincor_reference == 'MINCOR-UPDATED'
        assert bfa.delegate_level == 'DIR'
        assert bfa.funding_amount == Decimal('600000')


@pytest.mark.django_db
class TestBFADelete:
    def test_delete_get(self, auth_client, bfa):
        client, _ = auth_client
        assert client.get(f'/bfa/{bfa.pk}/delete/').status_code == 200

    def test_delete_post_removes_object(self, auth_client, bfa):
        client, _ = auth_client
        bfa_id = bfa.pk
        client.post(f'/bfa/{bfa_id}/delete/')
        assert not BriefFinancialApproval.objects.filter(pk=bfa_id).exists()


@pytest.mark.django_db
class TestBFAApproveReject:
    def test_approve_sets_status_and_user(self, auth_client, bfa):
        client, user = auth_client
        response = client.post(f'/bfa/{bfa.pk}/approve/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.APPROVED
        assert bfa.approved_by == user
        assert bfa.approved_at is not None

    def test_reject_sets_status(self, auth_client, bfa):
        client, _ = auth_client
        client.post(f'/bfa/{bfa.pk}/reject/')
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.REJECTED

    def test_cannot_approve_already_approved(self, auth_client, bfa):
        client, user = auth_client
        bfa.status = BriefFinancialApproval.Status.APPROVED
        bfa.approved_by = user
        bfa.save()
        response = client.post(f'/bfa/{bfa.pk}/approve/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.APPROVED

    def test_cannot_reject_already_rejected(self, auth_client, bfa):
        client, _ = auth_client
        bfa.status = BriefFinancialApproval.Status.REJECTED
        bfa.save()
        response = client.post(f'/bfa/{bfa.pk}/reject/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.REJECTED

    def test_total_amount_after_approval(self, auth_client, bfa):
        client, _ = auth_client
        client.post(f'/bfa/{bfa.pk}/approve/')
        bfa.refresh_from_db()
        assert bfa.total_amount == Decimal('550000')
