from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.models import ProjectDocument, DocumentType, Project


@login_required
def documents_list_view(request):
    """List all project documents with filtering"""
    project_id = request.GET.get('project', '')
    doc_type_id = request.GET.get('doc_type', '')

    documents = ProjectDocument.objects.select_related('project', 'document_type', 'uploaded_by').all()

    # Apply filters
    if project_id:
        documents = documents.filter(project_id=project_id)
    if doc_type_id:
        documents = documents.filter(document_type_id=doc_type_id)

    # Get filter options
    projects = Project.objects.all().order_by('name')
    doc_types = DocumentType.objects.filter(is_active=True).order_by('name')

    context = {
        'documents': documents,
        'projects': projects,
        'doc_types': doc_types,
        'selected_project': project_id,
        'selected_doc_type': doc_type_id,
    }
    return render(request, 'documents/list.html', context)
