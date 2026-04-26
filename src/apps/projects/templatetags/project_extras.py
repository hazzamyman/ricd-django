from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def filter_by_funding(changes, funding_id):
    """Filter changes by funding schedule ID"""
    if not changes:
        return []
    return [c for c in changes if c.funding_schedule_id == funding_id]
