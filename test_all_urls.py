#!/usr/bin/env python3
"""
Comprehensive URL testing script for Django application.
This script tests all URLs systematically to identify operational errors.
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings')

def test_url_patterns():
    """Test URL patterns without running the server"""
    try:
        django.setup()

        from django.urls import reverse, resolve, Resolver404
        from django.conf import settings
        from portal.urls import urlpatterns

        print("🔍 Testing Django URL Configuration...\n")

        # Test URL patterns that should exist
        test_urls = [
            # Dashboard URLs
            ('portal:ricd_dashboard', {}),
            ('portal:council_dashboard', {}),

            # Project URLs
            ('portal:project_list', {}),
            ('portal:project_create', {}),

            # Work Type URLs
            ('portal:work_type_list', {}),
            ('portal:work_type_create', {}),

            # Output Type URLs
            ('portal:output_type_list', {}),
            ('portal:output_type_create', {}),

            # Construction Method URLs
            ('portal:construction_method_list', {}),
            ('portal:construction_method_create', {}),

            # Work Output Config URL
            ('portal:work_output_type_config', {}),

            # Council URLs
            ('portal:council_list', {}),
            ('portal:council_create', {}),

            # Program URLs
            ('portal:program_list', {}),
            ('portal:program_create', {}),

            # User URLs
            ('portal:user_list', {}),
            ('portal:user_create', {}),

            # Officer URLs
            ('portal:officer_list', {}),
            ('portal:officer_create', {}),
        ]

        success_count = 0
        error_count = 0

        for url_name, kwargs in test_urls:
            try:
                url = reverse(url_name, kwargs=kwargs)
                resolved = resolve(url)
                print(f"✅ {url_name}: {url} -> {resolved.view_name}")
                success_count += 1
            except Exception as e:
                print(f"❌ {url_name}: Error - {str(e)}")
                error_count += 1

        print(f"\n📊 URL Test Results:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Errors: {error_count}")

        if error_count == 0:
            print("🎉 All URL patterns are correctly configured!")
        else:
            print("⚠️  Some URL patterns have issues that need to be fixed.")

    except Exception as e:
        print(f"❌ Error setting up Django: {str(e)}")
        print("This likely means Django isn't properly configured or the migration hasn't been applied.")

def test_database_schema():
    """Test database schema for potential issues"""
    try:
        django.setup()

        from django.db import connection
        from ricd.models import Work, Address, ConstructionMethod

        print("\n🔍 Testing Database Schema...\n")

        # Test if tables exist
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names()
            required_tables = ['ricd_work', 'ricd_address', 'ricd_constructionmethod']

            missing_tables = []
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)

            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables exist")

        # Test column existence
        with connection.cursor() as cursor:
            # Check Work table columns
            columns = connection.introspection.get_table_description(cursor, 'ricd_work')
            column_names = [col.name for col in columns]

            required_work_columns = ['id', 'construction_method_id']
            missing_work_columns = []

            for col in required_work_columns:
                if col not in column_names:
                    missing_work_columns.append(col)

            if missing_work_columns:
                print(f"❌ Missing columns in ricd_work table: {missing_work_columns}")
                print("The migration 0022_alter_work_construction_method needs to be applied.")
                return False
            else:
                print("✅ ricd_work table has correct construction_method_id column")

        # Test ConstructionMethod model
        try:
            cm_count = ConstructionMethod.objects.count()
            print(f"✅ ConstructionMethod model accessible ({cm_count} records)")
        except Exception as e:
            print(f"❌ ConstructionMethod model error: {str(e)}")
            return False

        print("🎉 Database schema looks good!")
        return True

    except Exception as e:
        print(f"❌ Database schema test failed: {str(e)}")
        return False

def generate_test_commands():
    """Generate commands to test the URLs manually"""
    print("\n🧪 Manual Testing Commands:")
    print("=" * 50)
    print("# 1. Apply the migration:")
    print("python manage.py migrate ricd 0022")
    print()
    print("# 2. Test the maintenance pages:")
    print("curl -s http://localhost:8000/portal/maintenance/construction-methods/ | head -20")
    print("curl -s http://localhost:8000/portal/maintenance/work-output-config/ | head -20")
    print()
    print("# 3. Test project detail page (previously broken):")
    print("curl -s http://localhost:8000/portal/projects/1/detail/ | head -20")
    print()
    print("# 4. Check Django URL patterns:")
    print("python manage.py shell -c \"from django.urls import reverse; print(reverse('portal:construction_method_list'))\"")
    print("python manage.py shell -c \"from django.urls import reverse; print(reverse('portal:work_output_type_config'))\"")
    print("=" * 50)

if __name__ == '__main__':
    print("🚀 Django Application URL and Database Testing")
    print("=" * 55)

    # Test URL patterns
    test_url_patterns()

    # Test database schema
    schema_ok = test_database_schema()

    # Generate manual test commands
    generate_test_commands()

    print("\n" + "=" * 55)
    if schema_ok:
        print("🎯 Next Steps:")
        print("1. Start Django server: python manage.py runserver")
        print("2. Visit the maintenance pages to verify they work")
        print("3. Test navigation links in the Management dropdown")
    else:
        print("🔧 Issues Found:")
        print("1. Apply the migration: python manage.py migrate ricd 0022")
        print("2. Restart Django server")
        print("3. Retest the URLs")

    print("=" * 55)