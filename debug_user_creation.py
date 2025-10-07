#!/usr/bin/env python
"""
Debug script to test council user creation and verify database state.
Run this script to test user creation and check if users appear in the council detail page.
"""

import os
import sys
import django

# Add the testproj directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'testproj'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings')
django.setup()

from django.contrib.auth.models import User, Group
from ricd.models import Council, UserProfile
from portal.forms import CouncilUserCreationForm

def test_user_creation():
    """Test council user creation and verify database state"""

    print("=== Council User Creation Debug Test ===\n")

    # Get or create test council
    council, created = Council.objects.get_or_create(
        name="Test Council for User Creation",
        defaults={
            'abn': '12345678901',
            'default_suburb': 'Test Suburb',
            'default_state': 'QLD'
        }
    )
    print(f"Test Council: {council.name} (ID: {council.pk})")

    # Create test RICD user for creating council users
    ricd_user, created = User.objects.get_or_create(
        username='test_ricd_user',
        defaults={
            'email': 'ricd@test.com',
            'first_name': 'Test',
            'last_name': 'RICD User',
            'is_active': True
        }
    )

    # Add to RICD Staff group
    ricd_group, _ = Group.objects.get_or_create(name='RICD Staff')
    ricd_user.groups.add(ricd_group)
    print(f"RICD User: {ricd_user.username} (ID: {ricd_user.pk})")

    # Test form creation
    form_data = {
        'username': 'test_council_user',
        'first_name': 'Test',
        'last_name': 'Council User',
        'email': 'council@test.com',
        'password1': 'testpassword123',
        'password2': 'testpassword123',
        'council': council.pk,
        'role': 'council_user',
        'is_active': True
    }

    print(f"\nForm data: {form_data}")

    # Create form instance
    form = CouncilUserCreationForm(data=form_data, user=ricd_user)

    if form.is_valid():
        print("\nForm is valid. Creating user...")

        try:
            user = form.save()
            print(f"✓ User created successfully!")
            print(f"  Username: {user.username}")
            print(f"  ID: {user.pk}")
            print(f"  Email: {user.email}")

            # Check UserProfile
            if hasattr(user, 'profile'):
                print(f"✓ UserProfile exists")
                print(f"  Council: {user.profile.council}")
            else:
                print("✗ UserProfile NOT found")

            # Check groups
            groups = list(user.groups.values_list('name', flat=True))
            print(f"✓ User groups: {groups}")

            # Verify council relationship
            council_users = council.users.all()
            user_in_council = council_users.filter(user=user).exists()
            print(f"✓ User in council.users: {user_in_council}")

            # Count total council users
            total_council_users = council_users.count()
            print(f"✓ Total council users: {total_council_users}")

            return True

        except Exception as e:
            print(f"✗ Error creating user: {str(e)}")
            return False
    else:
        print(f"\nForm is NOT valid. Errors:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False

def check_database_state():
    """Check the current state of the database"""

    print("\n=== Database State Check ===\n")

    # Check councils
    councils = Council.objects.all()
    print(f"Total councils: {councils.count()}")

    for council in councils[:5]:  # Show first 5
        users_count = council.users.count()
        print(f"  {council.name}: {users_count} users")

    # Check users
    users = User.objects.all()
    print(f"\nTotal users: {users.count()}")

    # Check users with profiles
    users_with_profiles = User.objects.filter(profile__isnull=False)
    print(f"Users with profiles: {users_with_profiles.count()}")

    # Check groups
    groups = Group.objects.all()
    print(f"\nGroups: {[g.name for g in groups]}")

if __name__ == '__main__':
    print("Starting council user creation debug test...\n")

    # Test user creation
    success = test_user_creation()

    # Check database state
    check_database_state()

    if success:
        print("\n🎉 Test completed successfully!")
        print("\nIf users are still not appearing in the council detail page:")
        print("1. Check Django admin for the user")
        print("2. Verify the user groups are correct")
        print("3. Check if there are any permission issues")
        print("4. Look at the Django logs for any errors")
    else:
        print("\n❌ Test failed. Check the error messages above.")

    print("\nDebug logging has been added to the form and view.")
    print("Check your Django logs when running the application for detailed debug information.")