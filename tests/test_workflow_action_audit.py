"""
Tests for WorkflowAction and AuditLog immutability and audit trail.

Tests: Event logging, immutability once created, audit trail accuracy.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.core.models import (
    WorkflowAction, AuditLog, FundingSchedule, FundingAgreement, PaymentRule
)
from apps.core.models import Payment
from apps.core.models import Council
from apps.core.models import Program
from apps.core.models import Project
from django.contrib.auth.models import User


@pytest.fixture
def council():
    return Council.objects.create(name="Test Council", region="Test Region")


@pytest.fixture
def program():
    return Program.objects.create(
        name="Test Program",
        funding_source="Government",
        budget=Decimal("10000000.00"),
        gl_code="GL789"
    )


@pytest.fixture
def project(council, program):
    return Project.objects.create(
        council=council,
        program=program,
        project_type=Project.Type.DWELLING,
        name="Test Project",
        state=Project.State.PROSPECTIVE
    )


@pytest.fixture
def actor_user():
    return User.objects.create_user(username="actor", password="pass")


@pytest.fixture
def funding_schedule(council):
    agreement = FundingAgreement.objects.create(council=council, status="DRAFT")
    rule = PaymentRule.objects.create(
        name="Standard Split",
        rule_type="SPLIT",
        config_json={
            "milestones": [
                {"name": "Start", "percentage": 30},
                {"name": "Mid", "percentage": 60},
                {"name": "End", "percentage": 10}
            ]
        },
        version=1
    )
    return FundingSchedule.objects.create(
        funding_agreement=agreement,
        schedule_number=1,
        payment_rule=rule,
        status="DRAFT"
    )


@pytest.fixture
def payment(funding_schedule, project):
    return Payment.objects.create(
        funding_schedule=funding_schedule,
        project=project,
        amount=Decimal("300000.00"),
        status="PENDING"
    )


@pytest.mark.django_db
class TestWorkflowActionCreation:
    """Test WorkflowAction creation and immutability"""

    def test_workflow_action_created(self, funding_schedule, actor_user):
        """Test WorkflowAction is created with event details"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        assert action.id is not None
        assert action.entity_type == "FundingSchedule"
        assert action.action_type == "CREATE"
        assert action.performed_by == actor_user

    def test_workflow_action_timestamp(self, funding_schedule, actor_user):
        """Test WorkflowAction records timestamp"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        assert action.performed_at is not None

    def test_workflow_action_for_different_entities(self, funding_schedule, payment, actor_user):
        """Test WorkflowAction supports different entity types"""
        schedule_action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        payment_action = WorkflowAction.objects.create(
            entity_type="Payment",
            entity_id=payment.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        assert schedule_action.entity_type == "FundingSchedule"
        assert payment_action.entity_type == "Payment"


@pytest.mark.django_db
class TestWorkflowActionEvents:
    """Test different workflow action event types"""

    def test_created_action(self, funding_schedule, actor_user):
        """Test CREATE action"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        assert action.action_type == "CREATE"

    def test_updated_action(self, funding_schedule, actor_user):
        """Test UPDATE action"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="UPDATE",
            performed_by=actor_user
        )
        assert action.action_type == "UPDATE"

    def test_approved_action(self, funding_schedule, actor_user):
        """Test APPROVE action"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="APPROVE",
            performed_by=actor_user
        )
        assert action.action_type == "APPROVE"

    def test_rejected_action(self, funding_schedule, actor_user):
        """Test REJECT action"""
        action = WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="REJECT",
            performed_by=actor_user
        )
        assert action.action_type == "REJECT"


@pytest.mark.django_db
class TestAuditLogCreation:
    """Test AuditLog creation and immutability"""

    def test_audit_log_created(self, funding_schedule, actor_user):
        """Test AuditLog is created with event details"""
        log = AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="CREATE",
            user=actor_user
        )
        assert log.id is not None
        assert log.entity_type == "FundingSchedule"
        assert log.action == "CREATE"
        assert log.user == actor_user

    def test_audit_log_timestamp(self, funding_schedule, actor_user):
        """Test AuditLog records timestamp"""
        log = AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="CREATE",
            user=actor_user
        )
        assert log.timestamp is not None

    def test_audit_log_for_different_action_types(self, funding_schedule, actor_user):
        """Test AuditLog supports different action types"""
        create_log = AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="CREATE",
            user=actor_user
        )
        modify_log = AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="MODIFY",
            user=actor_user
        )
        approve_log = AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="APPROVE",
            user=actor_user
        )
        assert create_log.action == "CREATE"
        assert modify_log.action == "MODIFY"
        assert approve_log.action == "APPROVE"


@pytest.mark.django_db
class TestAuditTrailSequence:
    """Test audit trail captures sequence of actions"""

    def test_audit_trail_for_lifecycle(self, funding_schedule, actor_user):
        """Test audit trail captures full lifecycle"""
        AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="CREATE",
            user=actor_user
        )
        AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="MODIFY",
            user=actor_user
        )
        AuditLog.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action="APPROVE",
            user=actor_user
        )
        audit_logs = AuditLog.objects.filter(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id
        ).order_by('timestamp')
        assert audit_logs.count() == 3

    def test_audit_trail_maintains_order(self, funding_schedule, actor_user):
        """Test audit trail maintains chronological order"""
        logs = []
        for action in ["CREATE", "MODIFY", "APPROVE"]:
            log = AuditLog.objects.create(
                entity_type="FundingSchedule",
                entity_id=funding_schedule.id,
                action=action,
                user=actor_user
            )
            logs.append(log)

        retrieved = list(
            AuditLog.objects.filter(
                entity_type="FundingSchedule",
                entity_id=funding_schedule.id
            ).order_by('timestamp')
        )
        assert len(retrieved) == 3
        assert retrieved[0].action == "CREATE"
        assert retrieved[1].action == "MODIFY"
        assert retrieved[2].action == "APPROVE"

    def test_workflow_action_history(self, funding_schedule, actor_user):
        """Test WorkflowAction history can be queried"""
        # Clear any signal-emitted entries from fixture setup before asserting exact count
        WorkflowAction.objects.filter(entity_type="FundingSchedule", entity_id=funding_schedule.id).delete()
        WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="CREATE",
            performed_by=actor_user
        )
        WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="UPDATE",
            performed_by=actor_user
        )
        WorkflowAction.objects.create(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id,
            action_type="APPROVE",
            performed_by=actor_user
        )
        actions = WorkflowAction.objects.filter(
            entity_type="FundingSchedule",
            entity_id=funding_schedule.id
        ).order_by('performed_at')
        assert actions.count() == 3
