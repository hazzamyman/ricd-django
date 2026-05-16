from django.contrib import admin
from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'entity_type', 'entity_id', 'action', 'user')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_type', 'entity_id', 'user__username')
    readonly_fields = ('user', 'timestamp', 'entity_type', 'entity_id', 'action', 'before_json', 'after_json')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
