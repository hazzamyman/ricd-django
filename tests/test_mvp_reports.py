"""Phase C tests — MVP reporting views (CM Report, EOM Reconciliation, CCL)."""
import datetime
import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_cm_report_loads(admin_client, council, project):
    """Contract Management Report renders for a Funding Schedule."""
    from apps.core.models import FundingSchedule
    fs = FundingSchedule.objects.create(project=project, council=council, schedule_number=1, amount=100000)
    resp = admin_client.get(reverse('ui:funding_schedule_contract_report', args=[fs.pk]))
    assert resp.status_code == 200
    assert b"Contract Management Report" in resp.content


def test_eom_reconciliation_loads(admin_client):
    """EOM Reconciliation view renders with no data."""
    resp = admin_client.get(reverse('ui:eom_reconciliation'))
    assert resp.status_code == 200
    assert b"End-of-Month Reconciliation" in resp.content


def test_eom_reconciliation_loads_with_month(admin_client):
    """EOM Reconciliation accepts ?month=YYYY-MM filter."""
    resp = admin_client.get(reverse('ui:eom_reconciliation') + '?month=2026-05')
    assert resp.status_code == 200
    assert b"May 2026" in resp.content


def test_eom_reconciliation_csv_export(admin_client):
    """EOM CSV export returns text/csv with expected header row."""
    resp = admin_client.get(reverse('ui:eom_reconciliation_export') + '?month=2026-05')
    assert resp.status_code == 200
    assert resp['Content-Type'] == 'text/csv'
    assert b'Release Date,Council,Project' in resp.content


def test_ccl_loads(admin_client):
    """Construction Creation List renders."""
    resp = admin_client.get(reverse('ui:construction_creation_list'))
    assert resp.status_code == 200
    assert b"Construction Creation List" in resp.content


def test_ccl_csv_export(admin_client):
    """CCL CSV export returns text/csv with expected header row."""
    resp = admin_client.get(reverse('ui:construction_creation_list_export'))
    assert resp.status_code == 200
    assert resp['Content-Type'] == 'text/csv'
    assert b'Council,Project,Program' in resp.content


def test_council_dashboard_renders_new_sections(admin_client, council):
    """Phase C1: Council detail includes new dashboard sections."""
    resp = admin_client.get(reverse('ui:council_detail', args=[council.pk]))
    assert resp.status_code == 200
    body = resp.content
    assert b"Financial Summary" in body
    assert b"Reporting Health" in body
    assert b"Project Pipeline" in body


def test_money_filter_formats_and_marks_negative():
    """The money filter formats with $,thousands,2dp and wraps negatives in red."""
    from apps.ui.templatetags.money import money, money_plain
    from decimal import Decimal
    # Positive — bare string, no wrapper
    assert str(money(Decimal('1234567890'))) == '$1,234,567,890.00'
    assert str(money(Decimal('1234.5'))) == '$1,234.50'
    assert str(money(0)) == '$0.00'
    # Negative — wrapped in span class="money-neg"
    out = str(money(Decimal('-1234.50')))
    assert 'money-neg' in out
    assert '-$1,234.50' in out
    # Blank fallback for None/empty
    assert money(None) == '—'
    assert money('') == '—'
    assert money(None, blank='') == ''
    # money_plain has no HTML wrapper, suitable for CSV
    assert money_plain(Decimal('-100')) == '-$100.00'
    assert money_plain(Decimal('100')) == '$100.00'


def test_council_detail_renders_electorate_fk_and_lead_officer(admin_client, council):
    """Regression: state/federal electorate FK + lead_officer FK must display."""
    from django.contrib.auth import get_user_model
    from apps.core.models import StateElectorate, FederalElectorate
    User = get_user_model()
    se, _ = StateElectorate.objects.get_or_create(name="Cook")
    fe, _ = FederalElectorate.objects.get_or_create(name="Leichhardt")
    officer = User.objects.create_user('jane.officer', first_name='Jane', last_name='Officer')
    council.state_electorate_link = se
    council.federal_electorate_link = fe
    council.lead_officer = officer
    council.save()

    resp = admin_client.get(reverse('ui:council_detail', args=[council.pk]))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Cook" in body, "state_electorate_link.name not rendered"
    assert "Leichhardt" in body, "federal_electorate_link.name not rendered"
    assert "Jane Officer" in body, "lead_officer full name not rendered"
