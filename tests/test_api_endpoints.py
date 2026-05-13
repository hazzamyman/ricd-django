"""Test that all required API endpoints exist and are accessible."""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestAPIEndpoints:
    """Verify all governance and funding APIs are accessible"""

    def test_payment_rules_endpoint(self):
        """GET /api/payment-rules/ should be accessible"""
        client = Client()
        response = client.get('/api/payment-rules/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_agreements_endpoint(self):
        """GET /api/funding-agreements/ should be accessible"""
        client = Client()
        response = client.get('/api/funding-agreements/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_schedules_endpoint(self):
        """GET /api/funding-schedules/ should be accessible"""
        client = Client()
        response = client.get('/api/funding-schedules/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_brief_financial_approvals_endpoint(self):
        """GET /api/brief-financial-approvals/ should be accessible"""
        client = Client()
        response = client.get('/api/brief-financial-approvals/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_payments_endpoint(self):
        """GET /api/payments/ should be accessible"""
        client = Client()
        response = client.get('/api/payments/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_approvals_endpoint(self):
        """GET /api/approvals/ should be accessible"""
        client = Client()
        response = client.get('/api/approvals/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_funding_notices_endpoint(self):
        """GET /api/funding-notices/ should be accessible"""
        client = Client()
        response = client.get('/api/funding-notices/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_expense_claims_endpoint(self):
        """GET /api/expense-claims/ should be accessible"""
        client = Client()
        response = client.get('/api/expense-claims/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_workflow_actions_endpoint(self):
        """GET /api/workflow-actions/ should be accessible (read-only)"""
        client = Client()
        response = client.get('/api/workflow-actions/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200

    def test_audit_logs_endpoint(self):
        """GET /api/audit-logs/ should be accessible (read-only)"""
        client = Client()
        response = client.get('/api/audit-logs/', HTTP_ACCEPT='application/json')
        assert response.status_code == 200
