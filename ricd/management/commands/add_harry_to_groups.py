from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Add user harry to Council User and Council Manager groups'

    def handle(self, *args, **options):
        try:
            # Get or create user harry
            user, created = User.objects.get_or_create(
                username='harry',
                defaults={
                    'first_name': 'Harry',
                    'last_name': 'Test',
                    'email': 'harry@example.com'
                }
            )

            if created:
                # Set a default password
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

            # Get the groups
            council_user_group = Group.objects.get(name='Council User')
            council_manager_group = Group.objects.get(name='Council Manager')

            # Add user to both groups
            user.groups.add(council_user_group, council_manager_group)
            user.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully added {user.username} to Council User and Council Manager groups'))

        except Group.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Group not found: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))