"""
Django management command to reset database and create default admin user
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Resets the database and creates default admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-data',
            action='store_true',
            help='Keep existing data (only create admin user if missing)',
        )

    def handle(self, *args, **options):
        keep_data = options.get('keep_data', False)
        
        if not keep_data:
            self.stdout.write(self.style.WARNING('Resetting database...'))
            
            # Delete all data from models
            from campaigns.models import Campaign, CampaignLead, Conversation
            from leads.models import Lead
            
            # Try to import Document model (may not exist)
            try:
                from documents.models import Document
                Document.objects.all().delete()
            except (ImportError, AttributeError):
                pass
            
            # Delete in correct order (respecting foreign keys)
            Conversation.objects.all().delete()
            CampaignLead.objects.all().delete()
            Campaign.objects.all().delete()
            Lead.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('✓ Database tables cleared'))
            
            # Clear ChromaDB data
            from django.conf import settings
            import shutil
            chroma_path = settings.CHROMA_PERSIST_DIRECTORY
            if os.path.exists(chroma_path):
                try:
                    shutil.rmtree(chroma_path)
                    os.makedirs(chroma_path, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS('✓ ChromaDB data cleared'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not clear ChromaDB: {e}'))
        else:
            self.stdout.write(self.style.NOTICE('Keeping existing data...'))
        
        # Create or update admin user
        self.stdout.write('Creating default admin user...')
        
        # Delete existing admin users
        User.objects.filter(username='admin').delete()
        User.objects.filter(email='admin@admin.com').delete()
        
        # Create new admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@admin.com',
            password='admin@123'
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Admin user created: {admin_user.email}'))
        self.stdout.write(self.style.SUCCESS('  Username: admin'))
        self.stdout.write(self.style.SUCCESS('  Email: admin@admin.com'))
        self.stdout.write(self.style.SUCCESS('  Password: admin@123'))

