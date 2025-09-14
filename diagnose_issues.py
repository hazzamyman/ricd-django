#!/usr/bin/env python3
"""
Diagnostic script to help identify Django application issues.
This script can run without Django being installed.
"""
import os
import json

def check_migration_status():
    """Check if the migration file exists and is properly structured"""
    migration_file = 'ricd/migrations/0022_alter_work_construction_method.py'

    print("🔍 Checking Migration File...")
    print("=" * 50)

    if os.path.exists(migration_file):
        with open(migration_file, 'r') as f:
            content = f.read()

        # Check for required elements
        checks = {
            'Django migration imports': 'from django.db import migrations, models' in content,
            'Migration class': 'class Migration(migrations.Migration):' in content,
            'Dependencies': "'ricd', '0021_constructionmethod_alter_address_construction_method_and_more'" in content,
            'AlterField operation': 'migrations.AlterField(' in content,
            'Work model reference': "model_name='work'" in content,
            'Construction method field': "name='construction_method'" in content,
            'ForeignKey field type': 'models.ForeignKey(' in content,
            'ConstructionMethod reference': "'ConstructionMethod'" in content,
            'on_delete=SET_NULL': 'on_delete=models.SET_NULL' in content,
            'null=True': 'null=True' in content,
            'blank=True': 'blank=True' in content,
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 Migration file is correctly structured!")
            return True
        else:
            print("\n❌ Migration file has issues that need to be fixed.")
            return False
    else:
        print("❌ Migration file not found!")
        return False

def check_navigation_links():
    """Check if navigation links are properly added"""
    nav_file = 'portal/templates/portal/base.html'

    print("\n🔍 Checking Navigation Links...")
    print("=" * 50)

    if os.path.exists(nav_file):
        with open(nav_file, 'r') as f:
            content = f.read()

        checks = {
            'Construction methods link': 'portal:construction_method_list' in content,
            'Work output config link': 'portal:work_output_type_config' in content,
            'Maintenance section': 'Maintenance' in content,
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 Navigation links are properly configured!")
            return True
        else:
            print("\n❌ Navigation links have issues.")
            return False
    else:
        print("❌ Navigation file not found!")
        return False

def check_url_patterns():
    """Check if URL patterns are properly configured"""
    url_file = 'portal/urls.py'

    print("\n🔍 Checking URL Patterns...")
    print("=" * 50)

    if os.path.exists(url_file):
        with open(url_file, 'r') as f:
            content = f.read()

        checks = {
            'Construction method list URL': "path('maintenance/construction-methods/'," in content,
            'Construction method create URL': "path('maintenance/construction-methods/create/'," in content,
            'Work output config URL': "path('maintenance/work-output-config/'," in content,
            'Construction method list view': 'ConstructionMethodListView' in content,
            'Work output config view': 'WorkOutputTypeConfigView' in content,
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 URL patterns are properly configured!")
            return True
        else:
            print("\n❌ URL patterns have issues.")
            return False
    else:
        print("❌ URL file not found!")
        return False

def generate_fix_commands():
    """Generate the exact commands to fix the issues"""
    print("\n🛠️  Commands to Fix Issues:")
    print("=" * 50)

    commands = [
        "# 1. Apply the database migration (run in Django environment):",
        "python manage.py migrate ricd 0022",
        "",
        "# 2. Check migration status:",
        "python manage.py showmigrations ricd",
        "",
        "# 3. Test the URLs after migration:",
        "python manage.py shell -c \"from django.urls import reverse; print('Construction methods:', reverse('portal:construction_method_list')); print('Work output config:', reverse('portal:work_output_type_config'))\"",
        "",
        "# 4. Start Django server:",
        "python manage.py runserver",
        "",
        "# 5. Test the pages in browser:",
        "# Visit: http://localhost:8000/portal/maintenance/construction-methods/",
        "# Visit: http://localhost:8000/portal/maintenance/work-output-config/",
        "# Visit: http://localhost:8000/portal/projects/1/detail/  (previously broken)",
        "",
        "# 6. If migration fails, try force apply:",
        "python manage.py migrate --run-syncdb",
    ]

    for command in commands:
        print(command)

def main():
    """Main diagnostic function"""
    print("🔧 Django Application Diagnostic Tool")
    print("=" * 50)
    print("This tool checks if all components are properly configured.")
    print()

    # Run all checks
    migration_ok = check_migration_status()
    nav_ok = check_navigation_links()
    url_ok = check_url_patterns()

    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary:")

    all_ok = migration_ok and nav_ok and url_ok

    if all_ok:
        print("✅ All components are properly configured!")
        print("The 404 error is likely due to the migration not being applied.")
        print("Follow the commands below to apply the migration and test.")
    else:
        print("❌ Some components have configuration issues that need to be fixed.")

    generate_fix_commands()

    print("\n" + "=" * 50)
    print("🎯 Expected Results After Migration:")
    print("- Construction Methods page: Full CRUD interface")
    print("- Work/Output Config page: Drag-and-drop association interface")
    print("- Project Detail page: No more OperationalError")
    print("- Navigation: 'Maintenance' section with working links")
    print("=" * 50)

if __name__ == '__main__':
    main()