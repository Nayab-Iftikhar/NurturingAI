from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings


@login_required
def documents_view(request):
    """Documents upload page"""
    context = {
        'embedding_model': settings.EMBEDDING_MODEL
    }
    return render(request, 'documents/upload.html', context)


@login_required
def chromadb_viewer_view(request):
    """ChromaDB contents viewer page"""
    return render(request, 'documents/chromadb_viewer.html')
