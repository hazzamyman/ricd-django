from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from .models import Profile, GroupPermission


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


class GroupPermissionInline(admin.StackedInline):
    model = GroupPermission
    can_delete = True


class GroupAdmin(admin.ModelAdmin):
    inlines = (GroupPermissionInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username', 'user__email')


@admin.register(GroupPermission)
class GroupPermissionAdmin(admin.ModelAdmin):
    list_display = ('group', 'group_type', 'can_approve_reports', 'can_approve_payments', 'can_manage_councils')
    list_filter = ('group_type', 'can_approve_reports', 'can_approve_payments')
    search_fields = ('group__name', 'description')
