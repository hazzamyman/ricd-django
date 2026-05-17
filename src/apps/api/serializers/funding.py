"""
Serializers for the funding domain:
  PaymentRule, FundingAgreement, FundingSchedule, BriefFinancialApproval,
  Payment, Approval, FundingNotice, ExpenseClaim, WorkflowAction, AuditLog

document_uri / document_link fields are plain CharField — they hold
SharePoint URLs, OpenText Content Manager references, or Windows UNC paths
(e.g. //fileserver/RICD/... or G:\\RICD\\...) depending on what the team is using.
"""
from rest_framework import serializers
from apps.core.models import (
    PaymentRule, FundingAgreement, FundingSchedule, BriefFinancialApproval,
    FundingNotice, ExpenseClaim, Approval, WorkflowAction, AuditLog, Payment,
)


class PaymentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRule
        fields = ['id', 'name', 'rule_type', 'config_json', 'version', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if self.instance:
            if FundingSchedule.objects.filter(payment_rule=self.instance).exists():
                raise serializers.ValidationError(
                    "PaymentRule is immutable once linked to a FundingSchedule."
                )
        return data


class FundingAgreementSerializer(serializers.ModelSerializer):
    # Plain CharField — accepts SharePoint URL, OpenText ref, or Windows UNC path
    document_uri = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = FundingAgreement
        fields = ['id', 'council', 'name', 'status', 'execution_date', 'document_uri', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class FundingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingSchedule
        fields = [
            'id', 'funding_agreement', 'schedule_number', 'payment_rule',
            'status', 'amount', 'contingency', 'total_funding', 'payment_split',
            'project', 'replaces_schedule', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        project = data.get('project') or (self.instance.project if self.instance else None)
        is_new = self.instance is None
        if is_new and project:
            has_bfa = BriefFinancialApproval.objects.filter(
                project=project,
                status=BriefFinancialApproval.Status.APPROVED,
            ).exists()
            if not has_bfa:
                raise serializers.ValidationError(
                    "An approved BriefFinancialApproval is required before creating a FundingSchedule."
                )
        return data


class BriefFinancialApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefFinancialApproval
        fields = ['id', 'project', 'funding_amount', 'delegate_level', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['id', 'approved_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'funding_schedule', 'project', 'payment_type', 'calculation_type',
            'payment_split', 'amount', 'status', 'release_date', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approval
        fields = [
            'id', 'entity_type', 'entity_id', 'approval_type', 'required_role',
            'status', 'approved_by', 'approved_at', 'comments',
        ]
        read_only_fields = ['id', 'approved_at']


class FundingNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingNotice
        fields = ['id', 'project', 'capped_amount', 'status', 'issued_date', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'funding_notice', 'amount', 'date_submitted',
            'status', 'approved_by', 'approved_date', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        status = data.get('status', self.instance.status if self.instance else ExpenseClaim.Status.DRAFT)
        funding_notice = data.get('funding_notice', self.instance.funding_notice if self.instance else None)
        amount = data.get('amount', self.instance.amount if self.instance else None)

        if status != ExpenseClaim.Status.DRAFT and funding_notice and amount is not None:
            from apps.core.business_rules import get_approved_claims_total
            approved_total = get_approved_claims_total(funding_notice)
            if self.instance and self.instance.status == ExpenseClaim.Status.APPROVED:
                approved_total -= self.instance.amount
            if approved_total + amount > funding_notice.capped_amount:
                raise serializers.ValidationError(
                    f"Claim ${amount} would exceed notice cap "
                    f"(approved: ${approved_total:,.2f}, cap: ${funding_notice.capped_amount:,.2f})."
                )
        return data


class WorkflowActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAction
        fields = ['id', 'entity_type', 'entity_id', 'action_type', 'performed_at', 'metadata_json']
        read_only_fields = ['id', 'performed_at']


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'entity_type', 'entity_id', 'action', 'timestamp', 'before_json', 'after_json']
        read_only_fields = ['id', 'timestamp']
