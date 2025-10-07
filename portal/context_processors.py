def user_flags(request):
    """
    Context processor to add user role flags to all templates.
    """
    if request.user.is_authenticated:
        is_ricd = request.user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
        is_council = request.user.groups.filter(name__in=['Council User', 'Council Manager']).exists()
    else:
        is_ricd = False
        is_council = False
    
    return {
        'is_ricd': is_ricd,
        'is_council': is_council,
    }