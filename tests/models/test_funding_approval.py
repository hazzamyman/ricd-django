import pytest
from django.utils import timezone
from ricd.models import FundingApproval, Project, Council, Program


class TestFundingApproval:
    """Test funding approval creation and project linking"""

    @pytest.mark.django_db
    def test_funding_approval_creation(self):
        """Test that funding approval can be created successfully"""
        approval = FundingApproval.objects.create(
            mincor_reference="TEST123",
            amount=500000,
            approved_by_position="Division Manager",
            approved_date=timezone.now().date()
        )
        assert approval.mincor_reference == "TEST123"
        assert approval.amount == 500000
        assert approval.approved_by_position == "Division Manager"

    @pytest.mark.django_db
    def test_funding_approval_str_representation(self):
        """Test string representation of funding approval"""
        approval = FundingApproval.objects.create(
            mincor_reference="APPROVAL456",
            amount=750000,
            approved_by_position="State Director",
            approved_date=timezone.now().date()
        )
        expected = f"Approval APPROVAL456 - $750000"
        assert str(approval) == expected

    @pytest.mark.django_db
    def test_funding_approval_project_relationship(self):
        """Test linking funding approval to multiple projects"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        project1 = Project.objects.create(
            name="Project 1",
            council=council,
            program=program
        )
        project2 = Project.objects.create(
            name="Project 2",
            council=council,
            program=program
        )

        approval = FundingApproval.objects.create(
            mincor_reference="MULTI456",
            amount=1200000,
            approved_by_position="Regional Director",
            approved_date=timezone.now().date()
        )

        # Link projects to approval
        approval.projects.add(project1, project2)

        # Test reverse relationship
        assert approval.projects.count() == 2
        assert project1.funding_approvals.count() == 1
        assert project2.funding_approvals.count() == 1
        assert project1.funding_approvals.first() == approval
        assert project2.funding_approvals.first() == approval

        # Test filtering projects by funding approval
        projects_with_approval = Project.objects.filter(funding_approvals=approval)
        assert projects_with_approval.count() == 2
        assert project1 in projects_with_approval
        assert project2 in projects_with_approval

    @pytest.mark.django_db
    def test_funding_approval_projects_queryset(self):
        """Test that funding approval provides access to associated projects queryset"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")

        approval = FundingApproval.objects.create(
            mincor_reference="QUERY789",
            amount=300000,
            approved_by_position="Program Officer",
            approved_date=timezone.now().date()
        )

        project1 = Project.objects.create(
            name="Query Project 1",
            council=council,
            program=program
        )
        project2 = Project.objects.create(
            name="Query Project 2",
            council=council,
            program=program
        )

        approval.projects.add(project1, project2)

        # Test projects queryset access
        assert approval.projects.exists()
        assert approval.projects.filter(name__icontains="Query").count() == 2

        # Test ordering
        for i, project in enumerate(approval.projects.order_by('name')):
            assert f"Query Project {i+1}" == project.name

    @pytest.mark.django_db
    def test_empty_funding_approval_no_projects(self):
        """Test funding approval with no associated projects"""
        approval = FundingApproval.objects.create(
            mincor_reference="EMPTY001",
            amount=100000,
            approved_by_position="Officer",
            approved_date=timezone.now().date()
        )

        assert approval.projects.count() == 0
        assert not approval.projects.exists()

    @pytest.mark.django_db
    def test_project_funding_approval_reverse_relation(self):
        """Test that projects can access their funding approvals"""
        council = Council.objects.create(name="Test Council")
        program = Program.objects.create(name="Test Program")
        project = Project.objects.create(
            name="Project with Funding",
            council=council,
            program=program
        )

        approval1 = FundingApproval.objects.create(
            mincor_reference="REV1",
            amount=500000,
            approved_by_position="Manager",
            approved_date=timezone.now().date()
        )
        approval2 = FundingApproval.objects.create(
            mincor_reference="REV2",
            amount=300000,
            approved_by_position="Director",
            approved_date=timezone.now().date()
        )

        approval1.projects.add(project)
        approval2.projects.add(project)

        # Test reverse access from project
        assert project.funding_approvals.count() == 2
        funding_references = list(project.funding_approvals.values_list('mincor_reference', flat=True).order_by('mincor_reference'))
        assert funding_references == ['REV1', 'REV2']

        # Test total funding amounts
        total_funding = sum(project.funding_approvals.values_list('amount', flat=True))
        assert total_funding == 800000