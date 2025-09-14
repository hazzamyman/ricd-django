import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from ricd.models import Council, Program, Project, WorkType, OutputType, Address, Work, QuarterlyReport


class TestRICDDashboardView:
    """Test RIC D Dashboard View and analytics functions"""

    @pytest.mark.django_db
    def test_ricd_dashboard_returns_200(self):
        """Test that RIC D dashboard returns 200 status"""
        from ricd.models import Council, Program, Project, Address, Work, QuarterlyReport
        from ricd.models import WorkType, OutputType

        client = Client()

        # Create basic data
        council = Council.objects.create(name="Test Council", abn="12345678910")
        program = Program.objects.create(name="Test Program", budget=1000000)
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=timezone.now().date()
        )

        # Create work type and output type
        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)
        output_type = OutputType.objects.create(name="House", code="HOUSE", is_active=True)

        # Create address and work
        address = Address.objects.create(
            project=project,
            street="123 Main Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=work_type,
            output_type_id=output_type
        )
        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type,
            output_quantity=1
        )

        # Create quarterly report
        QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=25.0,
            submission_date=timezone.now().date(),
            total_expenditure_council=25000
        )

        # Test GET request to dashboard
        url = reverse('portal:ricd_dashboard')
        response = client.get(url)

        # Should return 200 OK (no exception)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_project_progress_with_valid_data(self):
        """Test get_project_progress returns numeric percent"""
        from portal.views import RICDDashboardView

        view = RICDDashboardView()

        # Create test data similar to above
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=timezone.now().date()
        )

        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)
        output_type = OutputType.objects.create(name="House", code="HOUSE", is_active=True)

        address = Address.objects.create(
            project=project,
            street="123 Main Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=work_type,
            output_type_id=output_type
        )
        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type
        )

        # Create quarterly reports
        QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=30.0,
            submission_date=timezone.now().date()
        )
        QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=40.0,
            submission_date=timezone.now().date() + timezone.timedelta(days=1)
        )

        # Test get_project_progress method
        progress_percentage = view.get_project_progress(project)

        # Should return a valid number between 0 and 100
        assert isinstance(progress_percentage, (int, float))
        assert 0 <= progress_percentage <= 100

    @pytest.mark.django_db
    def test_get_project_progress_with_no_reports(self):
        """Test get_project_progress returns 0 when no reports exist"""
        from portal.views import RICDDashboardView

        view = RICDDashboardView()

        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project with No Reports",
            council=council,
            program=program
        )

        progress_percentage = view.get_project_progress(project)
        assert progress_percentage == 0

    @pytest.mark.django_db
    def test_get_project_progress_with_null_percentages(self):
        """Test get_project_progress handles null percentage values"""
        from portal.views import RICDDashboardView

        view = RICDDashboardView()

        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program
        )

        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)
        output_type = OutputType.objects.create(name="House", code="HOUSE", is_active=True)

        address = Address.objects.create(
            project=project,
            street="123 Main Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD",
            work_type_id=work_type,
            output_type_id=output_type
        )
        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type
        )

        # Create report with None percentage
        QuarterlyReport.objects.create(
            work=work,
            percentage_works_completed=None,
            submission_date=timezone.now().date()
        )

        progress_percentage = view.get_project_progress(project)
        assert progress_percentage == 0

    @pytest.mark.django_db
    def test_multiple_projects_in_dashboard(self):
        """Test dashboard handles multiple projects correctly"""
        client = Client()

        # Create multiple projects
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)
        output_type = OutputType.objects.create(name="House", code="HOUSE", is_active=True)

        for i in range(3):
            project = Project.objects.create(
                name=f"Test Project {i}",
                council=council,
                program=program,
                start_date=timezone.now().date() - timezone.timedelta(days=i*30)
            )

            address = Address.objects.create(
                project=project,
                street=f"12{i} Main Street",
                suburb="Test Suburb",
                postcode="4000",
                state="QLD",
                work_type_id=work_type,
                output_type_id=output_type
            )
            work = Work.objects.create(
                address=address,
                work_type_id=work_type,
                output_type_id=output_type
            )

            QuarterlyReport.objects.create(
                work=work,
                percentage_works_completed=20 + i*20,
                submission_date=timezone.now().date()
            )

        url = reverse('portal:ricd_dashboard')
        response = client.get(url)

        assert response.status_code == 200
        # Should contain projects data in context
        assert 'projects' in response.context
        assert len(response.context['projects']) == 3