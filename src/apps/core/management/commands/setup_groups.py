"""
Management command: python manage.py setup_groups

Creates (or updates) the five RICD permission groups with appropriate
Django model-level permissions. Safe to re-run — uses get_or_create.

Groups mirror the five officer_role values on Profile:
  RICD Officer       — FNC frontline, full CRUD on all delivery/funding records
  RICD Manager       — FNC senior, everything Officer can + delete + site config
  Council Officer    — Council staff, view own-council records + submit reports
  Council Manager    — Senior council staff, same scope as Council Officer
  Read Only          — Audit/finance/exec, view everything, no writes
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.core.models import GroupPermission


VIEW = ['view']
ADD_CHANGE_VIEW = ['add', 'change', 'view']
FULL = ['add', 'change', 'delete', 'view']


def _build_codenames(entries, actions):
    return {f'{app}.{action}_{model}' for app, model in entries for action in actions}


# Models visible to all roles (view only unless overridden below).
_ALL_VIEW = [
    ('core', 'council'), ('core', 'program'), ('core', 'project'),
    ('core', 'address'), ('core', 'work'), ('core', 'workstep'),
    ('core', 'worktype'), ('core', 'workstepgroup'), ('core', 'workstepdefinition'),
    ('core', 'fundingagreement'), ('core', 'fundingschedule'),
    ('core', 'payment'), ('core', 'paymentrule'),
    ('core', 'paymentmilestoneschedule'), ('core', 'paymentmilestonerule'),
    ('core', 'approval'), ('core', 'variation'), ('core', 'variationitem'),
    ('core', 'monthlytrackerentry'), ('core', 'quarterlyreport'),
    ('core', 'stagereport'), ('core', 'fundingnotice'), ('core', 'expenseclaim'),
    ('core', 'workfunding'), ('core', 'brieffinancialapproval'),
    ('core', 'brieffinancialapprovalitem'), ('core', 'document'),
    ('core', 'comment'), ('core', 'landtenure'), ('core', 'suburb'),
]

# Delivery + funding records Officers can create/edit (not delete).
_OFFICER_WRITE = [
    ('core', 'project'), ('core', 'address'), ('core', 'work'), ('core', 'workstep'),
    ('core', 'fundingagreement'), ('core', 'fundingschedule'),
    ('core', 'payment'), ('core', 'paymentrule'),
    ('core', 'approval'), ('core', 'variation'), ('core', 'variationitem'),
    ('core', 'monthlytrackerentry'), ('core', 'quarterlyreport'),
    ('core', 'stagereport'), ('core', 'fundingnotice'), ('core', 'expenseclaim'),
    ('core', 'workfunding'), ('core', 'brieffinancialapproval'),
    ('core', 'brieffinancialapprovalitem'), ('core', 'document'), ('core', 'comment'),
]

# Reference/lookup tables Officers can also edit.
_OFFICER_REF = [
    ('core', 'worktype'), ('core', 'workstepgroup'), ('core', 'workstepdefinition'),
    ('core', 'paymentmilestoneschedule'), ('core', 'paymentmilestonerule'),
    ('core', 'landtenure'), ('core', 'suburb'),
]

# Models only Managers can delete.
_MANAGER_DELETE = [
    ('core', 'project'), ('core', 'address'), ('core', 'work'),
    ('core', 'fundingagreement'), ('core', 'fundingschedule'),
    ('core', 'payment'), ('core', 'brieffinancialapproval'),
    ('core', 'variation'), ('core', 'document'),
]

# Site/user admin only Managers can touch.
_MANAGER_ADMIN = [
    ('core', 'sitesettings'), ('core', 'profile'), ('core', 'grouppermission'),
    ('auth', 'user'), ('auth', 'group'),
]

# What council roles can view (no BFA / funding internals).
_COUNCIL_VIEW = [
    ('core', 'council'), ('core', 'program'), ('core', 'project'),
    ('core', 'address'), ('core', 'work'), ('core', 'workstep'),
    ('core', 'worktype'), ('core', 'fundingschedule'), ('core', 'payment'),
    ('core', 'approval'), ('core', 'variation'), ('core', 'variationitem'),
    ('core', 'monthlytrackerentry'), ('core', 'quarterlyreport'),
    ('core', 'stagereport'), ('core', 'fundingnotice'), ('core', 'expenseclaim'),
    ('core', 'workfunding'), ('core', 'document'), ('core', 'comment'),
    ('core', 'landtenure'), ('core', 'suburb'),
]

# What council roles can submit/create.
_COUNCIL_WRITE = [
    ('core', 'monthlytrackerentry'), ('core', 'quarterlyreport'),
    ('core', 'stagereport'), ('core', 'expenseclaim'),
    ('core', 'document'), ('core', 'comment'),
]


GROUP_SPECS = {
    'RICD Officer': {
        'group_type': 'OFFICER',
        'description': 'FNC frontline staff — full create/edit on all delivery and funding records across all councils.',
        'can_approve_reports': False,
        'can_approve_payments': False,
        'can_manage_councils': False,
        'can_manage_programs': False,
        'can_manage_users': False,
        'codenames': (
            _build_codenames(_ALL_VIEW, VIEW) |
            _build_codenames(_OFFICER_WRITE, ADD_CHANGE_VIEW) |
            _build_codenames(_OFFICER_REF, ADD_CHANGE_VIEW)
        ),
    },
    'RICD Manager': {
        'group_type': 'MANAGER',
        'description': 'FNC senior staff — everything Officer can do, plus delete, archive, user management, and site config.',
        'can_approve_reports': True,
        'can_approve_payments': True,
        'can_manage_councils': True,
        'can_manage_programs': True,
        'can_manage_users': True,
        'codenames': (
            _build_codenames(_ALL_VIEW, VIEW) |
            _build_codenames(_OFFICER_WRITE, ADD_CHANGE_VIEW) |
            _build_codenames(_OFFICER_REF, FULL) |
            _build_codenames(_MANAGER_DELETE, ['delete']) |
            _build_codenames(_MANAGER_ADMIN, FULL)
        ),
    },
    'Council Officer': {
        'group_type': 'COUNCIL_USER',
        'description': 'Council staff — view own-council records only; submit reports and expense claims.',
        'can_approve_reports': False,
        'can_approve_payments': False,
        'can_manage_councils': False,
        'can_manage_programs': False,
        'can_manage_users': False,
        'codenames': (
            _build_codenames(_COUNCIL_VIEW, VIEW) |
            _build_codenames(_COUNCIL_WRITE, ADD_CHANGE_VIEW)
        ),
    },
    'Council Manager': {
        'group_type': 'COUNCIL_MANAGER',
        'description': 'Senior council staff — same scope as Council Officer (own-council data only).',
        'can_approve_reports': False,
        'can_approve_payments': False,
        'can_manage_councils': False,
        'can_manage_programs': False,
        'can_manage_users': False,
        'codenames': (
            _build_codenames(_COUNCIL_VIEW, VIEW) |
            _build_codenames(_COUNCIL_WRITE, ADD_CHANGE_VIEW)
        ),
    },
    'Read Only': {
        'group_type': 'READ_ONLY',
        'description': 'Internal audit / finance / executives — read everything across all councils, no writes.',
        'can_approve_reports': False,
        'can_approve_payments': False,
        'can_manage_councils': False,
        'can_manage_programs': False,
        'can_manage_users': False,
        'codenames': _build_codenames(_ALL_VIEW, VIEW),
    },
}


class Command(BaseCommand):
    help = 'Create or update RICD permission groups with correct model-level permissions.'

    def handle(self, *args, **options):
        perm_lookup = {
            f'{p.content_type.app_label}.{p.codename}': p
            for p in Permission.objects.select_related('content_type').all()
        }

        for group_name, spec in GROUP_SPECS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            action = 'Created' if created else 'Updated'

            perms, missing = [], []
            for codename in spec['codenames']:
                p = perm_lookup.get(codename)
                if p:
                    perms.append(p)
                else:
                    missing.append(codename)

            group.permissions.set(perms)

            gp, _ = GroupPermission.objects.get_or_create(group=group)
            gp.group_type = spec['group_type']
            gp.description = spec['description']
            gp.can_approve_reports = spec['can_approve_reports']
            gp.can_approve_payments = spec['can_approve_payments']
            gp.can_manage_councils = spec['can_manage_councils']
            gp.can_manage_programs = spec['can_manage_programs']
            gp.can_manage_users = spec['can_manage_users']
            gp.save()

            self.stdout.write(self.style.SUCCESS(
                f'{action} "{group_name}" — {len(perms)} permissions assigned.'
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f'  Skipped {len(missing)} unknown codenames: '
                    f'{", ".join(sorted(missing)[:5])}{"…" if len(missing) > 5 else ""}'
                ))

        self.stdout.write(self.style.SUCCESS('\nDone. Safe to re-run any time to resync.'))
