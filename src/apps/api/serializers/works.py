"""Serializers for Work and WorkFunding (allocation) entities."""
from rest_framework import serializers
from apps.core.models import Work, WorkFunding


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = [
            'id', 'project', 'address', 'work_type', 'work_type_other',
            'bedrooms', 'quantity', 'estimated_cost', 'actual_cost',
            'status', 'is_notional_cost', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkFundingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkFunding
        fields = [
            'id', 'funding_schedule', 'project', 'work',
            'cost_centre', 'gl_code', 'tax_code', 'amount', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        project = data.get('project')
        work = data.get('work')
        if self.instance:
            project = project if 'project' in data else self.instance.project
            work = work if 'work' in data else self.instance.work
        if project and work:
            raise serializers.ValidationError("Specify either project or work — not both.")
        if not project and not work:
            raise serializers.ValidationError("One of project or work is required.")
        return data
