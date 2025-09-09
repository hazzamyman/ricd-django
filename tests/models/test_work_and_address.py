import pytest
from ricd.models import Address, Work, Council, Program, Project, WorkType, OutputType


class TestWorkAndAddress:
    """Test work and address creation, relationships, and calculations"""

    @pytest.mark.django_db
    def test_project_creation(self):
        """Test basic project creation"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program
        )
        assert project.name == "Test Project"
        assert project.council == council
        assert project.program == program

    @pytest.mark.django_db
    def test_address_creation(self):
        """Test address creation linked to project"""
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
            output_type_id=output_type,
            bedrooms=3
        )

        assert address.project == project
        assert address.street == "123 Main Street"
        assert address.work_type_id == work_type
        assert address.output_type_id == output_type

        # Test reverse relationship through project
        assert project.addresses.count() == 1
        assert project.addresses.first() == address

    @pytest.mark.django_db
    def test_work_creation(self):
        """Test work creation linked to address"""
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
            output_type_id=output_type,
            bedrooms=3
        )

        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type,
            output_quantity=1,
            bedrooms=3
        )

        assert work.address == address
        assert work.work_type_id == work_type
        assert work.output_type_id == output_type

        # Test reverse relationship
        assert address.works.count() == 1
        assert address.works.first() == work

        # Test project access through work
        assert work.project == project

    @pytest.mark.django_db
    def test_work_total_dwellings_calculation(self):
        """Test total dwellings calculation for different output types"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program
        )
        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)

        # Test house (default)
        output_type_house = OutputType.objects.create(name="House", code="HOUSE", is_active=True)
        address = Address.objects.create(
            project=project,
            street="123 Main Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD"
        )

        work_house = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type_house,
            output_quantity=1
        )
        assert work_house.total_dwellings == 1

        # Test duplex
        output_type_duplex = OutputType.objects.create(name="Duplex", code="duplex", is_active=True)
        work_duplex = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type_duplex,
            output_quantity=1
        )
        assert work_duplex.total_dwellings == 2

        # Test triplex
        output_type_triplex = OutputType.objects.create(name="Triplex", code="triplex", is_active=True)
        work_triplex = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type_triplex,
            output_quantity=1
        )
        assert work_triplex.total_dwellings == 3

    @pytest.mark.django_db
    def test_work_total_bedrooms_calculation(self):
        """Test total bedrooms calculation"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Test Project",
            council=council,
            program=program
        )
        work_type = WorkType.objects.create(name="New Dwelling", code="ND", is_active=True)
        output_type_duplex = OutputType.objects.create(name="Duplex", code="duplex", is_active=True)
        address = Address.objects.create(
            project=project,
            street="123 Main Street",
            suburb="Test Suburb",
            postcode="4000",
            state="QLD"
        )

        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type_duplex,
            output_quantity=1,
            bedrooms=3  # 3 bedrooms per unit
        )

        # Should be 3 bedrooms × 2 units (duplex)
        assert work.total_bedrooms == 6

    @pytest.mark.django_db
    def test_work_string_representation(self):
        """Test work string representation"""
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
            state="QLD"
        )

        work = Work.objects.create(
            address=address,
            work_type_id=work_type,
            output_type_id=output_type
        )

        expected = f"{work_type.name} - {output_type.name} ({address})"
        assert str(work) == expected

    @pytest.mark.django_db
    def test_address_string_representation(self):
        """Test address string representation with work details"""
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
            output_type_id=output_type,
            bedrooms=3,
            output_quantity=1
        )

        expected_parts = ["123 Main Street", "Test Suburb • House • 3BR"]
        assert " • ".join(expected_parts[1:]) in str(address)