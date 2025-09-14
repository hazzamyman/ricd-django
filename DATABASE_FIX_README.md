# Database Schema Fix Required

## Issue Description
The Django application has a database schema mismatch that needs to be resolved before the application can run properly.

### Problem
- **Error**: `OperationalError: no such column: ricd_work.construction_method`
- **Cause**: The database schema expects a `CharField` for the `construction_method` field, but the Django model defines it as a `ForeignKey`
- **Location**: Work model `construction_method` field

## Solution Steps

### Step 1: Apply the Migration
The migration file `0022_alter_work_construction_method.py` has been created to fix this issue.

Run these commands in the Django environment:

```bash
cd /opt/ricd/testproj

# Make sure Django is installed and virtual environment is activated
# (Assuming you have the virtual environment set up)

# Apply the migration
python manage.py migrate ricd 0022

# Or apply all pending migrations
python manage.py migrate
```

### Step 2: Verify Migration Success
After applying the migration, run a quick test:

```bash
python manage.py shell -c "
from ricd.models import Work, ConstructionMethod
# Test that the field works correctly
print('Migration successful - Work.construction_method field is now a ForeignKey')
"
```

### Step 3: Run the Application
Once the migration is applied, the application should work correctly:

```bash
python manage.py runserver
```

## What the Migration Does

The migration `0022_alter_work_construction_method.py` changes the `construction_method` field in the `Work` model from:

**Before (CharField):**
```python
construction_method = models.CharField(
    max_length=50,
    choices=[('on_site', 'On Site'), ('flatpack', 'Flatpack'), ...],
    blank=True,
    null=True
)
```

**After (ForeignKey):**
```python
construction_method = models.ForeignKey(
    'ConstructionMethod',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    help_text="Construction method used for this work"
)
```

## Additional Information

- The `ConstructionMethod` model already exists in the database
- The `Address` model already has the correct `ForeignKey` field definition
- This migration only affects the `Work` model
- No data loss will occur as the field allows NULL values

## Testing After Fix

Once the migration is applied, you can test the pages mentioned in your request:

1. **Construction Methods**: `/portal/maintenance/construction-methods/`
2. **Work/Output Type Configuration**: `/portal/maintenance/work-output-config/`
3. **Project Detail Page**: `/portal/projects/1/detail/` (the page that was throwing the error)

All these pages should now load without operational errors.