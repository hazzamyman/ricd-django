```markdown
# ricd-django Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the `ricd-django` Python codebase. You'll learn how to structure files, write imports and exports, follow commit message conventions, and understand the project's approach to testing. While no automated workflows were detected, this guide provides suggested commands for common development tasks.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `userProfile.py`, `dataLoader.py`

### Import Style
- Use **relative imports** within the codebase.
  - Example:
    ```python
    from .models import User
    from ..utils import formatDate
    ```

### Export Style
- Use **named exports** (explicitly listing what is exported).
  - Example:
    ```python
    def calculateTotal():
        pass

    __all__ = ['calculateTotal']
    ```

### Commit Messages
- Follow **conventional commit** patterns.
- Use the `feat` prefix for new features.
  - Example:
    ```
    feat: add user authentication to login endpoint
    ```

## Workflows

### Feature Development
**Trigger:** When adding a new feature to the codebase  
**Command:** `/feature-dev`

1. Create a new branch for your feature.
2. Implement the feature using camelCase file names and relative imports.
3. Write or update tests in a `*.test.*` file.
4. Commit your changes with a message starting with `feat:`.
5. Open a pull request for review.

### Testing
**Trigger:** When validating your code changes  
**Command:** `/run-tests`

1. Locate or create test files matching the `*.test.*` pattern.
2. Run your tests using the project's preferred test runner (framework unknown; try `pytest` or `unittest`).
3. Ensure all tests pass before merging.

## Testing Patterns

- Test files follow the `*.test.*` naming convention.
  - Example: `userProfile.test.py`
- The specific testing framework is not detected; try using `pytest` or `unittest`.
- Place tests alongside the modules they cover or in a dedicated tests directory.

#### Example Test File
```python
# userProfile.test.py

from .userProfile import getUserName

def test_get_user_name():
    assert getUserName(1) == "Alice"
```

## Commands
| Command        | Purpose                                      |
|----------------|----------------------------------------------|
| /feature-dev   | Start a new feature development workflow      |
| /run-tests     | Run all tests in the codebase                |
```
