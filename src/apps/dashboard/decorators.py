from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages


def is_fnc_user(user):
    """Check if user is FNC staff (staff flag or FNC group)"""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return any('FNC' in g.name for g in user.groups.all())


def is_fnc_manager(user):
    """Check if user is FNC Manager"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return any('FNC Manager' in g.name for g in user.groups.all())


def is_council_user(user):
    """Check if user is council user"""
    if not user.is_authenticated:
        return False
    return any('Council' in g.name for g in user.groups.all())


def can_edit_projects(user):
    """Check if user can edit projects"""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return any('FNC' in g.name or 'Council Manager' in g.name for g in user.groups.all())


def can_approve_reports(user):
    """Check if user can approve reports"""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return any('Manager' in g.name for g in user.groups.all())


def fnc_required(view_func):
    """Decorator requiring FNC user access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_fnc_user(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """Decorator requiring Manager access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not can_edit_projects(request.user):
            messages.error(request, 'You do not have permission to perform this action.')
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def council_user_required(view_func):
    """Decorator requiring Council user access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_council_user(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# Backwards compatibility aliases (RICD → FNC rename)
is_ricd_user = is_fnc_user
is_ricd_manager = is_fnc_manager
ricd_required = fnc_required
