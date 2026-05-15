"""
Tests for issue #23 (FundingNotice→ExpenseClaim pipeline),
#33 (Allocation XOR validation), and #35 (document_uri display).
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import (
    Council, Program, Project, FundingSchedule, FundingNotice, ExpenseClaim,
    WorkFunding, Profile,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council():
    return Council.objects.create(name='Pipeline Test Council', region='NSW')


@pytest.fixture
def program(council):
    return Program.objects.create(
        name='Pipeline Test Program',
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('1000000'),
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        name='Pipeline Test Project', council=council, program=program,
        state=Project.State.PROSPECTIVE, financial_year='2025-2026',
    )


@pytest.fixture
def notice(project):
    return FundingNotice.objects.create(
        project=project,
        capped_amount=Decimal('10000'),
        status=FundingNotice.Status.OPEN,
    )


@pytest.fixture
def draft_claim(notice):
    return ExpenseClaim.objects.create(
        funding_notice=notice,
        amount=Decimal('2000'),
        status=ExpenseClaim.Status.DRAFT,
    )


@pytest.fixture
def submitted_claim(notice):
    return ExpenseClaim.objects.create(
        funding_notice=notice,
        amount=Decimal('3000'),
        status=ExpenseClaim.Status.SUBMITTED,
    )


@pytest.fixture
def funding_schedule(project):
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('500000'),
        contingency=Decimal('0'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
        status=FundingSchedule.Status.DRAFT,
    )


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='pipeline_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.SENIOR_OFFICER)
    client.force_login(user)
    return client, user


# ===========================================================================
# Issue #23 — FundingNotice → ExpenseClaim pipeline
# ===========================================================================

@pytest.mark.django_db
class TestExpenseClaimSubmit:
    def test_draft_becomes_submitted(self, auth_client, draft_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{draft_claim.pk}/submit/')
        draft_claim.refresh_from_db()
        assert draft_claim.status == ExpenseClaim.Status.SUBMITTED

    def test_non_draft_rejected(self, auth_client, submitted_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{submitted_claim.pk}/submit/')
        submitted_claim.refresh_from_db()
        assert submitted_claim.status == ExpenseClaim.Status.SUBMITTED

    def test_requires_login(self, draft_claim):
        response = Client().post(f'/expense-claims/{draft_claim.pk}/submit/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestExpenseClaimApprove:
    def test_submitted_becomes_approved(self, auth_client, submitted_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{submitted_claim.pk}/approve/')
        submitted_claim.refresh_from_db()
        assert submitted_claim.status == ExpenseClaim.Status.APPROVED

    def test_draft_cannot_be_approved(self, auth_client, draft_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{draft_claim.pk}/approve/')
        draft_claim.refresh_from_db()
        assert draft_claim.status == ExpenseClaim.Status.DRAFT

    def test_approval_sets_approved_by_and_date(self, auth_client, submitted_claim):
        client, user = auth_client
        client.post(f'/expense-claims/{submitted_claim.pk}/approve/')
        submitted_claim.refresh_from_db()
        assert submitted_claim.approved_by == user
        assert submitted_claim.approved_date is not None

    def test_cap_exceeded_blocked(self, auth_client, notice):
        # Create a claim that would exceed the cap
        big_claim = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('11000'),
            status=ExpenseClaim.Status.SUBMITTED,
        )
        client, _ = auth_client
        client.post(f'/expense-claims/{big_claim.pk}/approve/')
        big_claim.refresh_from_db()
        assert big_claim.status == ExpenseClaim.Status.SUBMITTED

    def test_auto_close_notice_when_exhausted(self, auth_client, notice):
        # Claim that fills the cap exactly
        full_claim = ExpenseClaim.objects.create(
            funding_notice=notice,
            amount=Decimal('10000'),
            status=ExpenseClaim.Status.SUBMITTED,
        )
        client, _ = auth_client
        client.post(f'/expense-claims/{full_claim.pk}/approve/')
        notice.refresh_from_db()
        assert notice.status == FundingNotice.Status.CLOSED


@pytest.mark.django_db
class TestExpenseClaimReject:
    def test_submitted_can_be_rejected(self, auth_client, submitted_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{submitted_claim.pk}/reject/')
        submitted_claim.refresh_from_db()
        assert submitted_claim.status == ExpenseClaim.Status.REJECTED

    def test_draft_cannot_be_rejected(self, auth_client, draft_claim):
        client, _ = auth_client
        client.post(f'/expense-claims/{draft_claim.pk}/reject/')
        draft_claim.refresh_from_db()
        assert draft_claim.status == ExpenseClaim.Status.DRAFT


@pytest.mark.django_db
class TestFundingNoticeRunningTotal:
    def test_remaining_updates_after_approval(self, auth_client, notice):
        c1 = ExpenseClaim.objects.create(
            funding_notice=notice, amount=Decimal('3000'), status=ExpenseClaim.Status.SUBMITTED,
        )
        c2 = ExpenseClaim.objects.create(
            funding_notice=notice, amount=Decimal('4000'), status=ExpenseClaim.Status.SUBMITTED,
        )
        client, _ = auth_client
        client.post(f'/expense-claims/{c1.pk}/approve/')
        assert notice.approved_claims_total == Decimal('3000')
        assert notice.remaining == Decimal('7000')
        client.post(f'/expense-claims/{c2.pk}/approve/')
        assert notice.approved_claims_total == Decimal('7000')
        assert notice.remaining == Decimal('3000')


# ===========================================================================
# Issue #33 — Allocation XOR constraint (model clean())
# ===========================================================================

@pytest.mark.django_db
class TestWorkFundingXOR:
    def test_only_project_passes(self, project, funding_schedule):
        wf = WorkFunding(
            funding_schedule=funding_schedule,
            project=project,
            work=None,
            amount=Decimal('100'),
        )
        wf.clean()  # should not raise

    def test_both_project_and_work_fails(self, project, funding_schedule):
        from apps.core.models import Work, WorkType
        wt = WorkType.objects.create(name='Civil', category='CIVIL')
        work = Work.objects.create(project=project, work_type=wt)
        wf = WorkFunding(
            funding_schedule=funding_schedule,
            project=project,
            work=work,
            amount=Decimal('100'),
        )
        with pytest.raises(ValidationError, match='not both'):
            wf.clean()

    def test_neither_project_nor_work_fails(self, funding_schedule):
        wf = WorkFunding(
            funding_schedule=funding_schedule,
            project=None,
            work=None,
            amount=Decimal('100'),
        )
        with pytest.raises(ValidationError, match='either a project or a work'):
            wf.clean()

    def test_only_work_passes(self, project, funding_schedule):
        from apps.core.models import Work, WorkType
        wt = WorkType.objects.create(name='Electrical', category='ELECTRICAL')
        work = Work.objects.create(project=project, work_type=wt)
        wf = WorkFunding(
            funding_schedule=funding_schedule,
            project=None,
            work=work,
            amount=Decimal('100'),
        )
        wf.clean()  # should not raise


# ===========================================================================
# Issue #35 — document_uri / document_link display
# ===========================================================================

@pytest.mark.django_db
class TestDocumentLinkDisplay:
    def test_variation_detail_shows_document_link(self, auth_client, project, funding_schedule):
        from apps.core.models import Variation
        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status=Variation.Status.DRAFT,
            document_link='https://drive.google.com/test-doc',
        )
        client, _ = auth_client
        response = client.get(f'/variations/{variation.pk}/')
        assert response.status_code == 200
        assert b'https://drive.google.com/test-doc' in response.content
        assert b'Open document' in response.content

    def test_variation_detail_no_document_shows_placeholder(self, auth_client, project, funding_schedule):
        from apps.core.models import Variation
        variation = Variation.objects.create(
            funding_schedule=funding_schedule,
            status=Variation.Status.DRAFT,
            document_link='',
        )
        client, _ = auth_client
        response = client.get(f'/variations/{variation.pk}/')
        assert response.status_code == 200
        assert b'No document attached' in response.content

    def test_funding_agreement_detail_shows_document_uri(self, auth_client, council):
        from apps.core.models import FundingAgreement
        agreement = FundingAgreement.objects.create(
            council=council,
            name='Test Agreement',
            document_uri='https://drive.google.com/agreement-doc',
            status=FundingAgreement.Status.ACTIVE,
        )
        client, _ = auth_client
        response = client.get(f'/funding-agreements/{agreement.pk}/')
        assert response.status_code == 200
        assert b'https://drive.google.com/agreement-doc' in response.content
        assert b'Open document' in response.content

    def test_funding_agreement_no_document_shows_placeholder(self, auth_client, council):
        from apps.core.models import FundingAgreement
        agreement = FundingAgreement.objects.create(
            council=council,
            name='Test Agreement 2',
            document_uri='',
            status=FundingAgreement.Status.DRAFT,
        )
        client, _ = auth_client
        response = client.get(f'/funding-agreements/{agreement.pk}/')
        assert response.status_code == 200
        assert b'No document attached' in response.content
