"""Money formatting filters for RICD templates.

Usage:
    {% load money %}
    {{ value|money }}             →  $1,234,567,890.00
    {{ value|money }}  (negative) →  <span class="money-neg">-$1,234.56</span>
    {{ value|money:"" }}          →  blank when value is None/blank
    {{ value|money_plain }}       →  same number, no HTML wrapping (CSV-safe)
"""
from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def _to_decimal(value):
    """Convert anything reasonable to Decimal. Returns None on failure."""
    if value in (None, '', 'None'):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


@register.filter(name='money')
def money(value, blank='—'):
    """Format as $1,234,567,890.00.  Wraps negatives in <span class="money-neg">."""
    amt = _to_decimal(value)
    if amt is None:
        return blank
    if amt < 0:
        formatted = f"-${(-amt):,.2f}"
        return format_html('<span class="money-neg">{}</span>', formatted)
    return mark_safe(f"${amt:,.2f}")


@register.filter(name='money_whole')
def money_whole(value, blank='—'):
    """Format as whole dollars with thousands separators: $1,234,567 (no cents)."""
    amt = _to_decimal(value)
    if amt is None:
        return blank
    if amt < 0:
        return format_html('<span class="money-neg">{}</span>', f"-${(-amt):,.0f}")
    return mark_safe(f"${amt:,.0f}")


@register.filter(name='money_plain')
def money_plain(value, blank='—'):
    """Same number formatting but with no HTML wrapper — suitable for CSV / titles."""
    amt = _to_decimal(value)
    if amt is None:
        return blank
    sign = '-' if amt < 0 else ''
    abs_amt = -amt if amt < 0 else amt
    return f"{sign}${abs_amt:,.2f}"
