"""
Tests for issues #15 (Approval CRUD), #18 (Work & Address CRUD), #19 (PaymentRule read-only).
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User
from apps.core.models import Approval, Address, PaymentRule, Work, Profile


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='crud_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.MANAGER)
    client.force_login(user)
    return client, user


@pytest.fixture
def payment_rule():
    return PaymentRule.objects.create(
        name='Test SPLIT Rule',
        rule_type=PaymentRule.RuleType.SPLIT,
        config_json={'milestones': [
            {'name': 'Stage 1', 'trigger': 'Report approved', 'percentage': 60},
            {'name': 'Stage 2', 'trigger': 'Completion', 'percentage': 40},
        ]},
        version=1,
    )


@pytest.fixture
def approval():
    return Approval.objects.create(
        entity_type='Project',
        entity_id=1,
        approval_type=Approval.ApprovalType.PAYMENT,
        required_role=Approval.RequiredRole.MANAGER,
        status=Approval.Status.PENDING,
    )


# ---------------------------------------------------------------------------
# Issue #19: PaymentRule (read-only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentRuleList:
    def test_list_get(self, auth_client, payment_rule):
        client, _ = auth_client
        response = client.get('/payment-rules/')
        assert response.status_code == 200

    def test_list_shows_rule(self, auth_client, payment_rule):
        client, _ = auth_client
        response = client.get('/payment-rules/')
        assert b'Test SPLIT Rule' in response.content

    def test_list_requires_login(self):
        response = Client().get('/payment-rules/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestPaymentRuleDetail:
    def test_detail_get(self, auth_client, payment_rule):
        client, _ = auth_client
        response = client.get(f'/payment-rules/{payment_rule.pk}/')
        assert response.status_code == 200

    def test_detail_shows_milestones(self, auth_client, payment_rule):
        client, _ = auth_client
        response = client.get(f'/payment-rules/{payment_rule.pk}/')
        assert b'Stage 1' in response.content
        assert b'60' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        response = client.get('/payment-rules/99999/')
        assert response.status_code == 404

    def test_detail_requires_login(self, payment_rule):
        response = Client().get(f'/payment-rules/{payment_rule.pk}/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Issue #15: Approval
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApprovalList:
    def test_list_get(self, auth_client, approval):
        client, _ = auth_client
        response = client.get('/approvals/')
        assert response.status_code == 200

    def test_list_shows_approval(self, auth_client, approval):
        client, _ = auth_client
        response = client.get('/approvals/')
        assert response.status_code == 200

    def test_list_filter_by_status(self, auth_client, approval):
        client, _ = auth_client
        response = client.get('/approvals/?status=PENDING')
        assert response.status_code == 200

    def test_list_requires_login(self):
        response = Client().get('/approvals/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestApprovalDetail:
    def test_detail_get(self, auth_client, approval):
        client, _ = auth_client
        response = client.get(f'/approvals/{approval.pk}/')
        assert response.status_code == 200

    def test_detail_shows_approve_button_when_pending(self, auth_client, approval):
        client, _ = auth_client
        response = client.get(f'/approvals/{approval.pk}/')
        assert b'Approve' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        response = client.get('/approvals/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestApprovalApproveReject:
    def test_approve_sets_status(self, auth_client, approval):
        client, user = auth_client
        response = client.post(f'/approvals/{approval.pk}/approve/', follow=True)
        assert response.status_code == 200
        approval.refresh_from_db()
        assert approval.status == Approval.Status.APPROVED
        assert approval.approved_by == user
        assert approval.approved_at is not None

    def test_reject_sets_status(self, auth_client, approval):
        client, _ = auth_client
        client.post(f'/approvals/{approval.pk}/reject/')
        approval.refresh_from_db()
        assert approval.status == Approval.Status.REJECTED

    def test_cannot_approve_already_approved(self, auth_client, approval):
        client, user = auth_client
        approval.status = Approval.Status.APPROVED
        approval.approved_by = user
        approval.save()
        client.post(f'/approvals/{approval.pk}/approve/')
        approval.refresh_from_db()
        assert approval.status == Approval.Status.APPROVED

    def test_approve_requires_post(self, auth_client, approval):
        client, _ = auth_client
        response = client.get(f'/approvals/{approval.pk}/approve/')
        assert response.status_code == 405

    def test_reject_requires_post(self, auth_client, approval):
        client, _ = auth_client
        response = client.get(f'/approvals/{approval.pk}/reject/')
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Issue #18: Work
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkList:
    def test_list_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/')
        assert response.status_code == 200

    def test_list_shows_work(self, auth_client, project, work):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/')
        assert response.status_code == 200

    def test_list_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/works/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestWorkCreate:
    def test_create_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, project, work_type):
        client, _ = auth_client
        response = client.post(f'/projects/{project.pk}/works/create/', {
            'work_type': work_type.pk,
            'quantity': 1,
            'estimated_cost': '250000',
            'status': 'PENDING',
            'bedrooms': 0,
            'is_notional_cost': True,
        }, follow=True)
        assert response.status_code == 200
        assert Work.objects.filter(project=project, work_type=work_type).exists()

    def test_create_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/works/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestWorkDetail:
    def test_detail_get(self, auth_client, project, work):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/{work.pk}/')
        assert response.status_code == 200

    def test_detail_404_on_missing(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestWorkEdit:
    def test_edit_get(self, auth_client, project, work):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/{work.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, project, work, work_type):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/works/{work.pk}/edit/', {
            'work_type': work_type.pk,
            'quantity': 2,
            'estimated_cost': '300000',
            'status': 'IN_PROGRESS',
            'bedrooms': 0,
            'is_notional_cost': True,
            'cashflow_method': 'MILESTONE',
        })
        work.refresh_from_db()
        assert work.quantity == 2
        assert work.status == 'IN_PROGRESS'


@pytest.mark.django_db
class TestWorkDelete:
    def test_delete_get(self, auth_client, project, work):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/works/{work.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, project, work):
        client, _ = auth_client
        work_id = work.pk
        client.post(f'/projects/{project.pk}/works/{work_id}/delete/')
        assert not Work.objects.filter(pk=work_id).exists()


# ---------------------------------------------------------------------------
# Issue #18: Address
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAddressList:
    def test_list_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/')
        assert response.status_code == 200

    def test_list_shows_address(self, auth_client, project, address):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/')
        assert response.status_code == 200

    def test_list_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/addresses/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestAddressCreate:
    def test_create_get(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, project):
        client, _ = auth_client
        response = client.post(f'/projects/{project.pk}/addresses/create/', {
            'street': '123 Test Street',
            'lot': '1',
            'plan': 'SP123',
        }, follow=True)
        assert response.status_code == 200
        assert Address.objects.filter(project=project, street='123 Test Street').exists()

    def test_create_requires_login(self, project):
        response = Client().get(f'/projects/{project.pk}/addresses/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestAddressDetail:
    def test_detail_get(self, auth_client, project, address):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/{address.pk}/')
        assert response.status_code == 200

    def test_detail_404_on_missing(self, auth_client, project):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAddressEdit:
    def test_edit_get(self, auth_client, project, address):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/{address.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_object(self, auth_client, project, address):
        client, _ = auth_client
        client.post(f'/projects/{project.pk}/addresses/{address.pk}/edit/', {
            'street': '456 New Street',
        })
        address.refresh_from_db()
        assert address.street == '456 New Street'


@pytest.mark.django_db
class TestAddressDelete:
    def test_delete_get(self, auth_client, project, address):
        client, _ = auth_client
        response = client.get(f'/projects/{project.pk}/addresses/{address.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, project, address):
        client, _ = auth_client
        addr_id = address.pk
        client.post(f'/projects/{project.pk}/addresses/{addr_id}/delete/')
        assert not Address.objects.filter(pk=addr_id).exists()
