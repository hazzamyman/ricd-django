"""
Tests for FundingNotice and ExpenseClaim CRUD views (issues #12 and #13).
Covers: list, create, detail, edit, delete, close, approve, reject.
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from apps.core.models import FundingNotice, ExpenseClaim


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='fn_superuser', email='fn@test.com', password='testpass123'
    )


@pytest.fixture
def auth_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture
def notice(project):
    return FundingNotice.objects.create(
        project=project,
        capped_amount=Decimal('100000'),
        issued_date='2025-01-01',
        status='OPEN',
    )


@pytest.fixture
def draft_claim(notice):
    return ExpenseClaim.objects.create(
        funding_notice=notice,
        amount=Decimal('20000'),
        date_submitted='2025-02-01',
        status='DRAFT',
    )


@pytest.fixture
def submitted_claim(notice):
    return ExpenseClaim.objects.create(
        funding_notice=notice,
        amount=Decimal('30000'),
        date_submitted='2025-02-15',
        status='SUBMITTED',
    )


# ---------------------------------------------------------------------------
# FundingNotice list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeList:

    def test_list_get(self, auth_client):
        response = auth_client.get('/funding-notices/')
        assert response.status_code == 200

    def test_list_shows_notice(self, auth_client, notice):
        response = auth_client.get('/funding-notices/')
        assert response.status_code == 200
        assert notice.project.name.encode() in response.content

    def test_list_requires_login(self, client):
        response = client.get('/funding-notices/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# FundingNotice create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeCreate:

    def test_create_get(self, auth_client):
        response = auth_client.get('/funding-notices/create/')
        assert response.status_code == 200

    def test_create_post_creates_object(self, auth_client, project):
        before = FundingNotice.objects.count()
        response = auth_client.post('/funding-notices/create/', {
            'project': project.pk,
            'capped_amount': '50000',
            'issued_date': '2025-03-01',
            'notes': '',
        })
        assert response.status_code in (200, 302)
        assert FundingNotice.objects.count() == before + 1

    def test_create_requires_login(self, client):
        response = client.get('/funding-notices/create/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# FundingNotice detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeDetail:

    def test_detail_get(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/')
        assert response.status_code == 200

    def test_detail_shows_cap(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/')
        assert b'100000' in response.content

    def test_detail_shows_claims(self, auth_client, notice, draft_claim):
        response = auth_client.get(f'/funding-notices/{notice.pk}/')
        assert response.status_code == 200
        assert b'20000' in response.content

    def test_detail_shows_remaining(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/')
        assert b'100000' in response.content  # full cap remaining

    def test_detail_404_on_missing(self, auth_client):
        response = auth_client.get('/funding-notices/99999/')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# FundingNotice edit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeEdit:

    def test_edit_get(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_cap(self, auth_client, notice, project):
        response = auth_client.post(f'/funding-notices/{notice.pk}/edit/', {
            'project': project.pk,
            'capped_amount': '200000',
            'issued_date': '2025-01-01',
            'notes': '',
        })
        assert response.status_code in (200, 302)
        notice.refresh_from_db()
        assert notice.capped_amount == Decimal('200000')


# ---------------------------------------------------------------------------
# FundingNotice delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeDelete:

    def test_delete_get(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_object(self, auth_client, notice):
        pk = notice.pk
        response = auth_client.post(f'/funding-notices/{pk}/delete/')
        assert response.status_code in (200, 302)
        assert not FundingNotice.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# FundingNotice close action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeClose:

    def test_close_sets_status(self, auth_client, notice):
        assert notice.status == 'OPEN'
        response = auth_client.post(f'/funding-notices/{notice.pk}/close/')
        assert response.status_code in (200, 302)
        notice.refresh_from_db()
        assert notice.status == 'CLOSED'

    def test_close_requires_post(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/close/')
        assert response.status_code == 405  # method not allowed


# ---------------------------------------------------------------------------
# ExpenseClaim create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExpenseClaimCreate:

    def test_create_get(self, auth_client, notice):
        response = auth_client.get(f'/funding-notices/{notice.pk}/claims/create/')
        assert response.status_code == 200

    def test_create_post_creates_claim(self, auth_client, notice):
        before = ExpenseClaim.objects.count()
        response = auth_client.post(f'/funding-notices/{notice.pk}/claims/create/', {
            'amount': '15000',
            'date_submitted': '2025-03-01',
            'status': 'DRAFT',
            'notes': '',
            'sap_document_reference': '',
        })
        assert response.status_code in (200, 302)
        assert ExpenseClaim.objects.count() == before + 1
        claim = ExpenseClaim.objects.latest('created_at')
        assert claim.funding_notice == notice


# ---------------------------------------------------------------------------
# ExpenseClaim edit / delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExpenseClaimEditDelete:

    def test_edit_get(self, auth_client, draft_claim):
        response = auth_client.get(f'/expense-claims/{draft_claim.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_amount(self, auth_client, draft_claim, notice):
        response = auth_client.post(f'/expense-claims/{draft_claim.pk}/edit/', {
            'amount': '25000',
            'date_submitted': '2025-02-01',
            'status': 'DRAFT',
            'notes': '',
            'sap_document_reference': '',
        })
        assert response.status_code in (200, 302)
        draft_claim.refresh_from_db()
        assert draft_claim.amount == Decimal('25000')

    def test_delete_get(self, auth_client, draft_claim):
        response = auth_client.get(f'/expense-claims/{draft_claim.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_claim(self, auth_client, draft_claim):
        pk = draft_claim.pk
        response = auth_client.post(f'/expense-claims/{pk}/delete/')
        assert response.status_code in (200, 302)
        assert not ExpenseClaim.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# ExpenseClaim approve / reject (with cap enforcement)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExpenseClaimApprove:

    def test_approve_within_cap(self, auth_client, submitted_claim, notice):
        response = auth_client.post(f'/expense-claims/{submitted_claim.pk}/approve/')
        assert response.status_code in (200, 302)
        submitted_claim.refresh_from_db()
        assert submitted_claim.status == 'APPROVED'
        assert submitted_claim.approved_by is not None

    def test_approve_over_cap_blocked(self, auth_client, notice, superuser):
        # Fill the cap with an approved claim first
        approved = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('90000'),
            status='APPROVED',
            approved_by=superuser,
            approved_date='2025-02-01',
        )
        # This claim would push total to 110000 > 100000 cap
        over_cap = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('20000'),
            status='SUBMITTED',
        )
        response = auth_client.post(f'/expense-claims/{over_cap.pk}/approve/', follow=True)
        over_cap.refresh_from_db()
        assert over_cap.status == 'SUBMITTED'  # not approved

    def test_approve_exhausts_cap_closes_notice(self, auth_client, notice, superuser):
        # Claim that exactly fills the cap
        claim = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('100000'),
            status='SUBMITTED',
        )
        auth_client.post(f'/expense-claims/{claim.pk}/approve/')
        notice.refresh_from_db()
        assert notice.status == 'CLOSED'

    def test_reject_sets_status(self, auth_client, submitted_claim):
        response = auth_client.post(f'/expense-claims/{submitted_claim.pk}/reject/')
        assert response.status_code in (200, 302)
        submitted_claim.refresh_from_db()
        assert submitted_claim.status == 'REJECTED'
