"""Serializers for Council, Program, and Project entities."""
from rest_framework import serializers
from apps.core.models import Council, Program, Project


class CouncilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Council
        fields = [
            'id', 'name', 'region', 'state_electorate', 'federal_electorate',
            'contact_email', 'contact_phone', 'is_registered_housing_provider',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = [
            'id', 'name', 'funding_source', 'funding_source_other',
            'budget', 'gl_code', 'business_case_reference',
            'description', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'council', 'program', 'project_type', 'name',
            'financial_year', 'state', 'dwelling_status', 'status_flag',
            'parent_land_project', 'start_date', 'completion_date',
            'stage1_target_date', 'stage2_target_date',
            'stage1_sunset_date', 'stage2_sunset_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        project_type = data.get('project_type', self.instance.project_type if self.instance else None)
        parent = data.get('parent_land_project', getattr(self.instance, 'parent_land_project_id', None))
        if parent is not None and project_type != 'DWELLING':
            raise serializers.ValidationError(
                "parent_land_project may only be set on DWELLING projects."
            )
        return data
