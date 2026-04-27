#!/usr/bin/env python3
"""
Systematic testing script for Django RICD portal application
Tests all views and URLs to ensure no runtime errors or missing dependencies
"""
import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory

# Add project to path
project_dir = '/opt/ricd/testproj'
sys.path.insert(0, project_dir)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings')
django.setup()

from django.urls import reverse
from portal import views, urls
from ricd import views as ricd_views, urls as ricd_urls
from ricd.models import Project, Council, Program, QuarterlyReport, MonthlyTracker, Stage1Report, Stage2Report, Address, Work
from django.utils import timezone
from django.contrib.auth.models import User

def test_imports():
    """Test that all imports work correctly"""
    print("=== Testing Imports ===")

    try:
        from portal.views import (
            RICDDashboardView, CouncilDashboardView, ProjectDetailView,
            ProjectListView, ProjectCreateView, ProjectUpdateView,
            ProjectDeleteView, ProjectStateUpdateView,
            CouncilListView, CouncilCreateView, CouncilUpdateView, CouncilDeleteView,
            ProgramListView, ProgramCreateView, ProgramUpdateView, ProgramDeleteView,
            AnalyticsDashboardView, MonthlyReportView, QuarterlyReportView,
            Stage1ReportView, Stage2ReportView
        )
        print("✅ All portal views imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import portal views: {e}")
        return False

    try:
        from ricd.models import (
            Project, Council, Program, QuarterlyReport, MonthlyTracker,
            Stage1Report, Stage2Report, Address, Work, FundingSchedule
        )
        print("✅ All ricd models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ricd models: {e}")
        return False

    return True

def test_view_initialization():
    """Test that all views can be initialized without errors"""
    print("\n=== Testing View Initialization ===")

    views_to_test = [
        (views.RICDDashboardView, "RICD Dashboard"),
        (views.CouncilDashboardView, "Council Dashboard"),
        (views.ProjectDetailView, "Project Detail"),
        (views.ProjectListView, "Project List"),
        (views.ProjectCreateView, "Project Create"),
        (views.ProjectUpdateView, "Project Update"),
        (views.ProjectDeleteView, "Project Delete"),
        (views.ProjectStateUpdateView, "Project State Update"),
        (views.CouncilListView, "Council List"),
        (views.CouncilCreateView, "Council Create"),
        (views.CouncilUpdateView, "Council Update"),
        (views.CouncilDeleteView, "Council Delete"),
        (views.AnalyticsDashboardView, "Analytics Dashboard"),
        (views.MonthlyReportView, "Monthly Report"),
        (views.QuarterlyReportView, "Quarterly Report"),
        (views.Stage1ReportView, "Stage 1 Report"),
        (views.Stage2ReportView, "Stage 2 Report"),
    ]

    for view_class, description in views_to_test:
        try:
            # Basic instantiation
            view = view_class()
            print(f"✅ {description} view initialized successfully")
        except Exception as e:
            print(f"❌ {description} view failed: {e}")
            return False

    return True

def test_urls_resolvable():
    """Test that all URL patterns are resolvable"""
    print("\n=== Testing URL Resolution ===")

    # Test main URL patterns
    test_patterns = [
        ('portal:ricd_dashboard', 'RICD Dashboard'),
        ('portal:council_dashboard', 'Council Dashboard'),
        ('portal:analytics_dashboard', 'Analytics Dashboard'),
        ('portal:project_list', 'Project List'),
        ('portal:council_list', 'Council List'),
    ]

    factory = RequestFactory()

    for pattern, description in test_patterns:
        try:
            url = reverse(pattern)
            print(f"✅ URL for {description} resolves to: {url}")
        except Exception as e:
            print(f"❌ Failed to resolve {description}: {e}")
            return False

    return True

def test_analytics_budget_forecasting():
    """Test the specific analytics budget forecasting function"""
    print("\n=== Testing Analytics Budget Forecasting ===")

    # Create sample data if none exists
    if not Project.objects.exists():
        # Create minimal test data
        try:
            council = Council.objects.create(
                name="Test Council",
                default_suburb="Test Suburb",
                default_state="QLD",
                default_postcode="4000"
            )

            program = Program.objects.create(
                name="Test Program",
                description="Test program for analytics"
            )

            project = Project.objects.create(
                name="Test Project",
                council=council,
                program=program,
                state="completed"
            )

            work = Work.objects.create(
                project=project,
                work_type="construction",
                output_type="detached_house",
                output_quantity=1,
                estimated_cost=100000
            )

            print("✅ Created test data for analytics")
        except Exception as e:
            print(f"❌ Failed to create test data: {e}")

    # Test the problematic function
    try:
        view = views.AnalyticsDashboardView()
        analysis_date = timezone.now().date()
        projects = Project.objects.all()

        result = view.analyze_budget_forecasting(projects, analysis_date)
        print("✅ Analytics budget forecasting executed successfully")
        print(f"   - Forecast summary has {len(result.get('forecast_summary', {}))} entries")
        print(f"   - Alerts found: {len(result.get('alerts', []))}")

        return True
    except Exception as e:
        print(f"❌ Analytics budget forecasting failed: {e}")
        return False

def test_model_relationships():
    """Test model relationships and potential FK issues"""
    print("\n=== Testing Model Relationships ===")

    # Test if we can access related models without errors
    try:
        projects = Project.objects.all()
        for project in projects[:1]:  # Test just first few
            # Test all related fields
            _ = project.council
            _ = project.program
            _ = project.funding_schedule if project.funding_schedule else None
            _ = list(project.addresses.all())

            # Test reverse relationships - all reports go through work intermediary
            from ricd.models import MonthlyTracker, QuarterlyReport, Stage1Report, Stage2Report
            _ = list(MonthlyTracker.objects.filter(work__project=project))
            _ = list(QuarterlyReport.objects.filter(work__project=project))
            _ = list(Stage1Report.objects.filter(project=project))
            _ = list(Stage2Report.objects.filter(project=project))
            _ = list(project.works.all())

        print("✅ Model relationships working correctly")
        return True
    except Exception as e:
        print(f"❌ Model relationship issue: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Starting Systematic Django Application Tests ===\n")

    all_passed = True

    test_results = [
        test_imports(),
        test_view_initialization(),
        test_urls_resolvable(),
        test_analytics_budget_forecasting(),
        test_model_relationships()
    ]

    all_passed = all(test_results)

    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Application appears to be working correctly.")
    else:
        print("❌ SOME TESTS FAILED! Please review the errors above.")
    print("="*60)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)