"""Test that all required API endpoints exist and are accessible."""
import pytest
from django.test import Client
from django.contrib.auth.models import User


def _make_fnc_client(db):
    """Create an authenticated FNC Manager client."""
    from apps.core.models import Profile
    user = User.objects.create_user(username='apitestuser', password='pass')
    Profile.objects.create(user=user, officer_role='MANAGER')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestAPIEndpoints:
    """Verify all governance and funding APIs are accessible"""

    def test_payment_rules_endpoint(self, db):
        """GET /api/v1/payment-rules/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/payment-rules/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_agreements_endpoint(self, db):
        """GET /api/v1/funding-agreements/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/funding-agreements/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_schedules_endpoint(self, db):
        """GET /api/v1/funding-schedules/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/funding-schedules/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_brief_financial_approvals_endpoint(self, db):
        """GET /api/v1/brief-financial-approvals/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/brief-financial-approvals/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_payments_endpoint(self, db):
        """GET /api/v1/payments/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/payments/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_approvals_endpoint(self, db):
        """GET /api/v1/approvals/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/approvals/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_notices_endpoint(self, db):
        """GET /api/v1/funding-notices/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/funding-notices/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_expense_claims_endpoint(self, db):
        """GET /api/v1/expense-claims/ should be accessible"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/expense-claims/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_workflow_actions_endpoint(self, db):
        """GET /api/v1/workflow-actions/ should be accessible (read-only)"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/workflow-actions/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_audit_logs_endpoint(self, db):
        """GET /api/v1/audit-logs/ should be accessible (read-only)"""
        client = _make_fnc_client(db)
        response = client.get('/api/v1/audit-logs/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_unauthenticated_returns_403(self):
        """Anonymous requests must be rejected"""
        client = Client()
        response = client.get('/api/v1/payment-rules/', HTTP_ACCEPT='application/json')
        assert response.status_code in (401, 403)
