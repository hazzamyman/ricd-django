from django.core.management.base import BaseCommand
from ricd.models import WorkType, OutputType, ConstructionMethod, Address, Work


class Command(BaseCommand):
    help = 'Populate WorkType and OutputType from existing choice values and migrate data'

    def handle(self, *args, **options):
        self.stdout.write('Creating Work Types...')

        # Work type choices from the original model
        work_types = [
            ('construction', 'Construction'),
            ('land_lot_development', 'Land Lot Development'),
            ('demolition', 'Demolition'),
            ('extension', 'Extension'),
            ('other', 'Other'),
        ]

        for code, name in work_types:
            work_type, created = WorkType.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True}
            )
            if created:
                self.stdout.write(f'  Created WorkType: {name}')
            else:
                self.stdout.write(f'  WorkType {name} already exists')

        # Output type choices from the original model
        output_types = [
            ('detached_house', 'Detached House'),
            ('unit', 'Self-contained Unit'),
            ('duplex', 'Duplex'),
            ('triplex', 'Triplex'),
            ('townhouse', 'Townhouse'),
            ('extension', 'Extension'),
            ('cluster_house', 'Cluster House'),
            ('consultancy', 'Consultancy'),
            ('other_expenses', 'Other Expenses'),
            ('demolition', 'Demolition'),
            ('lot', 'Lot'),
        ]

        for code, name in output_types:
            output_type, created = OutputType.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True}
            )
            if created:
                self.stdout.write(f'  Created OutputType: {name}')
            else:
                self.stdout.write(f'  OutputType {name} already exists')

        # Construction method choices from the original model
        construction_methods = [
            ('on_site', 'On Site'),
            ('flatpack', 'Flatpack'),
            ('modern_methods_of_construction', 'Modern Methods of Construction'),
            ('pre_built', 'Pre-built'),
            ('offsite', 'Offsite'),
        ]

        for code, name in construction_methods:
            construction_method, created = ConstructionMethod.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True}
            )
            if created:
                self.stdout.write(f'  Created ConstructionMethod: {name}')
            else:
                self.stdout.write(f'  ConstructionMethod {name} already exists')

        self.stdout.write('Migrating existing Address data...')

        # Address migration is handled in the migration file since we don't have existing data
        # but we'll show the logic here for completeness
        try:
            # Check if we have the required fields in the database
            if Address.objects.exists():
                addresses = Address.objects.all()
                for address in addresses:
                    if hasattr(address, 'work_type') and isinstance(address.work_type, str):
                        try:
                            work_type_obj = WorkType.objects.get(code=address.work_type)
                            address.work_type_id = work_type_obj
                        except WorkType.DoesNotExist:
                            self.stdout.write(f'Warning: Work type {address.work_type} not found')

                    if hasattr(address, 'output_type') and isinstance(address.output_type, str):
                        try:
                            output_type_obj = OutputType.objects.get(code=address.output_type)
                            address.output_type_id = output_type_obj
                        except OutputType.DoesNotExist:
                            self.stdout.write(f'Warning: Output type {address.output_type} not found')
                    address.save()
                self.stdout.write('Address data migration completed.')
            else:
                self.stdout.write('No existing address data to migrate.')
        except Exception as e:
            self.stdout.write(f'Skipping address migration due to database schema issues: {str(e)}')
            self.stdout.write('Address migration should be handled by Django migrations.')

        # Set up work type and output type relationships based on the provided requirements
        try:
            self.setup_work_output_relationships()
        except Exception as e:
            self.stdout.write(f'Skipping relationship setup due to database schema issues: {str(e)}')
            self.stdout.write('Relationships should be set up after running Django migrations.')

        self.stdout.write('Migration complete!')

    def setup_work_output_relationships(self):
        """Set up the relationships between work types and output types based on the table provided"""
        self.stdout.write('Setting up work type and output type relationships...')

        relationships = {
            'construction': [
                'detached_house', 'cluster_house', 'duplex', 'extension', 'unit', 'townhouse'
            ],
            'land_lot_development': ['lot'],
            'demolition': ['demolition'],
            'other': ['consultancy', 'other_expenses'],
        }

        for work_type_code, output_type_codes in relationships.items():
            try:
                work_type = WorkType.objects.get(code=work_type_code)
                output_types = OutputType.objects.filter(code__in=output_type_codes)

                work_type.allowed_output_types.clear()  # Clear existing relationships
                work_type.allowed_output_types.add(*output_types)

                self.stdout.write(f'  Set up {work_type.name}: {", ".join([ot.name for ot in output_types])}')

            except WorkType.DoesNotExist:
                self.stdout.write(f'  Warning: WorkType {work_type_code} not found')
            except OutputType.DoesNotExist as e:
                self.stdout.write(f'  Warning: Some output types not found: {e}')

        self.stdout.write('Work type and output type relationships set up successfully.')