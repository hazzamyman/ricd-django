import os
import django
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group, AnonymousUser
from django.http import HttpResponseForbidden
from ricd.models import Council, UserProfile, Project, Program
from portal.views import ProjectDetailView, CouncilProjectDetailView, RICDDashboardView


class SecurityTestCase(TestCase):
    """Test security controls for cross-council access"""

    def setUp(self):
        """Set up test data"""
        # Create councils
        self.council1, created = Council.objects.get_or_create(
            name='Council One',
            defaults={'abn': '11111111111', 'default_suburb': 'Suburb 1'}
        )

        self.council2, created = Council.objects.get_or_create(
            name='Council Two',
            defaults={'abn': '22222222222', 'default_suburb': 'Suburb 2'}
        )

        # Create program
        self.program, created = Program.objects.get_or_create(
            name='Test Program',
            defaults={'description': 'Test program'}
        )

        # Create projects
        self.project1, created = Project.objects.get_or_create(
            name='Project Council One',
            defaults={
                'council': self.council1,
                'program': self.program,
                'state': 'prospective'
            }
        )

        self.project2, created = Project.objects.get_or_create(
            name='Project Council Two',
            defaults={
                'council': self.council2,
                'program': self.program,
                'state': 'prospective'
            }
        )

        # Create users
        self.ricd_user = User.objects.create_user(
            username='ricd_user_test',
            email='ricd@test.com',
            password='test123'
        )
        ricd_group, _ = Group.objects.get_or_create(name='RICD Staff')
        self.ricd_user.groups.add(ricd_group)
        self.ricd_user.save()

        self.council1_user = User.objects.create_user(
            username='council1_user_test',
            email='council1@test.com',
            password='test123'
        )
        council_group, _ = Group.objects.get_or_create(name='Council User')
        self.council1_user.groups.add(council_group)
        UserProfile.objects.get_or_create(user=self.council1_user, defaults={'council': self.council1})

        self.council2_user = User.objects.create_user(
            username='council2_user_test',
            email='council2@test.com',
            password='test123'
        )
        self.council2_user.groups.add(council_group)
        UserProfile.objects.get_or_create(user=self.council2_user, defaults={'council': self.council2})

        self.factory = RequestFactory()

    def test_anonymous_access_blocked(self):
        """Test that anonymous users cannot access projects"""
        request = self.factory.get(f'/portal/project/{self.project1.pk}/')
        request.user = AnonymousUser()

        view = ProjectDetailView()
        view.request = request
        view.kwargs = {'pk': self.project1.pk}

        response = view.dispatch(request, pk=self.project1.pk)
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_ricd_user_can_access_any_project(self):
        """Test that RICD users can access any project"""
        request = self.factory.get(f'/portal/project/{self.project1.pk}/')
        request.user = self.ricd_user

        view = ProjectDetailView()
        view.request = request
        view.kwargs = {'pk': self.project1.pk}

        # Should not raise an exception
        response = view.dispatch(request, pk=self.project1.pk)
        self.assertIsNotNone(response)

        # Test accessing other council's project
        request = self.factory.get(f'/portal/project/{self.project2.pk}/')
        request.user = self.ricd_user
        view.kwargs = {'pk': self.project2.pk}

        response = view.dispatch(request, pk=self.project2.pk)
        self.assertIsNotNone(response)

    def test_council_user_can_access_own_project(self):
        """Test that council users can access their own council's projects"""
        request = self.factory.get(f'/portal/project/{self.project1.pk}/')
        request.user = self.council1_user

        view = ProjectDetailView()
        view.request = request
        view.kwargs = {'pk': self.project1.pk}

        # Should not raise an exception
        response = view.dispatch(request, pk=self.project1.pk)
        self.assertIsNotNone(response)

    def test_council_user_blocked_from_other_council_project(self):
        """Test that council users cannot access other councils' projects"""
        request = self.factory.get(f'/portal/project/{self.project2.pk}/')
        request.user = self.council1_user

        view = ProjectDetailView()
        view.request = request
        view.kwargs = {'pk': self.project2.pk}

        response = view.dispatch(request, pk=self.project2.pk)
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_council_project_detail_view_security(self):
        """Test CouncilProjectDetailView has same security controls"""
        # Council user can access own project
        request = self.factory.get(f'/portal/council/projects/{self.project1.pk}/detail/')
        request.user = self.council1_user

        view = CouncilProjectDetailView()
        view.request = request
        view.kwargs = {'pk': self.project1.pk}

        response = view.dispatch(request, pk=self.project1.pk)
        self.assertIsNotNone(response)

        # Council user blocked from other council project
        request = self.factory.get(f'/portal/council/projects/{self.project2.pk}/detail/')
        request.user = self.council1_user
        view.kwargs = {'pk': self.project2.pk}

        response = view.dispatch(request, pk=self.project2.pk)
        self.assertIsInstance(response, HttpResponseForbidden)

        # RICD user can access any council project
        request = self.factory.get(f'/portal/council/projects/{self.project2.pk}/detail/')
        request.user = self.ricd_user
        view.kwargs = {'pk': self.project2.pk}

        response = view.dispatch(request, pk=self.project2.pk)
        self.assertIsNotNone(response)

    def test_ricd_dashboard_redirects_council_users(self):
        """Test that RICD dashboard redirects council users to their council dashboard"""
        request = self.factory.get('/portal/ricd/')
        request.user = self.council1_user

        view = RICDDashboardView()
        view.request = request

        response = view.dispatch(request)
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/portal/council/', response['Location'])

    def test_ricd_dashboard_allows_ricd_users(self):
        """Test that RICD dashboard allows RICD users"""
        request = self.factory.get('/portal/ricd/')
        request.user = self.ricd_user

        view = RICDDashboardView()
        view.request = request

        response = view.dispatch(request)
        # Should not redirect or raise forbidden
        self.assertNotIsInstance(response, HttpResponseForbidden)
        if hasattr(response, 'status_code'):
            self.assertNotEqual(response.status_code, 302)
