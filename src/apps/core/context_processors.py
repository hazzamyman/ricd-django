ROLE_DISPLAY = {
    'PRINCIPAL_OFFICER': 'Principal Officer',
    'SENIOR_OFFICER': 'Senior Officer',
    'PROGRAM_OFFICER': 'Program Officer',
    'MANAGER': 'FNC Manager',
    'DIRECTOR': 'Director',
    'COUNCIL_USER': 'Council User',
    'COUNCIL_MANAGER': 'Council Manager',
    'OTHER': 'Read Only',
}
COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})
MANAGER_ROLES = frozenset({'MANAGER', 'DIRECTOR'})


def ricd_user_context(request):
    if not request.user.is_authenticated:
        return {'is_fnc': False, 'is_council': False, 'is_manager': False, 'user_role_display': ''}
    role = getattr(getattr(request.user, 'profile', None), 'officer_role', None)
    is_council = role in COUNCIL_ROLES
    is_fnc = (role is not None and not is_council) or request.user.is_superuser
    is_manager = role in MANAGER_ROLES or request.user.is_superuser
    return {
        'user_role': role or '',
        'is_fnc': is_fnc,
        'is_council': is_council,
        'is_manager': is_manager,
        'user_role_display': ROLE_DISPLAY.get(role, '') if role else ('Superuser' if request.user.is_superuser else ''),
    }
