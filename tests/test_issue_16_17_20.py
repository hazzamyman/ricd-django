"""
Tests for issues #16 (VariationItem CRUD + execute), #17 (WorkFunding/Allocation CRUD),
#20 (StageReport lifecycle actions: submit/endorse/assess/approve).
"""
import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import (
    Council, Program, Project, FundingSchedule,
    Variation, VariationItem, StageReport, WorkFunding, Profile,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council():
    return Council.objects.create(name='Test Council', region='QLD')


@pytest.fixture
def program(council):
    return Program.objects.create(
        name='Test Program',
        funding_source=Program.FundingSource.STATE,
        budget=Decimal('1000000'),
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        name='Test Project', council=council, program=program,
        state=Project.State.PROSPECTIVE, financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(project):
    return FundingSchedule.objects.create(
        project=project,
        amount=Decimal('500000'),
        contingency=Decimal('50000'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
    )


@pytest.fixture
def variation(funding_schedule):
    return Variation.objects.create(
        funding_schedule=funding_schedule,
        variation_option=Variation.VariationOption.OPTION_1_ADD_FS,
        status=Variation.Status.DRAFT,
        description='Test variation',
    )


@pytest.fixture
def variation_item(variation):
    return VariationItem.objects.create(
        variation=variation,
        option=VariationItem.OptionType.OPTION_1,
        description='Add a new funding schedule',
    )


@pytest.fixture
def stage_report(project, funding_schedule):
    return StageReport.objects.create(
        project=project,
        funding_schedule=funding_schedule,
        stage_type=StageReport.StageType.STAGE1,
        status=StageReport.Status.DRAFT,
    )


@pytest.fixture
def auth_client(council):
    client = Client()
    user = User.objects.create_user(username='test_user_16_17_20', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.OFFICER)
    client.force_login(user)
    return client, user


@pytest.fixture
def council_client(council):
    """Council-side user for submit actions."""
    client = Client()
    user = User.objects.create_user(username='council_user_16_17_20', password='pass')
    Profile.objects.create(user=user, council=council, officer_role=Profile.OfficerRole.COUNCIL_USER)
    client.force_login(user)
    return client, user


# ===========================================================================
# Issue #20 — StageReport lifecycle
# ===========================================================================

@pytest.mark.django_db
class TestStageReportSubmit:
    def test_submit_draft_report(self, council_client, stage_report):
        client, _ = council_client
        response = client.post(
            f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/'
        )
        assert response.status_code == 302
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.SUBMITTED

    def test_submit_non_draft_fails(self, auth_client, stage_report):
        client, _ = auth_client
        stage_report.status = StageReport.Status.SUBMITTED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.SUBMITTED  # unchanged

    def test_submit_requires_login(self, stage_report):
        response = Client().post(
            f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/'
        )
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
class TestStageReportEndorse:
    def test_endorse_submitted_report(self, auth_client, stage_report):
        client, user = auth_client
        stage_report.status = StageReport.Status.SUBMITTED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.ENDORSED
        assert stage_report.endorsed_by == user

    def test_endorse_draft_fails(self, auth_client, stage_report):
        client, _ = auth_client
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.DRAFT


@pytest.mark.django_db
class TestStageReportAssess:
    def test_assess_endorsed_report(self, auth_client, stage_report):
        client, user = auth_client
        stage_report.status = StageReport.Status.ENDORSED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/assess/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.ASSESSED
        assert stage_report.assessed_by == user

    def test_assess_submitted_fails(self, auth_client, stage_report):
        client, _ = auth_client
        stage_report.status = StageReport.Status.SUBMITTED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/assess/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.SUBMITTED


@pytest.mark.django_db
class TestStageReportApprove:
    def test_approve_assessed_report(self, auth_client, stage_report):
        client, user = auth_client
        stage_report.status = StageReport.Status.ASSESSED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/approve/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.APPROVED
        assert stage_report.approved_by == user

    def test_approve_endorsed_fails(self, auth_client, stage_report):
        client, _ = auth_client
        stage_report.status = StageReport.Status.ENDORSED
        stage_report.save()
        client.post(f'/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/approve/')
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.ENDORSED


# ===========================================================================
# Issue #16 — VariationItem CRUD + execute
# ===========================================================================

@pytest.mark.django_db
class TestVariationItemCreate:
    def test_create_get(self, auth_client, variation):
        client, _ = auth_client
        response = client.get(f'/variations/{variation.pk}/items/create/')
        assert response.status_code == 200

    def test_create_post_creates_item(self, auth_client, variation):
        client, _ = auth_client
        response = client.post(f'/variations/{variation.pk}/items/create/', {
            'option': 'OPTION_1',
            'description': 'Add new FS for project',
        }, follow=True)
        assert response.status_code == 200
        assert VariationItem.objects.filter(variation=variation, option='OPTION_1').exists()

    def test_create_requires_login(self, variation):
        response = Client().get(f'/variations/{variation.pk}/items/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestVariationItemEdit:
    def test_edit_get(self, auth_client, variation_item, variation):
        client, _ = auth_client
        response = client.get(f'/variations/{variation.pk}/items/{variation_item.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_item(self, auth_client, variation_item, variation):
        client, _ = auth_client
        client.post(f'/variations/{variation.pk}/items/{variation_item.pk}/edit/', {
            'option': 'OPTION_2',
            'description': 'Remove old FS',
        })
        variation_item.refresh_from_db()
        assert variation_item.option == 'OPTION_2'
        assert variation_item.description == 'Remove old FS'


@pytest.mark.django_db
class TestVariationItemDelete:
    def test_delete_get(self, auth_client, variation_item, variation):
        client, _ = auth_client
        response = client.get(f'/variations/{variation.pk}/items/{variation_item.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_item(self, auth_client, variation_item, variation):
        client, _ = auth_client
        item_id = variation_item.pk
        client.post(f'/variations/{variation.pk}/items/{item_id}/delete/')
        assert not VariationItem.objects.filter(pk=item_id).exists()


@pytest.mark.django_db
class TestVariationExecute:
    def test_execute_draft_variation(self, auth_client, variation):
        client, _ = auth_client
        client.post(f'/variations/{variation.pk}/execute/')
        variation.refresh_from_db()
        assert variation.status == Variation.Status.EXECUTED

    def test_execute_council_signed_variation(self, auth_client, variation):
        client, _ = auth_client
        variation.status = Variation.Status.COUNCIL_SIGNED
        variation.save()
        client.post(f'/variations/{variation.pk}/execute/')
        variation.refresh_from_db()
        assert variation.status == Variation.Status.EXECUTED

    def test_execute_already_executed_is_noop(self, auth_client, variation):
        client, _ = auth_client
        variation.status = Variation.Status.EXECUTED
        variation.save()
        client.post(f'/variations/{variation.pk}/execute/')
        variation.refresh_from_db()
        assert variation.status == Variation.Status.EXECUTED  # unchanged, error redirected

    def test_execute_requires_login(self, variation):
        response = Client().post(f'/variations/{variation.pk}/execute/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


# ===========================================================================
# Issue #17 — WorkFunding / Allocation CRUD
# ===========================================================================

@pytest.mark.django_db
class TestAllocationList:
    def test_list_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/allocations/')
        assert response.status_code == 200

    def test_list_requires_login(self):
        response = Client().get('/allocations/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_list_shows_allocation(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316333', amount=Decimal('100000'),
        )
        response = client.get('/allocations/')
        assert response.status_code == 200
        assert b'316333' in response.content


@pytest.mark.django_db
class TestAllocationCreate:
    def test_create_get(self, auth_client):
        client, _ = auth_client
        response = client.get('/allocations/create/')
        assert response.status_code == 200

    def test_create_post_project_allocation(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        response = client.post('/allocations/create/', {
            'funding_schedule': funding_schedule.pk,
            'project': project.pk,
            'cost_centre': '999001',
            'gl_code': 'GL001',
            'tax_code': 'GST',
            'amount': '200000.00',
        }, follow=True)
        assert response.status_code == 200
        assert WorkFunding.objects.filter(cost_centre='999001', project=project).exists()

    def test_create_requires_login(self):
        response = Client().get('/allocations/create/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestAllocationDetail:
    def test_detail_get(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        allocation = WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316001', amount=Decimal('50000'),
        )
        response = client.get(f'/allocations/{allocation.pk}/')
        assert response.status_code == 200
        assert b'316001' in response.content

    def test_detail_404_on_missing(self, auth_client):
        client, _ = auth_client
        response = client.get('/allocations/99999/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAllocationEdit:
    def test_edit_get(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        allocation = WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316001',
        )
        response = client.get(f'/allocations/{allocation.pk}/edit/')
        assert response.status_code == 200

    def test_edit_post_updates_allocation(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        allocation = WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316001',
        )
        client.post(f'/allocations/{allocation.pk}/edit/', {
            'funding_schedule': funding_schedule.pk,
            'project': project.pk,
            'cost_centre': '999999',
            'amount': '300000.00',
        })
        allocation.refresh_from_db()
        assert allocation.cost_centre == '999999'


@pytest.mark.django_db
class TestAllocationDelete:
    def test_delete_get(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        allocation = WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316001',
        )
        response = client.get(f'/allocations/{allocation.pk}/delete/')
        assert response.status_code == 200

    def test_delete_post_removes_allocation(self, auth_client, funding_schedule, project):
        client, _ = auth_client
        allocation = WorkFunding.objects.create(
            funding_schedule=funding_schedule, project=project,
            cost_centre='316001',
        )
        pk = allocation.pk
        client.post(f'/allocations/{pk}/delete/')
        assert not WorkFunding.objects.filter(pk=pk).exists()
