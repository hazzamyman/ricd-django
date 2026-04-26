"""
Common utilities for FNC system.
"""
from datetime import datetime


def get_current_financial_year():
    """Get current financial year based on today's date.
    
    QLD Financial Year:
    - July 2025 = 2025-26 starts
    - April 2026 = still in 2025-26
    """
    today = datetime.today()
    if today.month >= 7:
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{start_year + 1}"


def get_financial_year_choices(start_year=2025, num_years=10):
    """
    Generate financial year choices for dropdowns.
    
    Args:
        start_year: Starting year (e.g., 2025 for 2025-26)
        num_years: Number of years to generate
    
    Returns:
        List of tuples: [(code, display), ...]
    """
    choices = []
    current = get_current_financial_year()
    for i in range(num_years):
        year = start_year + i
        code = f"{year}-{year + 1}"
        if code == current:
            display = f"{year}-{year + 1} (Current)"
        else:
            display = f"{year}-{year + 1}"
        choices.append((code, display))
    return choices


def get_financial_year_choices_required(start_year=2025, num_years=10):
    """
    Generate financial year choices including blank first option.
    
    Returns:
        List of tuples: [('', '-- Select --'), ...]
    """
    choices = [('', '-- Select --')]
    choices.extend(get_financial_year_choices(start_year, num_years))
    return choices


FINANCIAL_YEAR_CHOICES = get_financial_year_choices(start_year=2025, num_years=15)
FINANCIAL_YEAR_CHOICES_REQUIRED = get_financial_year_choices_required(start_year=2025, num_years=15)
CURRENT_FINANCIAL_YEAR = get_current_financial_year()