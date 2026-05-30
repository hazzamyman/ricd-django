"""
Comprehensive DRF API tests for issue #32.

Covers:
  - Authentication / RBAC enforcement
  - CRUD access per role (FNC Manager, Council User, Read-Only)
  - State-transition actions (approve/execute/complete/release/submit/close/etc.)
  - Business-rule validation via API (cap enforcement, BFA pre-condition)
  - Council scoping (council-side roles only see own data)
"""
import json
import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth.models import User
from django.test import Client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_client(username, role, council=None):
    from apps.core.models import Profile
    u = User.objects.create_user(username=username, password='pass')
    Profile.objects.create(user=u, officer_role=role, council=council)
    c = Client()
    c.force_login(u)
    return c, u


def _api(client, method, path, data=None):
    kwargs = {'HTTP_ACCEPT': 'application/json', 'content_type': 'application/json'}
    if data is not None:
        kwargs['data'] = json.dumps(data)
    return getattr(client, method)(path, **kwargs)


def _make_council(name='Test Council A'):
    from apps.core.models import Council
    return Council.objects.create(name=name, region='R', state_electorate='SE', federal_electorate='FE')


def _make_program():
    from apps.core.models import Program
    return Program.objects.create(
        name='Test Program', funding_source='STATE',
        budget=Decimal('5000000'), gl_code='GL001',
    )


def _make_project(council, program, name='Proj A'):
    from apps.core.models import Project
    return Project.objects.create(
        name=name, council=council, program=program,
        state='PROSPECTIVE', financial_year='2025-2026',
    )


def _make_bfa(project, status='PENDING'):
    from apps.core.models import BriefFinancialApproval
    from tests.fixtures import make_bfa
    return make_bfa(
        project, Decimal('500000'),
        delegate_level=BriefFinancialApproval.DelegateLevel.MANAGER,
        status=status,
    )


def _make_payment_rule():
    from apps.core.models import PaymentRule
    return PaymentRule.objects.create(
        name='Standard Rule', rule_type='STANDARD',
        config_json={}, version=1,
    )


def _make_funding_agreement(council):
    from apps.core.models import FundingAgreement
    return FundingAgreement.objects.create(
        council=council,
        name='FA Test',
        status=FundingAgreement.Status.DRAFT,
    )


def _make_funding_schedule(project, bfa_approved=True):
    from apps.core.models import FundingSchedule
    if bfa_approved:
        _make_bfa(project, status='APPROVED')
    pr = _make_payment_rule()
    fa = _make_funding_agreement(project.council)
    return FundingSchedule.objects.create(
        project=project,
        funding_agreement=fa,
        payment_rule=pr,
        schedule_number=1,
        status=FundingSchedule.Status.DRAFT,
        amount=Decimal('400000'),
        contingency=Decimal('40000'),
        payment_split=FundingSchedule.PaymentSplit.STANDARD,
    )


def _make_funding_notice(project, capped_amount=Decimal('100000')):
    from apps.core.models import FundingNotice
    return FundingNotice.objects.create(
        project=project,
        capped_amount=capped_amount,
        status=FundingNotice.Status.OPEN,
        issued_date=date.today(),
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthentication:

    def test_anonymous_get_is_rejected(self):
        resp = Client().get('/api/v1/payment-rules/', HTTP_ACCEPT='application/json')
        assert resp.status_code in (401, 403)

    def test_user_without_profile_is_rejected(self):
        u = User.objects.create_user(username='noprofile', password='x')
        c = Client()
        c.force_login(u)
        resp = _api(c, 'get', '/api/v1/payment-rules/')
        assert resp.status_code in (401, 403)

    def test_superuser_bypasses_role_check(self):
        u = User.objects.create_superuser(username='admin2', password='x')
        c = Client()
        c.force_login(u)
        resp = _api(c, 'get', '/api/v1/payment-rules/')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# RBAC: read-only vs write access
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRBAC:

    def test_manager_can_list_and_create_funding_agreement(self):
        council = _make_council()
        client, _ = _user_client('mgr1', 'MANAGER')
        resp = _api(client, 'get', '/api/v1/funding-agreements/')
        assert resp.status_code == 200
        resp = _api(client, 'post', '/api/v1/funding-agreements/', {
            'council': council.pk, 'name': 'New FA', 'status': 'DRAFT',
        })
        assert resp.status_code == 201

    def test_council_user_can_read_but_not_write(self):
        council = _make_council()
        client, _ = _user_client('cu1', 'COUNCIL_USER', council=council)
        resp = _api(client, 'get', '/api/v1/funding-agreements/')
        assert resp.status_code == 200
        resp = _api(client, 'post', '/api/v1/funding-agreements/', {
            'council': council.pk, 'name': 'FA', 'status': 'DRAFT',
        })
        assert resp.status_code == 403

    def test_read_only_role_cannot_write(self):
        council = _make_council()
        client, _ = _user_client('ro1', 'READ_ONLY')
        resp = _api(client, 'post', '/api/v1/funding-agreements/', {
            'council': council.pk, 'name': 'FA', 'status': 'DRAFT',
        })
        assert resp.status_code == 403

    def test_audit_logs_blocked_for_council_user(self):
        council = _make_council()
        client, _ = _user_client('cu2', 'COUNCIL_USER', council=council)
        resp = _api(client, 'get', '/api/v1/audit-logs/')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Council scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCouncilScoping:

    def test_council_user_only_sees_own_council_data(self):
        council_a = _make_council('Council A')
        council_b = _make_council('Council B')
        prog = _make_program()
        proj_a = _make_project(council_a, prog, 'Proj A')
        proj_b = _make_project(council_b, prog, 'Proj B')
        _make_funding_notice(proj_a)
        _make_funding_notice(proj_b)

        client_a, _ = _user_client('cu_a', 'COUNCIL_USER', council=council_a)
        resp = _api(client_a, 'get', '/api/v1/funding-notices/')
        assert resp.status_code == 200
        data = resp.json()
        pks = [item['project'] for item in data['results']]
        assert proj_a.pk in pks
        assert proj_b.pk not in pks

    def test_fnc_officer_sees_all_councils(self):
        council_a = _make_council('Council C')
        council_b = _make_council('Council D')
        prog = _make_program()
        proj_a = _make_project(council_a, prog, 'ProjC')
        proj_b = _make_project(council_b, prog, 'ProjD')
        _make_funding_notice(proj_a)
        _make_funding_notice(proj_b)

        client, _ = _user_client('officer1', 'MANAGER')
        resp = _api(client, 'get', '/api/v1/funding-notices/')
        assert resp.status_code == 200
        data = resp.json()
        pks = [item['project'] for item in data['results']]
        assert proj_a.pk in pks
        assert proj_b.pk in pks


# ---------------------------------------------------------------------------
# PaymentRule (read-only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentRuleAPI:

    def test_list_payment_rules(self):
        _make_payment_rule()
        client, _ = _user_client('mgr_pr', 'MANAGER')
        resp = _api(client, 'get', '/api/v1/payment-rules/')
        assert resp.status_code == 200
        assert resp.json()['count'] >= 1

    def test_cannot_create_payment_rule_via_api(self):
        client, _ = _user_client('mgr_pr2', 'MANAGER')
        resp = _api(client, 'post', '/api/v1/payment-rules/', {
            'name': 'New Rule', 'rule_type': 'STANDARD', 'config_json': {}, 'version': 1,
        })
        assert resp.status_code == 405  # ReadOnlyModelViewSet


# ---------------------------------------------------------------------------
# FundingAgreement state transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingAgreementActions:

    def test_activate_draft_agreement(self):
        council = _make_council()
        fa = _make_funding_agreement(council)
        client, _ = _user_client('mgr_fa', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-agreements/{fa.pk}/activate/')
        assert resp.status_code == 200
        fa.refresh_from_db()
        assert fa.status == 'ACTIVE'

    def test_cease_active_agreement(self):
        council = _make_council()
        fa = _make_funding_agreement(council)
        fa.status = 'ACTIVE'
        fa.save()
        client, _ = _user_client('mgr_fa2', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-agreements/{fa.pk}/cease/')
        assert resp.status_code == 200
        fa.refresh_from_db()
        assert fa.status == 'CEASED'

    def test_council_user_cannot_activate(self):
        council = _make_council()
        fa = _make_funding_agreement(council)
        client, _ = _user_client('cu_fa', 'COUNCIL_USER', council=council)
        resp = _api(client, 'post', f'/api/v1/funding-agreements/{fa.pk}/activate/')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# BriefFinancialApproval state transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBFAActions:

    def test_approve_bfa(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        bfa = _make_bfa(proj)
        client, user = _user_client('mgr_bfa', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/brief-financial-approvals/{bfa.pk}/approve/')
        assert resp.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == 'APPROVED'
        assert bfa.approved_by == user

    def test_reject_bfa(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        bfa = _make_bfa(proj)
        client, _ = _user_client('mgr_bfa2', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/brief-financial-approvals/{bfa.pk}/reject/')
        assert resp.status_code == 200
        bfa.refresh_from_db()
        assert bfa.status == 'REJECTED'


# ---------------------------------------------------------------------------
# FundingSchedule — creation requires approved BFA, state transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingScheduleAPI:

    def test_create_funding_schedule_requires_approved_bfa(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        _make_bfa(proj, status='PENDING')  # not approved
        pr = _make_payment_rule()
        fa = _make_funding_agreement(council)
        client, _ = _user_client('mgr_fs', 'MANAGER')
        resp = _api(client, 'post', '/api/v1/funding-schedules/', {
            'project': proj.pk, 'funding_agreement': fa.pk, 'payment_rule': pr.pk,
            'schedule_number': 1, 'amount': '400000', 'contingency': '40000',
            'payment_split': '30/60/10',
        })
        assert resp.status_code == 400

    def test_create_funding_schedule_with_approved_bfa(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        _make_bfa(proj, status='APPROVED')
        pr = _make_payment_rule()
        fa = _make_funding_agreement(council)
        client, _ = _user_client('mgr_fs2', 'MANAGER')
        resp = _api(client, 'post', '/api/v1/funding-schedules/', {
            'project': proj.pk, 'funding_agreement': fa.pk, 'payment_rule': pr.pk,
            'schedule_number': 2, 'amount': '400000', 'contingency': '40000',
            'payment_split': '30/60/10',
        })
        assert resp.status_code == 201

    def test_approve_draft_schedule(self):
        from apps.core.models import FundingSchedule
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fs = _make_funding_schedule(proj)
        client, _ = _user_client('mgr_fs3', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-schedules/{fs.pk}/approve/')
        assert resp.status_code == 200
        fs.refresh_from_db()
        assert fs.status == FundingSchedule.Status.READY_FOR_EXECUTION.value

    def test_execute_ready_schedule(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fs = _make_funding_schedule(proj)
        fs.status = 'READY'
        fs.save()
        client, _ = _user_client('mgr_fs4', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-schedules/{fs.pk}/execute/')
        assert resp.status_code == 200
        fs.refresh_from_db()
        assert fs.status == 'EXECUTED'

    def test_approve_requires_draft_status(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fs = _make_funding_schedule(proj)
        fs.status = 'ACTIVE'
        fs.save()
        client, _ = _user_client('mgr_fs5', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-schedules/{fs.pk}/approve/')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Approval state transitions (generic)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApprovalActions:

    def _make_approval(self, entity_type='payment', entity_id=1):
        from apps.core.models import Approval
        return Approval.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            approval_type=Approval.ApprovalType.FINANCIAL,
            required_role='MANAGER',
            status=Approval.Status.PENDING,
        )

    def test_approve_pending_approval(self):
        appr = self._make_approval()
        client, user = _user_client('mgr_ap', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/approvals/{appr.pk}/approve/', {'comments': 'Looks good'})
        assert resp.status_code == 200
        appr.refresh_from_db()
        assert appr.status == 'APPROVED'
        assert appr.approved_by == user

    def test_reject_pending_approval(self):
        appr = self._make_approval()
        client, _ = _user_client('mgr_ap2', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/approvals/{appr.pk}/reject/', {'comments': 'No'})
        assert resp.status_code == 200
        appr.refresh_from_db()
        assert appr.status == 'REJECTED'

    def test_cannot_approve_already_approved(self):
        from apps.core.models import Approval
        appr = self._make_approval()
        appr.status = Approval.Status.APPROVED
        appr.save()
        client, _ = _user_client('mgr_ap3', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/approvals/{appr.pk}/approve/')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# FundingNotice close action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFundingNoticeActions:

    def test_close_open_notice(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj)
        client, _ = _user_client('mgr_fn', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/funding-notices/{fn.pk}/close/')
        assert resp.status_code == 200
        fn.refresh_from_db()
        assert fn.status == 'CLOSED'


# ---------------------------------------------------------------------------
# ExpenseClaim lifecycle and cap enforcement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExpenseClaimActions:

    def _make_claim(self, funding_notice, amount=Decimal('20000'), status='DRAFT'):
        from apps.core.models import ExpenseClaim
        return ExpenseClaim.objects.create(
            funding_notice=funding_notice,
            amount=amount,
            date_submitted=date.today(),
            status=status,
        )

    def test_submit_draft_claim(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj)
        claim = self._make_claim(fn)
        client, _ = _user_client('mgr_ec', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/expense-claims/{claim.pk}/submit/')
        assert resp.status_code == 200
        claim.refresh_from_db()
        assert claim.status == 'SUBMITTED'

    def test_approve_submitted_claim(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj, capped_amount=Decimal('100000'))
        claim = self._make_claim(fn, amount=Decimal('30000'), status='SUBMITTED')
        client, user = _user_client('mgr_ec2', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/expense-claims/{claim.pk}/approve/')
        assert resp.status_code == 200
        claim.refresh_from_db()
        assert claim.status == 'APPROVED'
        assert claim.approved_by == user

    def test_reject_submitted_claim(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj)
        claim = self._make_claim(fn, status='SUBMITTED')
        client, _ = _user_client('mgr_ec3', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/expense-claims/{claim.pk}/reject/')
        assert resp.status_code == 200
        claim.refresh_from_db()
        assert claim.status == 'REJECTED'

    def test_cap_enforcement_blocks_over_limit_claim(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj, capped_amount=Decimal('50000'))
        self._make_claim(fn, amount=Decimal('40000'), status='APPROVED')
        new_claim = self._make_claim(fn, amount=Decimal('20000'), status='SUBMITTED')
        client, _ = _user_client('mgr_ec4', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/expense-claims/{new_claim.pk}/approve/')
        assert resp.status_code == 400

    def test_cannot_submit_already_submitted_claim(self):
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fn = _make_funding_notice(proj)
        claim = self._make_claim(fn, status='SUBMITTED')
        client, _ = _user_client('mgr_ec5', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/expense-claims/{claim.pk}/submit/')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Payment release action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentActions:

    def test_release_approved_payment(self):
        from apps.core.models import Payment
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fs = _make_funding_schedule(proj)
        payment = Payment.objects.create(
            project=proj,
            funding_schedule=fs,
            payment_type=Payment.PaymentType.FIRST,
            calculation_type=Payment.CalculationType.PERCENTAGE,
            payment_split=Payment.PaymentSplit.STANDARD,
            amount=Decimal('100000'),
            status=Payment.Status.APPROVED,
        )
        client, _ = _user_client('mgr_pay', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/payments/{payment.pk}/release/')
        assert resp.status_code == 200
        payment.refresh_from_db()
        assert payment.status == 'RELEASED'
        assert payment.release_date is not None

    def test_cannot_release_pending_payment(self):
        from apps.core.models import Payment
        council = _make_council()
        prog = _make_program()
        proj = _make_project(council, prog)
        fs = _make_funding_schedule(proj)
        payment = Payment.objects.create(
            project=proj,
            funding_schedule=fs,
            payment_type=Payment.PaymentType.FIRST,
            calculation_type=Payment.CalculationType.PERCENTAGE,
            payment_split=Payment.PaymentSplit.STANDARD,
            amount=Decimal('100000'),
            status=Payment.Status.PENDING,
        )
        client, _ = _user_client('mgr_pay2', 'MANAGER')
        resp = _api(client, 'post', f'/api/v1/payments/{payment.pk}/release/')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# OpenAPI schema is reachable
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_openapi_schema_accessible():
    client, _ = _user_client('mgr_schema', 'MANAGER')
    resp = client.get('/api/v1/schema/', HTTP_ACCEPT='application/vnd.oai.openapi')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_swagger_ui_accessible():
    client, _ = _user_client('mgr_docs', 'MANAGER')
    resp = client.get('/api/v1/docs/', HTTP_ACCEPT='text/html')
    assert resp.status_code == 200
