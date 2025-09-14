import pytest
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from ricd.models import Council, Program, Project


class TestProjectDateDefaults:
    """Test that project stage dates are calculated correctly"""

    @pytest.mark.django_db
    def test_stage1_target_default_calculation(self):
        """Test stage1_target = start_date + 12 months"""
        from ricd.models import Council, Program, Project
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date = timezone.now().date()
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date
        )
        expected = start_date + relativedelta(months=12)
        assert project.stage1_target == expected

    @pytest.mark.django_db
    def test_stage1_sunset_default_calculation(self):
        """Test stage1_sunset = start_date + 18 months"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date = timezone.now().date()
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date
        )
        expected = start_date + relativedelta(months=18)
        assert project.stage1_sunset == expected

    @pytest.mark.django_db
    def test_stage2_target_default_calculation(self):
        """Test stage2_target = stage1_target + 12 months or start_date + 24 months"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date = timezone.now().date()
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date
        )
        expected = start_date + relativedelta(months=24)
        assert project.stage2_target == expected

    @pytest.mark.django_db
    def test_stage2_sunset_default_calculation(self):
        """Test stage2_sunset = stage1_sunset + 12 months or start_date + 30 months"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date = timezone.now().date()
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date
        )
        expected = start_date + relativedelta(months=30)
        assert project.stage2_sunset == expected

    @pytest.mark.django_db
    def test_manual_stage_dates_override_defaults(self):
        """Test that manually setting stage dates overrides calculations"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date = timezone.now().date()
        manual_stage1_target = start_date + timedelta(days=400)
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date,
            stage1_target=manual_stage1_target
        )
        assert project.stage1_target == manual_stage1_target
        # stage2_target should be based on manual stage1_target
        expected_stage2_target = manual_stage1_target + relativedelta(months=12)
        assert project.stage2_target == expected_stage2_target

    @pytest.mark.django_db
    def test_no_start_date_no_stage_dates(self):
        """Test that projects without start_date have no stage dates"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program
        )
        assert project.stage1_target is None
        assert project.stage1_sunset is None
        assert project.stage2_target is None
        assert project.stage2_sunset is None

    @pytest.mark.django_db
    def test_save_method_updates_dates_on_start_date_change(self):
        """Test that changing start_date recalculates stage dates on save"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        start_date1 = timezone.now().date()
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program,
            start_date=start_date1
        )
        start_date2 = start_date1 + relativedelta(months=5)
        project.start_date = start_date2
        project.save()
        assert project.stage1_target == start_date2 + relativedelta(months=12)
        assert project.stage1_sunset == start_date2 + relativedelta(months=18)