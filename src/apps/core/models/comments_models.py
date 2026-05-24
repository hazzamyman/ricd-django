"""
Generic threaded comment system with RBAC visibility control.

One Comment table handles all entities via Django's ContentType framework.
CommentSettings controls which entity types show the comment UI — intended
to be exposed as checkboxes on the maintenance/configuration page.

Visibility:
  INTERNAL — visible to FNC/RICD staff and READ_ONLY; hidden from council users
  EXTERNAL — visible to everyone (FNC + council roles)

Defaults: INTERNAL for FNC authors, always EXTERNAL for council authors.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models


class Comment(models.Model):
    class Visibility(models.TextChoices):
        INTERNAL = 'INTERNAL', 'Internal (RICD only)'
        EXTERNAL = 'EXTERNAL', 'Visible to Council'

    # Generic relation — works for any model without touching that model's file
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Threading — parent=None means top-level comment
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.CASCADE, related_name='replies',
    )

    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='ricd_comments',
    )
    body = models.TextField()
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.INTERNAL,
    )
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['content_type', 'object_id', 'parent'])]

    def __str__(self):
        return f"Comment by {self.author} on {self.content_type.model} #{self.object_id}"


class CommentSettings(models.Model):
    """
    Per-model toggle for the comment UI.
    Exposed as checkboxes on the maintenance/configuration page.
    Default (no row): comments enabled.
    """
    model_name = models.CharField(
        max_length=100, unique=True,
        help_text="Django model name (lowercase), e.g. 'project', 'fundingschedule'",
    )
    display_name = models.CharField(max_length=200, help_text="Human-readable page name")
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_name']
        verbose_name = 'Comment Settings'
        verbose_name_plural = 'Comment Settings'

    def __str__(self):
        status = 'on' if self.is_enabled else 'off'
        return f"{self.display_name} ({status})"

    @classmethod
    def is_comments_enabled(cls, model_name: str) -> bool:
        """Return True if comments are enabled for model_name. Defaults to True if no row."""
        try:
            return cls.objects.get(model_name=model_name).is_enabled
        except cls.DoesNotExist:
            return True


class Notice(models.Model):
    """
    A broadcast notice that can target multiple objects across any entity type.

    Unlike a Comment (1-to-1 with one object), a Notice is a 1-to-many
    announcement: e.g. "barge down — all coastal projects delayed" can target
    a dozen projects and several councils in one hit.
    """
    class Visibility(models.TextChoices):
        INTERNAL = 'INTERNAL', 'Internal (RICD only)'
        EXTERNAL = 'EXTERNAL', 'Visible to Council'

    title = models.CharField(max_length=200, blank=True, help_text="Short headline (optional)")
    body = models.TextField()
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.INTERNAL,
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='notices',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or self.body[:80]

    @property
    def target_count(self):
        return self.targets.count()


class NoticeTarget(models.Model):
    """
    One row per (notice, object) pair.  A single Notice can have many targets
    across any mix of entity types.
    """
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='targets')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = [('notice', 'content_type', 'object_id')]
        indexes = [models.Index(fields=['content_type', 'object_id'])]

    def __str__(self):
        return f"{self.notice_id} → {self.content_type.model} #{self.object_id}"
