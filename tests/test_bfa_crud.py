"""
Tests for BriefFinancialApproval CRUD views (issue #14).
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User
from apps.core.models import BriefFinancialApproval, Profile


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='bfa_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.SENIOR_OFFICER)
    client.force_login(user)
    return client, user


@pytest.fixture
def bfa(project):
    return BriefFinancialApproval.objects.create(
        project=project,
        funding_amount=Decimal('500000'),
        contingency_amount=Decimal('50000'),
        delegate_level=BriefFinancialApproval.DelegateLevel.MANAGER,
        status=BriefFinancialApproval.Status.PENDING,
    )


@pytest.mark.django_db
class TestBFAList:
    def test_list_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/')
        assert response.status_code == 200

    def test_list_shows_bfa(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/')
        assert response.status_code == 200
        assert b'500000' in response.content or b'500,000' in response.content

    def test_list_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/bfa/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestBFACreate:
    def test_create_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, project):
        client, _ = auth_client
        response = client.post(f'/projects/{project.pk}/bfa/create/', {
            'funding_amount': '750000',
            'contingency_amount': '75000',
            'delegate_level': 'DIR',
            'mincor_reference': 'MINCOR-001',
            'comments': 'Test approval',
        }, follow=True)
        assert response.status_code == 200
        assert BriefFinancialApproval.objects.filter(project=project, funding_amount=Decimal('750000')).exists()

    def test_create_sets_project_from_url(self, auth_client, project):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/bfa/create/', {
            'funding_amount': '200000',
            'contingency_amount': '0',
            'delegate_level': 'MGR',
        })
        bfa = BriefFinancialApproval.objects.filter(project=project).first()
        assert bfa is not None
        assert bfa.project == project

    def test_create_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/bfa/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestBFADetail:
    def test_detail_get(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/')
        assert response.status_code == 200

    def test_detail_shows_amounts(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/')
        assert b'500000' in response.content or b'500,000' in response.content

    def test_detail_shows_approve_button_when_pending(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/')
        assert b'Approve' in response.content

    def test_detail_404_on_missing(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestBFAEdit:
    def test_edit_get(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, project, bfa):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/edit/', {
            'funding_amount': '600000',
            'contingency_amount': '60000',
            'delegate_level': 'DIR',
            'mincor_reference': '',
            'comments': '',
        })
        bfa.refresh_from_db()
        assert bfa.funding_amount == Decimal('600000')
        assert bfa.delegate_level == 'DIR'


@pytest.mark.django_db
class TestBFADelete:
    def test_delete_get(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, project, bfa):
        client, _ = auth_client
        bfa_id = bfa.pk
        client.post(f'/projects/{project.pk}/bfa/{bfa_id}/delete/')
        assert not BriefFinancialApproval.objects.filter(pk=bfa_id).exists()


@pytest.mark.django_db
class TestBFAApproveReject:
    def test_approve_sets_status_and_user(self, auth_client, project, bfa):
        client, user = auth_client
        response = client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/approve/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.APPROVED
        assert bfa.approved_by == user
        assert bfa.approved_at is not None

    def test_reject_sets_status(self, auth_client, project, bfa):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/reject/')
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.REJECTED

    def test_cannot_approve_already_approved(self, auth_client, project, bfa):
        client, user = auth_client
        bfa.status = BriefFinancialApproval.Status.APPROVED
        bfa.approved_by = user
        bfa.save()
        response = client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/approve/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.APPROVED

    def test_cannot_reject_already_rejected(self, auth_client, project, bfa):
        client, _ = auth_client
        bfa.status = BriefFinancialApproval.Status.REJECTED
        bfa.save()
        response = client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/reject/', follow=True)
        assert response.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == BriefFinancialApproval.Status.REJECTED

    def test_approve_requires_post(self, auth_client, project, bfa):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/bfa/{bfa.pk}/approve/')
        assert response.status_code == 405

    def test_total_amount_after_approval(self, auth_client, project, bfa):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/bfa/{bfa.pk}/approve/')
        bfa.refresh_from_db()
        assert bfa.total_amount == Decimal('550000')
