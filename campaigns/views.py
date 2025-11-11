from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def campaigns_view(request):
    """Campaigns creation page"""
    return render(request, 'campaigns/create.html')


@login_required
def campaigns_list_view(request):
    """Campaign list page"""
    return render(request, 'campaigns/list.html')


@login_required
def conversations_view(request):
    """Conversations/Emails page - shows sent emails and allows replies"""
    return render(request, 'campaigns/conversations.html')
