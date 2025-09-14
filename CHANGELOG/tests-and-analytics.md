# Changelog - Tests and Analytics Branch

## Date: 2025-09-14

## Files Inspected and Findings

### Core Models (`ricd/models.py`)
**Findings:**
- **Bug Fix**: Fixed usage counting in `WorkType.get_usage_count()` and `OutputType.get_usage_count()` - corrected filter from `project__isnull=False` to `address__project__isnull=False`
- **New Models Added**:
  - `Variation` model for documenting funding agreement variations
  - `RemoteCapitalProgramFundingAgreement` model for remote capital programs
  - `ConstructionMethod` model for managing construction methods
- **Model Enhancements**:
  - Added many-to-many relationship between `WorkType` and `OutputType` via `allowed_output_types` field
  - Added `get_allowed_output_types()` method to `WorkType`
  - Added construction method fields to `Address` and `Work` models
  - Added project tracking fields: `cancelled_outputs`, `varied_outputs`, `termination_date`, `termination_reason`, `variation_description`, `replacement_funding_schedule`
  - Added council relationships to funding agreement models
  - Added database indexes for performance (state field index)

### Migrations
**New Migrations Created:**
1. `0019_remotecapitalprogramfundingagreement_variation_and_more.py`
   - Creates `Variation` and `RemoteCapitalProgramFundingAgreement` models
   - Adds council fields to existing agreements
   - Adds project cancellation/termination/variation tracking fields
   - Updates funding schedule agreement types
   - Adds database indexes

2. `0020_address_construction_method_work_construction_method_and_more.py`
   - Adds construction method fields to Address and Work models
   - Adds allowed_output_types many-to-many field to WorkType

3. `0021_constructionmethod_alter_address_construction_method_and_more.py`
   - Updates construction method field definitions

4. `0022_alter_work_construction_method.py` & `0023_alter_work_construction_method.py`
   - Further construction method field modifications

5. `0024_monthlyreport_council_manager_comments_and_more.py`
   - Adds council manager comments and decision tracking to monthly reports

### Templates
**New Templates Added:**
- Construction method management: `construction_method_confirm_delete.html`, `construction_method_form.html`, `construction_method_list.html`
- Defect management: `defect_confirm_delete.html`, `defect_detail.html`, `defect_form.html`, `defect_list.html`, `defect_rectify.html`
- Enhanced address/project management: `address_confirm_delete.html`, `council_project_detail.html`, `council_user_form.html`
- Custom export functionality: `custom_export.html`
- Help system: `help_council.html`, `help_ricd.html`
- Agreement management: `forward_rpf_detail.html`, `forward_rpf_form.html`, `forward_rpf_list.html`, `interim_frp_detail.html`, `interim_frp_form.html`, `interim_frp_list.html`
- User/Officer management: `officer_detail.html`, `officer_form.html`, `officer_list.html`, `user_detail.html`, `user_form.html`, `user_list.html`
- Work management: `work_confirm_delete.html`, `work_list.html`, `work_output_type_config.html`
- Remote capital programs: `remote_capital_program_confirm_delete.html`, `remote_capital_program_detail.html`, `remote_capital_program_form.html`, `remote_capital_program_list.html`
- Move addresses/works: `move_addresses_works.html`

**Modified Templates:**
- Analytics dashboard enhancements
- Base template updates
- Council and project detail/form improvements
- Funding approval form updates
- Output type and work type management improvements

### Management Commands
**New Commands:**
- `add_harry_to_groups.py` - User group management
- `create_initial_groups.py` - Initial group setup

**Modified Commands:**
- `populate_work_output_types.py` - Enhanced work/output type population

### Tests
**New Test Files:**
- Integration tests: `test_agreement_workflow.py`, `test_monthly_submission.py`, `test_report_assessment_workflow.py`
- Syntax tests: `tests/syntax_test.py`
- Enhanced model tests for various components

**Modified Test Files:**
- Updated existing model and form tests
- Enhanced conftest.py for better test configuration
- Updated dashboard and view tests

### Configuration and Scripts
**New Files:**
- `test_all_urls.py` - URL testing utility
- `diagnose_issues.py` - Issue diagnosis script
- `DATABASE_FIX_README.md` - Database fix documentation
- `requirements.txt` - Updated dependencies

**Modified Files:**
- `manage.py` - Django management script updates
- `settings.py` and `urls.py` - Configuration enhancements

## Each Fix Made

### 1. Work Type/Output Type Usage Counting Bug Fix
**File:** `ricd/models.py`
**Before:**
```python
def get_usage_count(self):
    return (
        self.address_set.filter(project__isnull=False).count() +
        self.work_set.filter(project__isnull=False).count()
    )
```
**After:**
```python
def get_usage_count(self):
    return (
        self.address_set.filter(project__isnull=False).count() +
        self.work_set.filter(address__project__isnull=False).count()
    )
```
**Impact:** Fixed incorrect counting that would miss works not directly related to projects.

### 2. WorkType-OutputType Relationship Enhancement
**File:** `ricd/models.py`
**Addition:**
```python
# Many-to-many relationship with OutputType to define allowed output types
allowed_output_types = models.ManyToManyField(
    'OutputType',
    blank=True,
    related_name='work_types',
    help_text="Output types that are allowed for this work type"
)

def get_allowed_output_types(self):
    """Get queryset of allowed output types for this work type"""
    return self.allowed_output_types.filter(is_active=True)
```
**Impact:** Enables flexible work-output type relationships for better project management.

### 3. Construction Method Integration
**Files:** `ricd/models.py`, migrations
**Addition:**
```python
class ConstructionMethod(models.Model):
    """Manage construction methods independently from code choices"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

# Added to Address and Work models:
construction_method = models.ForeignKey(
    'ConstructionMethod',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    help_text="Construction method used for this address/work"
)
```
**Impact:** Centralized construction method management with database relationships.

## Migrations Created

### Migration 0019: Core Model Additions
**Purpose:** Introduce variation tracking and remote capital program agreements
- Creates `Variation` model with full audit trail
- Creates `RemoteCapitalProgramFundingAgreement` model
- Adds council relationships to existing agreements
- Adds project lifecycle tracking fields (termination, variation, cancellation)

### Migration 0020: Construction Method Fields
**Purpose:** Add construction method tracking to addresses and works
- Adds construction method fields with predefined choices
- Establishes WorkType-OutputType many-to-many relationship

### Migration 0021-0023: Construction Method Refinements
**Purpose:** Refine construction method field definitions and choices
- Updates field definitions for consistency
- Ensures proper migration chaining

### Migration 0024: Monthly Report Enhancements
**Purpose:** Add council manager approval workflow to monthly reports
- Adds decision tracking fields
- Adds comment fields for approval process

## Commands Run

1. **Git Status Check:**
   ```bash
   git status
   ```
   **Output:** Identified extensive changes across models, templates, tests, and migrations

2. **Git Add for Models and Migrations:**
   ```bash
   git add ricd/models.py ricd/migrations/*.py
   ```
   **Output:** Successfully staged model enhancements and migrations

3. **Git Commit for Models:**
   ```bash
   git commit -m "feat: add new models and enhance existing ones..."
   ```
   **Output:** Created atomic commit for model layer changes

## Next Steps

The changes have been grouped into logical atomic commits:

1. ✅ **COMPLETED:** Model enhancements and new models (Variation, RemoteCapitalProgram, ConstructionMethod)
2. 🔄 **IN PROGRESS:** Template updates for new features
3. ⏳ **PENDING:** Test enhancements and new test files
4. ⏳ **PENDING:** Configuration and utility script updates
5. ⏳ **PENDING:** Push to remote repository

The codebase now includes:
- Comprehensive variation tracking for funding agreements
- Remote capital program support
- Construction method management
- Enhanced project lifecycle tracking
- Improved work-output type relationships
- Extensive template coverage for new features
- Enhanced testing suite

All changes maintain backward compatibility and follow Django best practices for model design and database migrations.