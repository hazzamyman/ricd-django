from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create initial user groups for RICD system'

    def handle(self, *args, **options):
        self.stdout.write('Creating initial user groups...')

        groups_to_create = [
            'RICD Staff',
            'RICD Manager',
            'Council User',
            'Council Manager'
        ]

        for group_name in groups_to_create:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {group_name}'))
            else:
                self.stdout.write(f'Group already exists: {group_name}')

        self.stdout.write(self.style.SUCCESS('Initial groups created successfully.'))