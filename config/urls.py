"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth.decorators import login_required
from ninja import NinjaAPI
from authentication.api import router as auth_router
from authentication.views import signup_view, login_view, forgot_password_view, reset_password_view, logout_view
from documents.api import router as documents_router
from documents.views import documents_view, chromadb_viewer_view
from leads.api import router as leads_router
from leads.views import leads_view
from campaigns.api import router as campaigns_router
from campaigns.views import campaigns_view, campaigns_list_view, conversations_view
from apps.agent.api import router as agent_router
from django.shortcuts import render

# Create NinjaAPI instance
api = NinjaAPI(
    title="NurturingAI API",
    description="AI-powered lead nurturing system API",
    version="1.0.0"
)

# Register API routers
api.add_router("/auth", auth_router, tags=["Authentication"])
api.add_router("/documents", documents_router, tags=["Documents"])
api.add_router("/leads", leads_router, tags=["Leads"])
api.add_router("/campaigns", campaigns_router, tags=["Campaigns"])
api.add_router("/agent", agent_router, tags=["Agent"])


@api.get("/hello")
def hello(request):
    """Test endpoint"""
    return {"message": "Hello from Django Ninja!"}


def dashboard_view(request):
    """Dashboard view"""
    return render(request, 'dashboard.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    # Frontend auth routes
    path('auth/signup/', signup_view, name='signup'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/forgot-password/', forgot_password_view, name='forgot_password'),
    path('auth/reset-password/', reset_password_view, name='reset_password'),
    # Dashboard
    path('', login_required(dashboard_view), name='dashboard'),
    # Documents
    path('documents/', login_required(documents_view), name='documents'),
    path('documents/chromadb/', login_required(chromadb_viewer_view), name='chromadb_viewer'),
    # Leads
    path('leads/', login_required(leads_view), name='leads'),
    # Campaigns
    path('campaigns/', login_required(campaigns_view), name='campaigns'),
    path('campaigns/list/', login_required(campaigns_list_view), name='campaigns_list'),
    path('campaigns/conversations/', login_required(conversations_view), name='conversations'),
]
