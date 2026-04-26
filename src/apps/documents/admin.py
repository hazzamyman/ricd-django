from django.contrib import admin
from .models import DocumentType, ProjectDocument


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_attachment', 'is_active')
    list_filter = ('is_attachment', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)


class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 1


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('project', 'document_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('project__name', 'description')
    date_hierarchy = 'uploaded_at'
