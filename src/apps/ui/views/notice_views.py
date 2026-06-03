"""
Notice views — broadcast notices that target multiple objects across any entity type.

A Notice is semantically different from a Comment:
  Comment → one thread attached to one object
  Notice  → one announcement that affects many objects (projects, councils, BFAs, etc.)

Entity registry keys match Django model_name (lowercase), so ContentType lookups are trivial.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import (
    BriefFinancialApproval,
    Council,
    FundingSchedule,
    Notice,
    NoticeTarget,
    Payment,
    Project,
    Variation,
)

COUNCIL_ROLES = frozenset({'COUNCIL_USER', 'COUNCIL_MANAGER'})


def _user_role(user):
    return getattr(getattr(user, 'profile', None), 'officer_role', None)


def _is_council(user):
    return _user_role(user) in COUNCIL_ROLES


# ---------------------------------------------------------------------------
# Entity registry
# ---------------------------------------------------------------------------

def _build_entity_registry():
    """
    Returns dict: key → (display_label, Model class, callable that returns [(pk, label), ...])
    Keys match Django model_name (lowercase) so ContentType.get_for_model() works.
    """
    return {
        'project': (
            'Projects',
            Project,
            lambda: [(p.pk, p.name) for p in Project.objects.order_by('name')[:300]],
        ),
        'council': (
            'Councils',
            Council,
            lambda: [(c.pk, c.name) for c in Council.objects.order_by('name')],
        ),
        'fundingschedule': (
            'Funding Schedules',
            FundingSchedule,
            lambda: [
                (fs.pk, f"FS #{fs.pk} — {getattr(fs.project, 'name', '?')}")
                for fs in FundingSchedule.objects.select_related('project').order_by('-pk')[:300]
            ],
        ),
        'payment': (
            'Payments',
            Payment,
            lambda: [
                (p.pk, f"Payment #{p.pk} — {getattr(p.project, 'name', '?')}")
                for p in Payment.objects.select_related('project').order_by('-pk')[:300]
            ],
        ),
        'brieffinancialapproval': (
            'BFAs',
            BriefFinancialApproval,
            lambda: [
                (b.pk, f"BFA #{b.pk} — {b.mincor_reference or '(no MINCOR ref)'}")
                for b in BriefFinancialApproval.objects.order_by('-pk')[:300]
            ],
        ),
        'variation': (
            'Variations',
            Variation,
            lambda: [
                (v.pk, f"Variation #{v.pk}")
                for v in Variation.objects.order_by('-pk')[:300]
            ],
        ),
    }


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@login_required
def notice_list(request):
    is_council = _is_council(request.user)
    qs = Notice.objects.prefetch_related('targets').order_by('-created_at')
    if is_council:
        qs = qs.filter(visibility=Notice.Visibility.EXTERNAL)
    return render(request, 'notices/list.html', {
        'notices': qs,
        'active_nav': 'notices',
    })


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@login_required
def notice_create(request):
    registry = _build_entity_registry()
    is_council = _is_council(request.user)

    # Pre-load all entity data as JSON for the JS multi-select
    entity_data = {
        key: [[pk, label] for pk, label in factory()]
        for key, (_, _, factory) in registry.items()
    }

    # Query params for pre-selecting when arriving from a detail page
    initial_entity_type = request.GET.get('entity_type', 'project')
    if initial_entity_type not in registry:
        initial_entity_type = 'project'
    raw_preselect = request.GET.get('preselect', '')
    try:
        initial_preselect = int(raw_preselect)
    except (ValueError, TypeError):
        initial_preselect = None

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        visibility = request.POST.get('visibility', Notice.Visibility.INTERNAL)
        if is_council:
            visibility = Notice.Visibility.EXTERNAL

        errors = []
        if not body:
            errors.append('Body is required.')

        # Parse numbered target groups: entity_type_0, object_ids_0, entity_type_1, ...
        groups = []
        i = 0
        while f'entity_type_{i}' in request.POST:
            etype = request.POST.get(f'entity_type_{i}')
            raw_ids = request.POST.getlist(f'object_ids_{i}')
            oids = [int(x) for x in raw_ids if x.isdigit()]
            if etype in registry and oids:
                groups.append((etype, oids))
            i += 1

        if not groups:
            errors.append('Select at least one target object.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            notice = Notice.objects.create(
                title=title,
                body=body,
                visibility=visibility,
                author=request.user,
            )
            for etype, oids in groups:
                _, Model, _ = registry[etype]
                ct = ContentType.objects.get_for_model(Model)
                for oid in oids:
                    NoticeTarget.objects.get_or_create(
                        notice=notice,
                        content_type=ct,
                        object_id=oid,
                    )
            messages.success(request, 'Notice created and applied to selected objects.')
            return redirect('ui:notice_list')

    context = {
        'entity_data_json': json.dumps(entity_data),
        'entity_labels': {key: label for key, (label, _, _) in registry.items()},
        'entity_keys': list(registry.keys()),
        'initial_entity_type': initial_entity_type,
        'initial_preselect': initial_preselect,
        'is_council': is_council,
        'active_nav': 'notices',
    }
    return render(request, 'notices/create.html', context)


# ---------------------------------------------------------------------------
# Delete / remove target
# ---------------------------------------------------------------------------

@login_required
@require_POST
def notice_delete(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    if notice.author != request.user and not request.user.is_superuser:
        messages.error(request, 'You can only delete your own notices.')
        return redirect('ui:notice_list')
    notice.delete()
    messages.success(request, 'Notice deleted.')
    return redirect('ui:notice_list')


@login_required
@require_POST
def notice_remove_target(request, pk):
    """Remove one (content_type, object_id) target from a notice."""
    notice = get_object_or_404(Notice, pk=pk)
    if notice.author != request.user and not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('ui:notice_list')
    ct_id = request.POST.get('content_type_id')
    obj_id = request.POST.get('object_id')
    NoticeTarget.objects.filter(
        notice=notice, content_type_id=ct_id, object_id=obj_id,
    ).delete()
    messages.success(request, 'Target removed.')
    return redirect(request.META.get('HTTP_REFERER') or 'ui:notice_list')
