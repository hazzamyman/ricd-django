#!/usr/bin/env python3
"""
Verify that the migration file is correctly structured.
This script can run without Django being installed.
"""
import os
import json

def verify_migration():
    """Verify the migration file structure and content"""

    migration_file = 'ricd/migrations/0022_alter_work_construction_method.py'

    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False

    try:
        with open(migration_file, 'r') as f:
            content = f.read()

        # Check for required Django migration structure
        required_elements = [
            'from django.db import migrations, models',
            'class Migration(migrations.Migration):',
            'dependencies = [',
            "'ricd', '0021_constructionmethod_alter_address_construction_method_and_more'",
            'operations = [',
            "migrations.AlterField(",
            "model_name='work'",
            "name='construction_method'",
            "field=models.ForeignKey(",
            "'ConstructionMethod'",
            'on_delete=models.SET_NULL',
            'null=True',
            'blank=True'
        ]

        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)

        if missing_elements:
            print("❌ Migration file is missing required elements:")
            for element in missing_elements:
                print(f"   - {element}")
            return False

        print("✅ Migration file structure is correct")
        print("✅ Dependencies are properly set")
        print("✅ AlterField operation is correctly defined")
        print("✅ ForeignKey relationship is properly configured")

        return True

    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False

def check_model_consistency():
    """Check that the model file has the expected structure"""

    model_file = 'ricd/models.py'

    if not os.path.exists(model_file):
        print(f"❌ Model file not found: {model_file}")
        return False

    try:
        with open(model_file, 'r') as f:
            content = f.read()

        # Check for Work model construction_method field
        if "construction_method = models.ForeignKey(" not in content:
            print("❌ Work model construction_method field not found as ForeignKey")
            return False

        if "'ConstructionMethod'" not in content:
            print("❌ ConstructionMethod reference not found in model")
            return False

        print("✅ Work model has correct ForeignKey field definition")
        print("✅ ConstructionMethod model reference is correct")

        return True

    except Exception as e:
        print(f"❌ Error reading model file: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Verifying Django migration and model consistency...\n")

    migration_ok = verify_migration()
    model_ok = check_model_consistency()

    print("\n" + "="*50)
    if migration_ok and model_ok:
        print("✅ All verifications passed!")
        print("\n📝 Next steps:")
        print("1. Ensure Django is installed in your virtual environment")
        print("2. Run: python manage.py migrate ricd 0022")
        print("3. Test the application: python manage.py runserver")
        print("4. Visit the maintenance pages:")
        print("   - /portal/maintenance/construction-methods/")
        print("   - /portal/maintenance/work-output-config/")
    else:
        print("❌ Verification failed. Please check the migration file.")

    print("="*50)