"""
Tests for issue #21 (FundingSchedule lifecycle) and #22 (Payment release pipeline).
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import Council, Program, Project, FundingSchedule, Payment, Profile


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council():
    return Council.objects.create(name='Lifecycle Test Council', region='QLD')


@pytest.fixture
def program(council):
    return Program.objects.create(
        name='Lifecycle Test Program',
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('2000000'),
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        name='Lifecycle Test Project', council=council, program=program,
        state=Project.State.PROSPECTIVE, financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(project):
    return FundingSchedule.objects.create(
        project=project,
        status=FundingSchedule.Status.DRAFT
    )


@pytest.fixture
def payment(project, funding_schedule):
    return Payment.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        calculation_type=Payment.CalculationType.PERCENTAGE,
        percentage=Decimal('30.00'),
        payment_type=Payment.PaymentType.FIRST,
        payment_split=Payment.PaymentSplit.STANDARD,
        status=Payment.Status.PENDING,
    )


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='lifecycle_user', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.MANAGER)
    client.force_login(user)
    return client, user


# ===========================================================================
# Issue #21 — FundingSchedule lifecycle
# DRAFT → READY → EXECUTED → ACTIVE → COMPLETED/SUPERSEDED/CANCELLED
# ===========================================================================

@pytest.mark.django_db
class TestFundingScheduleMarkReady:
    def test_draft_becomes_ready(self, auth_client, funding_schedule):
        client, _ = auth_client
        client.post(f'/funding-schedules/{funding_schedule.pk}/mark-ready/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.READY_FOR_EXECUTION

    def test_non_draft_rejected(self, auth_client, funding_schedule):
        client, _ = auth_client
        funding_schedule.status = FundingSchedule.Status.ACTIVE
        funding_schedule.save()
        client.post(f'/funding-schedules/{funding_schedule.pk}/mark-ready/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.ACTIVE

    def test_requires_login(self, funding_schedule):
        response = Client().post(f'/funding-schedules/{funding_schedule.pk}/mark-ready/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestFundingScheduleComplete:
    def test_active_becomes_completed(self, auth_client, funding_schedule):
        client, _ = auth_client
        # Use update() to bypass signals so we can set ACTIVE directly in test setup
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status=FundingSchedule.Status.ACTIVE)
        client.post(f'/funding-schedules/{funding_schedule.pk}/complete/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.COMPLETED

    def test_non_active_cannot_complete(self, auth_client, funding_schedule):
        client, _ = auth_client
        client.post(f'/funding-schedules/{funding_schedule.pk}/complete/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.DRAFT


@pytest.mark.django_db
class TestFundingScheduleSupersede:
    def test_active_can_be_superseded(self, auth_client, funding_schedule):
        client, _ = auth_client
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status=FundingSchedule.Status.ACTIVE)
        client.post(f'/funding-schedules/{funding_schedule.pk}/supersede/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.SUPERSEDED

    def test_draft_can_be_superseded(self, auth_client, funding_schedule):
        client, _ = auth_client
        client.post(f'/funding-schedules/{funding_schedule.pk}/supersede/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.SUPERSEDED

    def test_completed_cannot_be_superseded(self, auth_client, funding_schedule):
        client, _ = auth_client
        funding_schedule.status = FundingSchedule.Status.COMPLETED
        funding_schedule.save()
        client.post(f'/funding-schedules/{funding_schedule.pk}/supersede/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.COMPLETED


@pytest.mark.django_db
class TestFundingScheduleCancel:
    def test_draft_can_be_cancelled(self, auth_client, funding_schedule):
        client, _ = auth_client
        client.post(f'/funding-schedules/{funding_schedule.pk}/cancel/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.CANCELLED

    def test_active_can_be_cancelled(self, auth_client, funding_schedule):
        client, _ = auth_client
        FundingSchedule.objects.filter(pk=funding_schedule.pk).update(status=FundingSchedule.Status.ACTIVE)
        client.post(f'/funding-schedules/{funding_schedule.pk}/cancel/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.CANCELLED

    def test_completed_cannot_be_cancelled(self, auth_client, funding_schedule):
        client, _ = auth_client
        funding_schedule.status = FundingSchedule.Status.COMPLETED
        funding_schedule.save()
        client.post(f'/funding-schedules/{funding_schedule.pk}/cancel/')
        funding_schedule.refresh_from_db()
        assert funding_schedule.status == FundingSchedule.Status.COMPLETED


# ===========================================================================
# Issue #22 — Payment release pipeline
# PENDING → RECOMMENDED → APPROVED → RELEASED  (REJECTED at any pre-final step)
# ===========================================================================

@pytest.mark.django_db
class TestPaymentRecommend:
    def test_pending_becomes_recommended(self, auth_client, payment):
        client, _ = auth_client
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/recommend/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.RECOMMENDED

    def test_non_pending_rejected(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.APPROVED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/recommend/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED

    def test_requires_login(self, payment):
        response = Client().post(f'/projects/{payment.project_id}/payments/{payment.pk}/recommend/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestPaymentApprove:
    def test_recommended_becomes_approved(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.RECOMMENDED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/approve/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED

    def test_pending_cannot_approve(self, auth_client, payment):
        client, _ = auth_client
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/approve/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
class TestPaymentRelease:
    def test_approved_becomes_released(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.APPROVED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/release/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.RELEASED

    def test_pending_cannot_release(self, auth_client, payment):
        client, _ = auth_client
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/release/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
class TestPaymentReject:
    def test_pending_can_be_rejected(self, auth_client, payment):
        client, _ = auth_client
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/reject/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REJECTED

    def test_recommended_can_be_rejected(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.RECOMMENDED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/reject/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REJECTED

    def test_approved_can_be_rejected(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.APPROVED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/reject/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REJECTED

    def test_released_cannot_be_rejected(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.RELEASED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/reject/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.RELEASED

    def test_already_rejected_is_noop(self, auth_client, payment):
        client, _ = auth_client
        payment.status = Payment.Status.REJECTED
        payment.save()
        client.post(f'/projects/{payment.project_id}/payments/{payment.pk}/reject/')
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REJECTED
