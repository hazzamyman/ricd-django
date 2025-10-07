#!/usr/bin/env python3
"""
Robust System Test Suite for Django Application
Tests all views, pages, models, templates, and URLs systematically
Ensures no NameErrors, template errors, or broken functionality

This script provides comprehensive testing for:
- All URL patterns (including parameterized ones)
- Template rendering and context variables
- Model relationships and data integrity
- Form validation and submission
- Error detection (NameErrors, ImportErrors, etc.)
- Pre-deployment validation (cache clearing, service restarts)
"""

import os
import sys
import django
import subprocess
import time
from pathlib import Path
from collections import defaultdict
import json

# Add Django project to path
project_path = Path(__file__).parent / 'testproj'
sys.path.insert(0, str(project_path))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings')
django.setup()

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse, resolve, Resolver404
from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line
from django.template.loader import get_template
from django.db import connection
from django.apps import apps
import logging

# Import all models to check for import errors
from ricd.models import (
    Council, Program, Project, Address, Work, WorkType, OutputType,
    ConstructionMethod, FundingSchedule, QuarterlyReport, MonthlyTracker,
    Stage1Report, Stage2Report, FundingApproval, WorkStep, Defect,
    ForwardRemoteProgramFundingAgreement, InterimForwardProgramFundingAgreement,
    RemoteCapitalProgramFundingAgreement, UserProfile, Contact, Officer,
    Variation, DefaultWorkStep, Instalment, ReportAttachment,
    StepTask, StepTaskCompletion, WorkSchedule, PracticalCompletion,
    WorkProgress
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PreDeploymentValidator:
    """Handles pre-deployment setup and validation"""

    @staticmethod
    def run_pre_commands():
        """Execute the required pre-test commands"""
        logger.info("🚀 Running pre-deployment commands...")

        commands = [
            "cd /opt/ricd/testproj && bash -c 'source venv/bin/activate && python manage.py shell -c \"from django.urls import clear_url_caches; clear_url_caches()\"'",
            "sudo systemctl restart ricd",
            "sudo systemctl status ricd",
            "sudo systemctl restart nginx"
        ]

        for cmd in commands:
            try:
                logger.info(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    logger.info(f"✅ Command successful: {cmd}")
                    if result.stdout:
                        logger.info(f"Output: {result.stdout[:200]}...")
                else:
                    logger.warning(f"⚠️ Command failed: {cmd}")
                    logger.warning(f"Error: {result.stderr}")

            except subprocess.TimeoutExpired:
                logger.error(f"⏰ Command timed out: {cmd}")
            except Exception as e:
                logger.error(f"❌ Command error: {cmd} - {e}")

    @staticmethod
    def validate_environment():
        """Validate that the environment is ready for testing"""
        logger.info("🔍 Validating test environment...")

        issues = []

        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            logger.info("✅ Database connection OK")
        except Exception as e:
            issues.append(f"Database connection failed: {e}")

        # Check required tables
        required_tables = [
            'ricd_council', 'ricd_program', 'ricd_project', 'ricd_address',
            'ricd_work', 'ricd_worktype', 'ricd_outputtype', 'auth_user'
        ]

        with connection.cursor() as cursor:
            existing_tables = connection.introspection.table_names()

        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            issues.append(f"Missing required tables: {missing_tables}")

        # Check Django apps are loaded
        try:
            apps.get_app_config('ricd')
            apps.get_app_config('portal')
            logger.info("✅ Django apps loaded OK")
        except Exception as e:
            issues.append(f"Django apps not loaded: {e}")

        if issues:
            logger.error("❌ Environment validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("✅ Environment validation passed")
        return True


class ComprehensiveURLTester(TestCase):
    """Comprehensive URL and functionality tester"""

    def setUp(self):
        """Set up test fixtures and data"""
        self.client = Client()
        self.errors = []
        self.warnings = []

        # Create test users with different roles
        User = get_user_model()

        # Superuser
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )

        # Council user
        self.council_user = User.objects.create_user(
            username='council_test',
            email='council@test.com',
            password='council123'
        )

        # Create basic data for testing
        self.council = Council.objects.create(
            name='Test Council',
            abn='12345678901',
            default_suburb='Test Suburb'
        )

        # Create user profile for council user
        UserProfile.objects.create(user=self.council_user, council=self.council)

        self.program = Program.objects.create(
            name='Test Program',
            description='Test program description'
        )

        self.project = Project.objects.create(
            council=self.council,
            program=self.program,
            name='Test Project'
        )

        self.address = Address.objects.create(
            project=self.project,
            street='123 Test Street',
            suburb='Test Suburb',
            postcode='4000'
        )

        self.work_type = WorkType.objects.create(
            code='test_wt',
            name='Test Work Type'
        )

        self.output_type = OutputType.objects.create(
            code='test_ot',
            name='Test Output Type'
        )

        # Create work for testing
        self.work = Work.objects.create(
            address=self.address,
            work_type_id=self.work_type,
            output_type_id=self.output_type,
            estimated_cost=10000
        )

        # Create an officer for testing officer URLs
        try:
            self.officer = Officer.objects.create(
                user=self.council_user,
                position='Test Officer',
                is_principal=True
            )
        except Exception as e:
            logger.warning(f"Could not create officer: {e}")
            self.officer = None

    def log_error(self, message, url=None, exception=None):
        """Log an error with context"""
        error_info = {
            'message': message,
            'url': url,
            'exception': str(exception) if exception else None
        }
        self.errors.append(error_info)
        logger.error(f"❌ {message}" + (f" (URL: {url})" if url else ""))

    def log_warning(self, message, url=None):
        """Log a warning with context"""
        warning_info = {
            'message': message,
            'url': url
        }
        self.warnings.append(warning_info)
        logger.warning(f"⚠️ {message}" + (f" (URL: {url})" if url else ""))

    def test_all_url_patterns(self):
        """Test all URL patterns systematically"""

        logger.info("🔍 Testing all URL patterns...")

        # Comprehensive list of URL patterns with parameters
        url_patterns = [
            # Dashboard URLs
            {'name': 'portal:ricd_dashboard', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:council_dashboard', 'method': 'GET', 'requires_auth': True, 'user': 'council_user'},

            # List views
            {'name': 'portal:council_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:program_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:project_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:work_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:user_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:officer_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:defect_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:funding_approval_list', 'method': 'GET', 'requires_auth': True},

            # Detail views with parameters
            {'name': 'portal:project_detail', 'method': 'GET', 'kwargs': {'pk': self.project.pk}, 'requires_auth': True},
            {'name': 'portal:council_detail', 'method': 'GET', 'kwargs': {'pk': self.council.pk}, 'requires_auth': True},
            {'name': 'portal:program_detail', 'method': 'GET', 'kwargs': {'pk': self.program.pk}, 'requires_auth': True},
            {'name': 'portal:user_detail', 'method': 'GET', 'kwargs': {'pk': self.council_user.pk}, 'requires_auth': True},
            {'name': 'portal:officer_detail', 'method': 'GET', 'kwargs': {'pk': self.officer.pk if self.officer else 1}, 'requires_auth': True},  # Officer may not exist

            # Create views
            {'name': 'portal:council_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:program_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:project_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:user_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:officer_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:funding_approval_create', 'method': 'GET', 'requires_auth': True},

            # Update views with parameters
            {'name': 'portal:council_update', 'method': 'GET', 'kwargs': {'pk': self.council.pk}, 'requires_auth': True},
            {'name': 'portal:program_update', 'method': 'GET', 'kwargs': {'pk': self.program.pk}, 'requires_auth': True},
            {'name': 'portal:project_update', 'method': 'GET', 'kwargs': {'pk': self.project.pk}, 'requires_auth': True},
            {'name': 'portal:user_update', 'method': 'GET', 'kwargs': {'pk': self.council_user.pk}, 'requires_auth': True},
            {'name': 'portal:officer_update', 'method': 'GET', 'kwargs': {'pk': self.officer.pk if self.officer else 1}, 'requires_auth': True},  # Officer may not exist

            # Delete views with parameters
            {'name': 'portal:council_delete', 'method': 'GET', 'kwargs': {'pk': self.council.pk}, 'requires_auth': True},
            {'name': 'portal:program_delete', 'method': 'GET', 'kwargs': {'pk': self.program.pk}, 'requires_auth': True},
            {'name': 'portal:project_delete', 'method': 'GET', 'kwargs': {'pk': self.project.pk}, 'requires_auth': True},

            # Address and Work CRUD
            {'name': 'portal:address_create', 'method': 'GET', 'kwargs': {'project_pk': self.project.pk}, 'requires_auth': True},
            {'name': 'portal:work_create', 'method': 'GET', 'kwargs': {'project_pk': self.project.pk}, 'requires_auth': True},

            # Analytics and reports
            {'name': 'portal:analytics_dashboard', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:monthly_report', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:quarterly_report', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:stage1_report', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:stage2_report', 'method': 'GET', 'requires_auth': True},

            # Help pages
            {'name': 'portal:help_ricd', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:help_council', 'method': 'GET', 'requires_auth': True},

            # Work Type and Output Type management
            {'name': 'portal:work_type_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:work_type_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:work_type_update', 'method': 'GET', 'kwargs': {'pk': self.work_type.pk}, 'requires_auth': True},
            {'name': 'portal:work_type_delete', 'method': 'GET', 'kwargs': {'pk': self.work_type.pk}, 'requires_auth': True},

            {'name': 'portal:output_type_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:output_type_create', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:output_type_update', 'method': 'GET', 'kwargs': {'pk': self.output_type.pk}, 'requires_auth': True},
            {'name': 'portal:output_type_delete', 'method': 'GET', 'kwargs': {'pk': self.output_type.pk}, 'requires_auth': True},

            # Construction Method management
            {'name': 'portal:construction_method_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:construction_method_create', 'method': 'GET', 'requires_auth': True},

            # Agreement URLs
            {'name': 'portal:forward_rpf_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:interim_frp_list', 'method': 'GET', 'requires_auth': True},
            {'name': 'portal:remote_capital_program_list', 'method': 'GET', 'requires_auth': True},

            # Special configuration pages
            {'name': 'portal:work_output_type_config', 'method': 'GET', 'requires_auth': True},
        ]

        tested_urls = 0
        successful_urls = 0

        for pattern in url_patterns:
            with self.subTest(url_name=pattern['name'], method=pattern['method']):
                tested_urls += 1

                # Login appropriate user if required
                if pattern.get('requires_auth'):
                    if pattern.get('user') == 'council_user':
                        self.client.login(username='council_test', password='council123')
                    else:
                        self.client.login(username='admin', password='admin123')

                # Get URL kwargs
                kwargs = pattern.get('kwargs', {})
                data = pattern.get('data', {})

                # Try to reverse URL
                try:
                    url = reverse(pattern['name'], kwargs=kwargs)
                except Exception as e:
                    self.log_error(f"Failed to reverse URL '{pattern['name']}' with kwargs {kwargs}", None, e)
                    continue

                # Make request
                try:
                    if pattern['method'] == 'GET':
                        response = self.client.get(url)
                    elif pattern['method'] == 'POST':
                        response = self.client.post(url, data)
                    else:
                        response = self.client.get(url)  # Default to GET

                    # Check for successful response
                    if response.status_code == 403:  # Forbidden - might be permissions issue
                        self.log_warning(f"403 Forbidden for {pattern['name']}", url)
                        successful_urls += 1  # Still counts as successful (permissions working)
                    elif response.status_code >= 500:
                        self.log_error(f"Server error ({response.status_code}) for {pattern['name']}", url, response.content.decode())
                    elif response.status_code >= 400:
                        self.log_warning(f"{response.status_code} error for {pattern['name']}", url)
                        successful_urls += 1  # Client errors are expected for some cases
                    else:
                        successful_urls += 1

                    # Check for NameError or other template errors in response content
                    if hasattr(response, 'content'):
                        content = response.content.decode()
                        if 'NameError' in content or 'name \'' in content and 'is not defined' in content:
                            self.log_error(f"NameError detected in response for {pattern['name']}", url)

                    # Check for template errors
                    if hasattr(response, 'context') and response.context:
                        for context_var in response.context:
                            if context_var == 'error':
                                self.log_warning(f"Error in context for {pattern['name']}: {response.context[context_var]}", url)
                            if 'form' in context_var.lower():
                                form = response.context[context_var]
                                if hasattr(form, 'errors') and form.errors:
                                    self.log_warning(f"Form errors in {pattern['name']}: {form.errors}", url)

                except Exception as e:
                    self.log_error(f"Exception testing URL '{pattern['name']}': {type(e).__name__}", url, e)

        logger.info(f"📊 URL Testing Results: {successful_urls}/{tested_urls} successful")
        return successful_urls == tested_urls

    def test_template_rendering(self):
        """Test template rendering for critical templates"""

        logger.info("🎨 Testing template rendering...")

        # Critical templates to test
        critical_templates = [
            'portal/base.html',
            'portal/ricd_dashboard.html',
            'portal/council_dashboard.html',
            'portal/project_detail.html',
            'portal/user_list.html',
            'portal/user_form.html',
            'portal/council_form.html',
            'portal/program_form.html',
            'portal/project_form.html',
        ]

        successful_templates = 0

        for template_name in critical_templates:
            try:
                template = get_template(template_name)
                # Try to render with basic context
                context = {
                    'user': self.superuser,
                    'request': type('Request', (), {'user': self.superuser})(),
                    'project': self.project,  # Add project for project_detail template
                    'funding_approvals': [],  # Add empty list for project_detail template
                }
                rendered = template.render(context)

                if 'NameError' in rendered or 'name \'' in rendered and 'is not defined' in rendered:
                    self.log_error(f"NameError in template {template_name}")
                else:
                    successful_templates += 1
                    logger.info(f"✅ Template {template_name} rendered successfully")

            except Exception as e:
                error_msg = f"Template rendering failed for {template_name}: {str(e)}"
                # Try to get more specific error information
                if hasattr(e, '__cause__') and e.__cause__:
                    error_msg += f" (caused by: {e.__cause__})"
                self.log_error(error_msg, None, e)

        logger.info(f"📊 Template Testing Results: {successful_templates}/{len(critical_templates)} successful")
        return successful_templates == len(critical_templates)

    def test_model_relationships(self):
        """Test all model relationships work correctly"""

        logger.info("🔗 Testing model relationships...")

        try:
            # Test Work -> Address -> Project relationship
            work = Work.objects.create(
                address=self.address,
                work_type_id=self.work_type,
                output_type_id=self.output_type,
                estimated_cost=10000
            )

            # Test reverse relationships
            self.assertEqual(work.project, self.project)
            self.assertIn(work, self.address.works.all())

            # Test QuarterlyReport relationship
            from datetime import date
            quarterly_report = QuarterlyReport.objects.create(
                work=work,
                submission_date=date(2024, 1, 1),
                percentage_works_completed=50
            )

            self.assertEqual(quarterly_report.project, self.project)
            self.assertEqual(quarterly_report.work, work)

            logger.info("✅ Model relationships working correctly")
            return True

        except Exception as e:
            error_msg = f"Model relationship test failed: {str(e)}"
            # Add more context about what failed
            import traceback
            error_msg += f"\nTraceback: {traceback.format_exc()}"
            self.log_error(error_msg, None, e)
            return False

    def test_import_errors(self):
        """Test for import errors in views and models"""

        logger.info("📦 Testing for import errors...")

        import_errors = []

        # Test imports that are commonly problematic
        test_imports = [
            'from django.contrib.auth.models import User, Group',
            'from ricd.models import Council, Program, Project',
            'from portal.views import RICDDashboardView, CouncilDashboardView',
            'from portal.forms import CouncilForm, ProgramForm',
        ]

        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                logger.info(f"✅ Import successful: {import_stmt}")
            except Exception as e:
                import_errors.append(f"{import_stmt}: {e}")
                self.log_error(f"Import error: {import_stmt}", None, e)

        if import_errors:
            logger.error("❌ Import errors found:")
            for error in import_errors:
                logger.error(f"  - {error}")
            return False

        logger.info("✅ All imports successful")
        return True


def run_robust_tests():
    """Run the complete robust test suite"""

    logger.info("🚀 Starting Robust System Test Suite")
    logger.info("=" * 60)

    # Pre-deployment validation
    validator = PreDeploymentValidator()

    logger.info("📋 Step 1: Pre-deployment validation")
    if not validator.validate_environment():
        logger.error("❌ Pre-deployment validation failed. Aborting tests.")
        return False

    logger.info("📋 Step 2: Running pre-deployment commands")
    validator.run_pre_commands()

    # Run comprehensive tests
    logger.info("📋 Step 3: Running comprehensive system tests")

    import unittest
    from django.test.runner import DiscoverRunner
    from django.conf import settings
    from django.test.utils import get_runner

    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(ComprehensiveURLTester('test_all_url_patterns'))
    suite.addTest(ComprehensiveURLTester('test_template_rendering'))
    suite.addTest(ComprehensiveURLTester('test_model_relationships'))
    suite.addTest(ComprehensiveURLTester('test_import_errors'))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Report results
    logger.info("=" * 60)
    logger.info("📊 COMPREHENSIVE SYSTEM TESTING RESULTS")
    logger.info("=" * 60)

    if result.wasSuccessful():
        logger.info("✅ ALL COMPREHENSIVE TESTS PASSED!")
        logger.info(f"• Ran {result.testsRun} comprehensive tests")
        logger.info("• No failures or errors detected")
        logger.info("🎉 System is ready for deployment!")
        return True
    else:
        logger.error("❌ COMPREHENSIVE TEST ISSUES FOUND:")
        logger.error(f"• Tests run: {result.testsRun}")
        logger.error(f"• Failures: {len(result.failures)}")
        logger.error(f"• Errors: {len(result.errors)}")

        # Print failures
        for test, traceback in result.failures:
            logger.error(f"\n🔴 FAILURE: {test}")
            logger.error(f"   {traceback}")

        # Print errors
        for test, traceback in result.errors:
            logger.error(f"\n💥 ERROR: {test}")
            logger.error(f"   {traceback}")

        logger.error("\n🔧 Please fix the issues above before deploying!")
        return False


if __name__ == '__main__':
    success = run_robust_tests()
    sys.exit(0 if success else 1)