"""
Template filters for currency formatting.
"""
from django import template
import locale

register = template.Library()


@register.filter
def currency(value, decimals=0):
    """
    Format a number as Australian currency with comma separators.

    Usage: {{ amount|currency }}
           {{ amount|currency:2 }}  # for decimal places
    """
    if value is None or value == '':
        return '$0'

    try:
        # Convert to float to handle Decimal objects
        if hasattr(value, '__float__'):
            float_value = float(value)
        else:
            float_value = float(value)

        # Format with comma separators
        formatted = f"{float_value:,.{decimals}f}"

        # Remove .00 for zero decimals
        if decimals == 0 and formatted.endswith('.00'):
            formatted = formatted[:-3]

        return f'${formatted}'
    except (ValueError, TypeError):
        return '$0'


@register.filter
def currency_short(value):
    """
    Format large amounts in shortened form (K, M, B).
    Usage: {{ large_amount|currency_short }}
    """
    if value is None or value == '':
        return '$0'

    try:
        if hasattr(value, '__float__'):
            float_value = float(value)
        else:
            float_value = float(value)

        if float_value >= 1000000000:  # Billions
            return f'${float_value/1000000000:.1f}B'
        elif float_value >= 1000000:  # Millions
            return f'${float_value/1000000:.1f}M'
        elif float_value >= 1000:  # Thousands
            return f'${float_value/1000:.1f}K'
        else:
            return f'${float_value:,.0f}'
    except (ValueError, TypeError):
        return '$0'