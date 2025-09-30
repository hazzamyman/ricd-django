#!/usr/bin/env python3
"""
Script to automatically replace string references in Django ModelForm Meta.model
with direct imports. Scans all .py files in the project root and subdirectories.
"""

import os
import re
import sys
from pathlib import Path

def fix_model_references(file_path: Path) -> bool:
    """Fix model string references in a single file and return True if changed."""
    if not file_path.suffix == '.py':
        return False
    
    content = file_path.read_text(encoding='utf-8')
    
    # Pattern to matchfrom app.models import ModelName
 Meta.model = 'app.ModelName'
    # This assumes the format 'app.modelname' without extra spaces or quotes variationsMeta.model = ModelName
    pattern = r"(\s*Meta\.model\s*=\s*'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'\s*(?:#.*)?)"
    
    def replacement(match):
        indent = match.group(1)
        app_name = match.group(2)
        model_name = match.group(3)
        # Add import at the top, but for simplicity, insert before the class if possible
        # Here, we'll insert the import right before the Meta class definition
        # But to keep it simple, append to existing imports or add at top
        import_stmt = f"from {app_name}.models import {model_name}\n"
        model_ref = f"{indent}Meta.model = {model_name}"
        return f"{import_stmt}{model_ref}"
    
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if new_content != content:
        file_path.write_text(new_content, encoding='utf-8')
        print(f"Fixed: {file_path}")
        return True
    
    return False

def main():
    project_root = Path(__file__).parent.parent  # Assumes script in scripts/
    changed_files = []
    
    for py_file in project_root.rglob("*.py"):
        if fix_model_references(py_file):
            changed_files.append(str(py_file))
    
    if changed_files:
        print(f"Fixed {len(changed_files)} files:")
        for f in changed_files:
            print(f"  - {f}")
        sys.exit(0)
    else:
        print("No changes needed.")
        sys.exit(0)

if __name__ == "__main__":
    main()