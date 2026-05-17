"""Serializers for StageReport and QuarterlyReport."""
from rest_framework import serializers
from apps.core.models import StageReport, QuarterlyReport


class StageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageReport
        fields = [
            'id', 'project', 'funding_schedule', 'stage_type', 'status',
            'submitted_by', 'submitted_at',
            'endorsed_by', 'endorsed_at',
            'assessed_by', 'assessed_at',
            'approved_by', 'approved_at',
            'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuarterlyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuarterlyReport
        fields = [
            'id', 'project', 'year', 'quarter', 'status',
            'submitted_by', 'submitted_at',
            'endorsed_by', 'endorsed_at',
            'assessed_by', 'assessed_at',
            'approved_by', 'approved_at',
            'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
