"""
Tests for issue #34 — AuditLog signal wiring.

Covers:
- AuditLog created on CREATE of financial models
- AuditLog created on UPDATE (with before/after JSON)
- AuditLog created on DELETE
- user is captured from thread-local (CurrentUserMiddleware)
- AuditLog is immutable (no update/delete in admin)
- Detail views expose audit_logs context
"""
import pytest
from decimal import Decimal
from unittest.mock import patch
from django.test import RequestFactory, Client
from django.contrib.auth.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(username='auditor', password='pass')


@pytest.fixture
def council(db):
    from apps.core.models import Council
    return Council.objects.create(
        name='Test Council',
        region='Region',
        state_electorate='SE',
        federal_electorate='FE',
    )


@pytest.fixture
def program(db):
    from apps.core.models import Program
    return Program.objects.create(
        name='Test Program',
        funding_source='STATE',
        budget=Decimal('5000000'),
        gl_code='GL001',
        business_case_reference='BC-001',
    )


@pytest.fixture
def project(db, council, program):
    from apps.core.models import Project
    return Project.objects.create(
        name='Audit Test Project',
        council=council,
        program=program,
        state='PROSPECTIVE',
        dwelling_status='PROSPECTIVE',
        financial_year='2025-2026',
    )


@pytest.fixture
def funding_schedule(db, project):
    from apps.core.models import FundingSchedule
    return FundingSchedule.objects.create(
        project=project
    )


# ===========================================================================
# AuditLog creation via signals
# ===========================================================================

@pytest.mark.django_db
class TestAuditLogCreate:
    def test_create_financial_model_emits_audit_log(self, project):
        from apps.core.models import FundingSchedule, AuditLog
        before_count = AuditLog.objects.count()
        FundingSchedule.objects.create(
            project=project
        )
        assert AuditLog.objects.count() == before_count + 1
        log = AuditLog.objects.filter(entity_type='fundingschedule').latest('timestamp')
        assert log.action == 'CREATE'
        assert log.before_json == {}

    def test_create_log_captures_after_values(self, project):
        from apps.core.models import FundingSchedule, AuditLog
        fs = FundingSchedule.objects.create(
            project=project
        )
        log = AuditLog.objects.filter(entity_type='fundingschedule', entity_id=fs.pk).latest('timestamp')
        # schedule_number is a real stored field on FS
        assert 'schedule_number' in log.after_json
        assert log.action == 'CREATE'

    def test_non_financial_model_does_not_emit_audit_log(self, council):
        from apps.core.models import AuditLog
        # Council is not in FINANCIAL_MODELS — no audit log expected
        before_count = AuditLog.objects.filter(entity_type='council').count()
        council.name = 'Updated Council Name'
        council.save()
        assert AuditLog.objects.filter(entity_type='council').count() == before_count


@pytest.mark.django_db
class TestAuditLogUpdate:
    def test_update_emits_audit_log_with_before_after(self, funding_schedule):
        from apps.core.models import FundingSchedule, AuditLog
        old_number = funding_schedule.schedule_number
        funding_schedule.schedule_number = old_number + 1
        funding_schedule.save()

        log = AuditLog.objects.filter(
            entity_type='fundingschedule',
            entity_id=funding_schedule.pk,
            action='UPDATE',
        ).latest('timestamp')
        assert log.before_json.get('schedule_number') == old_number
        assert log.after_json.get('schedule_number') == old_number + 1

    def test_update_log_action_is_update(self, funding_schedule):
        from apps.core.models import AuditLog
        funding_schedule.status = 'READY'
        funding_schedule.save()
        log = AuditLog.objects.filter(
            entity_type='fundingschedule',
            entity_id=funding_schedule.pk,
            action='UPDATE',
        ).latest('timestamp')
        assert log.action == 'UPDATE'


@pytest.mark.django_db
class TestAuditLogDelete:
    def test_delete_emits_audit_log(self, funding_schedule):
        from apps.core.models import AuditLog
        pk = funding_schedule.pk
        funding_schedule.delete()
        log = AuditLog.objects.filter(
            entity_type='fundingschedule',
            entity_id=pk,
            action='DELETE',
        ).first()
        assert log is not None
        assert log.action == 'DELETE'
        assert 'schedule_number' in log.before_json

    def test_delete_log_has_before_state(self, funding_schedule):
        from apps.core.models import AuditLog
        pk = funding_schedule.pk
        expected_status = funding_schedule.status
        funding_schedule.delete()
        log = AuditLog.objects.filter(entity_type='fundingschedule', entity_id=pk).first()
        assert log.before_json.get('status') == expected_status


# ===========================================================================
# Thread-local user capture via CurrentUserMiddleware
# ===========================================================================

@pytest.mark.django_db
class TestCurrentUserMiddleware:
    def test_middleware_sets_thread_local_user(self):
        from apps.core.middleware import CurrentUserMiddleware, get_current_user

        captured = []

        def get_response(request):
            captured.append(get_current_user())
            from django.http import HttpResponse
            return HttpResponse()

        middleware = CurrentUserMiddleware(get_response)
        request = RequestFactory().get('/')
        request.user = User.objects.create_user(username='mw_user', password='x')
        middleware(request)
        assert captured[0] == request.user

    def test_middleware_clears_user_after_response(self):
        from apps.core.middleware import CurrentUserMiddleware, get_current_user

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse()

        middleware = CurrentUserMiddleware(get_response)
        request = RequestFactory().get('/')
        request.user = User.objects.create_user(username='mw_user2', password='x')
        middleware(request)
        assert get_current_user() is None

    def test_audit_log_captures_user_from_thread_local(self, project):
        from apps.core.models import FundingSchedule, AuditLog
        from apps.core.middleware import _thread_locals

        actor = User.objects.create_user(username='fs_actor', password='x')
        _thread_locals.user = actor
        try:
            fs = FundingSchedule.objects.create(
                project=project
            )
        finally:
            _thread_locals.user = None

        log = AuditLog.objects.filter(entity_type='fundingschedule', entity_id=fs.pk).latest('timestamp')
        assert log.user == actor

    def test_audit_log_user_is_none_without_middleware(self, project):
        from apps.core.models import FundingSchedule, AuditLog
        fs = FundingSchedule.objects.create(
            project=project
        )
        log = AuditLog.objects.filter(entity_type='fundingschedule', entity_id=fs.pk).latest('timestamp')
        assert log.user is None


# ===========================================================================
# AuditLog immutability
# ===========================================================================

@pytest.mark.django_db
class TestAuditLogImmutability:
    def test_audit_log_has_no_update_method(self, funding_schedule):
        from apps.core.models import AuditLog
        log = AuditLog.objects.filter(entity_type='fundingschedule').first()
        # AuditLog model should not define a custom save that allows re-save
        # The admin disallows change/delete — here we verify admin permission helpers
        from apps.core.admin import AuditLogAdmin
        from django.contrib.admin.sites import AdminSite
        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert not admin.has_add_permission(None)
        assert not admin.has_change_permission(None)
        assert not admin.has_delete_permission(None)

    def test_audit_log_is_created_on_funding_schedule_save(self, funding_schedule):
        from apps.core.models import AuditLog
        count = AuditLog.objects.filter(
            entity_type='fundingschedule', entity_id=funding_schedule.pk
        ).count()
        assert count >= 1


# ===========================================================================
# Detail view exposes audit_logs context
# ===========================================================================

@pytest.mark.django_db
class TestDetailViewAuditLogContext:
    def test_funding_schedule_detail_includes_audit_logs(self, funding_schedule):
        from apps.core.models import AuditLog
        from apps.ui.views.crud_views import FundingScheduleDetailView
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.user = User.objects.create_user(username='viewer', password='x')

        view = FundingScheduleDetailView()
        view.request = request
        view.kwargs = {'pk': funding_schedule.pk}
        view.object = funding_schedule

        ctx = view.get_context_data()
        assert 'audit_logs' in ctx
        # All returned entries should belong to this entity
        for log in ctx['audit_logs']:
            assert log.entity_type == 'fundingschedule'
            assert log.entity_id == funding_schedule.pk

    def test_audit_logs_capped_at_10(self, project):
        from apps.core.models import FundingSchedule, AuditLog
        from apps.ui.views.crud_views import FundingScheduleDetailView
        from django.test import RequestFactory

        fs = FundingSchedule.objects.create(
            project=project
        )
        # Create 15 extra audit entries
        for _ in range(15):
            AuditLog.objects.create(
                entity_type='fundingschedule',
                entity_id=fs.pk,
                action='UPDATE',
                before_json={},
                after_json={},
            )

        request = RequestFactory().get('/')
        request.user = User.objects.create_user(username='viewer2', password='x')
        view = FundingScheduleDetailView()
        view.request = request
        view.kwargs = {'pk': fs.pk}
        view.object = fs

        ctx = view.get_context_data()
        assert len(ctx['audit_logs']) <= 10
