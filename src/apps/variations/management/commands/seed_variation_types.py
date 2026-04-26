from django.core.management.base import BaseCommand
from apps.variations.models import VariationType


class Command(BaseCommand):
    help = 'Seed variation type templates'

    def handle(self, *args, **options):
        variation_types = [
            {
                'option_number': 'Option 1',
                'name': 'Add Funding Schedule',
                'description': 'Adding a new Funding Schedule to the Funding Agreement'
            },
            {
                'option_number': 'Option 2',
                'name': 'Remove Funding Schedule',
                'description': 'Terminating and removing a Funding Schedule from the Funding Agreement'
            },
            {
                'option_number': 'Option 3',
                'name': "Change Contact Details",
                'description': "Changing the State's or Council's contact details"
            },
            {
                'option_number': 'Option 4',
                'name': 'Replace Funding Schedule',
                'description': 'Replacing an original Funding Schedule with a replacement'
            },
            {
                'option_number': 'Option 5',
                'name': 'Vary Funding Schedule Dates',
                'description': 'Varying dates such as Stage 1 Target Date or Stage 2 Target Date'
            },
            {
                'option_number': 'Option 6',
                'name': 'Vary Scope of Works',
                'description': 'Varying Item 5 - Scope of Works in the Funding Schedule'
            },
            {
                'option_number': 'Option 7',
                'name': 'Vary Land',
                'description': 'Varying the land details (Lot, Plan, Title Reference, Address)'
            },
            {
                'option_number': 'Option 8',
                'name': 'Vary Funding',
                'description': 'Varying Item 3 and Payments - changing funding amounts and payment schedules'
            },
            {
                'option_number': 'Option 9',
                'name': 'Vary Reporting Requirements',
                'description': 'Varying Clause 9 - changing reporting requirements'
            },
            {
                'option_number': 'Option Other',
                'name': 'Other Variation',
                'description': 'Custom variation not covered by standard options'
            },
        ]
        
        for vt_data in variation_types:
            vt, created = VariationType.objects.get_or_create(
                option_number=vt_data['option_number'],
                defaults=vt_data
            )
            if created:
                self.stdout.write(f'Created: {vt}')
            else:
                self.stdout.write(f'Already exists: {vt}')
        
        self.stdout.write(self.style.SUCCESS('Done seeding variation types'))
