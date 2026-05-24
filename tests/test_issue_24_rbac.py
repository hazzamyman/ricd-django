"""
Tests for Issue #24: Role-based access control.

Covers:
- RoleRequiredMixin: 403 for wrong role, pass-through for correct role
- CouncilScopedMixin: council users see only their own council records
- CouncilSubmitMixin: only council roles can submit reports/claims
- FNCOnlyMixin: only FNC roles can approve/reject/execute
- Superuser bypass
- Unauthenticated redirect to login
"""
import pytest
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from apps.core.models import (
    Profile, Council, Program, Project, FundingAgreement, StageReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(role, council=None, username_suffix=""):
    client = Client()
    user = User.objects.create_user(
        username=f"user_{role}_{username_suffix}", password="pass"
    )
    Profile.objects.create(user=user, council=council, officer_role=role)
    client.force_login(user)
    return client, user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def council_a():
    return Council.objects.create(name="Council A", region="North")


@pytest.fixture
def council_b():
    return Council.objects.create(name="Council B", region="South")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Test Program", funding_source="Gov",
        budget=Decimal("5000000"), gl_code="GL001",
    )


@pytest.fixture
def agreement_a(council_a):
    return FundingAgreement.objects.create(council=council_a, status="DRAFT")


@pytest.fixture
def agreement_b(council_b):
    return FundingAgreement.objects.create(council=council_b, status="DRAFT")


@pytest.fixture
def project_a(council_a, program):
    return Project.objects.create(
        council=council_a, program=program,
        project_type=Project.Type.DWELLING,
        name="Project A", state=Project.State.PROSPECTIVE,
    )


# ---------------------------------------------------------------------------
# RoleRequiredMixin - basic gating
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRoleGating:
    """Write views return 403 for council and read-only roles."""

    def test_officer_can_access_create_view(self, council_a):
        client, _ = make_client("OFFICER", council_a, "o1")
        assert client.get("/councils/create/").status_code == 200

    def test_manager_can_access_create_view(self, council_a):
        client, _ = make_client("MANAGER", council_a, "m1")
        assert client.get("/councils/create/").status_code == 200

    def test_read_only_blocked_from_create_view(self, council_a):
        client, _ = make_client("READ_ONLY", council_a, "ro1")
        assert client.get("/councils/create/").status_code == 403

    def test_council_user_blocked_from_create_view(self, council_a):
        client, _ = make_client("COUNCIL_USER", council_a, "cu1")
        assert client.get("/councils/create/").status_code == 403

    def test_council_manager_blocked_from_create_view(self, council_a):
        client, _ = make_client("COUNCIL_MANAGER", council_a, "cm1")
        assert client.get("/councils/create/").status_code == 403

    def test_unauthenticated_redirects_to_login(self):
        response = Client().get("/councils/create/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_superuser_bypasses_role_check(self):
        client = Client()
        su = User.objects.create_superuser(username="su_rbac24", password="pass")
        client.force_login(su)
        assert client.get("/councils/create/").status_code == 200

    def test_user_without_profile_blocked(self):
        client = Client()
        user = User.objects.create_user(username="no_profile_24", password="pass")
        client.force_login(user)
        assert client.get("/councils/create/").status_code == 403


# ---------------------------------------------------------------------------
# Read views - all roles can access
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReadAccess:
    """All authenticated roles can read list/detail views."""

    def test_officer_can_list_councils(self, council_a):
        client, _ = make_client("OFFICER", council_a, "o2")
        assert client.get("/councils/").status_code == 200

    def test_read_only_can_list_councils(self, council_a):
        client, _ = make_client("READ_ONLY", council_a, "ro2")
        assert client.get("/councils/").status_code == 200

    def test_council_user_can_list_councils(self, council_a):
        client, _ = make_client("COUNCIL_USER", council_a, "cu2")
        assert client.get("/councils/").status_code == 200

    def test_council_manager_can_list_councils(self, council_a):
        client, _ = make_client("COUNCIL_MANAGER", council_a, "cm2")
        assert client.get("/councils/").status_code == 200


# ---------------------------------------------------------------------------
# CouncilScopedMixin - data isolation
# Uses FundingAgreementListView (/funding-agreements/) which has council_filter_field='council'
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCouncilScoping:
    """Council users see only records belonging to their own council."""

    def test_council_user_sees_own_agreements(self, agreement_a, agreement_b, council_a):
        client, _ = make_client("COUNCIL_USER", council_a, "cu3")
        response = client.get("/funding-agreements/")
        ids = [a.pk for a in response.context["object_list"]]
        assert agreement_a.pk in ids
        assert agreement_b.pk not in ids

    def test_council_manager_sees_own_agreements(self, agreement_a, agreement_b, council_b):
        client, _ = make_client("COUNCIL_MANAGER", council_b, "cm3")
        response = client.get("/funding-agreements/")
        ids = [a.pk for a in response.context["object_list"]]
        assert agreement_b.pk in ids
        assert agreement_a.pk not in ids

    def test_officer_sees_all_agreements(self, agreement_a, agreement_b, council_a):
        client, _ = make_client("OFFICER", council_a, "o3")
        response = client.get("/funding-agreements/")
        ids = [a.pk for a in response.context["object_list"]]
        assert agreement_a.pk in ids
        assert agreement_b.pk in ids

    def test_read_only_sees_all_agreements(self, agreement_a, agreement_b, council_a):
        client, _ = make_client("READ_ONLY", council_a, "ro3")
        response = client.get("/funding-agreements/")
        ids = [a.pk for a in response.context["object_list"]]
        assert agreement_a.pk in ids
        assert agreement_b.pk in ids

    def test_council_user_without_council_sees_nothing(self, agreement_a):
        client, _ = make_client("COUNCIL_USER", None, "cu4")
        response = client.get("/funding-agreements/")
        assert list(response.context["object_list"]) == []

    def test_council_user_cannot_access_other_council_agreement(self, agreement_b, council_a):
        """Council A user trying to access Council B's agreement gets 403 or 404."""
        client, _ = make_client("COUNCIL_USER", council_a, "cu5")
        response = client.get(f"/funding-agreements/{agreement_b.pk}/")
        assert response.status_code in (403, 404)

    def test_officer_can_access_any_agreement(self, agreement_b, council_a):
        client, _ = make_client("OFFICER", council_a, "o3b")
        response = client.get(f"/funding-agreements/{agreement_b.pk}/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# CouncilSubmitMixin - council-only submit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCouncilSubmitGating:
    """Submit views: council roles allowed, FNC and READ_ONLY get 403."""

    @pytest.fixture
    def stage_report(self, project_a):
        return StageReport.objects.create(
            project=project_a, stage_type="STAGE1",
            status=StageReport.Status.DRAFT,
        )

    def test_council_user_can_submit_report(self, stage_report, council_a):
        client, _ = make_client("COUNCIL_USER", council_a, "cu6")
        response = client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/"
        )
        assert response.status_code == 302
        stage_report.refresh_from_db()
        assert stage_report.status == StageReport.Status.SUBMITTED

    def test_officer_cannot_submit_report(self, stage_report, council_a):
        client, _ = make_client("OFFICER", council_a, "o4")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/"
        ).status_code == 403

    def test_read_only_cannot_submit_report(self, stage_report, council_a):
        client, _ = make_client("READ_ONLY", council_a, "ro4")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/submit/"
        ).status_code == 403


# ---------------------------------------------------------------------------
# FNCOnlyMixin - approve/endorse/execute
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFNCOnlyGating:
    """Approval/endorse/execute views: only OFFICER and MANAGER."""

    @pytest.fixture
    def stage_report(self, project_a):
        return StageReport.objects.create(
            project=project_a, stage_type="STAGE1",
            status=StageReport.Status.SUBMITTED,
        )

    def test_officer_can_endorse_report(self, stage_report, council_a):
        client, _ = make_client("OFFICER", council_a, "o5")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/"
        ).status_code == 302

    def test_manager_can_endorse_report(self, stage_report, council_a):
        client, _ = make_client("MANAGER", council_a, "m2")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/"
        ).status_code == 302

    def test_council_user_cannot_endorse_report(self, stage_report, council_a):
        client, _ = make_client("COUNCIL_USER", council_a, "cu7")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/"
        ).status_code == 403

    def test_read_only_cannot_endorse_report(self, stage_report, council_a):
        client, _ = make_client("READ_ONLY", council_a, "ro5")
        assert client.post(
            f"/projects/{stage_report.project_id}/stage-reports/{stage_report.pk}/endorse/"
        ).status_code == 403


# ---------------------------------------------------------------------------
# OfficerRole enum
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOfficerRoleEnum:

    def test_exactly_five_roles(self):
        values = {r.value for r in Profile.OfficerRole}
        assert values == {"OFFICER", "MANAGER", "COUNCIL_USER", "COUNCIL_MANAGER", "READ_ONLY"}

    def test_old_roles_removed(self):
        values = {r.value for r in Profile.OfficerRole}
        for removed in ["SENIOR_OFFICER", "PROGRAM_OFFICER", "PRINCIPAL_OFFICER", "DIRECTOR", "GM", "OTHER"]:
            assert removed not in values