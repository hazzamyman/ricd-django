from django import template

register = template.Library()

@register.filter
def get_key(dictionary, key):
    """Get a value from a dictionary by key, returning None if key doesn't exist"""
    return dictionary.get(key)

@register.filter
def can_approve_council_manager(entry, user):
    """Check if user can approve as Council Manager for the given entry"""
    if not entry or not user or not user.is_authenticated:
        return False

    try:
        # Check if user is Council Manager for this council
        if hasattr(user, 'profile') and hasattr(user.profile, 'council'):
            # Get the council from the entry's project
            council = entry.monthly_tracker.work.project.council
            return user.profile.council == council and user.profile.council_role == 'manager'
    except (AttributeError, TypeError):
        pass

    return False

@register.filter
def can_approve_ricd_officer(entry, user):
    """Check if user can approve as RICD Officer for the given entry"""
    if not entry or not user or not user.is_authenticated:
        return False
    # Check if user is RICD staff/manager
    return user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()