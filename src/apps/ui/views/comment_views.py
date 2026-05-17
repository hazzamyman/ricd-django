from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.core.models import Comment


COUNCIL_ROLES = {'COUNCIL_USER', 'COUNCIL_MANAGER'}


def _user_role(user):
    return getattr(getattr(user, 'profile', None), 'officer_role', None)


def _can_comment(user):
    return user.is_authenticated and _user_role(user) is not None


def _is_council(user):
    return _user_role(user) in COUNCIL_ROLES


def _resolve_redirect(request, comment):
    """Best-effort redirect back to the object that was commented on."""
    obj = comment.content_object
    if obj is not None and hasattr(obj, 'get_absolute_url'):
        return redirect(obj.get_absolute_url())
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def add_comment(request):
    content_type_id = request.POST.get('content_type_id')
    object_id = request.POST.get('object_id')
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id') or None

    if not body:
        messages.error(request, 'Comment cannot be empty.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if not _can_comment(request.user):
        return HttpResponseForbidden()

    ct = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(Comment, pk=parent_id) if parent_id else None

    # Council users always post externally; FNC users choose (default INTERNAL)
    if _is_council(request.user):
        visibility = Comment.Visibility.EXTERNAL
    else:
        visibility = request.POST.get('visibility', Comment.Visibility.INTERNAL)
        if visibility not in Comment.Visibility.values:
            visibility = Comment.Visibility.INTERNAL

    comment = Comment.objects.create(
        content_type=ct,
        object_id=object_id,
        parent=parent,
        author=request.user,
        body=body,
        visibility=visibility,
    )
    return _resolve_redirect(request, comment)


@login_required
@require_POST
def edit_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if comment.author != request.user and not request.user.is_superuser:
        return HttpResponseForbidden()

    body = request.POST.get('body', '').strip()
    if not body:
        messages.error(request, 'Comment cannot be empty.')
        return _resolve_redirect(request, comment)

    comment.body = body
    # Council users can't change visibility; FNC users can update it
    if not _is_council(request.user):
        visibility = request.POST.get('visibility', comment.visibility)
        if visibility in Comment.Visibility.values:
            comment.visibility = visibility
    comment.is_edited = True
    comment.save()
    return _resolve_redirect(request, comment)


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if comment.author != request.user and not request.user.is_superuser:
        return HttpResponseForbidden()

    redirect_response = _resolve_redirect(request, comment)
    comment.delete()
    return redirect_response
