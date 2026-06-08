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
# RICD staff who can write (officers + managers) — excludes councils AND
# read-only audit. Mirrors WriteRequiredMixin / WRITE_ROLES.
WRITE_ROLES = frozenset({'OFFICER', 'MANAGER'})


def ricd_user_context(request):
    if not request.user.is_authenticated:
        return {'is_fnc': False, 'is_council': False, 'is_manager': False,
                'is_writer': False, 'user_role_display': ''}
    role = getattr(getattr(request.user, 'profile', None), 'officer_role', None)
    is_council = role in COUNCIL_ROLES
    is_fnc = (role is not None and not is_council) or request.user.is_superuser
    is_manager = role in MANAGER_ROLES or request.user.is_superuser
    is_writer = role in WRITE_ROLES or request.user.is_superuser
    return {
        'user_role': role or '',
        'is_fnc': is_fnc,
        'is_council': is_council,
        'is_manager': is_manager,
        'is_writer': is_writer,
        'user_role_display': ROLE_DISPLAY.get(role, '') if role else ('Superuser' if request.user.is_superuser else ''),
    }
