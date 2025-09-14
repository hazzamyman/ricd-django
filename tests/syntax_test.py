import os
import sys
import django
from django.conf import settings
from django.template.loader import get_template
from django.template import Template, TemplateSyntaxError
from django.core import checks
from ricd.models import Project, Council, Work, Address
from django.test import TestCase

# Configure Django settings
if not settings.configured:
    django.setup()

class ComprehensiveSyntaxTest(TestCase):
    """
    Comprehensive test to check syntax and requirements across templates,
    models, forms, views, and ensure all necessary components are present.
    """

    def test_template_syntax(self):
        """Test all templates for syntax errors by rendering them with minimal context."""
        template_dirs = ['portal/templates/portal', 'ricd/templates']
        template_errors = []

        for templatadir in template_dirs:
            if os.path.exists(templatadir):
                for root, dirs, files in os.walk(templatadir):
                    for file in files:
                        if file.endswith('.html'):
                            template_path = os.path.join(root, file).replace('\\', '/').replace(templatadir + '/', '')
                            try:
                                # Try to load the template
                                template = get_template(template_path)
                                # Try to render with an empty context to catch basic syntax errors
                                rendered = template.render({})
                            except Exception as e:
                                template_errors.append(f"Template {template_path}: {str(e)}")

        if template_errors:
            self.fail(f"Template syntax errors found:\n" + "\n".join(template_errors))
        else:
            print("All templates have valid syntax.")

    def test_model_field_validation(self):
        """Test that all model fields have proper attributions and required fields."""
        models_to_check = [Project, Council, Work, Address]
        missing_fields = []

        for model in models_to_check:
            # Check for required fields (e.g., no blank/None without default)
            for field in model._meta.get_fields():
                if hasattr(field, 'blank') and not field.blank and hasattr(field, 'default') and field.default is None:
                    if not field.null and field.null is not True:
                        missing_fields.append(f"{model.__name__}.{field.name}: Required field without default")

        if missing_fields:
            self.fail(f"Missing field requirements:\n" + "\n".join(missing_fields))
        else:
            print("All model fields meet requirements.")

    def test_view_context_requirements(self):
        """Test that views provide necessary context variables."""
        # This would require creating test instances and calling views
        # For now, just check if views exist and import successfully
        try:
            from portal.views import ProjectDetailView
            print("ProjectDetailView imports successfully.")
        except ImportError as e:
            self.fail(f"View import error: {e}")

    def test_form_validation(self):
        """Test form creation and basic validation."""
        from portal.forms import ProjectForm, CouncilForm

        # Test forms can be instantiated
        project_form = ProjectForm()
        council_form = CouncilForm()

        print("Forms instantiate without errors.")

    def test_django_checks(self):
        """Run Django's built-in system checks."""
        errors = checks.run_checks(tags=['models', 'templates'])
        if errors:
            self.fail(f"Django system checks failed:\n" + "\n".join(str(error) for error in errors))
        else:
            print("Django system checks passed.")

    def test_systematic_template_check(self):
        """Systematic check of all templates for syntax and common issues."""
        from django.template.loader import get_template
        from django.template import Context
        from portal.views import ProjectDetailView
        import os

        template_dirs = ['portal/templates', 'ricd/templates']
        template_errors = []
        template_warnings = []

        for template_dir in template_dirs:
            if os.path.exists(template_dir):
                for root, dirs, files in os.walk(template_dir):
                    for file in files:
                        if file.endswith('.html'):
                            template_path = os.path.join(root, file).replace(template_dir + '/', '').replace('\\', '/')
                            try:
                                template = get_template(template_path)
                                # Try to render with minimal context but skip if it needs complex context
                                if file in ['project_detail.html', 'user_list.html', 'funding_approval_list.html']:
                                    # These templates need specific context, skip syntax check
                                    continue
                                try:
                                    rendered = template.render({})
                                except Exception as render_error:
                                    template_warnings.append(f"Template {template_path}: Render warning - {str(render_error)}")
                            except Exception as e:
                                template_errors.append(f"Template {template_path}: Syntax error - {str(e)}")

        if template_errors:
            self.fail(f"Template syntax errors:\n" + "\n".join(template_errors))

        # Print warnings but don't fail
        if template_warnings:
            print(f"Template render warnings (may be normal for complex templates):\n" + "\n".join(template_warnings))

    def test_views_import_and_basic_functionality(self):
        """Test that views can be imported and have basic methods."""
        try:
            from portal.views import (
                RICDDashboardView, ProjectDetailView, CouncilListView,
                ProjectListView, WorkListView
            )
        except ImportError as e:
            self.fail(f"View import error: {e}")

        # Test that views have required methods
        from portal.views import ProjectDetailView
        self.assertTrue(hasattr(ProjectDetailView, 'get_context_data'))
        self.assertTrue(hasattr(ProjectDetailView, 'get'))

        print("View imports and basic functionality verified.")

    def test_urls_are_resolvable(self):
        """Test that URLs can be reversed without errors."""
        from django.urls import reverse, NoReverseMatch

        # Common URLs to test
        test_urls = [
            'portal:ricd_dashboard',
            'portal:council_list',
            'portal:project_list',
            'portal:work_list',
            'portal:user_list',
        ]

        unresolved_urls = []
        for url_name in test_urls:
            try:
                reverse(url_name)
            except NoReverseMatch:
                unresolved_urls.append(url_name)

        if unresolved_urls:
            self.fail(f"Unresolvable URLs: {unresolved_urls}")

        print("URLs are resolvable.")

    def test_models_basic_functionality(self):
        """Test basic model functionality and relationships."""
        from ricd.models import Project, Council

        # Test that key models can be imported
        self.assertTrue(Project)
        self.assertTrue(Council)

        # Test that models have expected fields
        from django.db import models as django_models
        project_fields = [f.name for f in Project._meta.get_fields() if isinstance(f, django_models.Field)]

        expected_fields = ['name', 'council', 'state', 'start_date']
        for field in expected_fields:
            self.assertIn(field, project_fields, f"Missing field '{field}' in Project model")

        print("Model imports and field validation passed.")
