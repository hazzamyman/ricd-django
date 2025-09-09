from django.core.management.base import BaseCommand
from ricd.models import WorkType, OutputType, Address, Work


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

        self.stdout.write('Migrating existing Address data...')

        # Address migration is handled in the migration file since we don't have existing data
        # but we'll show the logic here for completeness
        addresses = Address.objects.all()
        for address in addresses:
            if hasattr(address, 'work_type') and isinstance(address.work_type, str):
                try:
                    work_type_obj = WorkType.objects.get(code=address.work_type)
                    address.work_type_id = work_type_obj.id
                except WorkType.DoesNotExist:
                    self.stdout.write(f'Warning: Work type {address.work_type} not found')

            if hasattr(address, 'output_type') and isinstance(address.output_type, str):
                try:
                    output_type_obj = OutputType.objects.get(code=address.output_type)
                    address.output_type_id = output_type_obj.id
                except OutputType.DoesNotExist:
                    self.stdout.write(f'Warning: Output type {address.output_type} not found')
            address.save()

        self.stdout.write('Migration complete!')