import pytest
from django.test import Client

def make_council_factory():
    import factory
    from ricd.models import Council
    class CouncilFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Council
        name = factory.Sequence(lambda n: f"Council {n}")
        abn = factory.Sequence(lambda n: f"1234{n:06}56789")
        default_suburb = factory.Sequence(lambda n: f"Suburb {n}")
        default_postcode = "4000"
        default_state = "QLD"
    return CouncilFactory

def make_program_factory():
    import factory
    from ricd.models import Program
    class ProgramFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Program
        name = factory.Sequence(lambda n: f"Program {n}")
        budget = 1000000
    return ProgramFactory

def make_work_type_factory():
    import factory
    from ricd.models import WorkType
    class WorkTypeFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = WorkType
        name = factory.Sequence(lambda n: f"WorkType {n}")
        code = factory.Sequence(lambda n: f"WT{n}")
        is_active = True
    return WorkTypeFactory

def make_output_type_factory():
    import factory
    from ricd.models import OutputType
    class OutputTypeFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = OutputType
        name = factory.Sequence(lambda n: f"OutputType {n}")
        code = factory.Sequence(lambda n: f"OT{n}")
        is_active = True
    return OutputTypeFactory

def make_project_factory():
    import factory
    from ricd.models import Project
    CouncilFactory = make_council_factory()
    ProgramFactory = make_program_factory()
    class ProjectFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Project
        name = factory.Sequence(lambda n: f"Test Project {n}")
        council = factory.SubFactory(CouncilFactory)
        program = factory.SubFactory(ProgramFactory)
        start_date = factory.Faker('date_past')
    return ProjectFactory

def make_address_factory():
    import factory
    from ricd.models import Address
    ProjectFactory = make_project_factory()
    WorkTypeFactory = make_work_type_factory()
    OutputTypeFactory = make_output_type_factory()
    class AddressFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Address
        project = factory.SubFactory(ProjectFactory)
        street = factory.Sequence(lambda n: f"Street {n}")
        suburb = "Test Suburb"
        postcode = "4000"
        state = "QLD"
        work_type_id = factory.SubFactory(WorkTypeFactory)
        output_type_id = factory.SubFactory(OutputTypeFactory)
    return AddressFactory

def make_work_factory():
    import factory
    from ricd.models import Work
    AddressFactory = make_address_factory()
    WorkTypeFactory = make_work_type_factory()
    OutputTypeFactory = make_output_type_factory()
    class WorkFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Work
        address = factory.SubFactory(AddressFactory)
        work_type_id = factory.SubFactory(WorkTypeFactory)
        output_type_id = factory.SubFactory(OutputTypeFactory)
    return WorkFactory

def make_quarterly_report_factory():
    import factory
    from ricd.models import QuarterlyReport
    WorkFactory = make_work_factory()
    class QuarterlyReportFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = QuarterlyReport
        work = factory.SubFactory(WorkFactory)
        percentage_works_completed = factory.Faker('pyfloat', min_value=0, max_value=100)
        submission_date = factory.Faker('date_recent')
    return QuarterlyReportFactory


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def council():
    return make_council_factory()()


@pytest.fixture
def program():
    return make_program_factory()()


@pytest.fixture
def project(council, program):
    ProjectFactory = make_project_factory()
    return ProjectFactory(council=council, program=program)


@pytest.fixture
def address(project):
    AddressFactory = make_address_factory()
    return AddressFactory(project=project)


@pytest.fixture
def work(address):
    WorkFactory = make_work_factory()
    return WorkFactory(address=address)


@pytest.fixture
def quarterly_report(work):
    QuarterlyReportFactory = make_quarterly_report_factory()
    return QuarterlyReportFactory(work=work)