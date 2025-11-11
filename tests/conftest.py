"""
Pytest configuration and fixtures
"""
import pytest
import os
import tempfile
import shutil
from django.contrib.auth import get_user_model
from django.test import Client
from django.conf import settings
from pathlib import Path

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup database for tests"""
    with django_db_blocker.unblock():
        # Create test user
        User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'password': 'pbkdf2_sha256$600000$test$test'
            }
        )


@pytest.fixture
def test_user(db):
    """Create a test user"""
    user, _ = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def authenticated_client(test_user):
    """Create an authenticated Django test client"""
    client = Client()
    client.force_login(test_user)
    return client


@pytest.fixture
def api_client(test_user):
    """Create an API client with JWT token"""
    from authentication.jwt_auth import create_access_token
    from django.test import Client
    
    client = Client()
    token = create_access_token(test_user)
    # Store token for use in API calls
    client.token = token
    return client


@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing"""
    return {
        'lead_id': 'TEST_L1',
        'name': 'Test Lead',
        'email': 'testlead@example.com',
        'country_code': '1',
        'phone': '1234567890',
        'project_name': 'Test Project',
        'unit_type': '2 bed',
        'budget_min': 1000000,
        'budget_max': 2000000,
        'status': 'Connected',
        'last_conversation_summary': 'Test conversation'
    }


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Test Property Brochure")
    p.drawString(100, 730, "This is a test document for property details.")
    p.drawString(100, 710, "Facilities: Swimming pool, Gym, Parking")
    p.drawString(100, 690, "Amenities: Shopping mall nearby, Schools in vicinity")
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer


@pytest.fixture
def temp_chromadb_dir():
    """Create a temporary ChromaDB directory for testing"""
    temp_dir = tempfile.mkdtemp()
    original_path = settings.CHROMA_PERSIST_DIRECTORY
    settings.CHROMA_PERSIST_DIRECTORY = Path(temp_dir)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    settings.CHROMA_PERSIST_DIRECTORY = original_path


@pytest.fixture(autouse=True)
def reset_chroma_service():
    """Reset ChromaDB service instance before each test"""
    from services import chromadb_service
    chromadb_service._chroma_service_instance = None
    yield
    chromadb_service._chroma_service_instance = None

