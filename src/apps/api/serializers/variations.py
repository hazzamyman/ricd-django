"""
Serializers for Variation and VariationItem.

document_link is a plain CharField — accepts SharePoint URL,
OpenText Content Manager reference, or Windows UNC path.
"""
from rest_framework import serializers
from apps.core.models import Variation, VariationItem


class VariationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariationItem
        fields = [
            'id', 'variation', 'option', 'description', 'funding_schedule',
            'original_amount', 'new_amount', 'original_contingency', 'new_contingency',
            'original_payment_split', 'new_payment_split',
            'stage1_target_date', 'stage2_target_date',
            'stage1_sunset_date', 'stage2_sunset_date',
            'original_scope', 'new_scope',
            'monthly_required', 'quarterly_required', 'stage1_required', 'stage2_required',
            'reporting_notes',
        ]
        read_only_fields = ['id']


class VariationSerializer(serializers.ModelSerializer):
    items = VariationItemSerializer(many=True, read_only=True)
    # document_link: plain CharField — SharePoint URL, OpenText ref, or UNC path
    document_link = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Variation
        fields = [
            'id', 'funding_schedule', 'variation_type', 'variation_option',
            'status', 'council_signed_date', 'department_executed_date',
            'document_link', 'description', 'reporting_requirements',
            'created_by', 'created_at', 'updated_at',
            'items',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
