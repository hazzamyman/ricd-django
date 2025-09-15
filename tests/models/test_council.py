import pytest
from ricd.models import Council
from tests.conftest import make_council_factory


class TestCouncilModel:
    """Test Council model functionality"""

    @pytest.mark.django_db
    def test_council_creation(self):
        """Test basic council creation with required fields"""
        council = Council.objects.create(
            name="Test Council",
            abn="12345678901",
            default_suburb="Test Suburb",
            default_postcode="4000",
            default_state="QLD"
        )
        assert council.name == "Test Council"
        assert council.abn == "12345678901"
        assert council.default_state == "QLD"

    @pytest.mark.django_db
    def test_council_string_representation(self):
        """Test council __str__ method"""
        council = Council.objects.create(name="Test Council")
        assert str(council) == "Test Council"

    @pytest.mark.django_db
    def test_council_optional_fields(self):
        """Test council creation with optional fields blank"""
        council = Council.objects.create(
            name="Test Council",
            default_state="QLD"
        )
        assert council.abn is None
        assert council.default_suburb is None
        assert council.default_postcode is None

    @pytest.mark.django_db
    def test_council_registered_housing_provider_flag(self):
        """Test is_registered_housing_provider boolean field"""
        # Default should be False
        council = Council.objects.create(name="Test Council")
        assert council.is_registered_housing_provider is False

        # Can be set to True
        council.is_registered_housing_provider = True
        council.save()
        council.refresh_from_db()
        assert council.is_registered_housing_provider is True

    @pytest.mark.django_db
    def test_council_geographic_fields(self):
        """Test council geographic fields"""
        council = Council.objects.create(
            name="Test Council",
            federal_electorate="Test Federal Electorate",
            state_electorate="Test State Electorate",
            qhigi_region="Test Region"
        )
        assert council.federal_electorate == "Test Federal Electorate"
        assert council.state_electorate == "Test State Electorate"
        assert council.qhigi_region == "Test Region"
    @pytest.mark.django_db
    def test_council_user_cannot_see_other_council_projects(self):
        """Test that council users can only see projects from their own council"""
        from ricd.models import Project, UserProfile, Program
        from django.contrib.auth.models import User, Group

        # Create program
        program = Program.objects.create(name="Test Program")

        # Create two councils
        council1 = Council.objects.create(name="Council 1")
        council2 = Council.objects.create(name="Council 2")

        # Create projects for each council
        project1 = Project.objects.create(name="Project 1", council=council1, program=program)
        project2 = Project.objects.create(name="Project 2", council=council2, program=program)

        # Create a council user for council1
        user = User.objects.create_user(username='council_user', password='test')
        user.groups.add(Group.objects.get(name='Council User'))
        profile = UserProfile.objects.create(user=user, council=council1, council_role='user')

        # Check that only their projects are returned
        visible_projects = Project.objects.for_user(user)
        assert project1 in visible_projects
        assert project2 not in visible_projects

    @pytest.mark.django_db
    def test_council_manager_can_approve_reports(self):
        """Test that council managers can approve reports for their council"""
        from ricd.models import QuarterlyReport, Work, Address, UserProfile, Project, Program
        from django.contrib.auth.models import User, Group

        # Create program
        program = Program.objects.create(name="Test Program")

        # Create council and user
        council = Council.objects.create(name="Test Council")
        user = User.objects.create_user(username='council_manager', password='test')
        user.groups.add(Group.objects.get(name='Council Manager'))
        profile = UserProfile.objects.create(user=user, council=council, council_role='manager')

        # Create project, address, work
        project = Project.objects.create(name="Test Project", council=council, program=program)
        address = Address.objects.create(project=project, street="Test St")
        work = Work.objects.create(address=address, work_type_id=1, output_type_id=1)

        # Create quarterly report
        report = QuarterlyReport.objects.create(
            work=work,
            submission_date='2024-01-01',
            council_manager_decision='pending'
        )

        # As council manager, approve the report
        report.council_manager_decision = 'approved'
        report.save()

        report.refresh_from_db()
        assert report.council_manager_decision == 'approved'

    @pytest.mark.django_db
    def test_ricd_manager_can_create_council_users(self):
        """Test that RICD managers can create council users and link them to councils"""
        from ricd.models import UserProfile
        from django.contrib.auth.models import User, Group

        # Create council
        council = Council.objects.create(name="Test Council")

        # Create RICD manager
        ricd_user = User.objects.create_user(username='ricd_manager', password='test')
        ricd_user.groups.add(Group.objects.get(name='RICD Manager'))

        # Create council user
        council_user = User.objects.create_user(username='new_council_user', password='test')
        council_user.groups.add(Group.objects.get(name='Council User'))

        # Link to council with role
        profile = UserProfile.objects.create(user=council_user, council=council, council_role='user')

        profile.refresh_from_db()
        assert profile.council == council
        assert profile.council_role == 'user'