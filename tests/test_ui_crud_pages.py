"""
CRUD Page Tests — tests all CRUD endpoints for core entities.
Each test knows the exact URL, POST data, and expected response code.
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='crud_superuser',
        email='crud@test.com',
        password='testpass123',
    )


@pytest.fixture
def auth_client(client, superuser):
    client.force_login(superuser)
    return client


# ---------------------------------------------------------------------------
# Council CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCouncilCRUD:

    def test_council_list_get(self, auth_client):
        response = auth_client.get('/councils/')
        assert response.status_code == 200, f"GET /ui/councils/ returned {response.status_code}"

    def test_council_create_get(self, auth_client):
        response = auth_client.get('/councils/create/')
        assert response.status_code == 200, f"GET /ui/councils/create/ returned {response.status_code}"

    def test_council_create_post_creates_object(self, auth_client):
        from apps.core.models import Council
        before = Council.objects.count()
        response = auth_client.post('/councils/create/', {
            'name': 'New Test Council',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/councils/create/ returned {response.status_code}"
        assert Council.objects.count() == before + 1

    def test_council_detail_get(self, auth_client, council):
        response = auth_client.get(f'/councils/{council.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/councils/{council.pk}/ returned {response.status_code}"

    def test_council_edit_get(self, auth_client, council):
        response = auth_client.get(f'/councils/{council.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/councils/{council.pk}/edit/ returned {response.status_code}"

    def test_council_edit_post_updates_object(self, auth_client, council):
        response = auth_client.post(f'/councils/{council.pk}/edit/', {
            'name': 'Updated Council Name',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/councils/{council.pk}/edit/ returned {response.status_code}"
        council.refresh_from_db()
        assert council.name == 'Updated Council Name'

    def test_council_delete_get(self, auth_client, council):
        response = auth_client.get(f'/councils/{council.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/councils/{council.pk}/delete/ returned {response.status_code}"

    def test_council_delete_post_removes_object(self, auth_client, council):
        from apps.core.models import Council
        pk = council.pk
        response = auth_client.post(f'/councils/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/councils/{pk}/delete/ returned {response.status_code}"
        assert not Council.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# Program CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProgramCRUD:

    def test_program_list_get(self, auth_client):
        response = auth_client.get('/programs/')
        assert response.status_code == 200, f"GET /ui/programs/ returned {response.status_code}"

    def test_program_create_get(self, auth_client):
        response = auth_client.get('/programs/create/')
        assert response.status_code == 200, f"GET /ui/programs/create/ returned {response.status_code}"

    def test_program_create_post_creates_object(self, auth_client):
        from apps.core.models import Program
        before = Program.objects.count()
        response = auth_client.post('/programs/create/', {
            'name': 'Test Program',
            'budget': '0',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/programs/create/ returned {response.status_code}"
        assert Program.objects.count() == before + 1

    def test_program_detail_get(self, auth_client, program):
        response = auth_client.get(f'/programs/{program.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/programs/{program.pk}/ returned {response.status_code}"

    def test_program_edit_get(self, auth_client, program):
        response = auth_client.get(f'/programs/{program.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/programs/{program.pk}/edit/ returned {response.status_code}"

    def test_program_edit_post_updates_object(self, auth_client, program):
        response = auth_client.post(f'/programs/{program.pk}/edit/', {
            'name': 'Updated Program',
            'budget': '0',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/programs/{program.pk}/edit/ returned {response.status_code}"
        program.refresh_from_db()
        assert program.name == 'Updated Program'

    def test_program_delete_get(self, auth_client, program):
        response = auth_client.get(f'/programs/{program.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/programs/{program.pk}/delete/ returned {response.status_code}"

    def test_program_delete_post_removes_object(self, auth_client, program):
        from apps.core.models import Program
        pk = program.pk
        response = auth_client.post(f'/programs/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/programs/{pk}/delete/ returned {response.status_code}"
        assert not Program.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectCRUD:

    def test_project_list_get(self, auth_client):
        response = auth_client.get('/projects/')
        assert response.status_code == 200, f"GET /ui/projects/ returned {response.status_code}"

    def test_project_create_get(self, auth_client):
        response = auth_client.get('/projects/create/')
        assert response.status_code == 200, f"GET /ui/projects/create/ returned {response.status_code}"

    def test_project_create_post_creates_object(self, auth_client, council, program):
        from apps.core.models import Project
        before = Project.objects.count()
        response = auth_client.post('/projects/create/', {
            'name': 'New Project',
            'council': council.pk,
            'program': program.pk,
            'project_type': 'DWELLING',
            'state': 'PROG',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/create/ returned {response.status_code}"
        assert Project.objects.count() == before + 1

    def test_project_detail_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/ returned {response.status_code}"

    def test_project_edit_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/edit/ returned {response.status_code}"

    def test_project_edit_post_updates_object(self, auth_client, project, council, program):
        response = auth_client.post(f'/projects/{project.pk}/edit/', {
            'name': 'Updated Project',
            'council': council.pk,
            'program': program.pk,
            'project_type': 'DWELLING',
            'state': 'PROG',
            'financial_year': '2025-2026',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{project.pk}/edit/ returned {response.status_code}"
        project.refresh_from_db()
        assert project.name == 'Updated Project'

    def test_project_delete_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/delete/ returned {response.status_code}"

    def test_project_delete_post_removes_object(self, auth_client, project):
        from apps.core.models import Project
        pk = project.pk
        response = auth_client.post(f'/projects/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{pk}/delete/ returned {response.status_code}"
        assert not Project.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# WorkType CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkTypeCRUD:

    def test_work_type_list_get(self, auth_client):
        response = auth_client.get('/work-types/')
        assert response.status_code == 200, f"GET /ui/work-types/ returned {response.status_code}"

    def test_work_type_create_get(self, auth_client):
        response = auth_client.get('/work-types/create/')
        assert response.status_code == 200, f"GET /ui/work-types/create/ returned {response.status_code}"

    def test_work_type_create_post_creates_object(self, auth_client):
        from apps.core.models import WorkType
        before = WorkType.objects.count()
        response = auth_client.post('/work-types/create/', {
            'name': 'New Work Type',
            'category': 'RESIDENTIAL',
            'default_bedrooms': '0',
            'min_bedrooms': '0',
            'max_bedrooms': '0',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/work-types/create/ returned {response.status_code}"
        assert WorkType.objects.count() == before + 1

    def test_work_type_detail_get(self, auth_client, work_type):
        response = auth_client.get(f'/work-types/{work_type.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/work-types/{work_type.pk}/ returned {response.status_code}"

    def test_work_type_edit_get(self, auth_client, work_type):
        response = auth_client.get(f'/work-types/{work_type.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/work-types/{work_type.pk}/edit/ returned {response.status_code}"

    def test_work_type_edit_post_updates_object(self, auth_client, work_type):
        response = auth_client.post(f'/work-types/{work_type.pk}/edit/', {
            'name': 'Updated Work Type',
            'category': 'EXTENSION',
            'default_bedrooms': '0',
            'min_bedrooms': '0',
            'max_bedrooms': '0',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/work-types/{work_type.pk}/edit/ returned {response.status_code}"
        work_type.refresh_from_db()
        assert work_type.name == 'Updated Work Type'

    def test_work_type_delete_get(self, auth_client, work_type):
        response = auth_client.get(f'/work-types/{work_type.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/work-types/{work_type.pk}/delete/ returned {response.status_code}"

    def test_work_type_delete_post_removes_object(self, auth_client, work_type):
        from apps.core.models import WorkType
        pk = work_type.pk
        response = auth_client.post(f'/work-types/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/work-types/{pk}/delete/ returned {response.status_code}"
        assert not WorkType.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# FundingSchedule CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingScheduleCRUD:

    def test_funding_schedule_list_get(self, auth_client):
        response = auth_client.get('/funding-schedules/')
        assert response.status_code == 200, \
            f"GET /ui/funding-schedules/ returned {response.status_code}"

    def test_funding_schedule_create_get(self, auth_client):
        response = auth_client.get('/funding-schedules/create/')
        assert response.status_code == 200, \
            f"GET /ui/funding-schedules/create/ returned {response.status_code}"
        # Regression: crud/form.html must render the form's fields, not just the
        # Save/Cancel buttons. Views that don't set `advanced_fields` previously
        # rendered an empty form because `{% if x not in undefined %}` is False.
        body = response.content.decode()
        assert 'name="schedule_number"' in body
        assert 'name="status"' in body

    def test_funding_schedule_create_post_creates_object(self, auth_client, project):
        from apps.core.models import FundingSchedule
        from tests.fixtures import make_bfa
        make_bfa(project, '500000', status='APPROVED')
        before = FundingSchedule.objects.count()
        response = auth_client.post('/funding-schedules/create/', {
            'projects': [project.pk],  # multi-select (multi-project per FS)
            'schedule_number': 1,
            'status': 'DRAFT',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/funding-schedules/create/ returned {response.status_code}"
        assert FundingSchedule.objects.count() == before + 1

    def test_funding_schedule_detail_get(self, auth_client, funding_schedule):
        response = auth_client.get(f'/funding-schedules/{funding_schedule.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/funding-schedules/{funding_schedule.pk}/ returned {response.status_code}"

    def test_funding_schedule_edit_get(self, auth_client, funding_schedule):
        response = auth_client.get(f'/funding-schedules/{funding_schedule.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/funding-schedules/{funding_schedule.pk}/edit/ returned {response.status_code}"
        # Regression guard: the edit form must show its editable fields, not an
        # empty shell with only Save/Cancel.
        body = response.content.decode()
        assert 'name="schedule_number"' in body
        assert 'name="status"' in body

    def test_funding_schedule_edit_post_updates_object(self, auth_client, funding_schedule, project):
        response = auth_client.post(f'/funding-schedules/{funding_schedule.pk}/edit/', {
            'projects': [project.pk],  # multi-select
            'schedule_number': 2,
            'status': 'DRAFT',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/funding-schedules/{funding_schedule.pk}/edit/ returned {response.status_code}"
        funding_schedule.refresh_from_db()
        assert funding_schedule.schedule_number == 2

    def test_funding_schedule_delete_get(self, auth_client, funding_schedule):
        response = auth_client.get(f'/funding-schedules/{funding_schedule.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/funding-schedules/{funding_schedule.pk}/delete/ returned {response.status_code}"

    def test_funding_schedule_delete_post_removes_object(self, auth_client, funding_schedule):
        from apps.core.models import FundingSchedule
        pk = funding_schedule.pk
        response = auth_client.post(f'/funding-schedules/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/funding-schedules/{pk}/delete/ returned {response.status_code}"
        assert not FundingSchedule.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# Variation CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVariationCRUD:

    def test_variation_list_get(self, auth_client):
        response = auth_client.get('/variations/')
        assert response.status_code == 200, f"GET /ui/variations/ returned {response.status_code}"

    def test_variation_create_get(self, auth_client):
        response = auth_client.get('/variations/create/')
        assert response.status_code == 200, \
            f"GET /ui/variations/create/ returned {response.status_code}"

    def test_variation_create_post_creates_object(self, auth_client):
        from apps.core.models import Variation
        before = Variation.objects.count()
        response = auth_client.post('/variations/create/', {
            'description': 'Test variation description',
            'status': 'DRAFT',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/variations/create/ returned {response.status_code}"
        assert Variation.objects.count() == before + 1

    def test_variation_detail_get(self, auth_client, variation):
        response = auth_client.get(f'/variations/{variation.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/variations/{variation.pk}/ returned {response.status_code}"

    def test_variation_edit_get(self, auth_client, variation):
        response = auth_client.get(f'/variations/{variation.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/variations/{variation.pk}/edit/ returned {response.status_code}"

    def test_variation_edit_post_updates_object(self, auth_client, variation):
        response = auth_client.post(f'/variations/{variation.pk}/edit/', {
            'description': 'Updated description',
            'status': 'DRAFT',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/variations/{variation.pk}/edit/ returned {response.status_code}"
        variation.refresh_from_db()
        assert variation.description == 'Updated description'

    def test_variation_delete_get(self, auth_client, variation):
        response = auth_client.get(f'/variations/{variation.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/variations/{variation.pk}/delete/ returned {response.status_code}"

    def test_variation_delete_post_removes_object(self, auth_client, variation):
        from apps.core.models import Variation
        pk = variation.pk
        response = auth_client.post(f'/variations/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/variations/{pk}/delete/ returned {response.status_code}"
        assert not Variation.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# Payment CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentCRUD:

    def test_payment_list_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/payments/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/payments/ returned {response.status_code}"

    def test_payment_create_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/payments/create/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/payments/create/ returned {response.status_code}"

    def test_payment_create_post_creates_object(self, auth_client, project, funding_schedule):
        from apps.core.models import Payment
        before = Payment.objects.count()
        response = auth_client.post(f'/projects/{project.pk}/payments/create/', {
            'project': project.pk,
            'funding_schedule': funding_schedule.pk,
            'payment_type': 'FIRST',
            'calculation_type': 'PERCENTAGE',
            'payment_split': '30/60/10',
            'status': 'PENDING',
        })
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{project.pk}/payments/create/ returned {response.status_code}"
        assert Payment.objects.count() == before + 1

    def test_payment_detail_get(self, auth_client, project, payment):
        response = auth_client.get(f'/projects/{project.pk}/payments/{payment.pk}/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/payments/{payment.pk}/ returned {response.status_code}"

    def test_payment_edit_get(self, auth_client, project, payment):
        response = auth_client.get(f'/projects/{project.pk}/payments/{payment.pk}/edit/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/payments/{payment.pk}/edit/ returned {response.status_code}"

    def test_payment_edit_post_updates_object(self, auth_client, project, payment, funding_schedule):
        response = auth_client.post(
            f'/projects/{project.pk}/payments/{payment.pk}/edit/', {
                'project': project.pk,
                'funding_schedule': funding_schedule.pk,
                'payment_type': 'SECOND',
                'calculation_type': 'PERCENTAGE',
                'payment_split': '30/60/10',
                'status': 'PENDING',
            }
        )
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{project.pk}/payments/{payment.pk}/edit/ returned {response.status_code}"
        payment.refresh_from_db()
        assert payment.payment_type == 'SECOND'

    def test_payment_delete_get(self, auth_client, project, payment):
        response = auth_client.get(f'/projects/{project.pk}/payments/{payment.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/payments/{payment.pk}/delete/ returned {response.status_code}"

    def test_payment_delete_post_removes_object(self, auth_client, project, payment):
        from apps.core.models import Payment
        pk = payment.pk
        response = auth_client.post(f'/projects/{project.pk}/payments/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{project.pk}/payments/{pk}/delete/ returned {response.status_code}"
        assert not Payment.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# StageReport CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStageReportCRUD:

    def test_stage_report_list_get(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/stage-reports/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/stage-reports/ returned {response.status_code}"

    def test_stage_report_create_get_redirects_to_legacy_open(self, auth_client, project):
        """The legacy create URL now redirects (via the legacy-project helper)."""
        response = auth_client.get(f'/projects/{project.pk}/stage-reports/create/')
        assert response.status_code == 302

    def test_stage_report_open_via_fs_creates_when_template_assigned(self, auth_client, project):
        """The new FS-based open flow creates a StageReport when the FS has a template."""
        from apps.core.models import (
            BriefFinancialApproval, FundingSchedule, StageItemGroup, StageReport
        )
        from tests.fixtures import make_bfa
        make_bfa(project, '100000', status='APPROVED')
        fs = FundingSchedule.objects.create(project=project, schedule_number=1)
        project.funding_schedule = fs
        project.save()

        grp = StageItemGroup.objects.create(stage_type='STAGE1', name='Test Group')
        fs.stage1_item_group = grp
        fs.save()

        before = StageReport.objects.count()
        response = auth_client.get(f'/funding-schedules/{fs.pk}/stage-reports/STAGE1/open/')
        assert response.status_code == 302
        assert StageReport.objects.count() == before + 1

    def test_stage_report_detail_redirects_to_grid(self, auth_client, project):
        from apps.core.models import StageReport
        sr = StageReport.objects.create(project=project, stage_type='STAGE1')
        response = auth_client.get(f'/projects/{project.pk}/stage-reports/{sr.pk}/')
        assert response.status_code == 302
        assert f'/stage-reports/{sr.pk}/' in response['Location']

    def test_stage_report_edit_redirects_to_grid(self, auth_client, project):
        from apps.core.models import StageReport
        sr = StageReport.objects.create(project=project, stage_type='STAGE1')
        response = auth_client.get(f'/projects/{project.pk}/stage-reports/{sr.pk}/edit/')
        assert response.status_code == 302
        assert f'/stage-reports/{sr.pk}/' in response['Location']

    def test_stage_report_delete_get(self, auth_client, project):
        from apps.core.models import StageReport
        sr = StageReport.objects.create(project=project, stage_type='STAGE1')
        response = auth_client.get(f'/projects/{project.pk}/stage-reports/{sr.pk}/delete/')
        assert response.status_code == 200, \
            f"GET /ui/projects/{project.pk}/stage-reports/{sr.pk}/delete/ returned {response.status_code}"

    def test_stage_report_delete_post_removes_object(self, auth_client, project):
        from apps.core.models import StageReport
        sr = StageReport.objects.create(project=project, stage_type='STAGE1')
        pk = sr.pk
        response = auth_client.post(f'/projects/{project.pk}/stage-reports/{pk}/delete/')
        assert response.status_code in (200, 302), \
            f"POST /ui/projects/{project.pk}/stage-reports/{pk}/delete/ returned {response.status_code}"
        assert not StageReport.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# QuarterlyReport CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestQuarterlyReportCRUD:
    """
    QuarterlyReport is now per-council (not per-project).
    The old project-nested URLs are kept as redirect-only stubs for backward compat.
    """

    def test_old_project_nested_list_redirects(self, auth_client, project):
        response = auth_client.get(f'/projects/{project.pk}/quarterly-reports/')
        assert response.status_code == 302

    def test_new_global_list_returns_200(self, auth_client):
        response = auth_client.get('/quarterly-reports/')
        assert response.status_code == 200

    def test_open_for_council_creates_report_and_redirects(self, auth_client, project):
        from apps.core.models import QuarterlyReport
        before = QuarterlyReport.objects.count()
        response = auth_client.get(f'/quarterly-reports/council/{project.council.pk}/open/')
        assert response.status_code == 302
        assert QuarterlyReport.objects.count() == before + 1

    def test_detail_get_returns_200(self, auth_client, project):
        from apps.core.models import QuarterlyReport
        qr = QuarterlyReport.objects.create(council=project.council, year=2025, quarter=2)
        response = auth_client.get(f'/quarterly-reports/{qr.pk}/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Unauthenticated redirect checks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUnauthenticatedRedirects:

    def test_council_list_redirects_unauthenticated(self, client):
        response = client.get('/councils/')
        assert response.status_code == 302, \
            f"Unauthenticated GET /ui/councils/ should redirect, got {response.status_code}"

    def test_program_list_redirects_unauthenticated(self, client):
        response = client.get('/programs/')
        assert response.status_code == 302

    def test_project_list_redirects_unauthenticated(self, client):
        response = client.get('/projects/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Addresses & Works combined page: inline edit/delete + ?next= redirects
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAddressesWorksActions:

    def test_combined_page_exposes_work_and_address_actions(
        self, auth_client, work, address, project
    ):
        """Both tables must offer Edit + Delete inline so the user doesn't have
        to dig into sub-pages — and works must be editable here, not just addresses."""
        resp = auth_client.get(f'/projects/{project.pk}/addresses-works/')
        assert resp.status_code == 200
        body = resp.content.decode()
        assert f'/projects/{project.pk}/works/{work.pk}/edit/' in body
        assert f'/projects/{project.pk}/works/{work.pk}/delete/' in body
        assert f'/projects/{project.pk}/addresses/{address.pk}/edit/' in body
        assert f'/projects/{project.pk}/addresses/{address.pk}/delete/' in body

    def test_work_delete_honors_next(self, auth_client, work, project):
        from apps.core.models import Work
        nxt = f'/projects/{project.pk}/addresses-works/'
        resp = auth_client.post(
            f'/projects/{project.pk}/works/{work.pk}/delete/?next={nxt}'
        )
        assert resp.status_code == 302
        assert resp.url == nxt
        assert not Work.objects.filter(pk=work.pk).exists()

    def test_address_edit_cancel_link_honors_next(self, auth_client, address, project):
        """The edit form's Cancel must return to wherever the user came from
        (the combined page), not the bare address list dead-end."""
        nxt = f'/projects/{project.pk}/addresses-works/'
        resp = auth_client.get(
            f'/projects/{project.pk}/addresses/{address.pk}/edit/?next={nxt}'
        )
        assert resp.status_code == 200
        assert f'href="{nxt}"' in resp.content.decode()
