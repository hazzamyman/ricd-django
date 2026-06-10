"""Council-scoped land-project linking: child dwellings, parcels, DA, infrastructure."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_child_dwellings_link_and_council_scoped(admin_client, land_project, program):
    from apps.core.models import Project, Council

    same = Project.objects.create(
        council=land_project.council, program=program, name='Same Council Dwelling',
        project_type=Project.Type.DWELLING, state=Project.State.PROGRAMMED)
    other_council = Council.objects.create(name='Other Council', region='Elsewhere')
    other = Project.objects.create(
        council=other_council, program=program, name='Other Council Dwelling',
        project_type=Project.Type.DWELLING, state=Project.State.PROGRAMMED)

    url = reverse('ui:project_link_child_dwellings', kwargs={'project_pk': land_project.pk})
    body = admin_client.get(url).content.decode()
    # Only the same-council dwelling is offered.
    assert 'Same Council Dwelling' in body
    assert 'Other Council Dwelling' not in body

    admin_client.post(url, {'children': [same.pk]})
    same.refresh_from_db()
    other.refresh_from_db()
    assert same.parent_land_project_id == land_project.pk
    assert other.parent_land_project_id is None


@pytest.mark.django_db
def test_link_land_parcel(admin_client, land_project, land_tenure):
    url = reverse('ui:project_link_land_parcels', kwargs={'project_pk': land_project.pk})
    resp = admin_client.post(url, {'parcels': [land_tenure.pk]})
    assert resp.status_code in (200, 302)
    assert land_project.land_parcels.filter(pk=land_tenure.pk).exists()


@pytest.mark.django_db
def test_link_da(admin_client, land_project, development_application):
    url = reverse('ui:project_link_da', kwargs={'project_pk': land_project.pk})
    admin_client.post(url, {'development_application': development_application.pk})
    land_project.refresh_from_db()
    assert land_project.development_application_id == development_application.pk


@pytest.mark.django_db
def test_infrastructure_edit(admin_client, land_project):
    url = reverse('ui:project_infrastructure_edit', kwargs={'project_pk': land_project.pk})
    admin_client.post(url, {
        'infra_water_assessment': 'Town water available',
        'infra_electricity_assessment': '', 'infra_sewerage_assessment': '',
        'infra_comments': '',
    })
    land_project.refresh_from_db()
    assert land_project.infra_water_assessment == 'Town water available'
