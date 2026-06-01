"""
Regression tests: contingency funding must be hidden from council users.

Business rule (FNC): councils must never see that a contingency exists, nor any
total that silently includes it — otherwise they would budget against funds FNC
holds back and releases only if needed. Contingency is FNC-team-only.
"""
import pytest
from decimal import Decimal

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

from apps.core.models import Profile, Council, Program, Project
from fixtures import make_bfa


FUNDING = Decimal("1000000")
CONTINGENCY = Decimal("100000")


def _client(role, council=None):
    user = User.objects.create_user(username=f"u_{role}_{council and council.pk}", password="x")
    Profile.objects.create(user=user, council=council, officer_role=role)
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def council():
    return Council.objects.create(name="Council A", region="North")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Prog", funding_source="Gov", budget=Decimal("5000000"), gl_code="GL1",
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        council=council, program=program, project_type=Project.Type.DWELLING,
        name="Proj A", state=Project.State.PROSPECTIVE,
    )


@pytest.fixture
def bfa(project):
    return make_bfa(project, FUNDING, contingency_amount=CONTINGENCY, status="APPROVED")


@pytest.mark.django_db
def test_bfa_detail_shows_contingency_to_fnc(bfa, project, council):
    """FNC staff see the full BFA detail including the contingency hold-back."""
    url = reverse("ui:bfa_detail", args=[bfa.pk])

    fnc = _client("OFFICER")
    fnc_html = fnc.get(url).content.decode()

    assert "Contingency" in fnc_html


@pytest.mark.django_db
def test_bfa_detail_blocked_for_council(bfa, project, council):
    """Councils must never reach a BFA detail page at all — it exposes the
    contingency, delegate level, and cost-centre internals. They learn only
    *whether* funding was approved via their own project pages."""
    url = reverse("ui:bfa_detail", args=[bfa.pk])

    council_user = _client("COUNCIL_USER", council=council)
    resp = council_user.get(url)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_project_detail_hides_contingency_from_council(bfa, project, council):
    url = reverse("ui:project_detail", args=[project.pk])

    fnc = _client("OFFICER")
    council_user = _client("COUNCIL_USER", council=council)

    fnc_html = fnc.get(url).content.decode()
    council_html = council_user.get(url).content.decode()

    assert "Contingency" in fnc_html
    assert "Contingency" not in council_html


@pytest.mark.django_db
def test_council_detail_excludes_contingency_from_totals(bfa, project, council):
    """The council's own dashboard must show funding only — never a grand total
    that bundles in the hidden contingency."""
    url = reverse("ui:council_detail", args=[council.pk])

    council_user = _client("COUNCIL_USER", council=council)
    html = council_user.get(url).content.decode()

    assert "contingency" not in html.lower()


@pytest.mark.django_db
def test_bfa_global_list_blocked_for_council(bfa, project, council):
    """The all-BFA list is FNC/internal only — councils get 403, not a leak."""
    url = reverse("ui:bfa_global_list")

    council_user = _client("COUNCIL_USER", council=council)
    assert council_user.get(url).status_code == 403


@pytest.mark.django_db
def test_bfa_views_allowed_for_internal_readonly(bfa, project, council):
    """Internal read-only audit/finance/exec staff still see BFAs in full —
    only council roles are excluded."""
    detail_url = reverse("ui:bfa_detail", args=[bfa.pk])
    list_url = reverse("ui:bfa_global_list")

    audit = _client("READ_ONLY")
    assert audit.get(list_url).status_code == 200

    detail_html = audit.get(detail_url)
    assert detail_html.status_code == 200
    assert "Contingency" in detail_html.content.decode()
