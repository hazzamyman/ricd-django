def fnc_context(request):
    """Add FNC user context to all templates"""
    is_fnc_user = False
    can_edit_projects = False
    user_group = None
    
    if request.user.is_authenticated:
        user_groups = set(request.user.groups.values_list('name', flat=True))
        
        # Check if user is FNC (any FNC group) or superuser
        is_fnc_user = request.user.is_superuser or any('FNC' in g for g in user_groups)
        
        # Check if user can edit projects
        can_edit_projects = request.user.is_superuser or any(
            g in ['FNC Manager', 'FNC User'] for g in user_groups
        )
        
        # Get primary user group
        if user_groups:
            user_group = list(user_groups)[0]
    
    return {
        'is_fnc_user': is_fnc_user,
        'is_ricd_user': is_fnc_user,  # Backwards compatibility alias
        'can_edit_projects': can_edit_projects,
        'user_group': user_group,
    }


# Backwards compatibility alias
ricd_context = fnc_context