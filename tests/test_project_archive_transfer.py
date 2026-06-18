"""Project archive (reversible) + transfer-works-between-same-council projects.

Uses pytest-django's `admin_client` (a logged-in superuser) — superusers pass the
FNC/manager checks on these actions.
"""
import pytest


@pytest.mark.django_db
def test_archive_then_unarchive_hides_and_restores(admin_client, project):
    r = admin_client.post(f'/projects/{project.pk}/archive/', {'reason': 'cancelled mid-build'})
    assert r.status_code in (302, 200)
    project.refresh_from_db()
    assert project.is_archived is True
    assert project.archived_at is not None
    assert project.archived_reason == 'cancelled mid-build'

    # Hidden from the default list, visible with ?archived=1 (match the row's
    # detail link, not the name, to avoid duplicate-name false positives).
    row_link = f'href="/projects/{project.pk}/"'
    assert row_link not in admin_client.get('/projects/').content.decode('utf8', 'ignore')
    assert row_link in admin_client.get('/projects/?archived=1').content.decode('utf8', 'ignore')

    admin_client.post(f'/projects/{project.pk}/unarchive/')
    project.refresh_from_db()
    assert project.is_archived is False
    assert project.archived_at is None


@pytest.mark.django_db
def test_transfer_moves_work_and_its_address_same_council(admin_client, project, work, council, program):
    from apps.core.models import Project
    target = Project.objects.create(
        name='Target Project', council=council, program=program,
        state=Project.State.PROSPECTIVE,
    )
    addr_id = work.address_id

    r = admin_client.post(f'/projects/{project.pk}/transfer-works/', {
        'target_project': target.pk, 'works': [work.pk],
    })
    assert r.status_code in (302, 200)

    work.refresh_from_db()
    assert work.project_id == target.pk
    if addr_id:  # address moves with the work so it doesn't span two projects
        from apps.core.models import Address
        assert Address.objects.get(pk=addr_id).project_id == target.pk


@pytest.mark.django_db
def test_transfer_to_other_council_is_blocked(admin_client, project, work, program):
    from apps.core.models import Project, Council
    other_council = Council.objects.create(
        name='Other Shire Council', region='R', state_electorate='S',
        federal_electorate='F', is_registered_housing_provider=False,
    )
    other = Project.objects.create(
        name='Other-council Project', council=other_council, program=program,
        state=Project.State.PROSPECTIVE,
    )

    admin_client.post(f'/projects/{project.pk}/transfer-works/', {
        'target_project': other.pk, 'works': [work.pk],
    })
    work.refresh_from_db()
    assert work.project_id == project.pk  # NOT moved — different council
