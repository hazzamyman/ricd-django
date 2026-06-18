"""Inline (popup) contractor quick-add from a Work form — name-only, council derived."""
import pytest


@pytest.mark.django_db
def test_quick_add_with_name_only(admin_client, council):
    from apps.core.models import Contractor
    r = admin_client.post(
        f'/contractors/quick-add/?council={council.pk}&_popup=1&field=id_contractor',
        {'company_name': 'Acme Builders', '_popup': '1', 'field': 'id_contractor'},
    )
    assert r.status_code == 200          # popup response page
    assert b'popup_added' in r.content   # posts the new contractor back to the dropdown

    c = Contractor.objects.get(company_name='Acme Builders')
    assert c.council_id == council.pk            # council taken from the work's project
    assert c.trade_type == Contractor.TradeType.OTHER  # defaulted; not required
    assert c.abn == '' and c.licence_number == ''      # other fields optional


@pytest.mark.django_db
def test_quick_add_requires_name(admin_client, council):
    from apps.core.models import Contractor
    before = Contractor.objects.count()
    r = admin_client.post(
        f'/contractors/quick-add/?council={council.pk}&_popup=1&field=id_contractor',
        {'company_name': '', '_popup': '1', 'field': 'id_contractor'},
    )
    # Re-renders the popup form with an error; nothing created.
    assert Contractor.objects.count() == before
