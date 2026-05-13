from rest_framework import serializers
from apps.core.models import (
    PaymentRule, FundingAgreement, FundingSchedule, BriefFinancialApproval,
    FundingNotice, ExpenseClaim, Approval, WorkflowAction, AuditLog
)
from apps.core.models import Payment


class PaymentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRule
        fields = ['id', 'name', 'rule_type', 'config_json', 'version', 'created_at']
        read_only_fields = ['id', 'created_at']


class FundingAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingAgreement
        fields = ['id', 'council', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class FundingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingSchedule
        fields = ['id', 'funding_agreement', 'schedule_number', 'payment_rule', 'status', 'amount', 'project', 'created_at']
        read_only_fields = ['id', 'created_at']


class BriefFinancialApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefFinancialApproval
        fields = ['id', 'project', 'funding_amount', 'delegate_level', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['id', 'approved_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'funding_schedule', 'project', 'amount', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approval
        fields = ['id', 'entity_type', 'entity_id', 'approval_type', 'required_role', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['id', 'approved_at']


class FundingNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingNotice
        fields = ['id', 'project', 'capped_amount', 'status', 'issued_date']
        read_only_fields = ['id']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseClaim
        fields = ['id', 'funding_notice', 'amount', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['id', 'approved_at']


class WorkflowActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAction
        fields = ['id', 'entity_type', 'entity_id', 'action_type', 'performed_by', 'performed_at']
        read_only_fields = ['id', 'performed_at']


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'entity_type', 'entity_id', 'action', 'user', 'timestamp']
        read_only_fields = ['id', 'timestamp']
