from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def leads_view(request):
    """Leads filtering page"""
    return render(request, 'leads/filter.html')
