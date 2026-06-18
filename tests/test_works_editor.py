"""Combined Address + Works editor: single-Save create / edit / delete."""
import json
import pytest
from decimal import Decimal
from django.urls import reverse


def _url(project):
    return reverse('ui:project_addresses_works_edit', kwargs={'pk': project.pk})


@pytest.mark.django_db
def test_create_address_and_work(admin_client, project, work_type):
    from apps.core.models import Address, Work
    payload = {
        'addresses': [{
            'id': None, 'street': '1 New St', 'lot': '1', 'plan': 'SP1',
            'suburb': None, 'lease_status': '',
            'works': [{'id': None, 'work_type': work_type.pk, 'bedrooms': 3,
                       'quantity': 2, 'estimated_cost': '500000', 'status': 'PENDING'}],
        }],
        'deleted_addresses': [], 'deleted_works': [],
    }
    resp = admin_client.post(_url(project), {'payload': json.dumps(payload)})
    assert resp.status_code in (200, 302)

    addr = Address.objects.get(project=project, street='1 New St')
    assert addr.lot == '1' and addr.plan == 'SP1'
    w = Work.objects.get(address=addr)
    assert w.work_type_id == work_type.pk
    assert w.quantity == 2 and w.bedrooms == 3
    assert w.estimated_cost == Decimal('500000.00')


@pytest.mark.django_db
def test_edit_then_delete_work(admin_client, work):
    from apps.core.models import Work
    project, addr = work.project, work.address
    base_addr = {'id': addr.pk, 'street': addr.street, 'lot': addr.lot, 'plan': addr.plan,
                 'suburb': addr.suburb_id, 'lease_status': ''}

    # Edit the work.
    payload = {'addresses': [dict(base_addr, works=[{
        'id': work.pk, 'work_type': work.work_type_id, 'bedrooms': 4,
        'quantity': 5, 'estimated_cost': '123', 'status': 'COMPLETED'}])],
        'deleted_addresses': [], 'deleted_works': []}
    admin_client.post(_url(project), {'payload': json.dumps(payload)})
    work.refresh_from_db()
    assert work.quantity == 5 and work.bedrooms == 4 and work.status == 'COMPLETED'

    # Delete the work.
    payload2 = {'addresses': [dict(base_addr, works=[])],
                'deleted_addresses': [], 'deleted_works': [work.pk]}
    admin_client.post(_url(project), {'payload': json.dumps(payload2)})
    assert not Work.objects.filter(pk=work.pk).exists()


@pytest.mark.django_db
def test_cannot_delete_another_projects_work(admin_client, project, work_type, council, program):
    from apps.core.models import Project, Address, Work
    other = Project.objects.create(council=council, program=program, name='Other Project',
                                   project_type=Project.Type.DWELLING)
    other_addr = Address.objects.create(project=other, street='99 Other St')
    other_work = Work.objects.create(project=other, address=other_addr, work_type=work_type,
                                     quantity=1, estimated_cost=Decimal('0'))

    payload = {'addresses': [], 'deleted_addresses': [], 'deleted_works': [other_work.pk]}
    admin_client.post(_url(project), {'payload': json.dumps(payload)})
    # The editor is scoped to `project`, so another project's work survives.
    assert Work.objects.filter(pk=other_work.pk).exists()
