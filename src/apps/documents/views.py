from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import DocumentType


@login_required
def document_list(request):
    """List all document types"""
    doc_types = DocumentType.objects.all()
    return render(request, 'documents/document_list.html', {'doc_types': doc_types})
