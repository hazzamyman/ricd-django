"""Delegate positions (maintenance CRUD) + Funding Approval works-total auto-fill."""
import json
from decimal import Decimal

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_works_total_endpoint(admin_client, work, project):
    # `work` fixture: quantity 2 x $250,000 = $500,000; 10% contingency = $50,000.
    url = reverse('ui:project_works_total', kwargs={'project_pk': project.pk})
    resp = admin_client.get(url)
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert Decimal(data['works_total']) == Decimal('500000')
    assert Decimal(data['contingency']) == Decimal('50000.00')
    assert Decimal(data['total']) == Decimal('550000.00')


@pytest.mark.django_db
def test_works_total_zero_when_no_works(admin_client, project):
    url = reverse('ui:project_works_total', kwargs={'project_pk': project.pk})
    data = json.loads(admin_client.get(url).content)
    assert Decimal(data['works_total']) == Decimal('0')
    assert Decimal(data['contingency']) == Decimal('0')


@pytest.mark.django_db
def test_delegate_position_list_renders(admin_client):
    # Migration 0051 seeds Manager / Director / General Manager.
    resp = admin_client.get(reverse('ui:delegate_position_list'))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'Manager' in body
    assert 'Director' in body


@pytest.mark.django_db
def test_delegate_position_create(admin_client):
    from apps.core.models import DelegatePosition
    resp = admin_client.post(reverse('ui:delegate_position_create'), {
        'title': 'Executive Director',
        'max_approval_amount': '5000000',
        'is_active': 'on',
        'order': '4',
        'notes': 'High-value approvals.',
    })
    assert resp.status_code == 302
    p = DelegatePosition.objects.get(title='Executive Director')
    assert p.max_approval_amount == Decimal('5000000')


@pytest.mark.django_db
def test_funding_approval_form_lists_active_positions_only(admin_client):
    from apps.core.models import DelegatePosition
    DelegatePosition.objects.filter(title='Director').update(is_active=False)
    body = admin_client.get(reverse('ui:bfa_create_global')).content.decode()
    # Active seeded position present; the inactivated one is not offered.
    assert 'Manager' in body
    assert 'Director' not in body
