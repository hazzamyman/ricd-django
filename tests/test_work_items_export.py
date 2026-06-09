"""All Work Items CSV dump export."""
import pytest
from decimal import Decimal
from django.urls import reverse
from tests.fixtures import make_bfa


@pytest.mark.django_db
def test_work_items_export_csv(admin_client, project, work_type):
    from apps.core.models import Work

    work_type.category = 'RESIDENTIAL'
    work_type.save()
    Work.objects.create(project=project, work_type=work_type, quantity=2,
                        estimated_cost=Decimal('300000'), is_notional_cost=False,
                        actual_cost=Decimal('300000'), status='IN_PROGRESS')
    make_bfa(project, funding_amount=600000, status='APPROVED')

    resp = admin_client.get(reverse('ui:work_items_export'))

    assert resp.status_code == 200
    assert resp['Content-Type'].startswith('text/csv')
    assert 'attachment' in resp['Content-Disposition']
    body = resp.content.decode()
    # Header columns the request asked for.
    assert 'Council (LGA)' in body
    assert 'Project Approved Budget (BFA)' in body
    assert 'Project Expended (Released)' in body
    assert 'All Steps Complete' in body
    # The work item row carries its project + project-level approved budget.
    assert project.name in body
    assert '600000.00' in body


@pytest.mark.django_db
def test_work_items_export_excludes_archived_by_default(admin_client, project, work_type):
    from apps.core.models import Work

    work_type.category = 'RESIDENTIAL'
    work_type.save()
    Work.objects.create(project=project, work_type=work_type, quantity=1,
                        estimated_cost=Decimal('100000'), is_notional_cost=False,
                        actual_cost=Decimal('100000'))
    project.is_archived = True
    project.save()

    resp = admin_client.get(reverse('ui:work_items_export'))
    assert project.name not in resp.content.decode()

    resp2 = admin_client.get(reverse('ui:work_items_export'), {'include_archived': '1'})
    assert project.name in resp2.content.decode()
